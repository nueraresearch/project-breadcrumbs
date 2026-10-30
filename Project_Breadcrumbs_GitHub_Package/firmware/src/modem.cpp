#include "modem.h"
#include "config.h"

#include <Arduino.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// NOTE: the AT sequences below follow the BG95 command set but have not been
// run against a module. Firmware revisions differ in details — notably the
// order of QHTTPPOST arguments and whether the HTTP status arrives as a
// +QHTTPPOST URC or inside the QHTTPREAD exchange. Both forms are accepted
// below, and a missing status is treated as failure rather than assumed
// success. Verify against the module's own AT manual before trusting it.

namespace {

HardwareSerial s_modem(1);
bool s_ready = false;

// Reads until `want` appears or timeout. Copies the last response line into
// `out` when provided.
bool expect(const char* want, uint32_t timeout_ms, char* out = nullptr,
            size_t cap = 0) {
    uint32_t start = millis();
    String buf;
    while (millis() - start < timeout_ms) {
        while (s_modem.available()) {
            char c = (char)s_modem.read();
            buf += c;
            if (c == '\n') {
                if (buf.indexOf(want) >= 0) {
                    if (out && cap) {
                        strncpy(out, buf.c_str(), cap - 1);
                        out[cap - 1] = '\0';
                    }
                    return true;
                }
                if (buf.indexOf("ERROR") >= 0) return false;
                buf = "";
            }
            if (buf.length() > 512) buf = "";
        }
    }
    return false;
}

bool cmd(const char* c, const char* want, uint32_t timeout_ms = 2000) {
    s_modem.print(c);
    s_modem.print("\r\n");
    return expect(want, timeout_ms);
}

bool http_config(uint8_t content_type) {
    if (!cmd("AT+QHTTPCFG=\"contextid\",1", "OK")) return false;
    if (!cmd("AT+QHTTPCFG=\"responseheader\",0", "OK")) return false;
    char c[64];
    snprintf(c, sizeof(c), "AT+QHTTPCFG=\"contenttype\",%u",
             (unsigned)content_type);
    return cmd(c, "OK");
}

bool set_url(const char* host, const char* path) {
    char url[128];
    snprintf(url, sizeof(url), "https://%s%s", host, path);

    char c[64];
    snprintf(c, sizeof(c), "AT+QHTTPURL=%u,80", (unsigned)strlen(url));
    if (!cmd(c, "CONNECT", 10000)) return false;

    s_modem.print(url);
    return expect("OK", 10000);
}

// Reads the HTTP exchange and decides success.
//
// Two response shapes exist across BG95 firmware revisions: the status may
// arrive as a +QHTTPPOST URC carrying (err, http_status, length), or the read
// may report only +QHTTPREAD:<err>. Success requires one of them to say yes.
// Silence is failure — the alternative is deleting a record whose bytes never
// arrived.
bool http_result(uint32_t timeout_ms) {
    bool post_seen = false;
    bool post_ok = false;
    bool read_ok = false;

    s_modem.print("AT+QHTTPREAD=90\r\n");

    uint32_t start = millis();
    String line;

    while (millis() - start < timeout_ms) {
        while (s_modem.available()) {
            char ch = (char)s_modem.read();

            if (ch == '\r') continue;
            if (ch != '\n') {
                line += ch;
                if (line.length() > 256) line = "";
                continue;
            }

            if (line.startsWith("+QHTTPPOST:")) {
                post_seen = true;
                int err = -1, status = 0;
                if (sscanf(line.c_str() + 11, "%d,%d", &err, &status) == 2) {
                    post_ok = (err == 0 && status >= 200 && status < 300);
                }
            } else if (line.startsWith("+QHTTPREAD:")) {
                int err = -1;
                if (sscanf(line.c_str() + 11, "%d", &err) == 1) {
                    read_ok = (err == 0);
                }
            } else if (line.startsWith("OK")) {
                return post_seen ? post_ok : read_ok;
            } else if (line.startsWith("ERROR")) {
                return false;
            }

            line = "";
        }
    }
    return false;
}

}  // namespace

bool modem_power_on() {
    pinMode(PIN_MODEM_PWRKEY, OUTPUT);
    pinMode(PIN_MODEM_STATUS, INPUT);

    digitalWrite(PIN_MODEM_PWRKEY, LOW);
    delay(100);
    digitalWrite(PIN_MODEM_PWRKEY, HIGH);   // BG95 needs a ~500 ms pulse
    delay(600);
    digitalWrite(PIN_MODEM_PWRKEY, LOW);

    s_modem.begin(MODEM_BAUD, SERIAL_8N1, PIN_MODEM_RX, PIN_MODEM_TX);
    s_ready = false;
    return modem_ready(15000);
}

void modem_power_off() {
    if (s_ready) cmd("AT+QPOWD=1", "OK", 3000);
    s_ready = false;
}

bool modem_ready(uint32_t timeout_ms) {
    if (s_ready) return true;
    uint32_t start = millis();
    while (millis() - start < timeout_ms) {
        if (cmd("AT", "OK", 500)) {
            s_ready = true;
            return true;
        }
        delay(200);
    }
    return false;
}

bool modem_sync_time(int64_t* utc_seconds) {
    if (!modem_ready(5000)) return false;
    if (!cmd("AT+CTZU=1", "OK")) return false;   // automatic time zone update

    char line[128] = {0};
    s_modem.print("AT+QLTS=2\r\n");
    // +QLTS: "26/10/30,14:22:05-28,0"
    if (!expect("+QLTS:", 5000, line, sizeof(line))) return false;

    const char* p = strchr(line, '"');
    if (!p) return false;
    int yy, mm, dd, hh, mi, ss;
    if (sscanf(p + 1, "%2d/%2d/%2d,%2d:%2d:%2d",
               &yy, &mm, &dd, &hh, &mi, &ss) != 6) {
        return false;
    }

    // Days since epoch, civil-from-days. Avoids pulling in a time library and
    // its DST rules, which are irrelevant for a UTC timestamp.
    int y = 2000 + yy;
    int era = (y >= 0 ? y : y - 399) / 400;
    unsigned yoe = (unsigned)(y - era * 400);
    unsigned doy = (153u * (mm > 2 ? mm - 3 : mm + 9) + 2) / 5 + dd - 1;
    unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    long days = (long)era * 146097L + (long)doe - 719468L;

    *utc_seconds = (int64_t)days * 86400LL + hh * 3600LL + mi * 60LL + ss;
    return true;
}

bool modem_location(double* lat, double* lon, uint16_t* accuracy_m,
                    uint8_t* method, uint32_t timeout_ms) {
    if (!modem_ready(5000)) return false;

    // GNSS first: best accuracy, worst power. Fall back to the serving cell,
    // which works indoors and on a covered porch where GNSS will not fix.
    if (cmd("AT+QGPS=1", "OK", 5000)) {
        char line[160] = {0};
        uint32_t start = millis();
        while (millis() - start < timeout_ms) {
            s_modem.print("AT+QGPSLOC=2\r\n");
            if (expect("+QGPSLOC:", 3000, line, sizeof(line))) {
                // +QGPSLOC: <UTC>,<lat>,<lon>,<hdop>,<alt>,...
                const char* p = strchr(line, ':');
                if (p) {
                    double la = 0, lo = 0;
                    float hdop = 99;
                    if (sscanf(p + 1, "%*[^,],%lf,%lf,%f",
                               &la, &lo, &hdop) == 3) {
                        *lat = la;
                        *lon = lo;
                        *method = 1;
                        *accuracy_m = (uint16_t)(hdop * 5.0f + 0.5f);
                        cmd("AT+QGPSEND", "OK", 2000);
                        return true;
                    }
                }
            }
            delay(1000);
        }
        cmd("AT+QGPSEND", "OK", 2000);
    }

    // Cell-based fallback.
    if (cmd("AT+QCELLLOC=1", "OK", 8000)) {
        // Module-specific query; parse per the installed firmware's manual.
        // Left unimplemented rather than guessed: a wrong coordinate is worse
        // than a flagged missing one (DATA_MODEL §5 kFlagMissingLocation).
        *method = 2;
        return false;
    }
    return false;
}

bool modem_http_post(const char* host, const char* path,
                     const uint8_t* body, size_t len) {
    if (!modem_ready(5000)) return false;
    if (!http_config(QHTTP_CT_JSON)) return false;
    if (!set_url(host, path)) return false;

    char c[64];
    snprintf(c, sizeof(c), "AT+QHTTPPOST=%u,60,120", (unsigned)len);
    if (!cmd(c, "CONNECT", 10000)) return false;

    s_modem.write(body, len);
    if (!expect("OK", 60000)) return false;

    return http_result(120000);
}

bool modem_http_post_stream(const char* host, const char* path,
                            size_t stream_len, StreamReader reader, void* ctx,
                            uint8_t content_type) {
    if (stream_len == 0) return false;
    if (!modem_ready(5000)) return false;
    if (!http_config(content_type)) return false;
    if (!set_url(host, path)) return false;

    char c[64];
    snprintf(c, sizeof(c), "AT+QHTTPPOST=%u,60,120", (unsigned)stream_len);
    if (!cmd(c, "CONNECT", 10000)) return false;

    // Stream in small chunks. A 3-frame burst is a few hundred kilobytes,
    // which will not fit in RAM alongside the camera buffers, so nothing
    // larger than this scratch buffer is ever held at once.
    uint8_t buf[512];
    size_t sent = 0;
    while (sent < stream_len) {
        size_t want = sizeof(buf);
        if (stream_len - sent < want) want = stream_len - sent;

        size_t got = reader(ctx, buf, want);
        if (got == 0) {
            // Declared length not delivered. Abort rather than send a short
            // body: a truncated JPEG is worse than a retry.
            return false;
        }
        s_modem.write(buf, got);
        sent += got;
    }

    if (!expect("OK", 120000)) return false;
    return http_result(180000);
}

void modem_enable_psm() {
    if (!modem_ready(5000)) return;
    // Requested values are placeholders: the network grants what it grants,
    // and the granted values should be read back and recorded.
    cmd("AT+CPSMS=1,,,\"00000011\",\"00000001\"", "OK", 5000);
}

int modem_rssi() {
    if (!modem_ready(5000)) return 0;
    char line[96] = {0};
    s_modem.print("AT+CSQ\r\n");
    if (!expect("+CSQ:", 3000, line, sizeof(line))) return 0;
    const char* p = strchr(line, ':');
    if (!p) return 0;
    int rssi = 0;
    if (sscanf(p + 1, "%d", &rssi) != 1 || rssi == 99) return 0;
    return -113 + 2 * rssi;   // 3GPP mapping
}
