// drift_bench.cpp — measure the RTC oscillator against network time.
//
// This is a bench sketch, not flight firmware. It prints one CSV line per sync
// and never sleeps the modem between samples, because the point is measurement
// rather than endurance.
//
// The interval is the whole design. AT+QLTS reports whole seconds, so a sample
// pair carries up to a second of quantisation error. At a 10-minute interval
// that is about 1,700 ppm of noise, which is larger than any crystal worth
// measuring. Set kIntervalSeconds to at least 6 hours (21,600) and preferably
// 24 hours, and let it run for a week. analyze_drift.py does the fitting.
//
// Output, one line per cycle:
//   cycle,utc_s,rtc_us,temp_c
// Feed that file to analyze_drift.py.

#include <Arduino.h>
#include <Wire.h>

// ---------------------------------------------------------------------------
// Bench configuration — adjust to the board in front of you
// ---------------------------------------------------------------------------

#define PIN_I2C_SDA       GPIO_NUM_10
#define PIN_I2C_SCL       GPIO_NUM_11
#define PIN_MODEM_TX      GPIO_NUM_17
#define PIN_MODEM_RX      GPIO_NUM_18
#define PIN_MODEM_PWRKEY  GPIO_NUM_12
#define MODEM_BAUD        115200

// At least 6 hours. See the header comment for why.
static const uint32_t kIntervalSeconds = 6UL * 60UL * 60UL;

// How many syncs before the sketch stops. 28 x 6 h is one week.
static const uint16_t kCycles = 28;

HardwareSerial modem(1);

RTC_DATA_ATTR static uint16_t s_cycle = 0;

// ---------------------------------------------------------------------------
// Modem
// ---------------------------------------------------------------------------

static bool wait_for(const char* want, uint32_t timeout_ms) {
    uint32_t start = millis();
    String buf;
    while (millis() - start < timeout_ms) {
        while (modem.available()) {
            char c = (char)modem.read();
            if (c == '\n') {
                if (buf.indexOf(want) >= 0) return true;
                if (buf.indexOf("ERROR") >= 0) return false;
                buf = "";
            } else {
                buf += c;
            }
            if (buf.length() > 256) buf = "";
        }
    }
    return false;
}

static bool at(const char* cmd, const char* want, uint32_t timeout_ms = 2000) {
    modem.print(cmd);
    modem.print("\r\n");
    return wait_for(want, timeout_ms);
}

static bool modem_up() {
    modem.begin(MODEM_BAUD, SERIAL_8N1, PIN_MODEM_RX, PIN_MODEM_TX);

    // Pulse PWRKEY in case the module is off; harmless if it is already on.
    pinMode(PIN_MODEM_PWRKEY, OUTPUT);
    digitalWrite(PIN_MODEM_PWRKEY, LOW);
    delay(100);
    digitalWrite(PIN_MODEM_PWRKEY, HIGH);
    delay(600);
    digitalWrite(PIN_MODEM_PWRKEY, LOW);

    uint32_t start = millis();
    while (millis() - start < 15000) {
        if (at("AT", "OK", 500)) return true;
        delay(250);
    }
    return false;
}

// Returns UTC seconds, or 0 on failure. Whole-second resolution is the limit
// that shapes the whole measurement.
static int64_t network_utc() {
    if (!at("AT+CTZU=1", "OK")) return 0;

    modem.print("AT+QLTS=2\r\n");
    uint32_t start = millis();
    String line;
    while (millis() - start < 5000) {
        while (modem.available()) {
            char c = (char)modem.read();
            if (c == '\n') {
                int idx = line.indexOf("+QLTS:");
                if (idx >= 0) {
                    int q = line.indexOf('"', idx);
                    if (q >= 0) {
                        int yy, mm, dd, hh, mi, ss;
                        if (sscanf(line.c_str() + q + 1,
                                   "%2d/%2d/%2d,%2d:%2d:%2d",
                                   &yy, &mm, &dd, &hh, &mi, &ss) == 6) {
                            int y = 2000 + yy;
                            int era = (y >= 0 ? y : y - 399) / 400;
                            unsigned yoe = (unsigned)(y - era * 400);
                            unsigned doy =
                                (153u * (mm > 2 ? mm - 3 : mm + 9) + 2) / 5
                                + dd - 1;
                            unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
                            long days = (long)era * 146097L + (long)doe - 719468L;
                            return (int64_t)days * 86400LL
                                 + hh * 3600LL + mi * 60LL + ss;
                        }
                    }
                }
                line = "";
            } else {
                line += c;
            }
            if (line.length() > 256) line = "";
        }
    }
    return 0;
}

// ---------------------------------------------------------------------------
// Entry
// ---------------------------------------------------------------------------

void setup() {
    Serial.begin(115200);
    delay(200);

    // Commented header so the analyzer skips it and a human can still read it.
    Serial.println("# cycle,utc_s,rtc_us,temp_c");
    Serial.flush();

    if (!modem_up()) {
        Serial.println("# modem did not answer AT; sleeping one interval");
        Serial.flush();
        esp_deep_sleep((uint64_t)kIntervalSeconds * 1000000ULL);
    }

    int64_t utc = network_utc();
    if (utc == 0) {
        Serial.println("# modem up but time unavailable; sleeping one interval");
        Serial.flush();
        esp_deep_sleep((uint64_t)kIntervalSeconds * 1000000ULL);
    }

    // Sample the RTC as close to the network reply as possible. The modem
    // round trip is a few hundred milliseconds at worst; against a 6 hour
    // interval that is negligible, and it is the same bias every cycle.
    uint64_t rtc_us = rtc_time_get();

    // Temperature is only meaningful for correlation, and the internal sensor
    // is accurate to a few degrees at best. It is logged, not trusted.
    float temp_c = temperatureRead();

    s_cycle++;
    Serial.printf("%u,%lld,%llu,%.1f\n",
                  (unsigned)s_cycle,
                  (long long)utc,
                  (unsigned long long)rtc_us,
                  (double)temp_c);
    Serial.flush();

    if (s_cycle >= kCycles) {
        Serial.println("# done; copy the lines above into a CSV and run "
                       "analyze_drift.py");
        Serial.flush();
        while (true) delay(10000);   // stay awake so the log can be captured
    }

    esp_deep_sleep((uint64_t)kIntervalSeconds * 1000000ULL);
}

void loop() {
    // Never reached: setup() ends in deep sleep or a halt.
}
