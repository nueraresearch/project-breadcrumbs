#!/usr/bin/env python3
"""Derive the episode gap and window from measured openings.

The server groups records into episodes with two constants in
`server/sequences.py`: how long a pause may be before a new episode starts, and
how long one episode may run. Both were chosen before any opening had been
observed — 180 s and 900 s, from reasoning about what an opening ought to take.
This tool replaces them with numbers from scripted trials, the same way
`analyze_drift.py` replaces the RTC residual.

**Why it needs a scripted trial rather than field data.** In the field you never
see the ground truth: a cluster of records could be one person opening a parcel
or two people disturbing it an hour apart, and the whole question is where that
line falls. A trial is a known answer — one opening, one carry, one set-down —
so the spread within it can be measured directly.

**What it computes.** Within each trial, the span from the first record to the
last, and the largest pause between consecutive records. The recommendation is
twice the largest observed internal pause and one and a half times the longest
observed span, both rounded up to 30 s. Those margins are a judgement, not a
confidence bound: they buy room for an opening slower than any observed, and
the report prints the observed maximum beside the recommendation so the margin
stays visible.

**It refuses to guess.** Fewer than five trials is an error rather than a
number, unsynced records are skipped and counted, and if the recommended gap
would merge two trials the tool says so instead of returning a figure that
cannot distinguish them.

Usage:
    python3 analyze_sequences.py trials.jsonl
    python3 analyze_sequences.py --db ../server/data/records.db
    python3 analyze_sequences.py trials.jsonl --check 60 120
    python3 analyze_sequences.py --synthetic 8          # self-test only
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys

# Same four types the server treats as an episode. Kept here rather than
# imported, so the bench tool stays runnable without the server on the path.
EPISODE_TYPES = frozenset({
    "LIGHT_TRIGGER",
    "MOVEMENT_EVENT",
    "IMAGE_CAPTURE_COMPLETE",
    "IMAGE_CAPTURE_PARTIAL",
})

# Trials are separated by a rest far longer than any plausible opening, so this
# only has to be "longer than an opening", not a tuned value.
TRIAL_SPLIT_S = 300

# Below this, a fitted number would look measured without being so.
MIN_TRIALS = 5

# AT-03 asks for 30 scripted trials. Five produces a figure; thirty deserves
# to be quoted.
TARGET_TRIALS = 30

MARGIN_GAP = 2.0
MARGIN_SPAN = 1.5
ROUND_S = 30


def _pick(rec):
    """Returns (row, reason). reason is 'device' or 'unsynced' when dropped."""
    if rec.get("event_type") not in EPISODE_TYPES:
        return None, "device"
    ts = rec.get("sensor_ts")
    # A record whose clock never synced carries ±18 minutes. Grouping on it
    # would measure the clock, not the opening.
    if not rec.get("clock_synced") or not ts:
        return None, "unsynced"
    return {"module_id": rec["module_id"],
            "record_id": rec.get("record_id"),
            "sensor_ts": int(ts)}, None


def load_jsonl(path: str):
    rows, skipped = [], 0
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: {exc}")
            row, why = _pick(rec)
            if why == "unsynced":
                skipped += 1
            if row:
                rows.append(row)
    return rows, skipped


def load_db(path: str):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        records = [dict(r) for r in conn.execute(
            "SELECT record_id, module_id, event_type, sensor_ts, clock_synced"
            " FROM events")]
    finally:
        conn.close()

    rows, skipped = [], 0
    for rec in records:
        row, why = _pick(rec)
        if why == "unsynced":
            skipped += 1
        if row:
            rows.append(row)
    return rows, skipped


def group(rows, split_s, window_s=None):
    """Groups records into runs, per module, by the rule the server uses."""
    by_module = {}
    for r in rows:
        by_module.setdefault(r["module_id"], []).append(r)

    out = []
    for module in sorted(by_module):
        items = sorted(by_module[module], key=lambda r: r["sensor_ts"])
        current = []
        for r in items:
            if current and (
                    r["sensor_ts"] - current[-1]["sensor_ts"] > split_s
                    or (window_s and r["sensor_ts"] - current[0]["sensor_ts"] > window_s)):
                out.append(current)
                current = []
            current.append(r)
        if current:
            out.append(current)
    return out


def separation(trials):
    """Shortest rest between two trials of the same module, or None."""
    by_module = {}
    for t in trials:
        by_module.setdefault(t[0]["module_id"], []).append(t)

    seps = []
    for module, runs in by_module.items():
        runs.sort(key=lambda t: t[0]["sensor_ts"])
        for a, b in zip(runs, runs[1:]):
            seps.append(b[0]["sensor_ts"] - a[-1]["sensor_ts"])
    return min(seps) if seps else None


def _ceil_to(step, value):
    return int(math.ceil(value / float(step)) * step)


def recommend(trials):
    """Both constants, with the observations they came from."""
    if len(trials) < MIN_TRIALS:
        raise ValueError(
            f"need at least {MIN_TRIALS} scripted trials to produce a figure, "
            f"got {len(trials)}. A number from fewer would look measured "
            f"without being so.")

    spans = [t[-1]["sensor_ts"] - t[0]["sensor_ts"] for t in trials]
    gaps = [b["sensor_ts"] - a["sensor_ts"]
            for t in trials for a, b in zip(t, t[1:])]

    max_gap = max(gaps) if gaps else 0
    max_span = max(spans) if spans else 0

    gap_s = _ceil_to(ROUND_S, max(ROUND_S, MARGIN_GAP * max_gap))
    window_s = _ceil_to(ROUND_S, max(3 * ROUND_S, MARGIN_SPAN * max_span))
    window_s = max(window_s, gap_s)

    warnings = []
    if len(trials) < TARGET_TRIALS:
        warnings.append(
            f"{len(trials)} trials; AT-03 calls for {TARGET_TRIALS}. This is "
            f"enough to produce a figure, not enough to quote without the "
            f"sample size beside it.")

    sep = separation(trials)
    if sep is not None and sep <= gap_s:
        warnings.append(
            f"trials are only {sep} s apart, which the recommended {gap_s} s "
            f"gap would merge. Re-run with longer rests, or the measurement "
            f"cannot distinguish two openings from one.")

    return {
        "gap_s": gap_s,
        "window_s": window_s,
        "max_internal_gap_s": max_gap,
        "max_span_s": max_span,
        "span_min_s": min(spans) if spans else 0,
        "span_max_s": max(spans) if spans else 0,
        "trials": len(trials),
        "records": sum(len(t) for t in trials),
        "shortest_separation_s": sep,
        "warnings": warnings,
    }


def check(rows, gap_s, window_s):
    """Does this pair of constants reproduce the trials it was fitted on?

    The reference grouping splits at TRIAL_SPLIT_S, which is the operator's
    rest and not a tuned value. If the proposed constants produce the same
    runs, every trial stays one episode and no two trials merge.
    """
    reference = group(rows, TRIAL_SPLIT_S)
    proposed = group(rows, gap_s, window_s)

    def key(t):
        return (t[0]["module_id"], t[0]["sensor_ts"], len(t))

    return (sorted(key(t) for t in reference) == sorted(key(t) for t in proposed),
            len(reference), len(proposed))


def synthetic(trials: int, seed: int = 0):
    """A log with known trials, for testing the tool rather than the world."""
    import random
    rng = random.Random(seed)
    rows = []
    for i in range(trials):
        start = 1_700_000_000 + i * 600
        span = rng.uniform(6.0, 18.0)
        for k in range(4):
            rows.append({
                "record_id": f"SYN-{i}-{k}",
                "module_id": "BENCH",
                "event_type": ("LIGHT_TRIGGER" if k == 0 else "MOVEMENT_EVENT"),
                "sensor_ts": int(start + span * k / 3.0),
                "clock_synced": True,
            })
    return rows


def format_report(rec) -> str:
    lines = [
        "Sequence window measurement",
        "=" * 40,
        f"trials             {rec['trials']}",
        f"records            {rec['records']}",
        f"span (s)           {rec['span_min_s']} .. {rec['span_max_s']}",
        f"largest pause (s)  {rec['max_internal_gap_s']}",
    ]
    if rec["shortest_separation_s"] is not None:
        lines.append(f"shortest rest (s)  {rec['shortest_separation_s']}")

    lines += [
        "",
        "Recommended for server/sequences.py:",
        f"  GAP_S = {rec['gap_s']}        # 2 x largest pause "
        f"({rec['max_internal_gap_s']} s)",
        f"  WINDOW_S = {rec['window_s']}     # 1.5 x longest span "
        f"({rec['max_span_s']} s)",
        "",
        "Bump RULE_VERSION when you change them, so stored sequences record",
        "which rule produced them.",
    ]

    if rec["warnings"]:
        lines.append("")
        lines.append("Warnings:")
        for w in rec["warnings"]:
            lines.append(f"  ! {w}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", help="JSONL, one record per line")
    ap.add_argument("--db", help="read from an ingest records.db instead")
    ap.add_argument("--synthetic", type=int, metavar="TRIALS",
                    help="self-test with generated trials, not a measurement")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", nargs=2, type=int, metavar=("GAP_S", "WINDOW_S"),
                    help="test a proposed pair against the log")
    args = ap.parse_args(argv)

    try:
        if args.synthetic is not None:
            rows, skipped = synthetic(args.synthetic), 0
        elif args.db:
            rows, skipped = load_db(args.db)
        elif args.path:
            rows, skipped = load_jsonl(args.path)
        else:
            ap.error("give a JSONL path, --db, or --synthetic")
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not rows:
        print("error: no clock-synced episode records in that log",
              file=sys.stderr)
        return 2

    if args.check:
        gap_s, window_s = args.check
        ok, n_ref, n_prop = check(rows, gap_s, window_s)
        if ok:
            print(f"ok: GAP_S={gap_s} WINDOW_S={window_s} reproduce all "
                  f"{n_ref} trials exactly")
            return 0
        print(f"mismatch: {n_ref} trials under the reference split, "
              f"{n_prop} with GAP_S={gap_s} WINDOW_S={window_s}. "
              f"Some trial is split or two trials are merged.", file=sys.stderr)
        return 1

    try:
        rec = recommend(group(rows, TRIAL_SPLIT_S))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rec["skipped_unsynced"] = skipped

    if args.json:
        print(json.dumps(rec, indent=2))
    else:
        print(format_report(rec))
        if skipped:
            print(f"\n{skipped} record(s) skipped: clock never synced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
