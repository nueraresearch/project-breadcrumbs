#!/usr/bin/env python3
"""Fit RTC drift from a bench log and recommend the constants in config.h.

The device's RTC runs on a slow oscillator of unknown rate. The firmware
measures it against network time, but the *residual* it assumes
(kResidualPpmSteady) is a guess until someone measures the real oscillator.
This turns a bench log into that number.

Why least squares rather than first-and-last: network time arrives in whole
seconds, so any single pair of samples carries up to a second of quantisation
error. Fitting a line through every sample averages that error down, and the
standard error tells you whether you have measured anything at all.

Usage:
    python3 analyze_drift.py bench_log.csv
    python3 analyze_drift.py bench_log.csv --json
    python3 analyze_drift.py --synthetic 25 --days 7     # self-test
"""

from __future__ import annotations

import argparse
import json
import math
import sys

# AT+QLTS reports whole seconds. Every UTC value carries up to this much
# quantisation error, which sets the shortest useful measurement span.
QUANTUM_S = 1.0

# Below this span the quantisation floor dominates any plausible oscillator.
MIN_USEFUL_SPAN_S = 50_000


def load_csv(path: str):
    """Reads cycle,utc_s,rtc_us[,temp_c]. Comment and header lines are skipped."""
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 3:
                continue
            if parts[0].lower().startswith("cycle"):
                continue
            try:
                cycle = int(parts[0])
                utc_s = float(parts[1])
                rtc_us = int(parts[2])
            except ValueError:
                raise ValueError(f"{path}:{lineno}: expected cycle,utc_s,rtc_us")
            temp = None
            if len(parts) > 3 and parts[3] not in ("", "nan", "NaN"):
                try:
                    temp = float(parts[3])
                except ValueError:
                    temp = None
            rows.append((cycle, utc_s, rtc_us, temp))
    return rows


def fit(points):
    """Least-squares fit of utc against rtc.

    points: list of (rtc_seconds, utc_seconds), both relative to the first sample.
    slope is (true seconds)/(rtc seconds); drift_ppm = (slope - 1) * 1e6.
    """
    n = len(points)
    if n < 3:
        raise ValueError(f"need at least 3 syncs, got {n}")

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    mx = sum(xs) / n
    my = sum(ys) / n

    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        raise ValueError("all samples share the same RTC reading")

    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx

    residuals = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    rms = math.sqrt(sum(r * r for r in residuals) / n)

    dof = max(n - 2, 1)
    s2 = sum(r * r for r in residuals) / dof
    slope_se = math.sqrt(s2 / sxx)

    span = xs[-1] - xs[0]
    drift_ppm = (slope - 1.0) * 1e6

    result = {
        "n": n,
        "span_s": span,
        "span_days": span / 86400.0,
        "drift_ppm": drift_ppm,
        "drift_se_ppm": slope_se * 1e6,
        "rms_residual_s": rms,
        "max_abs_residual_s": max(abs(r) for r in residuals),
        "quantisation_ppm": (QUANTUM_S / span * 1e6) if span > 0 else float("inf"),
        "residuals": residuals,
        "xs": xs,
    }
    return result


def analyse(raw):
    """Takes absolute samples and returns the fit with diagnostics."""
    if len(raw) < 3:
        raise ValueError(f"need at least 3 syncs, got {len(raw)}")

    utc0 = raw[0][1]
    rtc0 = raw[0][2]
    points = [((row[2] - rtc0) / 1e6, row[1] - utc0) for row in raw]

    stats = fit(points)

    temps = [row[3] for row in raw]
    if all(t is not None for t in temps) and len(set(temps)) > 1:
        stats["temp_correlation"] = _pearson(stats["residuals"], temps)
        stats["temp_min_c"] = min(temps)
        stats["temp_max_c"] = max(temps)
    else:
        stats["temp_correlation"] = None

    stats["warnings"] = _warnings(stats)
    stats["recommendation"] = _recommendation(stats)
    return stats


def _pearson(a, b) -> float:
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((y - mb) ** 2 for y in b))
    if da == 0 or db == 0:
        return 0.0
    return num / (da * db)


def _warnings(stats) -> list[str]:
    out = []

    if stats["span_s"] < MIN_USEFUL_SPAN_S:
        out.append(
            f"span is {stats['span_s'] / 3600:.1f} h, under the "
            f"{MIN_USEFUL_SPAN_S / 3600:.0f} h minimum. Whole-second network "
            "time makes the quantisation floor "
            f"{stats['quantisation_ppm']:.0f} ppm here, so any drift figure "
            "below that is noise.")

    if abs(stats["drift_ppm"]) < 3 * stats["quantisation_ppm"]:
        out.append(
            "drift is not separable from quantisation: run longer, or repeat "
            "the measurement over several days and pool the fits.")

    r = stats.get("temp_correlation")
    if r is not None and abs(r) > 0.7:
        out.append(
            f"residuals correlate with temperature (r={r:+.2f}). The oscillator "
            "rate is not constant, so one ppm figure will not hold across a "
            "deployment; widen kResidualPpmSteady rather than tightening it.")

    if stats["drift_se_ppm"] > max(10.0, abs(stats["drift_ppm"]) / 2):
        out.append(
            "standard error is large relative to the estimate. More samples "
            "spread over a longer span will improve it.")

    return out


def _recommendation(stats) -> dict:
    span = stats["span_s"]
    # What the firmware should assume when it cannot measure again: three
    # standard errors, or the observed non-linearity, whichever is larger.
    linearity_ppm = (stats["max_abs_residual_s"] / span * 1e6) if span > 0 else 0.0
    steady = max(50.0, 3.0 * stats["drift_se_ppm"], linearity_ppm)

    # Sync interval that keeps the bound under 30 s at that residual.
    interval_s = 30.0 / (steady / 1e6) if steady > 0 else float("inf")

    return {
        "kResidualPpmSteady": int(math.ceil(steady)),
        "sync_interval_for_30s_bound_s": int(interval_s),
        "sync_interval_for_30s_bound_h": round(interval_s / 3600.0, 1),
        "measured_drift_ppm": round(stats["drift_ppm"], 1),
    }


def format_report(stats) -> str:
    rec = stats["recommendation"]
    lines = [
        "RTC drift measurement",
        "=" * 40,
        f"samples            {stats['n']}",
        f"span               {stats['span_days']:.2f} days "
        f"({stats['span_s']:.0f} s)",
        f"measured drift     {stats['drift_ppm']:+.1f} ppm "
        f"(± {stats['drift_se_ppm']:.1f})",
        f"quantisation floor {stats['quantisation_ppm']:.1f} ppm",
        f"residual RMS       {stats['rms_residual_s']:.3f} s",
        f"residual max       {stats['max_abs_residual_s']:.3f} s",
    ]
    if stats.get("temp_correlation") is not None:
        lines.append(
            f"temp correlation   r={stats['temp_correlation']:+.2f} "
            f"({stats['temp_min_c']:.1f}–{stats['temp_max_c']:.1f} °C)")
    lines += [
        "",
        "Recommended for firmware/include/config.h:",
        f"  #define kResidualPpmSteady  {rec['kResidualPpmSteady']}",
        "",
        f"Sync every {rec['sync_interval_for_30s_bound_h']:.1f} h keeps the "
        "clock bound under ±30 s.",
    ]
    if stats["warnings"]:
        lines.append("")
        lines.append("Warnings:")
        for w in stats["warnings"]:
            lines.append(f"  ! {w}")
    return "\n".join(lines)


def _synthetic(drift_ppm: float, days: float, samples: int, seed: int = 0):
    """Generates a log with known drift, quantised the way real time arrives."""
    import random
    rng = random.Random(seed)
    span = days * 86400.0
    rows = []
    for i in range(samples):
        rtc_s = span * i / (samples - 1)
        true_utc = 1_700_000_000.0 + rtc_s * (1.0 + drift_ppm / 1e6)
        # Network time is whole seconds, with occasional jitter from the tower.
        utc = round(true_utc + (rng.uniform(-0.4, 0.4) if i else 0.0))
        rows.append((i + 1, utc, 1_000_000 + int(round(rtc_s * 1e6)), 21.0))
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("log", nargs="?", help="CSV: cycle,utc_s,rtc_us[,temp_c]")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--synthetic", type=float, metavar="PPM",
                    help="generate a log with this drift instead of reading a file")
    ap.add_argument("--days", type=float, default=7.0)
    ap.add_argument("--samples", type=int, default=48)
    args = ap.parse_args(argv)

    if args.synthetic is not None:
        raw = _synthetic(args.synthetic, args.days, args.samples)
    elif args.log:
        raw = load_csv(args.log)
    else:
        ap.error("provide a log path or --synthetic")

    try:
        stats = analyse(raw)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        out = {k: v for k, v in stats.items() if k not in ("residuals", "xs")}
        print(json.dumps(out, indent=2))
    else:
        print(format_report(stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
