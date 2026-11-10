# Bench harness — measuring the RTC oscillator

**Status:** The analyzer runs and is tested here (`python3 -m unittest test_analyze_drift.py`, 13 tests). The sketch is written but uncompiled and unrun, like the rest of the firmware.

**Purpose:** replace the guessed `kResidualPpmSteady` in `config.h` with a measured value.

## 1. Why this needs a whole week

`AT+QLTS` reports **whole seconds**. Every UTC sample therefore carries up to ±1 s of quantisation error, and that error sets a floor on what can be measured:

| Sample span | Quantisation floor |
|---|---:|
| 10 minutes | ~1,700 ppm |
| 6 hours | ~46 ppm |
| 24 hours | ~12 ppm |
| 7 days | ~1.7 ppm |

A typical 32.768 kHz crystal is accurate to 20–50 ppm, and an RC oscillator is far worse. **A ten-minute test cannot see the thing you are trying to measure** — it reports the quantisation, not the oscillator. The analyzer says so explicitly rather than printing a confident number.

Run for **at least six hours per sample, ideally 24, for a week or more.** The sketch defaults to 6 h × 28 cycles.

## 2. Running it

```bash
cd firmware/bench
pio run -t upload
pio device monitor --baud 115200 | tee bench_log.csv
```

Each wake emits one line:

```
cycle,utc_s,rtc_us,temp_c
1,1793500000,1205000211,21.4
```

Leave it running. At the end the sketch halts and says so rather than sleeping forever, so the log is complete.

## 3. Analysing it

```bash
python3 analyze_drift.py bench_log.csv
```

```
RTC drift measurement
========================================
samples            168
span               7.00 days (604800 s)
measured drift     +23.4 ppm (± 0.4)
quantisation floor 1.7 ppm
residual RMS       0.28 s
residual max       0.61 s
temp correlation   r=+0.81 (14.0-29.0 C)

Recommended for firmware/include/config.h:
  #define kResidualPpmSteady  150

Sync every 55.6 h keeps the clock bound under +/-30 s.

  ! residuals correlate with temperature (r=+0.81). The oscillator rate is not
    constant, so one ppm figure will not hold across a deployment; widen
    kResidualPpmSteady rather than tightening it.
```

The recommendation is deliberately conservative: three standard errors, or the observed non-linearity, whichever is larger. A tight figure that only holds at one temperature is worse than a loose one that holds all year.

`--json` gives the same thing machine-readable. `--synthetic 25 --days 7` generates a known-drift log so you can check the tool before trusting it.

Self-test:

```bash
python3 -m unittest test_analyze_drift.py -v
```

## 4. What to do with the answer

1. Set `kResidualPpmSteady` in `firmware/include/config.h` to the recommendation.
2. Pick a sync interval from the output — it is the interval that keeps the clock bound under ±30 s at that residual.
3. Leave `kResidualPpmCold` alone. It governs the period *before* the first two syncs, when nothing is known and 50,000 ppm is the honest worst case.
4. Record the measurement in `docs/hardware/` alongside the other bench results.

## 5. Known limits

- **The network is not truth.** Tower time is typically within a second but is not an atomic reference; errors partly average out across a fit and partly do not.
- **Temperature dominates.** The internal sensor is accurate to a few degrees, which is enough to show correlation but not to model it. Expect the residual to be larger in a real deployment where the box sees sun.
- **The modem round trip biases each sample** by its own latency. It is small against a 6-hour interval and roughly constant, so it moves the intercept rather than the slope — but it is not zero.
- **This measures the board, not the enclosure.** A deployed module runs hotter and colder than a bench one.

## Measuring the opening and carry window

The server groups records into episodes with two constants in `server/sequences.py`: `GAP_S` (180 s) and `WINDOW_S` (900 s). Both were chosen before any opening had been observed, and both are marked as assumptions wherever they are described. `analyze_sequences.py` replaces them with numbers, the same way `analyze_drift.py` replaces the RTC residual.

**Procedure.**

1. Flash a module with production firmware, arm it at placement, and run scripted trials. One trial is: open the lid, lift the package, carry it about ten metres, set it down.
2. Leave at least five minutes between trials, so the tool can tell one trial from the next.
3. Collect the records as JSONL — one record per line, the same shape the device uploads — or point the tool straight at an ingest database.
4. Run the analyzer, then paste the two constants into `server/sequences.py` and bump `RULE_VERSION`.

```bash
python3 analyze_sequences.py trials.jsonl
python3 analyze_sequences.py --db ../../server/data/records.db
python3 analyze_sequences.py trials.jsonl --check 60 120
```

**What it computes.** Within each trial, the span from the first record to the last and the largest pause between consecutive records. The recommendation is twice the largest observed pause and one and a half times the longest observed span, both rounded up to 30 s. Those margins are a judgement, not a confidence bound, and the report prints the observed maximum next to each recommendation so the margin stays visible.

**It refuses to guess.** Fewer than five trials is an error rather than a number. Records whose clock never synced are skipped and counted, because a trial measured on an unsynced clock is bounded by ±18 minutes rather than ±43 seconds. If the recommended gap would merge two trials, the tool says so instead of returning a figure that cannot distinguish them. `--check` tests a proposed pair against the log and exits non-zero on any mismatch.

**Thirty trials is the AT-03 figure.** Five produces a figure; fewer than thirty deserves to be quoted with its sample size attached, and the tool says so.

**Until this has run, the server's constants stay as they are.** A figure fitted to a handful of synthetic trials would be worse than an assumption, because it would look measured.
