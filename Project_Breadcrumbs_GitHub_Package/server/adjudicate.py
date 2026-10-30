#!/usr/bin/env python3
"""Project Breadcrumbs — adjudication.

Two different reviews happen here, and they are kept apart on purpose.

**Event adjudication** (PRE_REGISTRATION_ANALYSIS_PLAN §6) classifies a
movement-event sequence as removal, handling or indeterminate from telemetry
alone. Two reviewers decide independently; a disagreement goes to a third and
the rule applied is recorded. This path never touches an image, and a reviewer
who has already looked at the frames is refused, because §6 requires the
classification to rest on telemetry alone so that it survives for modules whose
images were never recovered — which is the case that actually matters.

**Image adjudication** (D-52, DATA_PROTECTION_CONTROLS §11) is the opposite:
somebody has to look. A frame that appears to depict a minor, or a person with
no connection to the opening, is withheld; age is estimated from appearance and
the rule errs toward withholding. A withheld frame is access-restricted, kept
only until the adjudication record is written, then deleted. What survives is
the hash, the category, the reviewers and the date.

Neither review belongs in ingest, and publish.py never decides anything. It
only asks whether somebody with the authority to look has already said so.

Usage:
    ADJUDICATORS=alice,bob python3 adjudicate.py pending
    ... show RECORD_ID --reviewer alice
    ... decide-event RECORD_ID --reviewer alice --outcome removal
    ... view-images RECORD_ID --reviewer alice --out review/
    ... decide-image RECORD_ID --reviewer alice --decision withhold --category minor
    ... status
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
from contextlib import contextmanager
from datetime import date, datetime, timezone

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

# DATA_MODEL §3. These are the only values validation_status may hold.
STATUS_UNREVIEWED = "unreviewed"
STATUS_REVIEWED = "reviewed"
STATUS_FALSE_TRIGGER = "false_trigger"
STATUS_INDETERMINATE = "indeterminate"

VALID_STATUSES = (STATUS_UNREVIEWED, STATUS_REVIEWED, STATUS_FALSE_TRIGGER,
                  STATUS_INDETERMINATE)

# PRE_REGISTRATION_ANALYSIS_PLAN §6. Three outcome classes for an event; a
# false trigger is the fourth thing a reviewer needs to be able to say.
EVENT_OUTCOMES = ("removal", "handling", "indeterminate", "false_trigger")

OUTCOME_TO_STATUS = {
    "removal": STATUS_REVIEWED,
    "handling": STATUS_REVIEWED,
    "false_trigger": STATUS_FALSE_TRIGGER,
    "indeterminate": STATUS_INDETERMINATE,
}

# D-52. The categories are the published breakdown, so they are fixed here
# rather than typed freely at review time.
IMAGE_DECISIONS = ("publish", "withhold")
WITHHOLD_CATEGORIES = ("minor", "unconnected")

SCHEMA = """
CREATE TABLE IF NOT EXISTS adjudications (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id        TEXT NOT NULL,
    kind             TEXT NOT NULL,
    reviewer         TEXT NOT NULL,
    outcome          TEXT,
    decision         TEXT,
    category         TEXT,
    rationale        TEXT,
    image_hashes     TEXT,
    legal_hold_until TEXT,
    decided_at       TEXT NOT NULL,
    UNIQUE(record_id, kind, reviewer)
);

CREATE INDEX IF NOT EXISTS idx_adj_record ON adjudications(record_id, kind);
"""


class AdjudicationError(Exception):
    pass


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Adjudicator:
    """Adjudication against an existing ingest data directory.

    `allowed_reviewers` is the access restriction from DATA_PROTECTION_CONTROLS
    §1: only named individuals may view captured images. A caller that passes
    None can record event verdicts but cannot view an image, because there is
    no list saying who is permitted.
    """

    def __init__(self, data_dir: str, allowed_reviewers=None):
        self.data_dir = os.path.abspath(data_dir)
        self.image_dir = os.path.join(self.data_dir, "images")
        self.db_path = os.path.join(self.data_dir, "records.db")
        if not os.path.exists(self.db_path):
            raise AdjudicationError(f"no database at {self.db_path}")
        self.allowed_reviewers = (
            None if allowed_reviewers is None else set(allowed_reviewers))
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    # -- plumbing ---------------------------------------------------------

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _log(self, conn, kind: str, detail: dict) -> None:
        # Reuses the ingest audit table rather than inventing a second log.
        conn.execute(
            "INSERT INTO ingest_log (at, kind, detail) VALUES (?,?,?)",
            (utcnow(), kind, json.dumps(detail, sort_keys=True)))

    def _check_reviewer(self, name: str, *, viewing: bool = False) -> str:
        name = (name or "").strip()
        if not name or len(name) > 64:
            raise AdjudicationError("a reviewer name is required")
        if viewing:
            if self.allowed_reviewers is None:
                raise AdjudicationError(
                    "no reviewer allowlist is configured; image access is "
                    "restricted to named individuals (DATA_PROTECTION §1)")
            if name not in self.allowed_reviewers:
                raise AdjudicationError(
                    f"{name!r} is not on the reviewer allowlist")
        return name

    # -- reading ----------------------------------------------------------

    def pending(self, limit: int = 50):
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT e.record_id, e.event_type, e.sensor_ts,
                          e.received_timestamp, e.frame_count,
                          e.validation_status,
                          (SELECT COUNT(*) FROM images i
                            WHERE i.record_id = e.record_id) AS frames_held,
                          (SELECT COUNT(*) FROM adjudications a
                            WHERE a.record_id = e.record_id
                              AND a.kind = 'event') AS event_votes,
                          (SELECT COUNT(*) FROM adjudications a
                            WHERE a.record_id = e.record_id
                              AND a.kind = 'image') AS image_decisions
                     FROM events e
                    WHERE e.validation_status = ?
                       OR (SELECT COUNT(*) FROM adjudications a
                            WHERE a.record_id = e.record_id
                              AND a.kind = 'image') = 0
                    ORDER BY e.received_timestamp
                    LIMIT ?""",
                (STATUS_UNREVIEWED, limit)).fetchall()
        return [dict(r) for r in rows]

    def telemetry(self, record_id: str) -> dict:
        """Everything a reviewer may see when classifying an event.

        Deliberately excludes image references: §6 requires the classification
        to be possible without them, and to remain possible for modules whose
        images were never recovered.
        """
        with self._conn() as conn:
            row = conn.execute(
                "SELECT record_id, module_id, deployment_id, event_type,"
                " sensor_ts, clock_synced, clock_uncertainty_s,"
                " received_timestamp, battery_mv, frame_count, flags, lux,"
                " location_valid, lat, lon, loc_method, loc_accuracy_m,"
                " validation_status FROM events WHERE record_id=?",
                (record_id,)).fetchone()
            if row is None:
                raise AdjudicationError(f"unknown record_id {record_id!r}")
            held = conn.execute(
                "SELECT COUNT(*) c FROM images WHERE record_id=?",
                (record_id,)).fetchone()["c"]
        out = dict(row)
        out["frames_on_disk"] = held
        return out

    # -- event adjudication ----------------------------------------------

    def vote_event(self, record_id: str, reviewer: str, outcome: str,
                   rationale: str | None = None) -> dict:
        reviewer = self._check_reviewer(reviewer)
        if outcome not in EVENT_OUTCOMES:
            raise AdjudicationError(
                f"outcome must be one of {', '.join(EVENT_OUTCOMES)}")

        with self._conn() as conn:
            # §6: the classification must rest on telemetry alone. A reviewer
            # who has opened the frames is not a valid telemetry reader.
            if conn.execute(
                    "SELECT 1 FROM ingest_log WHERE kind='image_access'"
                    " AND detail LIKE ? AND detail LIKE ?",
                    (f'%"{record_id}"%', f'%"{reviewer}"%')).fetchone():
                raise AdjudicationError(
                    f"{reviewer!r} has already viewed the images for "
                    f"{record_id}; event adjudication must be blind to them")

            conn.execute(
                """INSERT INTO adjudications
                       (record_id, kind, reviewer, outcome, rationale, decided_at)
                   VALUES (?, 'event', ?, ?, ?, ?)
                   ON CONFLICT(record_id, kind, reviewer) DO UPDATE SET
                       outcome=excluded.outcome,
                       rationale=excluded.rationale,
                       decided_at=excluded.decided_at""",
                (record_id, reviewer, outcome, rationale, utcnow()))

            resolution = self._resolve(conn, record_id)
            self._log(conn, "event_adjudicated", {
                "record_id": record_id, "reviewer": reviewer,
                "outcome": outcome, "state": resolution["state"]})

        self._write_status(record_id, resolution["status"])
        return resolution

    def _resolve(self, conn, record_id: str) -> dict:
        votes = conn.execute(
            "SELECT reviewer, outcome FROM adjudications"
            " WHERE record_id=? AND kind='event' ORDER BY id",
            (record_id,)).fetchall()
        votes = [dict(v) for v in votes]

        if not votes:
            return {"state": "unreviewed", "status": STATUS_UNREVIEWED,
                    "votes": votes}
        if len(votes) == 1:
            # One reviewer is an opinion, not a classification.
            return {"state": "awaiting_second", "status": STATUS_UNREVIEWED,
                    "votes": votes}

        outcomes = {v["outcome"] for v in votes}
        if len(outcomes) == 1:
            outcome = votes[0]["outcome"]
            return {"state": "resolved", "status": OUTCOME_TO_STATUS[outcome],
                    "votes": votes, "decided_outcome": outcome}

        if len(votes) >= 3:
            # The third reviewer decides, and their verdict is the one applied.
            outcome = votes[-1]["outcome"]
            return {"state": "resolved_by_third",
                    "status": OUTCOME_TO_STATUS[outcome],
                    "votes": votes, "decided_outcome": outcome}

        # Disagreement without a third is retained as indeterminate rather than
        # forced into one class (§6).
        return {"state": "needs_third",
                "status": STATUS_INDETERMINATE,
                "votes": votes, "decided_outcome": None}

    def _write_status(self, record_id: str, status: str) -> None:
        if status not in VALID_STATUSES:
            raise AdjudicationError(f"refusing to write unknown status {status!r}")
        with self._conn() as conn:
            conn.execute(
                "UPDATE events SET validation_status=? WHERE record_id=?",
                (status, record_id))

    # -- image adjudication ----------------------------------------------

    def view_images(self, record_id: str, reviewer: str, out_dir: str):
        reviewer = self._check_reviewer(reviewer, viewing=True)

        with self._conn() as conn:
            rows = conn.execute(
                "SELECT frame_index, secure_object_ref, integrity_hash"
                " FROM images WHERE record_id=? ORDER BY frame_index",
                (record_id,)).fetchall()
            rows = [dict(r) for r in rows]
            self._log(conn, "image_access", {
                "record_id": record_id, "reviewer": reviewer,
                "frames": [r["frame_index"] for r in rows]})

        os.makedirs(out_dir, exist_ok=True)
        written = []
        for r in rows:
            src = os.path.join(self.image_dir, r["secure_object_ref"])
            if not r["secure_object_ref"] or not os.path.exists(src):
                continue
            dst = os.path.join(out_dir,
                               f"{record_id}_{r['frame_index']:02d}.jpg")
            shutil.copyfile(src, dst)
            written.append(dst)
        return written

    def decide_image(self, record_id: str, reviewer: str, decision: str,
                     category: str | None = None,
                     rationale: str | None = None,
                     legal_hold_until: str | None = None) -> dict:
        reviewer = self._check_reviewer(reviewer, viewing=True)
        if decision not in IMAGE_DECISIONS:
            raise AdjudicationError(
                f"decision must be one of {', '.join(IMAGE_DECISIONS)}")
        if decision == "withhold" and category not in WITHHOLD_CATEGORIES:
            raise AdjudicationError(
                f"a withheld image needs a category: "
                f"{', '.join(WITHHOLD_CATEGORIES)}")
        if decision == "publish":
            category = None
        if legal_hold_until:
            try:
                date.fromisoformat(legal_hold_until)
            except ValueError:
                raise AdjudicationError(
                    "legal hold needs a date (YYYY-MM-DD); an open-ended hold "
                    "is how deletion quietly stops happening")

        with self._conn() as conn:
            hashes = [r["integrity_hash"] for r in conn.execute(
                "SELECT integrity_hash FROM images WHERE record_id=?",
                (record_id,)).fetchall()]

            conn.execute(
                """INSERT INTO adjudications
                       (record_id, kind, reviewer, decision, category,
                        rationale, image_hashes, legal_hold_until, decided_at)
                   VALUES (?, 'image', ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(record_id, kind, reviewer) DO UPDATE SET
                       decision=excluded.decision,
                       category=excluded.category,
                       rationale=excluded.rationale,
                       image_hashes=excluded.image_hashes,
                       legal_hold_until=excluded.legal_hold_until,
                       decided_at=excluded.decided_at""",
                (record_id, reviewer, decision, category, rationale,
                 json.dumps(hashes), legal_hold_until, utcnow()))

            self._log(conn, "image_adjudicated", {
                "record_id": record_id, "reviewer": reviewer,
                "decision": decision, "category": category,
                "legal_hold_until": legal_hold_until})

        destroyed = 0
        if decision == "withhold":
            destroyed = self._destroy(record_id, legal_hold_until, reviewer)

        return {"record_id": record_id, "decision": decision,
                "category": category, "images_destroyed": destroyed,
                "hashes_retained": len(hashes)}

    def _destroy(self, record_id: str, hold_until: str | None,
                 reviewer: str) -> int:
        """D-52: a withheld frame lives only until its record is written."""
        if hold_until:
            try:
                if date.fromisoformat(hold_until) >= date.today():
                    with self._conn() as conn:
                        self._log(conn, "image_destruction_suspended", {
                            "record_id": record_id, "reviewer": reviewer,
                            "legal_hold_until": hold_until})
                    return 0
            except ValueError:
                raise AdjudicationError("invalid legal hold date")

        with self._conn() as conn:
            rows = conn.execute(
                "SELECT frame_index, secure_object_ref FROM images"
                " WHERE record_id=?", (record_id,)).fetchall()

        removed = 0
        for r in rows:
            ref = r["secure_object_ref"]
            if not ref:
                continue
            path = os.path.join(self.image_dir, ref)
            try:
                os.remove(path)
                removed += 1
            except FileNotFoundError:
                pass

        with self._conn() as conn:
            # The row survives with its hash so the audit trail keeps saying a
            # frame existed; only the pixels are gone.
            conn.execute(
                "UPDATE images SET secure_object_ref='' WHERE record_id=?",
                (record_id,))
            self._log(conn, "image_destroyed", {
                "record_id": record_id, "frames": removed})
        return removed

    # -- summary ----------------------------------------------------------

    def status(self) -> dict:
        with self._conn() as conn:
            by_status = {r["validation_status"]: r["c"] for r in conn.execute(
                "SELECT validation_status, COUNT(*) c FROM events"
                " GROUP BY validation_status").fetchall()}
            withheld = {r["category"]: r["c"] for r in conn.execute(
                "SELECT category, COUNT(*) c FROM adjudications"
                " WHERE kind='image' AND decision='withhold'"
                " GROUP BY category").fetchall()}
            published = conn.execute(
                "SELECT COUNT(*) c FROM adjudications"
                " WHERE kind='image' AND decision='publish'").fetchone()["c"]
            images_held = conn.execute(
                "SELECT COUNT(*) c FROM images WHERE secure_object_ref != ''"
            ).fetchone()["c"]
        return {"by_status": by_status, "withheld_by_category": withheld,
                "image_publish_decisions": published,
                "images_held": images_held}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _adjudicator() -> Adjudicator:
    reviewers = os.environ.get("ADJUDICATORS", "")
    allowed = {r.strip() for r in reviewers.split(",") if r.strip()} or None
    data_dir = os.environ.get("INGEST_DATA", "data")
    return Adjudicator(data_dir, allowed_reviewers=allowed)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Project Breadcrumbs adjudication")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("pending", help="records awaiting review")
    p.add_argument("--limit", type=int, default=50)

    p = sub.add_parser("show", help="telemetry for one record (never images)")
    p.add_argument("record_id")

    p = sub.add_parser("view-images", help="copy frames out for review")
    p.add_argument("record_id")
    p.add_argument("--reviewer", required=True)
    p.add_argument("--out", default="review")

    p = sub.add_parser("decide-event", help="classify an event from telemetry")
    p.add_argument("record_id")
    p.add_argument("--reviewer", required=True)
    p.add_argument("--outcome", required=True, choices=EVENT_OUTCOMES)
    p.add_argument("--rationale")

    p = sub.add_parser("decide-image", help="publish or withhold the frames")
    p.add_argument("record_id")
    p.add_argument("--reviewer", required=True)
    p.add_argument("--decision", required=True, choices=IMAGE_DECISIONS)
    p.add_argument("--category", choices=WITHHOLD_CATEGORIES)
    p.add_argument("--rationale")
    p.add_argument("--legal-hold-until")

    sub.add_parser("status", help="counts by status and category")

    args = ap.parse_args(argv)

    try:
        adj = _adjudicator()

        if args.cmd == "pending":
            rows = adj.pending(args.limit)
            if not rows:
                print("nothing awaiting review")
            for r in rows:
                print(f"{r['record_id']}  {r['event_type']:<22} "
                      f"frames={r['frames_held']} "
                      f"event_votes={r['event_votes']} "
                      f"image_decisions={r['image_decisions']}  "
                      f"{r['received_timestamp']}")

        elif args.cmd == "show":
            for k, v in adj.telemetry(args.record_id).items():
                print(f"{k:<20} {v}")

        elif args.cmd == "view-images":
            files = adj.view_images(args.record_id, args.reviewer, args.out)
            print(f"wrote {len(files)} frame(s) to {args.out}")
            print("access to this record is now logged against "
                  f"{args.reviewer}; they can no longer adjudicate its event")

        elif args.cmd == "decide-event":
            res = adj.vote_event(args.record_id, args.reviewer,
                                 args.outcome, args.rationale)
            print(f"state={res['state']} validation_status={res['status']} "
                  f"votes={len(res['votes'])}")

        elif args.cmd == "decide-image":
            res = adj.decide_image(
                args.record_id, args.reviewer, args.decision,
                category=args.category, rationale=args.rationale,
                legal_hold_until=args.legal_hold_until)
            print(f"{res['decision']} {res['record_id']}"
                  f"({res['category'] or 'publishable'}); "
                  f"{res['images_destroyed']} frame(s) destroyed, "
                  f"{res['hashes_retained']} hash(es) retained")

        elif args.cmd == "status":
            s = adj.status()
            print("by validation_status:")
            for k, v in sorted(s["by_status"].items()):
                print(f"  {k:<16} {v}")
            print("image decisions:")
            print(f"  publish         {s['image_publish_decisions']}")
            for k, v in sorted(s["withheld_by_category"].items()):
                print(f"  withheld({k}){' ' * max(0, 3 - len(k))} {v}")
            print(f"  frames on disk  {s['images_held']}")

    except AdjudicationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
