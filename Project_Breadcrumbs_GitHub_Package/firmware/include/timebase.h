// timebase.h — monotonic time that survives deep sleep, disciplined by the modem.
//
// The device spends almost all of its life asleep. millis() and the ESP timer
// both restart on every wake, so neither can timestamp an event that happened
// between them. The RTC timer keeps counting through deep sleep, which makes it
// the only usable monotonic source here.
//
// The RTC runs on a slow oscillator that is not accurate, so a bare conversion
// drifts. This module measures the drift at every network sync and applies it,
// and reports a per-record uncertainty so a timestamp is never mistaken for
// something more precise than it is (DATA_MODEL §4).

#pragma once

#include <stdint.h>

// UTC seconds, or 0 when never synced. Advanced by the RTC between syncs and
// corrected by the measured drift.
int64_t timebase_utc_now();

// True once a network time has been accepted and the RTC has not lost power
// since. Records carry this verbatim.
bool timebase_is_synced();

// Half-width of the error bound, in seconds, at the current moment. Grows with
// time since sync; shrinks as the drift estimate settles.
uint32_t timebase_uncertainty_s();

// Accept a network time. Updates the drift estimate if enough time has passed
// since the previous sync to measure it, then rebases.
void timebase_sync(int64_t utc_s);

// Measured RTC rate error in ppm. Exposed for diagnostics and the bench report;
// positive means the RTC runs fast.
int32_t timebase_drift_ppm();

// Number of accepted syncs. Two or more means the drift estimate is meaningful.
uint32_t timebase_sync_count();
