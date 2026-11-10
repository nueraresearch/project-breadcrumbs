#!/usr/bin/env python3
"""Tests for the sequence-window analyzer. Standard library only."""

import json
import os
import tempfile
import unittest

import analyze_sequences as A


# Real epoch seconds -- a synced device never reports 0, and the loader
# deliberately treats 0 as an unset clock.
BASE = 1_700_000_000


def trial(start, span, n=4, module="MOD000", synced=True,
          event_type="MOVEMENT_EVENT"):
    rows = []
    for k in range(n):
        ts = int(BASE + start + span * k / float(n - 1))
        rows.append({
            "record_id": f"r{start}-{k}",
            "module_id": module,
            "event_type": event_type if k else "LIGHT_TRIGGER",
            "sensor_ts": ts,
            "clock_synced": synced,
        })
    return rows


def log(trials):
    return [row for t in trials for row in t]


class GroupingTests(unittest.TestCase):
    def test_separate_trials_stay_separate(self):
        rows = log([trial(0, 10), trial(600, 10), trial(1200, 10)])
        self.assertEqual(len(A.group(rows, A.TRIAL_SPLIT_S)), 3)

    def test_records_within_a_trial_stay_together(self):
        rows = log([trial(0, 20, n=5)])
        self.assertEqual(len(A.group(rows, A.TRIAL_SPLIT_S)), 1)

    def test_the_window_caps_a_long_run(self):
        rows = trial(0, 600, n=8)
        runs = A.group(rows, 300, window_s=120)
        self.assertGreater(len(runs), 1)
        for run in runs:
            self.assertLessEqual(run[-1]["sensor_ts"] - run[0]["sensor_ts"], 120)

    def test_modules_never_merge(self):
        rows = trial(0, 10, module="A") + trial(5, 10, module="B")
        self.assertEqual(len(A.group(rows, A.TRIAL_SPLIT_S)), 2)


class RecommendationTests(unittest.TestCase):
    def setUp(self):
        self.rows = log([trial(i * 600, 12) for i in range(8)])
        self.trials = A.group(self.rows, A.TRIAL_SPLIT_S)

    def test_gap_is_at_least_twice_the_largest_pause(self):
        rec = A.recommend(self.trials)
        self.assertGreaterEqual(rec["gap_s"], 2 * rec["max_internal_gap_s"])

    def test_window_covers_the_longest_span(self):
        rec = A.recommend(self.trials)
        self.assertGreaterEqual(rec["window_s"], rec["max_span_s"])

    def test_values_are_rounded(self):
        rec = A.recommend(self.trials)
        self.assertEqual(rec["gap_s"] % A.ROUND_S, 0)
        self.assertEqual(rec["window_s"] % A.ROUND_S, 0)

    def test_recommendation_reproduces_its_own_trials(self):
        rec = A.recommend(self.trials)
        ok, n_ref, n_prop = A.check(self.rows, rec["gap_s"], rec["window_s"])
        self.assertTrue(ok)
        self.assertEqual(n_ref, n_prop)
        self.assertEqual(n_ref, len(self.trials))

    def test_a_too_small_gap_fails_the_check(self):
        ok, _, _ = A.check(self.rows, 1, 30)
        self.assertFalse(ok)

    def test_too_few_trials_is_an_error(self):
        with self.assertRaises(ValueError):
            A.recommend(A.group(log([trial(0, 10)]), A.TRIAL_SPLIT_S))

    def test_small_sample_is_warned_about(self):
        rec = A.recommend(A.group(log([trial(i * 600, 10) for i in range(5)]),
                                  A.TRIAL_SPLIT_S))
        self.assertTrue(any("AT-03" in w for w in rec["warnings"]))

    def test_trials_too_close_together_are_flagged(self):
        # One opening with a 200 s internal pause forces a recommended gap
        # wider than the rest before the next trial - the case the warning
        # exists for, and one where the tool must say so rather than return
        # a figure that would merge them.
        rows = log([trial(0, 200, n=2), trial(510, 10),
                    trial(1200, 10), trial(1800, 10), trial(2400, 10)])
        rec = A.recommend(A.group(rows, A.TRIAL_SPLIT_S))
        self.assertEqual(rec["trials"], 5)
        self.assertGreaterEqual(rec["gap_s"], 310)
        self.assertTrue(any("merge" in w for w in rec["warnings"]))


class LoadingTests(unittest.TestCase):
    def write(self, rows):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        for r in rows:
            tmp.write(json.dumps(r) + "\n")
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        return tmp.name

    def test_unsynced_records_are_skipped_and_counted(self):
        rows = trial(0, 10) + trial(600, 10, synced=False)
        loaded, skipped = A.load_jsonl(self.write(rows))
        self.assertEqual(len(loaded), 4)
        self.assertEqual(skipped, 4)

    def test_device_records_are_ignored(self):
        rows = trial(0, 10) + [{
            "record_id": "batt", "module_id": "MOD000",
            "event_type": "LOW_BATTERY", "sensor_ts": 5,
            "clock_synced": True}]
        loaded, skipped = A.load_jsonl(self.write(rows))
        self.assertEqual(len(loaded), 4)
        self.assertEqual(skipped, 0)

    def test_zero_timestamp_is_treated_as_unsynced(self):
        rows = [{"record_id": "x", "module_id": "MOD000",
                 "event_type": "MOVEMENT_EVENT", "sensor_ts": 0,
                 "clock_synced": True}]
        loaded, skipped = A.load_jsonl(self.write(rows))
        self.assertEqual((loaded, skipped), ([], 1))


class CliTests(unittest.TestCase):
    def test_synthetic_run_prints_constants(self):
        self.assertEqual(A.main(["--synthetic", "8"]), 0)

    def test_synthetic_check_passes_on_its_own_recommendation(self):
        rows = A.synthetic(8)
        rec = A.recommend(A.group(rows, A.TRIAL_SPLIT_S))
        self.assertEqual(
            A.main(["--synthetic", "8", "--check",
                    str(rec["gap_s"]), str(rec["window_s"])]), 0)

    def test_too_few_trials_exits_nonzero(self):
        self.assertEqual(A.main(["--synthetic", "2"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
