// store.h — flash record queue with a logged eviction rule (D-66).
//
// 16 MB of flash, roughly twenty events per cycle (COST_REDUCTION_PLAN). The
// point of this module is that overflow is never silent: something is always
// deleted and always counted.

#pragma once

#include "records.h"
#include <stddef.h>
#include <stdint.h>

bool store_init();

// Appends a record. Evicts if necessary. Returns false only on I/O failure.
bool store_put_record(const Record& r, const char* json, size_t json_len);

// Saves one frame. frame_index is 1..3.
bool store_put_image(const char* record_id, uint8_t frame_index,
                     const uint8_t* data, size_t len);

// Fills ids with the record IDs that still need uploading, oldest first.
// Returns the count written.
size_t store_pending(char ids[][40], size_t max_ids);

// Reads a stored record's JSON back. Returns bytes written, 0 if missing.
size_t store_read_record(const char* record_id, char* out, size_t cap);

// Reads a stored frame. Returns bytes written, 0 if missing.
size_t store_read_image(const char* record_id, uint8_t frame_index,
                        uint8_t* out, size_t cap);

// Marks a record and its images as uploaded. Idempotent.
bool store_mark_uploaded(const char* record_id);

// Removes a record and its images after successful upload.
bool store_remove(const char* record_id);

// Number of records evicted without ever being uploaded. Transmitted as a
// record itself so the loss appears in the dataset rather than only in a log.
uint32_t store_dropped_count();

// Free space in bytes.
size_t store_free_bytes();
