#include "timebase.h"
#include "config.h"

#include <Arduino.h>

// rtc_time_get() reads the RTC timer, which is in the always-on domain and
// therefore keeps counting while the CPU is in deep sleep. It is an SoC-level
// API rather than a stable public one, so it is guarded: if a future core drops
// it, the fallback still compiles and the uncertainty model degrades honestly
// instead of silently claiming accuracy it does not have.
#if defined(__has_include)
#  if __has_include("soc/rtc.h")
#    include "soc/rtc.h"
#    define BREADCRUMBS_RTC_TIMEBASE 1
#  endif
#endif

namespace {

RTC_DATA_ATTR int64_t  s_utc_base_s  = 0;   // UTC at the last accepted sync
RTC_DATA_ATTR uint64_t s_rtc_base_us = 0;   // RTC reading at that instant
RTC_DATA_ATTR int32_t  s_drift_ppm   = 0;   // measured rate error
RTC_DATA_ATTR uint32_t s_sync_count  = 0;
RTC_DATA_ATTR bool     s_have_sync   = false;

uint64_t raw_us() {
#ifdef BREADCRUMBS_RTC_TIMEBASE
    return rtc_time_get();
#else
    // Loses the sleep interval. Kept only so the project builds; the drift
    // model cannot rescue a timebase that stops while asleep.
    return (uint64_t)esp_timer_get_time();
#endif
}

// Seconds elapsed since the base, uncorrected.
int64_t raw_elapsed_s(uint64_t now_us) {
    if (now_us <= s_rtc_base_us) return 0;
    return (int64_t)((now_us - s_rtc_base_us) / 1000000ULL);
}

}  // namespace

bool timebase_is_synced() { return s_have_sync; }

int32_t timebase_drift_ppm() { return s_drift_ppm; }

uint32_t timebase_sync_count() { return s_sync_count; }

int64_t timebase_utc_now() {
    if (!s_have_sync) return 0;

    uint64_t now = raw_us();

    // The RTC counter went backwards, so the always-on domain lost power and
    // the base is meaningless. Better to report unsynced than to emit a
    // confidently wrong timestamp.
    if (now < s_rtc_base_us) {
        s_have_sync = false;
        return 0;
    }

    int64_t elapsed = raw_elapsed_s(now);
    int64_t correction = (elapsed * (int64_t)s_drift_ppm) / 1000000;
    return s_utc_base_s + elapsed + correction;
}

uint32_t timebase_uncertainty_s() {
    if (!s_have_sync) return 0;

    uint64_t now = raw_us();
    if (now < s_rtc_base_us) return 0;

    int64_t elapsed = raw_elapsed_s(now);

    // Before two syncs the rate is unknown and the bound has to be the worst
    // case for this class of oscillator. After that the residual is the error
    // left by the smoothed estimate, not the raw drift.
    int32_t residual_ppm =
        (s_sync_count >= 2) ? kResidualPpmSteady : kResidualPpmCold;

    int64_t u = (elapsed * (int64_t)residual_ppm) / 1000000 + 1;
    if (u > 3600) u = 3600;   // beyond an hour the record is ordering-only
    return (uint32_t)u;
}

void timebase_sync(int64_t utc_s) {
    if (utc_s <= 0) return;

    uint64_t now = raw_us();

    // Measure the oscillator against the network before rebasing. This only
    // means something if enough real time has passed for the error to exceed
    // the network's own resolution.
    if (s_have_sync && now > s_rtc_base_us) {
        int64_t raw_s  = raw_elapsed_s(now);
        int64_t true_s = utc_s - s_utc_base_s;

        if (raw_s >= (int64_t)kMinIntervalForDriftS &&
            llabs(true_s - raw_s) <= (int64_t)kMaxPlausibleDriftS) {

            int32_t ppm = (int32_t)(((true_s - raw_s) * 1000000LL) / raw_s);
            if (ppm >  kMaxDriftPpm) ppm =  kMaxDriftPpm;
            if (ppm < -kMaxDriftPpm) ppm = -kMaxDriftPpm;

            if (s_sync_count >= 2) {
                // Weighted blend: a single noisy sample should not swing the
                // correction the whole device depends on.
                s_drift_ppm = (int32_t)((3LL * s_drift_ppm + ppm) / 4);
            } else {
                s_drift_ppm = ppm;
            }
        }
        // A wild disagreement means either the RTC jumped or the network time
        // is wrong. Rebase without touching the drift estimate.
    }

    s_utc_base_s  = utc_s;
    s_rtc_base_us = now;
    s_have_sync   = true;
    if (s_sync_count < 0xFFFFFFFFu) s_sync_count++;
}
