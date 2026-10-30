#!/usr/bin/env python3
"""Tests for the drift analyzer. Standard library only: python3 -m unittest."""

import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

import analyze_drift as ad


def synthetic(drift_ppm, days=7.0, samples=48, seed=0):
    return ad._synthetic(drift_ppm, days, samples, seed)


class FitTests(unittest.TestCase):
    def test_recovers_positive_drift(self):
        stats = ad.analyse(synthetic(25.0))
        self.assertAlmostEqual(stats["drift_ppm"], 25.0, delta=5.0)

    def test_recovers_negative_drift(self):
        stats = ad.analyse(synthetic(-40.0))
        self.assertAlmostEqual(stats["drift_ppm"], -40.0, delta=5.0)

    def test_recovers_large_drift(self):
        # An RC oscillator can be several percent out.
        stats = ad.analyse(synthetic(-40000.0))
        self.assertAlmostEqual(stats["drift_ppm"], -40000.0, delta=2000.0)

    def test_standard_error_shrinks_with_span(self):
        short = ad.analyse(synthetic(25.0, days=1.0, samples=48))
        long = ad.analyse(synthetic(25.0, days=14.0, samples=48))
        self.assertLess(long["drift_se_ppm"], short["drift_se_ppm"])

    def test_rejects_too_few_samples(self):
        with self.assertRaises(ValueError):
            ad.analyse(synthetic(25.0, samples=2))

    def test_rejects_identical_rtc(self):
        rows = [(1, 1000, 5_000_000, None),
                (2, 1001, 5_000_000, None),
                (3, 1002, 5_000_000, None)]
        with self.assertRaises(ValueError) as ctx:
            ad.analyse(rows)
        self.assertIn("same RTC", str(ctx.exception))


class WarningTests(unittest.TestCase):
    def test_short_span_is_flagged(self):
        stats = ad.analyse(synthetic(25.0, days=0.007, samples=10))
        joined = " ".join(stats["warnings"])
        self.assertIn("quantisation", joined.lower())

    def test_seven_day_span_is_not_flagged_for_shortness(self):
        stats = ad.analyse(synthetic(25.0))
        self.assertFalse(any("under the" in w for w in stats["warnings"]))

    def test_quantisation_floor_is_reported(self):
        stats = ad.analyse(synthetic(25.0))
        # 1 s over 7 days is about 1.65 ppm.
        self.assertAlmostEqual(stats["quantisation_ppm"], 1.65, delta=0.1)

    def test_temperature_correlation_detected(self):
        rows = []
        span = 7 * 86400
        n = 120
        for i in range(n):
            rtc = span * i / (n - 1)
            temp = 10 + 20 * math.sin(math.pi * i / (n - 1))
            # Drift that follows temperature rather than a constant rate.
            extra = 30.0 * temp
            utc = 1_700_000_000 + round(rtc + extra)
            rows.append((i + 1, utc, 1_000_000 + int(rtc * 1e6), round(temp, 1)))
        stats = ad.analyse(rows)
        self.assertIsNotNone(stats["temp_correlation"])
        self.assertGreater(abs(stats["temp_correlation"]), 0.7)
        self.assertTrue(any("temperature" in w for w in stats["warnings"]))


class RecommendationTests(unittest.TestCase):
    def test_recommends_a_finite_lifetime(self):
        rec = ad.analyse(synthetic(25.0))["recommendation"]
        self.assertGreaterEqual(rec["kResidualPpmSteady"], 50)
        self.assertGreater(rec["sync_interval_for_30s_bound_s"], 0)
        self.assertTrue(math.isfinite(rec["sync_interval_for_30s_bound_h"]))

    def test_bigger_residual_shrinks_sync_interval(self):
        tight = ad.analyse(synthetic(25.0, days=14.0, samples=200))["recommendation"]
        loose = ad.analyse(synthetic(25.0, days=1.0, samples=24))["recommendation"]
        self.assertGreaterEqual(loose["kResidualPpmSteady"],
                                tight["kResidualPpmSteady"])
        self.assertLessEqual(loose["sync_interval_for_30s_bound_s"],
                             tight["sync_interval_for_30s_bound_s"])


class CliTests(unittest.TestCase):
    def test_csv_round_trip(self):
        rows = synthetic(25.0)
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
            fh.write("# cycle,utc_s,rtc_us,temp_c\n")
            fh.write("cycle,utc_s,rtc_us,temp_c\n")
            for r in rows:
                fh.write(",".join(str(x) for x in r) + "\n")
            path = fh.name
        try:
            loaded = ad.load_csv(path)
            self.assertEqual(len(loaded), len(rows))
            self.assertAlmostEqual(ad.analyse(loaded)["drift_ppm"], 25.0, delta=5.0)
        finally:
            os.unlink(path)

    def test_cli_json_output(self):
        here = os.path.dirname(os.path.abspath(__file__))
        out = subprocess.run(
            [sys.executable, os.path.join(here, "analyze_drift.py"),
             "--synthetic", "25", "--json"],
            capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        payload = json.loads(out.stdout)
        self.assertIn("drift_ppm", payload)
        self.assertIn("recommendation", payload)
        self.assertAlmostEqual(payload["drift_ppm"], 25.0, delta=5.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
