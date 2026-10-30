// main.cpp — wake dispatch, capture, arming, upload.
//
// There is no loop(). The device wakes, handles exactly one cause, then sleeps.
// That structure is what makes a 30-day cycle on a single cell possible, and it
// is also a privacy control: with no running loop there is no listening
// surface for a command to reach.
//
// HW-30 is enforced structurally. capture_burst() is static, file-local, and
// called from exactly one place: the light path in handle_light_trigger().
// No UART, BLE or network handler exists in this build that could call it.

#include <Arduino.h>
#include <esp_camera.h>
#include <esp_sleep.h>
#include <Wire.h>
#include <stdio.h>
#include <Adafruit_VEML7700.h>
#include <Adafruit_Sensor.h>

#include "config.h"
#include "modem.h"
#include "records.h"
#include "store.h"
#include "timebase.h"

// ---------------------------------------------------------------------------
// State that survives deep sleep
// ---------------------------------------------------------------------------

RTC_DATA_ATTR static bool     s_armed = false;
RTC_DATA_ATTR static uint32_t s_last_trigger_ms = 0;
RTC_DATA_ATTR static uint32_t s_last_motion_ms = 0;
RTC_DATA_ATTR static uint32_t s_boot_count = 0;

static Adafruit_VEML7700 s_lux = Adafruit_VEML7700();

// The accelerometer is used through its interrupt pin only. Motion magnitude is
// not read yet, so kMotionThresholdMg is a placeholder until the part is
// configured (README §2).

enum class WakeCause { Light, Motion, Timer, ColdBoot };

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Stamps a record with the current time and the bound on its accuracy. Every
// record site goes through here so the two can never disagree.
static void stamp_now(Record& r) {
    r.sensor_ts           = timebase_utc_now();
    r.clock_synced        = timebase_is_synced();
    r.clock_uncertainty_s = timebase_uncertainty_s();
}

static uint16_t battery_mv() {
    int raw = analogRead(PIN_BATTERY_ADC);
    float v = (raw / 4095.0f) * kAdcReferenceMv * kBatteryDivider;
    return (uint16_t)(v + 0.5f);
}

static bool armed_now() {
    // Reed switch closed to ground when the magnet is removed at placement.
    return digitalRead(PIN_REED_SWITCH) == HIGH;
}

static void persist(const Record& r) {
    char json[512];
    size_t n = record_to_json(r, json, sizeof(json));
    if (n == 0) return;
    store_put_record(r, json, n);
}

// Record and then attempt an upload. Upload failure is not an error: the
// record stays queued and is retried on the next wake (HW-08).
static void persist_and_flush(const Record& r) {
    persist(r);
    // Flush is deliberately left to the timer path to avoid paying a modem
    // attach on every event; see upload_pending().
}

// ---------------------------------------------------------------------------
// Arming (HW-32, D-63)
// ---------------------------------------------------------------------------

static void check_arming() {
    bool now = armed_now();
    if (now == s_armed) return;

    if (now && !s_armed) {
        // Magnet removed: the operator has finished sealing and placing.
        Record r;
        record_init(r, EventType::DeploymentClosed);
        stamp_now(r);
        r.battery_mv = battery_mv();
        persist(r);
        s_armed = true;
    } else {
        // Magnet present: disarmed, so retrieval or service is under way.
        s_armed = false;
    }
}

// ---------------------------------------------------------------------------
// Imaging — reachable only from the light path (HW-23, HW-30)
// ---------------------------------------------------------------------------

static bool camera_begin() {
    camera_config_t cfg = {};
    cfg.ledc_channel = LEDC_CHANNEL_0;
    cfg.ledc_timer   = LEDC_TIMER_0;
    cfg.pin_d0 = 15; cfg.pin_d1 = 16; cfg.pin_d2 = 14; cfg.pin_d3 = 48;
    cfg.pin_d4 = 47; cfg.pin_d5 = 21; cfg.pin_d6 = 20; cfg.pin_d7 = 19;
    cfg.pin_xclk = 45; cfg.pin_pclk = 38; cfg.pin_vsync = 39; cfg.pin_href = 40;
    cfg.pin_sccb_sda = PIN_I2C_SDA; cfg.pin_sccb_scl = PIN_I2C_SCL;
    cfg.pin_pwdn = -1; cfg.pin_reset = -1;
    cfg.xclk_freq_hz = 20000000;
    cfg.pixel_format = PIXFORMAT_JPEG;
    cfg.frame_size   = kFrameSize;
    cfg.jpeg_quality = kJpegQuality;
    cfg.fb_count     = 2;
    cfg.grab_mode    = CAMERA_GRAB_LATEST;
    return esp_camera_init(&cfg) == ESP_OK;
}

// Three frames at 0 / 0.5 / 1.5 s (D-64), exposure-bracketed because the first
// frame is expected to be blown when a dark cavity opens onto daylight.
static uint8_t capture_burst(const char* record_id) {
    digitalWrite(PIN_CAM_POWER, HIGH);
    delay(kCameraSettleMs);

    uint8_t stored = 0;
    if (!camera_begin()) {
        digitalWrite(PIN_CAM_POWER, LOW);
        return 0;
    }

    uint32_t t0 = millis();
    for (uint8_t i = 0; i < kBurstFrameCount; ++i) {
        uint32_t due = kBurstOffsetsMs[i];
        while (millis() - t0 < due) delay(5);

        sensor_t* s = esp_camera_sensor_get();
        if (s) {
            s->set_exposure_ctrl(s, 0);
            s->set_aec_value(s, kBurstExposures[i][0]);
        }

        camera_fb_t* fb = esp_camera_fb_get();
        if (fb) {
            if (store_put_image(record_id, (uint8_t)(i + 1), fb->buf, fb->len)) {
                stored++;
            }
            esp_camera_fb_return(fb);
        }
    }

    esp_camera_deinit();
    digitalWrite(PIN_CAM_POWER, LOW);
    return stored;
}

// ---------------------------------------------------------------------------
// Wake handlers
// ---------------------------------------------------------------------------

static void handle_light_trigger() {
    // Not armed: the operator is still sealing or carrying the box. Carriage
    // must not be recorded as an event (HW-32).
    if (!s_armed) return;

    uint32_t now = millis();
    if (s_last_trigger_ms && (now - s_last_trigger_ms) < kTriggerLockoutMs) return;
    s_last_trigger_ms = now;

    // Confirm the step rather than trusting the interrupt alone.
    s_lux.begin();
    delay(10);
    float lux = s_lux.readLux();
    if (lux < kLightThresholdLux) return;

    uint32_t stable_from = millis();
    while (millis() - stable_from < kLightDebounceMs) {
        delay(10);
        if (s_lux.readLux() < kLightThresholdLux) return;   // flicker, not a lid
    }

    Record r;
    record_init(r, EventType::LightTrigger);
    stamp_now(r);
    r.battery_mv = battery_mv();
    r.lux        = lux;

    // The camera is powered and read here and nowhere else.
    uint8_t frames = capture_burst(r.record_id);
    r.frame_count = frames;

    if (frames == 0) {
        r.type = EventType::LightTrigger;              // opening still happened
        r.flags |= kFlagIncompleteBurst | kFlagDeviceMalfunction;
    } else if (frames < kBurstFrameCount) {
        r.type = EventType::ImageCapturePartial;
        r.flags |= kFlagIncompleteBurst;
    } else {
        r.type = EventType::ImageCaptureComplete;
    }

    persist_and_flush(r);
}

static void handle_motion() {
    // Movement is logged and never images (HW-23, HW-24). There is no camera
    // call in this function and there must never be one.
    uint32_t now = millis();
    if (s_last_motion_ms && (now - s_last_motion_ms) < kMotionLockoutMs) return;
    s_last_motion_ms = now;

    Record r;
    record_init(r, EventType::MovementEvent);
    stamp_now(r);
    r.battery_mv = battery_mv();
    persist(r);
}

static void handle_timer() {
    // Periodic health: battery, a location fix, and a flush of the queue.
    Record r;
    record_init(r, EventType::LocationFix);
    stamp_now(r);
    r.battery_mv = battery_mv();

    if (modem_power_on()) {
        int64_t utc = 0;
        if (modem_sync_time(&utc)) {
            // Disciplines the RTC as a side effect: the drift estimate is
            // updated from the gap since the last sync, not from a fixed value.
            timebase_sync(utc);
            stamp_now(r);   // now reflects the corrected base
        }

        double lat = 0, lon = 0;
        uint16_t acc = 0;
        uint8_t method = 0;
        if (modem_location(&lat, &lon, &acc, &method, kLocationTimeoutMs)) {
            r.location_valid = true;
            r.lat = lat; r.lon = lon;
            r.loc_method = (LocationMethod)method;
            r.loc_accuracy_m = acc;
        } else {
            r.flags |= kFlagMissingLocation;
        }
        modem_enable_psm();
        modem_power_off();
    } else {
        r.flags |= kFlagMissingLocation;
    }

    if (r.battery_mv < kLowBatteryMv) {
        Record lb;
        record_init(lb, EventType::LowBattery);
        stamp_now(lb);
        lb.battery_mv = r.battery_mv;
        persist(lb);
    }

    persist(r);
}

// Uploads the queue, oldest first. Runs on the timer path only, so an event
// never pays for a modem attach at the moment it happens.
//
// Order matters. The record JSON goes first, because the frame routes are
// addressed under it. Frames then go 1..3 ascending, and the record is removed
// only when every frame present on disk has been confirmed. A failure at any
// point leaves the record in place with its per-frame markers intact, so the
// next flush resumes rather than restarting.
static bool post_record_json(const char* record_id) {
    char body[512];
    size_t len = store_read_record(record_id, body, sizeof(body) - 1);
    if (len == 0) return false;
    body[len] = '\0';

    bool ok = false;
    uint32_t backoff = kUploadRetryBaseMs;
    for (uint8_t attempt = 0; attempt < kUploadAttempts && !ok; ++attempt) {
        ok = modem_http_post(kUploadHost, kUploadPath,
                             (const uint8_t*)body, len);
        if (!ok) {
            delay(backoff);
            backoff = min(backoff * 2, kUploadRetryMaxMs);
        }
    }
    return ok;
}

static bool upload_frame(const char* record_id, uint8_t frame,
                         size_t size, uint32_t* budget) {
    if (*budget == 0) return false;   // flush allowance spent

    char path[96];
    snprintf(path, sizeof(path), "/v1/records/%s/images/%u",
             record_id, (unsigned)frame);

    bool ok = false;
    uint32_t backoff = kUploadRetryBaseMs;

    for (uint8_t attempt = 0; attempt < kUploadAttempts && !ok; ++attempt) {
        // Re-open for each attempt: a failed stream has already been consumed
        // and cannot simply be retried from its current position.
        void* src = store_open_image(record_id, frame);
        if (!src) return false;

        ok = modem_http_post_stream(kUploadHost, path, size,
                                    store_read_image_chunk, src,
                                    QHTTP_CT_BINARY);
        store_close_image(src);

        if (!ok) {
            delay(backoff);
            backoff = min(backoff * 2, kUploadRetryMaxMs);
        }
    }

    if (ok) {
        store_mark_image_uploaded(record_id, frame);
        (*budget)--;
    }
    return ok;
}

static bool upload_frames(const char* record_id, uint32_t* budget) {
    uint8_t present = store_image_mask(record_id);
    uint8_t done    = store_uploaded_image_mask(record_id);
    uint8_t todo    = (uint8_t)(present & ~done);

    for (uint8_t frame = 1; frame <= 3; ++frame) {
        if (!(todo & (uint8_t)(1u << (frame - 1)))) continue;

        // Size is read before streaming so QHTTPPOST gets the exact length;
        // the firmware refuses to send a body of the wrong size.
        void* probe = store_open_image(record_id, frame);
        if (!probe) continue;   // marker without a file; nothing to send
        size_t size = store_image_size(probe);
        store_close_image(probe);

        if (size == 0) continue;
        if (!upload_frame(record_id, frame, size, budget)) return false;
    }
    return true;
}

static void upload_pending() {
    char ids[kMaxRecordsPerFlush][40];
    size_t n = store_pending(ids, kMaxRecordsPerFlush);
    if (n == 0) return;

    if (!modem_power_on()) return;

    uint32_t frame_budget = kMaxFramesPerFlush;

    for (size_t i = 0; i < n; ++i) {
        if (!post_record_json(ids[i])) continue;

        // Frames are best-effort within the flush budget. If the budget runs
        // out the record stays queued and the remainder goes next cycle.
        if (!upload_frames(ids[i], &frame_budget)) continue;

        // Only now is the record complete: JSON stored and every frame on disk
        // confirmed. Removing it earlier would orphan the images.
        store_remove(ids[i]);
    }

    modem_power_off();
}

// ---------------------------------------------------------------------------
// Sleep
// ---------------------------------------------------------------------------

static void deep_sleep(uint32_t seconds) {
    // The light and motion interrupts are the only always-on loads.
    esp_sleep_enable_ext1_wakeup(
        (1ULL << PIN_LIGHT_INT) | (1ULL << PIN_ACCEL_INT),
        ESP_EXT1_WAKEUP_ANY_HIGH);
    esp_sleep_enable_timer_wakeup((uint64_t)seconds * 1000000ULL);
    esp_deep_sleep_start();
}

// ---------------------------------------------------------------------------
// Entry
// ---------------------------------------------------------------------------

void setup() {
    s_boot_count++;

    pinMode(PIN_CAM_POWER, OUTPUT);
    digitalWrite(PIN_CAM_POWER, LOW);   // camera stays unpowered between events

    // The sensors hang off a shared I2C bus; without this the light read in the
    // wake path returns nothing and every opening looks like a flicker.
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);

    pinMode(PIN_REED_SWITCH, INPUT_PULLDOWN);
    pinMode(PIN_LIGHT_INT, INPUT);
    pinMode(PIN_ACCEL_INT, INPUT);

    if (!store_init()) {
        // No storage means nothing this device records survives. Sleep long
        // and let the operator inspect it rather than burn the cell retrying.
        deep_sleep(3600);
    }

    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
    WakeCause wake = WakeCause::Timer;

    if (cause == ESP_SLEEP_WAKEUP_UNDEFINED) {
        wake = WakeCause::ColdBoot;
        Record r;
        record_init(r, EventType::PowerReset);
        stamp_now(r);
        r.battery_mv = battery_mv();
        persist(r);
    } else if (cause == ESP_SLEEP_WAKEUP_EXT1) {
        uint64_t mask = esp_sleep_get_ext1_wakeup_status();
        if (mask & (1ULL << PIN_LIGHT_INT))      wake = WakeCause::Light;
        else if (mask & (1ULL << PIN_ACCEL_INT)) wake = WakeCause::Motion;
    }

    check_arming();

    if (wake == WakeCause::Light) {
        handle_light_trigger();
    } else if (wake == WakeCause::Motion) {
        handle_motion();
    } else {
        handle_timer();
        upload_pending();
    }

    deep_sleep((uint32_t)(kLocationIntervalMs / 1000));
}
