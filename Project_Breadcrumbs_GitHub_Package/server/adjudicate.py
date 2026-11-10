#!/usr/bin/env python3
"""Project Breadcrumbs — adjudication.

Two different reviews happen here, and they are kept apart on purpose.

**Event adjudication** (PRE_REGISTRATION_ANALYSIS_PLAN §6) classifies a
movement-event sequence as removal, handling or indeterminate from telemetry
alone. The sequence is the unit, not the record: one opening produces a light
trigger, a capture record and several movement events, and asking a reviewer
about each of those separately would let a single episode be classified two
ways. sequences.py does the grouping and stores the rule it used. Two reviewers
decide independently; a disagreement goes to a third and the rule applied is
recorded. This path never touches an image, and a reviewer
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
    ... show seq_1a2b3c4d5e6f7a8b
    ... show RECORD_ID
    ... decide-event seq_1a2b3c4d5e6f7a8b --reviewer alice --outcome removal
    ... decide-event RECORD_ID --reviewer alice --outcome removal  # same episode
    ... view-images RECORD_ID --reviewer alice --out review/
    ... decide-image RECORD_ID --reviewer alice --decision withhold --category minor
    ... status
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import date, datetime, timezone

import imagecrypt
import sequences

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

-- Event votes are cast on a sequence, not a record: §6 asks for one
-- classification per movement-event sequence, and a sequence is what a
-- reviewer is shown. Image decisions stay on the record holding the frames.
CREATE TABLE IF NOT EXISTS sequence_adjudications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence_id TEXT NOT NULL,
    reviewer    TEXT NOT NULL,
    outcome     TEXT NOT NULL,
    rationale   TEXT,
    decided_at  TEXT NOT NULL,
    UNIQUE(sequence_id, reviewer)
);

CREATE INDEX IF NOT EXISTS idx_seqadj_sequence
    ON sequence_adjudications(sequence_id);
"""


class AdjudicationError(Exception):
    pass


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_outcomes(outcomes: list) -> tuple:
    """§6 applied to the verdicts on one sequence, in the order cast.

    Pure, because the queue and the decision have to agree about what counts
    as settled; two copies of this rule would drift apart.
    """
    if not outcomes:
        return "unreviewed", STATUS_UNREVIEWED, None
    if len(outcomes) == 1:
        # One reviewer is an opinion, not a classification.
        return "awaiting_second", STATUS_UNREVIEWED, None
    if len(set(outcomes)) == 1:
        return "resolved", OUTCOME_TO_STATUS[outcomes[0]], outcomes[0]
    if len(outcomes) >= 3:
        # The third reviewer decides, and their verdict is the one applied.
        return ("resolved_by_third", OUTCOME_TO_STATUS[outcomes[-1]],
                outcomes[-1])
    # Disagreement without a third is retained as indeterminate rather than
    # forced into one class (§6).
    return "needs_third", STATUS_INDETERMINATE, None


class Adjudicator:
    """Adjudication against an existing ingest data directory.

    `allowed_reviewers` is the access restriction from DATA_PROTECTION_CONTROLS
    §1: only named individuals may view captured images. A caller that passes
    None can record event verdicts but cannot view an image, because there is
    no list saying who is permitted.
    """

    def __init__(self, data_dir: str, allowed_reviewers=None,
                 image_key: bytes | None = None):
        self.data_dir = os.path.abspath(data_dir)
        self.image_dir = os.path.join(self.data_dir, "images")
        self.db_path = os.path.join(self.data_dir, "records.db")
        if not os.path.exists(self.db_path):
            raise AdjudicationError(f"no database at {self.db_path}")
        self.allowed_reviewers = (
            None if allowed_reviewers is None else set(allowed_reviewers))
        self.image_key = (image_key if image_key is not None
                          else imagecrypt.key_from_env())
        with self._conn() as conn:
            conn.executescript(SCHEMA)
            sequences.ensure_schema(conn)

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
        """Episodes awaiting an event classification (§6).

        Image review is a separate queue, because a reviewer who looks at the
        frames stops being eligible to classify the episode they belong to.
        """
        with self._conn() as conn:
            sequences.sync(conn)
            votes = {}
            for row in conn.execute(
                    "SELECT sequence_id, outcome FROM sequence_adjudications"
                    " ORDER BY id"):
                votes.setdefault(row["sequence_id"], []).append(row["outcome"])

            rows = conn.execute(
                """SELECT s.sequence_id, s.module_id, s.anchor_record_id,
                          s.started_ts, s.ended_ts, s.member_count,
                          s.rule_version,
                          (SELECT GROUP_CONCAT(m.record_id)
                             FROM sequence_members m
                            WHERE m.sequence_id = s.sequence_id) AS members,
                          (SELECT COUNT(*) FROM sequence_members m
                             JOIN images i ON i.record_id = m.record_id
                            WHERE m.sequence_id = s.sequence_id) AS frames
                     FROM sequences s
                    WHERE s.is_episode = 1
                    ORDER BY s.started_ts
                    LIMIT ?""", (limit,)).fetchall()

        out = []
        for row in rows:
            item = dict(row)
            item["members"] = sorted((item["members"] or "").split(","))
            seq_votes = votes.get(item["sequence_id"], [])
            item["votes"] = len(seq_votes)
            state, status, decided = resolve_outcomes(seq_votes)
            item["state"], item["status"] = state, status
            item["decided_outcome"] = decided
            if state not in ("resolved", "resolved_by_third"):
                out.append(item)
        return out

    def pending_images(self, limit: int = 50):
        """Records holding frames that nobody has adjudicated yet (D-52)."""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT e.record_id, e.event_type, e.received_timestamp,
                          (SELECT COUNT(*) FROM images i
                            WHERE i.record_id = e.record_id) AS frames
                     FROM events e
                    WHERE EXISTS (SELECT 1 FROM images i
                                   WHERE i.record_id = e.record_id)
                      AND NOT EXISTS (
                          SELECT 1 FROM adjudications a
                           WHERE a.record_id = e.record_id
                             AND a.kind = 'image')
                    ORDER BY e.received_timestamp
                    LIMIT ?""", (limit,)).fetchall()
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

    def sequence_of(self, record_id: str) -> str:
        """The sequence a record belongs to, grouping first if needed."""
        with self._conn() as conn:
            if conn.execute("SELECT 1 FROM events WHERE record_id=?",
                            (record_id,)).fetchone() is None:
                raise AdjudicationError(f"unknown record_id {record_id!r}")
            sequences.sync(conn)
            row = conn.execute(
                "SELECT sequence_id FROM sequence_members WHERE record_id=?",
                (record_id,)).fetchone()
        if row is None:
            raise AdjudicationError(f"{record_id} belongs to no sequence")
        return row["sequence_id"]

    def vote_event(self, record_id: str, reviewer: str, outcome: str,
                   rationale: str | None = None) -> dict:
        """Classifies the episode this record belongs to (§6).

        Kept because a caller holding a record id should not have to know how
        records were grouped. The vote lands on the sequence, so two records
        from one opening cannot end up classified differently.
        """
        return self.vote_sequence(self.sequence_of(record_id), reviewer,
                                  outcome, rationale)

    def vote_sequence(self, sequence_id: str, reviewer: str, outcome: str,
                      rationale: str | None = None) -> dict:
        reviewer = self._check_reviewer(reviewer)
        if outcome not in EVENT_OUTCOMES:
            raise AdjudicationError(
                f"outcome must be one of {', '.join(EVENT_OUTCOMES)}")

        with self._conn() as conn:
            members = [r["record_id"] for r in conn.execute(
                "SELECT record_id FROM sequence_members WHERE sequence_id=?",
                (sequence_id,)).fetchall()]
            if not members:
                raise AdjudicationError(f"unknown sequence {sequence_id!r}")

            # §6: the classification must rest on telemetry alone. Looking at
            # any frame of the episode disqualifies the reviewer for the whole
            # episode, not only for the record they happened to open.
            for rid in members:
                if conn.execute(
                        "SELECT 1 FROM ingest_log WHERE kind='image_access'"
                        " AND detail LIKE ? AND detail LIKE ?",
                        (f'%"{rid}"%', f'%"{reviewer}"%')).fetchone():
                    raise AdjudicationError(
                        f"{reviewer!r} has already viewed the images for "
                        f"{rid}; event adjudication must be blind to them")

            conn.execute(
                """INSERT INTO sequence_adjudications
                       (sequence_id, reviewer, outcome, rationale, decided_at)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(sequence_id, reviewer) DO UPDATE SET
                       outcome=excluded.outcome,
                       rationale=excluded.rationale,
                       decided_at=excluded.decided_at""",
                (sequence_id, reviewer, outcome, rationale, utcnow()))

            resolution = self._resolve_sequence(conn, sequence_id)
            if resolution["status"] not in VALID_STATUSES:
                raise AdjudicationError(
                    f"refusing to write unknown status {resolution['status']!r}")

            # Every member carries the verdict. Publication reads this column
            # per record, and the records of one episode must not disagree.
            conn.execute(
                "UPDATE events SET validation_status=?"
                " WHERE record_id IN (SELECT record_id FROM sequence_members"
                "                      WHERE sequence_id=?)",
                (resolution["status"], sequence_id))

            self._log(conn, "event_adjudicated", {
                "sequence_id": sequence_id, "members": members,
                "reviewer": reviewer, "outcome": outcome,
                "state": resolution["state"]})

        resolution["sequence_id"] = sequence_id
        resolution["records"] = members
        return resolution

    def _resolve_sequence(self, conn, sequence_id: str) -> dict:
        votes = [dict(v) for v in conn.execute(
            "SELECT reviewer, outcome FROM sequence_adjudications"
            " WHERE sequence_id=? ORDER BY id", (sequence_id,)).fetchall()]
        state, status, decided = resolve_outcomes([v["outcome"] for v in votes])
        return {"state": state, "status": status, "votes": votes,
                "decided_outcome": decided}

    # -- sequence inspection ---------------------------------------------

    def sequence_detail(self, sequence_id: str) -> dict:
        """Members, verdicts, and the location fixes around them.

        Location fixes are context, not members. §3 decides a removal partly by
        where the module reported afterwards, so a reviewer needs those rows,
        but a periodic fix is not part of the opening and does not decide where
        one episode ends.
        """
        with self._conn() as conn:
            seq = conn.execute("SELECT * FROM sequences WHERE sequence_id=?",
                               (sequence_id,)).fetchone()
            if seq is None:
                raise AdjudicationError(f"unknown sequence {sequence_id!r}")

            members = [dict(r) for r in conn.execute(
                """SELECT e.record_id, e.event_type, e.sensor_ts,
                          e.clock_synced, e.clock_uncertainty_s, e.flags,
                          e.lux, e.battery_mv, e.validation_status
                     FROM events e
                     JOIN sequence_members m ON m.record_id = e.record_id
                    WHERE m.sequence_id = ?
                    ORDER BY e.sensor_ts""", (sequence_id,)).fetchall()]

            lo = (seq["started_ts"] or 0) - sequences.WINDOW_S
            hi = (seq["ended_ts"] or 0) + sequences.WINDOW_S
            fixes = [dict(r) for r in conn.execute(
                """SELECT record_id, sensor_ts, location_valid, loc_method,
                          loc_accuracy_m
                     FROM events
                    WHERE module_id=? AND event_type='LOCATION_FIX'
                      AND sensor_ts BETWEEN ? AND ?
                    ORDER BY sensor_ts""",
                (seq["module_id"], lo, hi)).fetchall()]

            votes = [dict(v) for v in conn.execute(
                "SELECT reviewer, outcome, rationale, decided_at"
                " FROM sequence_adjudications WHERE sequence_id=?"
                " ORDER BY id", (sequence_id,)).fetchall()]

        state, status, decided = resolve_outcomes([v["outcome"] for v in votes])
        return {"sequence_id": sequence_id, "module_id": seq["module_id"],
                "deployment_id": seq["deployment_id"],
                "started_ts": seq["started_ts"],
                "ended_ts": seq["ended_ts"],
                "rule_version": seq["rule_version"],
                "members": members, "context_fixes": fixes,
                "votes": votes, "state": state, "status": status,
                "decided_outcome": decided}

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

        if self.image_key is None:
            raise AdjudicationError(
                f"{imagecrypt.KEY_ENV} is not set; stored frames cannot be "
                f"decrypted for review")

        os.makedirs(out_dir, exist_ok=True)
        written = []
        for r in rows:
            if not r["secure_object_ref"]:
                continue
            src = os.path.join(self.image_dir, r["secure_object_ref"])
            if not os.path.exists(src):
                continue
            with open(src, "rb") as fh:
                sealed = fh.read()
            try:
                plain = imagecrypt.decrypt(self.image_key, sealed)
            except imagecrypt.CryptoError as exc:
                raise AdjudicationError(
                    f"{r['secure_object_ref']}: {exc}")
            if hashlib.sha256(plain).hexdigest() != r["integrity_hash"]:
                raise AdjudicationError(
                    f"{r['secure_object_ref']}: decrypted frame does not "
                    f"match its recorded hash")
            dst = os.path.join(out_dir,
                               f"{record_id}_{r['frame_index']:02d}.jpg")
            with open(dst, "wb") as fh:
                fh.write(plain)
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
            if not hashes:
                # A decision recorded over no frames approves nothing while
                # looking as though it approved something. Frames upload after
                # their record, so this is the ordinary mistake rather than an
                # exotic one, and publication would have honoured the empty
                # decision by releasing nothing at all.
                raise AdjudicationError(
                    f"{record_id} holds no frames; there is nothing to "
                    f"adjudicate")

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

            sequences.sync(conn)
            episode_rows = conn.execute(
                "SELECT sequence_id FROM sequences WHERE is_episode = 1"
            ).fetchall()
            votes = {}
            for row in conn.execute(
                    "SELECT sequence_id, outcome FROM sequence_adjudications"
                    " ORDER BY id"):
                votes.setdefault(row["sequence_id"], []).append(row["outcome"])

        episodes = {"total": len(episode_rows), "decided": 0, "open": 0}
        for row in episode_rows:
            state, _, _ = resolve_outcomes(votes.get(row["sequence_id"], []))
            if state in ("resolved", "resolved_by_third"):
                episodes["decided"] += 1
            else:
                episodes["open"] += 1

        return {"by_status": by_status, "withheld_by_category": withheld,
                "image_publish_decisions": published,
                "images_held": images_held, "episodes": episodes}


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

    p = sub.add_parser("pending", help="episodes awaiting classification")
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
                print("no episodes awaiting classification")
            for r in rows:
                print(f"{r['sequence_id']}  {r['module_id']:<12} "
                      f"members={r['member_count']} votes={r['votes']} "
                      f"frames={r['frames']} "
                      f"{r['started_ts']}..{r['ended_ts']}  {r['state']}")
                print(f"    {', '.join(r['members'])}")

            images = adj.pending_images(args.limit)
            if images:
                print("\nframes awaiting image review:")
                for r in images:
                    print(f"  {r['record_id']}  {r['event_type']:<22} "
                          f"frames={r['frames']}")

        elif args.cmd == "show":
            if args.record_id.startswith("seq_"):
                d = adj.sequence_detail(args.record_id)
                print(f"sequence      {d['sequence_id']}")
                print(f"module        {d['module_id']}")
                print(f"rule_version  {d['rule_version']}")
                print(f"state         {d['state']} ({d['status']})")
                for m in d["members"]:
                    print(f"  {m['record_id']}  {m['event_type']:<22} "
                          f"ts={m['sensor_ts']} flags={m['flags']} "
                          f"lux={m['lux']} battery={m['battery_mv']} "
                          f"status={m['validation_status']}")
                for f in d["context_fixes"]:
                    print(f"  fix {f['record_id']} ts={f['sensor_ts']} "
                          f"valid={f['location_valid']} "
                          f"acc={f['loc_accuracy_m']}")
                for v in d["votes"]:
                    print(f"  vote {v['reviewer']} -> {v['outcome']} "
                          f"{v['decided_at']}")
            else:
                for k, v in adj.telemetry(args.record_id).items():
                    print(f"{k:<20} {v}")

        elif args.cmd == "view-images":
            files = adj.view_images(args.record_id, args.reviewer, args.out)
            print(f"wrote {len(files)} frame(s) to {args.out}")
            print("review copies are plaintext inside that folder; treat it "
                  "as sensitive and delete it when the review is written up")

        elif args.cmd == "decide-event":
            if args.record_id.startswith("seq_"):
                res = adj.vote_sequence(args.record_id, args.reviewer,
                                        args.outcome, args.rationale)
            else:
                res = adj.vote_event(args.record_id, args.reviewer,
                                     args.outcome, args.rationale)
            print(f"state={res['state']} validation_status={res['status']} "
                  f"votes={len(res['votes'])} "
                  f"records={len(res['records'])}")

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
            e = s["episodes"]
            print(f"episodes        {e['decided']} decided, {e['open']} open, "
                  f"{e['total']} total")
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
