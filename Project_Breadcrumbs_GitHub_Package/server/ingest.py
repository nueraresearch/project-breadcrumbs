#!/usr/bin/env python3
"""Project Breadcrumbs — record ingest endpoint.

Accepts the JSON records and JPEG frames the monitoring module produces,
validates them against docs/data/DATA_MODEL.md, and stores them.

Standard library only, by design. The pilot ingests a few hundred records over
90 days, so a dependency-free service is easier to audit, easier to run on a
borrowed machine, and has no lockfile to rot.

There is deliberately **no endpoint that causes a device to do anything**.
HW-30 requires that no command path can initiate imaging. The simplest way to
honour that on the server is to have no such path at all — not a disabled one,
not an authenticated one, none.

Run:
    INGEST_TOKEN=... python3 ingest.py --port 8787 --data-dir data
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import re
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# DATA_MODEL §3. Kept in step with firmware/include/records.h.
EVENT_TYPES = frozenset({
    "LIGHT_TRIGGER",
    "MOVEMENT_EVENT",
    "LOCATION_FIX",
    "IMAGE_CAPTURE_COMPLETE",
    "IMAGE_CAPTURE_PARTIAL",
    "LOW_BATTERY",
    "POWER_RESET",
    "SYNC_SUCCESS",
    "SYNC_FAILURE",
    "MODULE_RECOVERED",
    "DEPLOYMENT_CLOSED",
})

# Strict because these values become filenames and SQL parameters.
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

MAX_RECORD_BYTES = 256 * 1024
MAX_IMAGE_BYTES = 4 * 1024 * 1024
JPEG_MAGIC = b"\xff\xd8\xff"
JPEG_EOI = b"\xff\xd9"

SCHEMA = """
CREATE TABLE IF NOT EXISTS modules (
    module_id         TEXT PRIMARY KEY,
    hardware_revision TEXT,
    firmware_revision TEXT,
    status            TEXT DEFAULT 'available',
    created_at        TEXT
);

CREATE TABLE IF NOT EXISTS deployments (
    deployment_id       TEXT PRIMARY KEY,
    module_id           TEXT,
    participant_code    TEXT,
    site_code           TEXT,
    start_timestamp     TEXT,
    end_timestamp       TEXT,
    status              TEXT,
    outcome_state       TEXT,
    location_record_ref TEXT
);

-- One row per ingested event. record_id is globally unique and survives module
-- reuse (DATA_MODEL §2), so it is the natural primary key.
CREATE TABLE IF NOT EXISTS events (
    record_id           TEXT PRIMARY KEY,
    module_id           TEXT NOT NULL,
    deployment_id       TEXT,
    event_type          TEXT NOT NULL,
    sensor_ts           INTEGER,
    clock_synced        INTEGER NOT NULL,
    clock_uncertainty_s INTEGER,
    received_timestamp  TEXT NOT NULL,
    battery_mv          INTEGER,
    frame_count         INTEGER,
    flags               INTEGER,
    lux                 REAL,
    location_valid      INTEGER,
    lat                 REAL,
    lon                 REAL,
    loc_method          INTEGER,
    loc_accuracy_m      INTEGER,
    validation_status   TEXT DEFAULT 'unreviewed'
);

CREATE INDEX IF NOT EXISTS idx_events_deployment ON events(deployment_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);

-- Images are keyed by (record_id, frame) rather than by event row, so a frame
-- that arrives before its record is still stored and links up afterwards.
CREATE TABLE IF NOT EXISTS images (
    record_id         TEXT NOT NULL,
    frame_index       INTEGER NOT NULL,
    image_id          TEXT NOT NULL,
    secure_object_ref TEXT NOT NULL,
    integrity_hash    TEXT NOT NULL,
    access_class      TEXT DEFAULT 'restricted',
    bytes             INTEGER NOT NULL,
    uploaded_at       TEXT NOT NULL,
    PRIMARY KEY (record_id, frame_index)
);

CREATE TABLE IF NOT EXISTS ingest_log (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    at     TEXT NOT NULL,
    kind   TEXT NOT NULL,
    detail TEXT
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def is_num(v) -> bool:
    return (isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(v))


# ---------------------------------------------------------------------------
# Validation — the contract with the firmware
# ---------------------------------------------------------------------------

def validate_record(rec) -> list[str]:
    """Returns a list of human-readable errors. Empty list means valid."""
    errors: list[str] = []

    if not isinstance(rec, dict):
        return ["record is not a JSON object"]

    for field, maxlen in (("record_id", 64), ("module_id", 32),
                          ("deployment_id", 32)):
        v = rec.get(field)
        if not isinstance(v, str) or not v:
            errors.append(f"{field}: required string")
        elif len(v) > maxlen:
            errors.append(f"{field}: longer than {maxlen} characters")
        elif not ID_RE.match(v):
            errors.append(f"{field}: only A-Z a-z 0-9 _ - are allowed")

    if rec.get("event_type") not in EVENT_TYPES:
        errors.append("event_type: not in the documented taxonomy")

    ts = rec.get("sensor_ts")
    if not is_int(ts):
        errors.append("sensor_ts: required integer seconds")
        ts = None
    elif ts < 0:
        errors.append("sensor_ts: must not be negative")

    synced = rec.get("clock_synced")
    if not isinstance(synced, bool):
        errors.append("clock_synced: required boolean")

    unc = rec.get("clock_uncertainty_s")
    if not is_int(unc) or not (0 <= unc <= 86400):
        errors.append("clock_uncertainty_s: integer 0..86400")

    # The firmware sends 0 when it has never synced. That is not an epoch
    # timestamp, and treating it as one would place every pre-sync event in 1970.
    if ts == 0 and synced is True:
        errors.append("clock_synced: true with sensor_ts 0 is contradictory")

    bmv = rec.get("battery_mv")
    if bmv is not None and (not is_int(bmv) or not (0 <= bmv <= 6000)):
        errors.append("battery_mv: integer 0..6000")

    fc = rec.get("frame_count")
    if fc is not None and (not is_int(fc) or not (0 <= fc <= 3)):
        errors.append("frame_count: integer 0..3")

    fl = rec.get("flags")
    if fl is not None and (not is_int(fl) or not (0 <= fl <= 255)):
        errors.append("flags: integer 0..255")

    lux = rec.get("lux")
    if lux is not None and (not is_num(lux) or lux < 0 or lux > 200000):
        errors.append("lux: finite 0..200000")

    loc = rec.get("location")
    if loc is not None:
        if not isinstance(loc, dict):
            errors.append("location: must be an object")
        else:
            valid = loc.get("valid")
            if not isinstance(valid, bool):
                errors.append("location.valid: required boolean")
            elif valid:
                lat, lon = loc.get("lat"), loc.get("lon")
                if not is_num(lat) or not (-90 <= lat <= 90):
                    errors.append("location.lat: -90..90")
                if not is_num(lon) or not (-180 <= lon <= 180):
                    errors.append("location.lon: -180..180")
                if loc.get("method") not in (1, 2):
                    errors.append("location.method: 1 (GNSS) or 2 (cell)")
                acc = loc.get("accuracy_m")
                if not is_int(acc) or not (0 <= acc <= 100000):
                    errors.append("location.accuracy_m: integer 0..100000")

    return errors


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

class Store:
    def __init__(self, data_dir: str):
        self.data_dir = os.path.abspath(data_dir)
        self.image_dir = os.path.join(self.data_dir, "images")
        os.makedirs(self.image_dir, exist_ok=True)
        self.db_path = os.path.join(self.data_dir, "records.db")
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    @contextmanager
    def _conn(self):
        """Commits on success, always closes. `with conn:` alone does not close."""
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # -- records ----------------------------------------------------------

    def insert_record(self, rec: dict) -> str:
        """Returns 'stored', 'duplicate', or 'conflict'."""
        loc = rec.get("location") or {}
        valid = bool(loc.get("valid"))
        now = utcnow()

        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO modules"
                "(module_id, status, created_at) VALUES(?,?,?)",
                (rec["module_id"], "available", now))

            if rec.get("deployment_id"):
                conn.execute(
                    "INSERT OR IGNORE INTO deployments"
                    "(deployment_id, module_id, status) VALUES(?,?,?)",
                    (rec["deployment_id"], rec["module_id"], "deployed"))

            cur = conn.execute(
                """INSERT OR IGNORE INTO events (
                       record_id, module_id, deployment_id, event_type,
                       sensor_ts, clock_synced, clock_uncertainty_s,
                       received_timestamp, battery_mv, frame_count, flags, lux,
                       location_valid, lat, lon, loc_method, loc_accuracy_m)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    rec["record_id"], rec["module_id"], rec.get("deployment_id"),
                    rec["event_type"], rec.get("sensor_ts"),
                    1 if rec.get("clock_synced") else 0,
                    rec.get("clock_uncertainty_s"), now,
                    rec.get("battery_mv"), rec.get("frame_count"),
                    rec.get("flags"), rec.get("lux"),
                    1 if valid else 0,
                    loc.get("lat") if valid else None,
                    loc.get("lon") if valid else None,
                    loc.get("method") if valid else None,
                    loc.get("accuracy_m") if valid else None,
                ))

            if cur.rowcount == 1:
                return "stored"

            # Already present. Identical re-uploads are expected: the device
            # retries until it sees a 2xx (HW-08). Different content under the
            # same ID is a real problem and gets its own name.
            existing = conn.execute(
                "SELECT module_id, event_type, sensor_ts FROM events"
                " WHERE record_id=?", (rec["record_id"],)).fetchone()
            same = (existing is not None
                    and existing["module_id"] == rec["module_id"]
                    and existing["event_type"] == rec["event_type"]
                    and existing["sensor_ts"] == rec.get("sensor_ts"))
            return "duplicate" if same else "conflict"

    def get_record(self, record_id: str):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM events WHERE record_id=?", (record_id,)).fetchone()
            if row is None:
                return None
            images = conn.execute(
                "SELECT frame_index, image_id, secure_object_ref, integrity_hash,"
                " bytes FROM images WHERE record_id=? ORDER BY frame_index",
                (record_id,)).fetchall()
        out = dict(row)
        out["images"] = [dict(i) for i in images]
        return out

    # -- images -----------------------------------------------------------

    def store_image(self, record_id: str, frame: int, blob: bytes) -> str:
        """Writes the frame atomically and records its hash. Returns the hash."""
        digest = hashlib.sha256(blob).hexdigest()
        name = f"{record_id}_{frame:02d}.jpg"
        final = os.path.join(self.image_dir, name)

        # Write to a temp file in the same directory, then rename: a crash
        # mid-write must not leave a truncated JPEG that looks valid.
        fd, tmp = tempfile.mkstemp(dir=self.image_dir, suffix=".part")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(blob)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, final)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO images
                   (record_id, frame_index, image_id, secure_object_ref,
                    integrity_hash, bytes, uploaded_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (record_id, frame, f"{record_id}-{frame}", name, digest,
                 len(blob), utcnow()))
        return digest

    # -- health -----------------------------------------------------------

    def counts(self) -> dict:
        with self._conn() as conn:
            records = conn.execute("SELECT COUNT(*) c FROM events").fetchone()["c"]
            images = conn.execute("SELECT COUNT(*) c FROM images").fetchone()["c"]
        return {"records": records, "images": images}


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

IMAGE_PATH_RE = re.compile(r"^/v1/records/([^/]+)/images/(\d+)$")
RECORD_PATH_RE = re.compile(r"^/v1/records/([^/]+)$")


class Handler(BaseHTTPRequestHandler):
    server_version = "breadcrumbs-ingest/0.1"
    protocol_version = "HTTP/1.1"

    # Records carry volunteer location, so nothing about a request body is
    # logged. Even the path is suppressed unless explicitly asked for.
    def log_message(self, fmt, *args):
        if os.environ.get("INGEST_VERBOSE"):
            super().log_message(fmt, *args)

    # -- helpers ----------------------------------------------------------

    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        # Closing beats keep-alive here: error responses are sent before the
        # request body is always consumed, and a reused connection would then
        # be misaligned. A device uploads a few times a day, so the cost is nil.
        self.send_header("Connection", "close")
        self.close_connection = True
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, payload) -> None:
        self._send(status, json.dumps(payload).encode("utf-8"),
                   "application/json")

    def _authorized(self) -> bool:
        token = getattr(self.server, "token", None)
        if not token:
            return True
        header = self.headers.get("Authorization", "")
        return hmac.compare_digest(header, f"Bearer {token}")

    def _read_body(self, limit: int):
        """Returns (bytes, None) or (None, (status, message))."""
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None, (400, "invalid Content-Length")
        if length <= 0:
            return None, (400, "empty body")
        if length > limit:
            return None, (413, f"body exceeds {limit} bytes")
        return self.rfile.read(length), None

    # -- routes -----------------------------------------------------------

    def do_GET(self):
        if not self._authorized():
            return self._json(401, {"error": "unauthorized"})

        path = urlparse(self.path).path

        if path == "/healthz":
            return self._json(200, {"status": "ok", **self.server.store.counts()})

        m = RECORD_PATH_RE.match(path)
        if m:
            rec = self.server.store.get_record(m.group(1))
            if rec is None:
                return self._json(404, {"error": "unknown record_id"})
            return self._json(200, rec)

        return self._json(404, {"error": "not_found"})

    def do_POST(self):
        if not self._authorized():
            return self._json(401, {"error": "unauthorized"})

        path = urlparse(self.path).path

        if path == "/v1/records":
            return self._post_records()

        m = IMAGE_PATH_RE.match(path)
        if m:
            return self._post_image(m.group(1), int(m.group(2)))

        return self._json(404, {"error": "not_found"})

    def _post_records(self):
        body, err = self._read_body(MAX_RECORD_BYTES)
        if err:
            return self._json(err[0], {"error": err[1]})

        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return self._json(400, {"error": f"invalid JSON: {exc}"})

        records = payload if isinstance(payload, list) else [payload]
        if not records:
            return self._json(400, {"error": "no records in body"})

        accepted = duplicates = conflicts = 0
        rejected = []

        for rec in records:
            errors = validate_record(rec)
            if errors:
                rejected.append({
                    "record_id": rec.get("record_id") if isinstance(rec, dict) else None,
                    "errors": errors,
                })
                continue
            outcome = self.server.store.insert_record(rec)
            if outcome == "stored":
                accepted += 1
            elif outcome == "duplicate":
                duplicates += 1
            else:
                conflicts += 1
                rejected.append({
                    "record_id": rec["record_id"],
                    "errors": ["record_id already exists with different content"],
                })

        result = {
            "accepted": accepted,
            "duplicates": duplicates,
            "conflicts": conflicts,
            "rejected": rejected,
        }
        status = 200 if (accepted or duplicates) else 400
        self._json(status, result)

    def _post_image(self, record_id: str, frame: int):
        # Checked before the value is used as a filename (path traversal).
        if not ID_RE.match(record_id):
            return self._json(400, {"error": "invalid record_id"})
        if not (1 <= frame <= 3):
            return self._json(400, {"error": "frame must be 1, 2 or 3"})

        body, err = self._read_body(MAX_IMAGE_BYTES)
        if err:
            return self._json(err[0], {"error": err[1]})

        if not body.startswith(JPEG_MAGIC):
            return self._json(415, {"error": "not a JPEG"})
        if not body.endswith(JPEG_EOI):
            # Truncated uploads happen on a marginal link; refusing them here
            # is better than storing a file that will not open later.
            return self._json(400, {"error": "JPEG appears truncated"})

        digest = self.server.store.store_image(record_id, frame, body)
        return self._json(201, {
            "record_id": record_id,
            "frame_index": frame,
            "bytes": len(body),
            "sha256": digest,
        })


def create_server(host: str, port: int, data_dir: str, token=None):
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.store = Store(data_dir)
    httpd.token = token
    return httpd


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Project Breadcrumbs ingest")
    ap.add_argument("--host", default=os.environ.get("INGEST_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int,
                    default=int(os.environ.get("INGEST_PORT", "8787")))
    ap.add_argument("--data-dir", default=os.environ.get("INGEST_DATA", "data"))
    args = ap.parse_args(argv)

    token = os.environ.get("INGEST_TOKEN")
    if not token:
        print("warning: INGEST_TOKEN is not set; the endpoint accepts "
              "unauthenticated writes", file=sys.stderr)

    httpd = create_server(args.host, args.port, args.data_dir, token)
    host, port = httpd.server_address[:2]
    print(f"listening on http://{host}:{port}  "
          f"data={os.path.abspath(args.data_dir)}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
