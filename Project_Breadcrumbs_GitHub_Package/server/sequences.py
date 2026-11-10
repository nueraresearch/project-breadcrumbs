#!/usr/bin/env python3
"""Project Breadcrumbs — movement-event sequences.

PRE_REGISTRATION_ANALYSIS_PLAN §6 says reviewers classify "each movement-event
sequence", and §3 defines a removal in terms of movement events, but neither
document says where one episode ends and the next begins. A record on its own
is not an episode: one opening produces a light trigger, a capture record and
some number of movement events, and classifying each of those separately asks
a reviewer the same question several times and lets the answers disagree.

This module answers the missing question, once, so that adjudication and any
later analysis group records the same way.

**The grouping rule.** Records from one module are ordered by their own clock
and merged into one sequence while consecutive movement-bearing records are no
more than `GAP_S` apart and the sequence as a whole spans no more than
`WINDOW_S`. Beyond either bound a new sequence starts.

**Those two figures are this implementation's assumption, not values taken from
the plan.** They are recorded in every row as `rule_version` so a bundle can
say which rule produced it. `firmware/bench/analyze_sequences.py` derives both
from scripted openings and prints them for pasting here; **it has not been run
against a real opening, because none has been recorded**, so the numbers below
are reasoning rather than measurement and should be read as such. Changing them
does not rewrite existing sequences: membership is frozen as soon as a reviewer
votes, because a classification must not end up attached to a different set of
events than the one it was made about.

**What never joins an episode.** Battery, sync and reset records describe the
device rather than the opening. Folding a low-battery alert into an episode
would put an administrative event in front of a reviewer as evidence of a
removal, so those records stay singletons and are marked `is_episode = 0`.

**Unsynced records stay singletons.** A module that has never synced carries
±18 minutes of clock uncertainty (see the firmware README), which cannot
separate a thirty-minute handling window from a removal. Grouping on that clock
would invent an ordering, so a record with `clock_synced = 0` is adjudicated on
its own and the limitation is visible in the row rather than hidden in a
merge. At the scale of this pilot that is a handful of records per cycle.

**Identifiers are deterministic.** A sequence is named from its module and its
first record, so re-running the grouping produces the same identifiers and a
recorded decision keeps pointing at the same episode. They are not random, but
they are also not derivable from a published record id alone without the module.

Usage:
    INGEST_DATA=data python3 sequences.py
    INGEST_DATA=data python3 sequences.py --limit 50
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import sys
from datetime import datetime, timezone

# Bumped when the grouping rule changes, so a stored sequence says which rule
# produced it rather than which rule happens to be installed today.
RULE_VERSION = "1.0"

# Both are assumptions. See the module docstring; they are not plan values.
GAP_S = 180
WINDOW_S = 900

# §3: a movement event is an accelerometer threshold crossing; an opening also
# produces a light trigger and a capture record. These four describe the
# episode. Everything else describes the device.
EPISODE_TYPES = ("LIGHT_TRIGGER", "MOVEMENT_EVENT",
                 "IMAGE_CAPTURE_COMPLETE", "IMAGE_CAPTURE_PARTIAL")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sequences (
    sequence_id      TEXT PRIMARY KEY,
    module_id        TEXT NOT NULL,
    deployment_id    TEXT,
    anchor_record_id TEXT NOT NULL,
    started_ts       INTEGER,
    ended_ts         INTEGER,
    member_count     INTEGER NOT NULL,
    is_episode       INTEGER NOT NULL,
    rule_version     TEXT NOT NULL,
    built_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sequence_members (
    sequence_id TEXT NOT NULL,
    record_id   TEXT NOT NULL,
    PRIMARY KEY (sequence_id, record_id)
);

CREATE INDEX IF NOT EXISTS idx_seq_module ON sequences(module_id);
CREATE INDEX IF NOT EXISTS idx_seq_member ON sequence_members(record_id);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA)


def sequence_id_for(module_id: str, anchor_record_id: str) -> str:
    """Deterministic id: same episode, same name, on every rebuild."""
    digest = hashlib.sha256(
        f"{module_id}\x00{anchor_record_id}".encode("utf-8")).hexdigest()
    return "seq_" + digest[:16]


# ---------------------------------------------------------------------------
# Grouping — pure, so it can be tested without a database
# ---------------------------------------------------------------------------

def _groupable(row) -> bool:
    return (bool(row["clock_synced"])
            and row["event_type"] in EPISODE_TYPES
            and row["sensor_ts"] is not None)


def _breaks(run: list, row) -> bool:
    return (row["sensor_ts"] - run[-1]["sensor_ts"] > GAP_S
            or row["sensor_ts"] - run[0]["sensor_ts"] > WINDOW_S)


def _sequence(module_id: str, members: list, is_episode: bool) -> dict:
    first, last = members[0], members[-1]
    return {
        "sequence_id": sequence_id_for(module_id, first["record_id"]),
        "module_id": module_id,
        "deployment_id": first.get("deployment_id"),
        "anchor_record_id": first["record_id"],
        "started_ts": first["sensor_ts"],
        "ended_ts": last["sensor_ts"],
        "member_ids": [m["record_id"] for m in members],
        "is_episode": is_episode,
    }


def build(rows) -> list[dict]:
    """Groups event rows into sequences.

    Input rows need record_id, module_id, deployment_id, event_type, sensor_ts
    and clock_synced. No database, no clock, no ordering requirement: the
    output is sorted, so the same rows always give the same sequences.
    """
    by_module: dict[str, list] = {}
    for row in rows:
        by_module.setdefault(row["module_id"], []).append(row)

    out: list[dict] = []

    for module_id in sorted(by_module):
        items = sorted(by_module[module_id],
                       key=lambda r: ((r["sensor_ts"] or 0), r["record_id"]))

        # Device records and unsynced records cannot join an episode, so each
        # one is its own sequence. They are still stored: a record with no
        # sequence would be invisible to review.
        for row in items:
            if not _groupable(row):
                out.append(_sequence(module_id, [row], is_episode=False))

        run: list = []
        for row in items:
            if not _groupable(row):
                continue
            if run and _breaks(run, row):
                out.append(_sequence(module_id, run, is_episode=True))
                run = []
            run.append(row)
        if run:
            out.append(_sequence(module_id, run, is_episode=True))

    out.sort(key=lambda s: (s["module_id"], s["started_ts"] or 0,
                            s["sequence_id"]))
    return out


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _decided(conn, sequence_id: str) -> bool:
    """True once anyone has voted on this sequence.

    The table belongs to adjudicate.py and may not exist yet, which simply
    means nobody has voted.
    """
    try:
        return conn.execute(
            "SELECT 1 FROM sequence_adjudications WHERE sequence_id=?"
            " LIMIT 1", (sequence_id,)).fetchone() is not None
    except sqlite3.OperationalError:
        return False


def sync(conn, now: str | None = None) -> dict:
    """Builds sequences and stores any that are not there yet.

    Safe to re-run. New members are added to an undecided sequence, because a
    late upload belongs to the episode it happened in. A sequence that has been
    voted on is left alone: changing its membership afterwards would attach a
    classification to records the reviewer never saw.
    """
    ensure_schema(conn)
    now = now or utcnow()

    rows = [dict(r) for r in conn.execute(
        "SELECT record_id, module_id, deployment_id, event_type,"
        " sensor_ts, clock_synced FROM events").fetchall()]

    created = extended = frozen = 0

    for seq in build(rows):
        known_row = conn.execute(
            "SELECT 1 FROM sequences WHERE sequence_id=?",
            (seq["sequence_id"],)).fetchone()

        if known_row is None:
            conn.execute(
                "INSERT INTO sequences (sequence_id, module_id,"
                " deployment_id, anchor_record_id, started_ts, ended_ts,"
                " member_count, is_episode, rule_version, built_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (seq["sequence_id"], seq["module_id"], seq["deployment_id"],
                 seq["anchor_record_id"], seq["started_ts"], seq["ended_ts"],
                 len(seq["member_ids"]), 1 if seq["is_episode"] else 0,
                 RULE_VERSION, now))
            conn.executemany(
                "INSERT OR IGNORE INTO sequence_members"
                " (sequence_id, record_id) VALUES (?,?)",
                [(seq["sequence_id"], rid) for rid in seq["member_ids"]])
            created += 1
            continue

        known = {r["record_id"] for r in conn.execute(
            "SELECT record_id FROM sequence_members WHERE sequence_id=?",
            (seq["sequence_id"],)).fetchall()}
        new = [rid for rid in seq["member_ids"] if rid not in known]
        if not new:
            continue
        if _decided(conn, seq["sequence_id"]):
            frozen += 1
            continue

        conn.executemany(
            "INSERT OR IGNORE INTO sequence_members"
            " (sequence_id, record_id) VALUES (?,?)",
            [(seq["sequence_id"], rid) for rid in new])
        conn.execute(
            "UPDATE sequences SET member_count = member_count + ?,"
            " ended_ts = ? WHERE sequence_id = ?",
            (len(new), seq["ended_ts"], seq["sequence_id"]))
        extended += 1

    total = conn.execute("SELECT COUNT(*) c FROM sequences").fetchone()["c"]
    return {"built": len(build(rows)), "created": created,
            "extended": extended, "frozen": frozen, "stored": total}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Group event records into movement-event sequences.")
    ap.add_argument("--data-dir", default=os.environ.get("INGEST_DATA", "data"))
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args(argv)

    db_path = os.path.join(args.data_dir, "records.db")
    if not os.path.exists(db_path):
        print(f"error: no database at {db_path}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(db_path, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        report = sync(conn)
        conn.commit()
        print(f"{report['built']} sequence(s) from the event log: "
              f"{report['created']} new, {report['extended']} extended, "
              f"{report['frozen']} left alone after a decision")

        rows = conn.execute(
            "SELECT sequence_id, module_id, started_ts, ended_ts,"
            " member_count FROM sequences WHERE is_episode = 1"
            " ORDER BY started_ts DESC LIMIT ?", (args.limit,)).fetchall()
        for r in rows:
            print(f"{r['sequence_id']}  {r['module_id']:<12} "
                  f"{r['started_ts']}..{r['ended_ts']}  "
                  f"members={r['member_count']}")
        if not rows:
            print("no episodes yet")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
