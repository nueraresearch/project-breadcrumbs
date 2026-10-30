#!/usr/bin/env python3
"""Project Breadcrumbs — the release step.

Takes stored records and images and emits a publishable copy. Everything in
here exists to honour three decisions:

  D-41  published location is reduced in precision and delayed, because a
        precise coordinate identifies the volunteer's home rather than the
        subject.
  D-42  captions say the package was opened, never that a theft occurred; no
        names, no identification requests, no guilt framing.
  D-52  images that appear to depict a minor, or a person with no connection
        to the opening, are never published. The number withheld is published
        by category.

The design principle is that this step is a whitelist, not a filter. Nothing
is published unless it appears in OUTPUT_FIELDS below. A column added to the
database later cannot leak by default.

It also fails closed:

  - no raw coordinates are ever written, at any setting
  - an image is not released unless its record has been adjudicated, because
    D-52 requires a human to have looked at it first
  - deployment identifiers are replaced by a keyed hash, so events can be
    grouped by deployment without naming a household
  - the run aborts if no salt is supplied, rather than falling back to plain
    identifiers

Usage:
    PUBLISH_SALT=... python3 publish.py --data-dir data --out published
    python3 publish.py --help
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

POLICY_VERSION = "1.0"

# D-41 requires delay; it does not fix a figure. Until the owner sets one this
# is a placeholder, and the manifest records it so a published bundle always
# states which delay produced it.
DEFAULT_DELAY_DAYS = 30

# No latitude or longitude is published, ever. Distance is published as a
# coarse bucket instead, which answers the displacement question without
# saying where a volunteer lives.
DISPLACEMENT_BUCKETS = [
    (0.25, "under 250 m"),
    (1.0, "250 m to 1 km"),
    (5.0, "1 km to 5 km"),
    (float("inf"), "over 5 km"),
]

# Every field that may reach the output. Anything not listed is dropped, which
# is the whole safety property of this module.
OUTPUT_FIELDS = (
    "record_id",
    "event_type",
    "sensor_ts",
    "clock_synced",
    "clock_uncertainty_s",
    "battery_mv",
    "frame_count",
    "flags",
    "caption",
    "deployment_key",
    "displacement_bucket",
    "displacement_km",
)

# D-42: the wording is fixed, not generated. A caption that describes a theft
# would prejudice a person who merely opened a misdelivered parcel.
CAPTIONS = {
    "LIGHT_TRIGGER": "A package was opened.",
    "IMAGE_CAPTURE_COMPLETE":
        "A package was opened; three still images were recorded.",
    "IMAGE_CAPTURE_PARTIAL":
        "A package was opened; fewer than three still images were recorded.",
    "MOVEMENT_EVENT": "A monitored package was moved.",
    "LOCATION_FIX": "A location observation was recorded.",
    "LOW_BATTERY": "The monitoring module reported a low battery.",
    "POWER_RESET": "The monitoring module restarted.",
    "SYNC_SUCCESS": "Stored records were uploaded.",
    "SYNC_FAILURE": "An upload attempt did not complete.",
    "MODULE_RECOVERED": "The monitoring module was returned to the project.",
    "DEPLOYMENT_CLOSED": "A deployment was closed.",
}

# Checked against every caption before it is written. This is a guard against a
# future edit reintroducing accusatory language, not a substitute for review.
BANNED_TERMS = (
    "theft", "stolen", "thief", "thieves", "steal", "stolen from",
    "suspect", "criminal", "guilty", "offender", "culprit",
    "do you know", "identify this", "reward for information",
)

# Adjudication outcomes that suppress an image (D-52).
WITHHELD_PREFIX = "withheld_"


class PublishError(Exception):
    pass


# ---------------------------------------------------------------------------
# Captions
# ---------------------------------------------------------------------------

def caption_for(event_type: str) -> str:
    text = CAPTIONS.get(event_type)
    if text is None:
        # Fail closed: an unclassified event does not get an invented caption.
        raise PublishError(f"no approved caption for event type {event_type!r}")
    return text


def check_caption(text: str) -> None:
    lowered = text.lower()
    for term in BANNED_TERMS:
        if term in lowered:
            raise PublishError(
                f"caption contains banned term {term!r}: {text!r}")


# ---------------------------------------------------------------------------
# JPEG metadata stripping
# ---------------------------------------------------------------------------

def strip_jpeg_metadata(data: bytes) -> bytes:
    """Removes APPn (except JFIF) and COM segments.

    A phone photo carries GPS in APP1; these do not, but the event location
    attached to the record identifies the volunteer's property, so anything
    embedded in the frame is removed rather than trusted (DATA_MODEL §6).
    """
    if not data.startswith(b"\xff\xd8"):
        raise PublishError("not a JPEG")

    out = bytearray(b"\xff\xd8")
    i = 2
    n = len(data)

    while i + 1 < n:
        if data[i] != 0xFF:
            raise PublishError("malformed JPEG: expected marker")

        marker = data[i + 1]

        if marker == 0xD9:                      # EOI
            out += b"\xff\xd9"
            return bytes(out)

        if marker == 0xDA:                      # SOS: entropy data follows
            out += data[i:]
            if not out.endswith(b"\xff\xd9"):
                raise PublishError("malformed JPEG: no EOI")
            return bytes(out)

        # Standalone markers carry no length field.
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            out += data[i:i + 2]
            i += 2
            continue

        if i + 3 >= n:
            raise PublishError("malformed JPEG: truncated segment header")

        seg_len = (data[i + 2] << 8) | data[i + 3]
        if seg_len < 2 or i + 2 + seg_len > n:
            raise PublishError("malformed JPEG: bad segment length")

        # Drop APP1..APP15 and comments; keep JFIF (APP0) and all coding tables.
        drop = (0xE1 <= marker <= 0xEF) or marker == 0xFE
        if not drop:
            out += data[i:i + 2 + seg_len]

        i += 2 + seg_len

    raise PublishError("malformed JPEG: no EOI")


# ---------------------------------------------------------------------------
# Geography
# ---------------------------------------------------------------------------

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def bucket_for(distance_km: float) -> str:
    for limit, label in DISPLACEMENT_BUCKETS:
        if distance_km <= limit:
            return label
    return DISPLACEMENT_BUCKETS[-1][1]


def deployment_displacement(conn, deployment_id: str):
    """Distance between the first and last fix in a deployment.

    Absolute coordinates never leave this function. The distance is rounded to
    100 m, which is coarser than the bucket boundary it feeds.
    """
    rows = conn.execute(
        "SELECT lat, lon, sensor_ts FROM events"
        " WHERE deployment_id=? AND location_valid=1",
        (deployment_id,)).fetchall()

    points = [(r["sensor_ts"] or 0, r["lat"], r["lon"]) for r in rows]
    if len(points) < 2:
        return None, None

    points.sort(key=lambda p: p[0])
    km = haversine_km(points[0][1], points[0][2],
                      points[-1][1], points[-1][2])
    return round(km, 1), bucket_for(km)


# ---------------------------------------------------------------------------
# Publication
# ---------------------------------------------------------------------------

def _parse_ts(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc)


def deployment_key(salt: bytes, deployment_id: str) -> str:
    return hmac.new(salt, deployment_id.encode(), hashlib.sha256).hexdigest()[:16]


def publish(data_dir: str, out_dir: str, salt: bytes, *,
            delay_days: int = DEFAULT_DELAY_DAYS,
            release_images: bool = False,
            now: datetime | None = None) -> dict:
    import sqlite3

    db_path = os.path.join(data_dir, "records.db")
    if not os.path.exists(db_path):
        raise PublishError(f"no database at {db_path}")

    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=delay_days)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    counts = {
        "records_total": 0,
        "records_published": 0,
        "records_withheld_delay": 0,
        "images_published": 0,
        "images_withheld_unadjudicated": 0,
        "images_withheld_by_category": {},
    }

    os.makedirs(out_dir, exist_ok=True)
    image_out = os.path.join(out_dir, "images")
    if release_images:
        os.makedirs(image_out, exist_ok=True)

    records_path = os.path.join(out_dir, "records.jsonl")

    with open(records_path, "w", encoding="utf-8") as fh:
        for row in conn.execute("SELECT * FROM events ORDER BY sensor_ts"):
            counts["records_total"] += 1

            received = _parse_ts(row["received_timestamp"])
            if received > cutoff:
                # D-41: too recent to be safe. Delayed, not redacted away, so
                # it will publish on a later run.
                counts["records_withheld_delay"] += 1
                continue

            caption = caption_for(row["event_type"])
            check_caption(caption)

            distance, bucket = deployment_displacement(
                conn, row["deployment_id"])

            out = {
                "record_id": row["record_id"],
                "event_type": row["event_type"],
                "sensor_ts": row["sensor_ts"],
                "clock_synced": bool(row["clock_synced"]),
                "clock_uncertainty_s": row["clock_uncertainty_s"],
                "battery_mv": row["battery_mv"],
                "frame_count": row["frame_count"],
                "flags": row["flags"],
                "caption": caption,
                "deployment_key": deployment_key(salt, row["deployment_id"] or ""),
                "displacement_bucket": bucket,
                "displacement_km": distance,
            }

            # Belt and braces: the record is built from a whitelist, but assert
            # it so a future edit adding a stray key fails the run.
            for key in out:
                if key not in OUTPUT_FIELDS:
                    raise PublishError(f"unexpected output field {key!r}")

            fh.write(json.dumps(out, sort_keys=True) + "\n")
            counts["records_published"] += 1

            if release_images:
                _publish_images(conn, row, data_dir, image_out, counts)

    manifest = {
        "policy_version": POLICY_VERSION,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "delay_days": delay_days,
        "images_released": release_images,
        "counts": counts,
        "notes": [
            "No latitude or longitude is published at any setting (D-41).",
            "Deployment identifiers are replaced by a keyed hash (D-41).",
            "Captions describe an opening, not a theft (D-42).",
            "Images are released only when adjudicated (D-52).",
        ],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w",
              encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    conn.close()
    return manifest


def _publish_images(conn, row, data_dir, image_out, counts):
    status = (row["validation_status"] or "").strip()

    if status.startswith(WITHHELD_PREFIX):
        category = status[len(WITHHELD_PREFIX):] or "unspecified"
        counts["images_withheld_by_category"][category] = (
            counts["images_withheld_by_category"].get(category, 0) + 1)
        return

    if status != "reviewed":
        # D-52 cannot be honoured without a human decision, so an unadjudicated
        # image is never published. This is the fail-closed branch.
        counts["images_withheld_unadjudicated"] += 1
        return

    images = conn.execute(
        "SELECT frame_index, secure_object_ref FROM images"
        " WHERE record_id=? ORDER BY frame_index",
        (row["record_id"],)).fetchall()

    for img in images:
        src = os.path.join(data_dir, "images", img["secure_object_ref"])
        if not os.path.exists(src):
            continue
        with open(src, "rb") as fh:
            blob = fh.read()
        cleaned = strip_jpeg_metadata(blob)

        name = f"{row['record_id']}_{img['frame_index']:02d}.jpg"
        with open(os.path.join(image_out, name), "wb") as fh:
            fh.write(cleaned)
        counts["images_published"] += 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Publish stored records under D-41, D-42 and D-52.")
    ap.add_argument("--data-dir", default=os.environ.get("INGEST_DATA", "data"))
    ap.add_argument("--out", default="published")
    ap.add_argument("--delay-days", type=int, default=DEFAULT_DELAY_DAYS,
                    help=f"hold records newer than this many days "
                         f"(default {DEFAULT_DELAY_DAYS}; D-41 requires a delay "
                         f"but does not fix the figure)")
    ap.add_argument("--no-images", action="store_true",
                    help="publish event metadata only")
    args = ap.parse_args(argv)

    salt_hex = os.environ.get("PUBLISH_SALT", "")
    if not salt_hex:
        print("error: PUBLISH_SALT is not set. Deployment keys cannot be "
              "computed, and publishing plain identifiers would defeat D-41.",
              file=sys.stderr)
        return 2
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        print("error: PUBLISH_SALT must be hex", file=sys.stderr)
        return 2

    try:
        manifest = publish(args.data_dir, args.out, salt,
                           delay_days=args.delay_days,
                           release_images=not args.no_images)
    except PublishError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    c = manifest["counts"]
    print(f"published {c['records_published']} of {c['records_total']} records "
          f"to {args.out}")
    print(f"  held for delay        {c['records_withheld_delay']}")
    if manifest["images_released"]:
        print(f"  images published      {c['images_published']}")
        print(f"  images unadjudicated  {c['images_withheld_unadjudicated']}")
        for cat, n in sorted(c["images_withheld_by_category"].items()):
            print(f"  withheld ({cat}){' ' * max(0, 9 - len(cat))} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
