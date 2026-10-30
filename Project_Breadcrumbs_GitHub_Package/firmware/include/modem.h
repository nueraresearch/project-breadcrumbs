// modem.h — Quectel BG95-M3 driver.
//
// The modem does the TLS work (QHTTP) rather than the MCU, because it is the
// lower-power path: the ESP32-S3 never has to run a TLS stack, and PSM keeps
// the module registered between uploads.

#pragma once

#include <stddef.h>
#include <stdint.h>

// QHTTP content-type indices. The module takes an index, not a MIME string.
#define QHTTP_CT_URLENC   0
#define QHTTP_CT_TEXT     1
#define QHTTP_CT_BINARY   2
#define QHTTP_CT_MULTI    3
#define QHTTP_CT_JSON     4

// Fills buf with up to cap bytes. Returns 0 at end of input or on error;
// a zero return aborts the upload rather than sending a short body.
typedef size_t (*StreamReader)(void* ctx, uint8_t* buf, size_t cap);

bool modem_power_on();
void modem_power_off();

// Waits for the module to answer AT. Returns false on timeout.
bool modem_ready(uint32_t timeout_ms);

// Network time. Populates utc_seconds. Returns false if unsynced.
bool modem_sync_time(int64_t* utc_seconds);

// One location fix. method is 1 for GNSS, 2 for cell-derived.
bool modem_location(double* lat, double* lon, uint16_t* accuracy_m,
                    uint8_t* method, uint32_t timeout_ms);

// POSTs a buffer. Returns true on a 2xx response.
bool modem_http_post(const char* host, const char* path,
                     const uint8_t* body, size_t len);

// POSTs stream_len bytes without ever holding them all in RAM. The reader is
// called repeatedly until stream_len bytes have been sent.
bool modem_http_post_stream(const char* host, const char* path,
                            size_t stream_len, StreamReader reader, void* ctx,
                            uint8_t content_type);

// Enables power saving mode so the module sleeps between uploads.
void modem_enable_psm();

// Signal quality in dBm, or 0 if unknown.
int modem_rssi();
