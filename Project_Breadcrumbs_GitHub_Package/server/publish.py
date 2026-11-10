#!/usr/bin/env python3
"""Project Breadcrumbs — the release step.

Takes stored records and images and emits a publishable copy. Everything in
here exists to honour three decisions:

  D-41  published location is reduced in precision and delayed, because a
        precise coordinate identifies the volunteer's home rather than the
        subject. D-76 fixes what the reduction is: a published grid cell at a
        resolution stated at release, never a point.
  D-42  captions say the package was opened, never that a theft occurred; no
        names, no identification requests, no guilt framing.
  D-52  images that appear to depict a minor, or a person with no connection
        to the opening, are never published. The number withheld is published
        by category.

The design principle is that this step is a whitelist, not a filter. Nothing
is published unless it appears in OUTPUT_FIELDS below. A column added to the
database later cannot leak by default.

It also fails closed:

  - location is written as a grid cell at a stated resolution, never as a
    coordinate, and the run refuses a resolution finer than the floor
  - an image is not released unless its record has been adjudicated, because
    D-52 requires a human to have looked at it first
  - a stored frame is encrypted at rest, and is decrypted only in memory, so
    a copy of the data directory holds no photographs
  - deployment identifiers are replaced by a keyed hash, so events can be
    grouped by deployment without naming a household
  - the run aborts if no salt is supplied, rather than falling back to plain
    identifiers

Usage:
    PUBLISH_SALT=... python3 publish.py --data-dir data --out published \\
        --grid-m 1000
    python3 publish.py --help
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

import adjudicate
import imagecrypt
import sequences

# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

POLICY_VERSION = "1.0"

# D-41 requires delay; it does not fix a figure. Until the owner sets one this
# is a placeholder, and the manifest records it so a published bundle always
# states which delay produced it.
DEFAULT_DELAY_DAYS = 30

# D-76: the coarsening is a grid cell, and the resolution is stated at release
# rather than defaulted. "Unspecified precision" is how a coarsening rule
# quietly turns back into a precise trace, so the value has to be chosen and it
# cannot be chosen below this floor.
MIN_GRID_M = 1000

# Used only to size longitude cells, which narrow with latitude. At the pilot
# town's latitude a metre of longitude is about 0.79 m of ground.
GRID_REFERENCE_LAT = 37.58

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
    "grid_cell",
    "grid_size_m",
    "episode_key",
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

FALSE_TRIGGER_CAPTION = (
    "A sensor trigger was recorded that review did not classify as an "
    "opening."
)

# Checked against every caption before it is written. This is a guard against a
# future edit reintroducing accusatory language, not a substitute for review.
BANNED_TERMS = (
    "theft", "stolen", "thief", "thieves", "steal", "stolen from",
    "suspect", "criminal", "guilty", "offender", "culprit",
    "do you know", "identify this", "reward for information",
)

# Adjudication decisions that suppress an image (D-52).
IMAGE_DECISIONS = ("publish", "withhold")


class PublishError(Exception):
    pass


# ---------------------------------------------------------------------------
# Captions
# ---------------------------------------------------------------------------

def caption_for(event_type: str, validation_status: str | None = None) -> str:
    if (validation_status or "") == "false_trigger":
        # Adjudication concluded this was not an opening. Using the normal
        # caption would publish a claim the review directly contradicts.
        return FALSE_TRIGGER_CAPTION
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


def grid_cell(lat: float, lon: float, grid_m: int) -> str:
    """The cell containing a point, as two integer indices.

    Two fixes in the same cell are indistinguishable in the output. That is the
    whole of the protection: a cell, never a point. The resolution is published
    beside the index, so the cell can be placed on a map by design — otherwise
    displacement could not be mapped at all, which is what D-76 exists to allow.
    """
    lat_step = grid_m / 111_320.0
    lon_step = grid_m / (111_320.0 * math.cos(math.radians(GRID_REFERENCE_LAT)))
    return f"{math.floor(lat / lat_step)}:{math.floor(lon / lon_step)}"


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


def _episode_index(conn) -> dict:
    """record_id -> (sequence_id, is_episode)."""
    rows = conn.execute(
        "SELECT s.sequence_id, s.is_episode, m.record_id"
        " FROM sequences s"
        " JOIN sequence_members m ON m.sequence_id = s.sequence_id").fetchall()
    return {r["record_id"]: (r["sequence_id"], bool(r["is_episode"]))
            for r in rows}


def _episode_votes(conn) -> dict:
    """Verdicts per sequence, in the order they were cast."""
    try:
        rows = conn.execute(
            "SELECT sequence_id, outcome FROM sequence_adjudications"
            " ORDER BY id").fetchall()
    except sqlite3.OperationalError:
        # Nobody has adjudicated yet; every episode is unresolved.
        return {}
    votes = {}
    for r in rows:
        votes.setdefault(r["sequence_id"], []).append(r["outcome"])
    return votes


def _episode_counts(conn, published_ids) -> dict:
    """The bundle counted by episode, because that is the analysed unit.

    One opening produces a light trigger, a capture record and several movement
    events, all of which publish. A record count therefore overstates removals
    by however many movement events each opening generated, which is why the
    removal figure has to come from here.

    An episode counts as published only when every one of its records is in
    this bundle. Splitting an episode across two runs would otherwise count the
    same removal twice, and a bundle that straddles the delay cutoff is reported
    as partial rather than silently counted.
    """
    votes = _episode_votes(conn)

    members = {}
    for r in conn.execute(
            "SELECT s.sequence_id, m.record_id FROM sequences s"
            " JOIN sequence_members m ON m.sequence_id = s.sequence_id"
            " WHERE s.is_episode = 1"):
        members.setdefault(r["sequence_id"], []).append(r["record_id"])

    out = {
        "episodes_total": 0,
        "episodes_published": 0,
        "episodes_partial": 0,
        "episodes_withheld_delay": 0,
        "episodes_by_outcome": {},
        "removals_published": 0,
    }

    for seq_id, record_ids in members.items():
        out["episodes_total"] += 1

        state, _, decided = adjudicate.resolve_outcomes(votes.get(seq_id, []))
        label = decided or "unresolved"
        out["episodes_by_outcome"][label] = (
            out["episodes_by_outcome"].get(label, 0) + 1)

        published = [r for r in record_ids if r in published_ids]
        if len(published) == len(record_ids):
            out["episodes_published"] += 1
            if label == "removal":
                out["removals_published"] += 1
        elif published:
            out["episodes_partial"] += 1
        else:
            out["episodes_withheld_delay"] += 1

    return out


def publish(data_dir: str, out_dir: str, salt: bytes, *,
            delay_days: int = DEFAULT_DELAY_DAYS,
            release_images: bool = False,
            image_key: bytes | None = None,
            grid_m: int | None = None,
            now: datetime | None = None) -> dict:
    db_path = os.path.join(data_dir, "records.db")
    if not os.path.exists(db_path):
        raise PublishError(f"no database at {db_path}")

    if grid_m is None:
        raise PublishError(
            "grid resolution is not set; D-76 requires a release to state the "
            "resolution it used")
    if not isinstance(grid_m, int) or grid_m < MIN_GRID_M:
        raise PublishError(
            f"grid resolution must be a whole number of metres, at least "
            f"{MIN_GRID_M}; {grid_m!r} is finer than D-76 permits")

    if image_key is None:
        image_key = imagecrypt.key_from_env()

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
        "images_withheld_unreviewed": 0,
        "images_withheld_by_category": {},
    }

    # Grouped with the same rule and the same frozen memberships adjudication
    # used, so a manifest cannot disagree with the reviews behind it.
    sequences.sync(conn)
    conn.commit()
    episode_index = _episode_index(conn)
    published_ids = set()

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

            caption = caption_for(row["event_type"], row["validation_status"])
            check_caption(caption)

            distance, bucket = deployment_displacement(
                conn, row["deployment_id"])

            grouped = episode_index.get(row["record_id"])
            episode_key = grouped[0] if grouped and grouped[1] else None

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
                "grid_cell": (grid_cell(row["lat"], row["lon"], grid_m)
                              if row["location_valid"] else None),
                "grid_size_m": grid_m,
                "episode_key": episode_key,
            }

            # Belt and braces: the record is built from a whitelist, but assert
            # it so a future edit adding a stray key fails the run.
            for key in out:
                if key not in OUTPUT_FIELDS:
                    raise PublishError(f"unexpected output field {key!r}")

            fh.write(json.dumps(out, sort_keys=True) + "\n")
            counts["records_published"] += 1
            published_ids.add(row["record_id"])

            if release_images:
                _publish_images(conn, row, data_dir, image_out, counts,
                                image_key)

    counts.update(_episode_counts(conn, published_ids))

    manifest = {
        "policy_version": POLICY_VERSION,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "delay_days": delay_days,
        "grid_m": grid_m,
        "grid_floor_m": MIN_GRID_M,
        "images_released": release_images,
        "counts": counts,
        "notes": [
            "Location is a grid cell at the stated resolution, never a "
            "coordinate (D-41, D-76).",
            "The grid resolution is recorded rather than defaulted, so a "
            "bundle states the precision that produced it.",
            "Records are not removals: one opening produces several records, "
            "so the removal figure is removals_published, which counts "
            "episodes whose every record is in this bundle.",
            "Deployment identifiers are replaced by a keyed hash (D-41).",
            "Captions describe an opening, not a theft (D-42).",
            "Images are released only when adjudicated (D-52).",
            "Only the frames a decision covered are released, so a frame that "
            "arrived later is not published unreviewed.",
        ],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w",
              encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    conn.close()
    return manifest


def _image_decision(conn, record_id):
    """The latest image adjudication for a record, or None.

    This module does not judge whether a frame is safe. It asks whether
    somebody with the authority to look has already said so. If the table does
    not exist nobody has, which is the fail-closed answer.
    """
    try:
        return conn.execute(
            "SELECT decision, category, image_hashes FROM adjudications"
            " WHERE record_id=? AND kind='image'"
            " ORDER BY decided_at DESC, id DESC LIMIT 1",
            (record_id,)).fetchone()
    except sqlite3.OperationalError:
        return None


def _frame_count(conn, row) -> int:
    """Frames held for this record.

    The manifest is a count of images, so it counts images. Counting records
    here would overstate it by every record that has no frames at all.
    """
    return conn.execute(
        "SELECT COUNT(*) c FROM images WHERE record_id=?",
        (row["record_id"],)).fetchone()["c"]


def _publish_images(conn, row, data_dir, image_out, counts, image_key=None):
    decision = _image_decision(conn, row["record_id"])

    if decision is None:
        # D-52 cannot be honoured without a human decision, so an unadjudicated
        # frame is never published. This is the fail-closed branch.
        counts["images_withheld_unadjudicated"] += _frame_count(conn, row)
        return

    if decision["decision"] == "withhold":
        # D-52 wants the count by category, and never the image.
        category = decision["category"] or "unspecified"
        counts["images_withheld_by_category"][category] = (
            counts["images_withheld_by_category"].get(category, 0)
            + _frame_count(conn, row))
        return

    # A publish decision covers the frames that existed when it was made; the
    # adjudication stored their hashes. A frame that arrived, or was replaced,
    # afterwards has not been looked at by anybody, so it is not released on
    # the strength of a review that never saw it.
    try:
        reviewed = set(json.loads(decision["image_hashes"] or "[]"))
    except (TypeError, ValueError):
        reviewed = set()

    images = conn.execute(
        "SELECT frame_index, secure_object_ref, integrity_hash FROM images"
        " WHERE record_id=? ORDER BY frame_index",
        (row["record_id"],)).fetchall()

    for img in images:
        if img["integrity_hash"] not in reviewed:
            counts["images_withheld_unreviewed"] += 1
            continue
        src = os.path.join(data_dir, "images", img["secure_object_ref"])
        if not os.path.exists(src):
            continue
        if image_key is None:
            # Fail closed rather than skip: a release that quietly drops the
            # frames would under-report what was published.
            raise PublishError(
                f"{imagecrypt.KEY_ENV} is not set; stored frames cannot be "
                f"decrypted for release")
        with open(src, "rb") as fh:
            sealed = fh.read()
        try:
            blob = imagecrypt.decrypt(image_key, sealed)
        except imagecrypt.CryptoError as exc:
            raise PublishError(f"{row['record_id']}: {exc}")
        if hashlib.sha256(blob).hexdigest() != img["integrity_hash"]:
            raise PublishError(
                f"{row['record_id']}: decrypted frame does not match its "
                f"recorded hash; refusing to publish it")

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
    ap.add_argument("--grid-m", type=int, required=True,
                    help=f"published grid cell size in metres "
                         f"(minimum {MIN_GRID_M}; D-76 requires a release to "
                         f"state its resolution)")
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
                           grid_m=args.grid_m,
                           release_images=not args.no_images)
    except PublishError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    c = manifest["counts"]
    print(f"published {c['records_published']} of {c['records_total']} records "
          f"to {args.out}")
    print(f"  held for delay        {c['records_withheld_delay']}")
    print(f"episodes              {c['episodes_published']} of "
          f"{c['episodes_total']} whole, {c['episodes_partial']} partial, "
          f"{c['episodes_withheld_delay']} held")
    print(f"  removals published    {c['removals_published']}")
    for label, n in sorted(c["episodes_by_outcome"].items()):
        print(f"  episode {label:<14} {n}")
    if manifest["images_released"]:
        print(f"  images published      {c['images_published']}")
        print(f"  images unadjudicated  {c['images_withheld_unadjudicated']}")
        print(f"  images unreviewed     {c['images_withheld_unreviewed']}")
        for cat, n in sorted(c["images_withheld_by_category"].items()):
            print(f"  withheld ({cat}){' ' * max(0, 9 - len(cat))} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
