#include "store.h"

#include <Arduino.h>
#include <LittleFS.h>
#include <stdio.h>
#include <string.h>

namespace {

constexpr const char* kRecordDir = "/r";
constexpr const char* kImageDir  = "/i";

// Leave headroom so a burst can always be written even when the queue is
// nearly full: three SVGA JPEGs plus the record.
constexpr size_t kReserveBytes = 512 * 1024;

RTC_DATA_ATTR uint32_t s_dropped = 0;

void record_path(const char* id, char* out, size_t cap) {
    snprintf(out, cap, "%s/%s.json", kRecordDir, id);
}

void image_path(const char* id, uint8_t frame, char* out, size_t cap) {
    snprintf(out, cap, "%s/%s_%u.jpg", kImageDir, id, (unsigned)frame);
}

void marker_path(const char* id, char* out, size_t cap) {
    snprintf(out, cap, "%s/%s.up", kRecordDir, id);
}

bool is_uploaded(const char* id) {
    char p[64];
    marker_path(id, p, sizeof(p));
    return LittleFS.exists(p);
}

// Deletes the images that belong to a record. Missing files are fine.
void drop_images(const char* id) {
    char p[64];
    for (uint8_t f = 1; f <= 3; ++f) {
        image_path(id, f, p, sizeof(p));
        if (LittleFS.exists(p)) LittleFS.remove(p);
    }
}

// Finds the oldest record ID on disk, optionally skipping uploaded ones.
// Returns false when there is nothing to find.
bool oldest_id(char* out, size_t cap, bool prefer_uploaded) {
    File dir = LittleFS.open(kRecordDir);
    if (!dir) return false;

    char best[40] = {0};
    uint32_t best_key = 0xFFFFFFFFu;
    bool found = false;

    File f = dir.openNextFile();
    while (f) {
        const char* name = f.name();
        size_t len = strlen(name);

        // Only consider .json records.
        if (len > 5 && strcmp(name + len - 5, ".json") == 0 && len - 5 < 40) {
            char id[40];
            memcpy(id, name, len - 5);
            id[len - 5] = '\0';

            bool up = is_uploaded(id);
            if (prefer_uploaded ? up : !up) {
                // Record IDs embed a monotonic counter; lexicographic order
                // over fixed-width fields is chronological here.
                uint32_t key = 0;
                const char* dash = strrchr(id, '-');
                if (dash) key = (uint32_t)strtoul(dash + 1, nullptr, 10);

                if (key < best_key) {
                    best_key = key;
                    strncpy(best, id, sizeof(best) - 1);
                    found = true;
                }
            }
        }
        f = dir.openNextFile();
    }
    if (!found) return false;

    strncpy(out, best, cap - 1);
    out[cap - 1] = '\0';
    return true;
}

}  // namespace

bool store_init() {
    if (!LittleFS.begin(true)) return false;   // true = format on failure
    if (!LittleFS.exists(kRecordDir)) LittleFS.mkdir(kRecordDir);
    if (!LittleFS.exists(kImageDir))  LittleFS.mkdir(kImageDir);
    return true;
}

uint32_t store_dropped_count() { return s_dropped; }

size_t store_free_bytes() {
    // LittleFS on ESP32 reports total and used; free is the difference.
    size_t total = LittleFS.totalBytes();
    size_t used  = LittleFS.usedBytes();
    return total > used ? total - used : 0;
}

// D-66: the buffer must never overflow silently. Preference order:
//   1. delete a record that has already been uploaded (costs nothing)
//   2. delete the oldest unsent record and count the loss
// The counter is transmitted, so lost observations appear in the dataset.
bool store_evict_if_needed(size_t bytes_needed) {
    while (store_free_bytes() < bytes_needed + kReserveBytes) {
        char id[40];

        if (oldest_id(id, sizeof(id), /*prefer_uploaded=*/true)) {
            store_remove(id);
            continue;
        }
        if (oldest_id(id, sizeof(id), /*prefer_uploaded=*/false)) {
            store_remove(id);
            s_dropped++;
            continue;
        }
        return false;   // nothing left to evict and still no room
    }
    return true;
}

bool store_put_record(const Record& r, const char* json, size_t json_len) {
    if (!store_evict_if_needed(json_len)) return false;

    char p[64];
    record_path(r.record_id, p, sizeof(p));

    File f = LittleFS.open(p, FILE_WRITE);
    if (!f) return false;
    size_t written = f.write((const uint8_t*)json, json_len);
    f.close();
    return written == json_len;
}

bool store_put_image(const char* record_id, uint8_t frame_index,
                     const uint8_t* data, size_t len) {
    if (frame_index < 1 || frame_index > 3) return false;
    if (!store_evict_if_needed(len)) return false;

    char p[64];
    image_path(record_id, frame_index, p, sizeof(p));

    File f = LittleFS.open(p, FILE_WRITE);
    if (!f) return false;
    size_t written = f.write(data, len);
    f.close();
    return written == len;
}

size_t store_pending(char ids[][40], size_t max_ids) {
    File dir = LittleFS.open(kRecordDir);
    if (!dir) return 0;

    size_t n = 0;
    File f = dir.openNextFile();
    while (f && n < max_ids) {
        const char* name = f.name();
        size_t len = strlen(name);
        if (len > 5 && strcmp(name + len - 5, ".json") == 0 && len - 5 < 40) {
            char id[40];
            memcpy(id, name, len - 5);
            id[len - 5] = '\0';
            if (!is_uploaded(id)) {
                strncpy(ids[n], id, 39);
                ids[n][39] = '\0';
                n++;
            }
        }
        f = dir.openNextFile();
    }
    return n;
}

size_t store_read_record(const char* record_id, char* out, size_t cap) {
    char p[64];
    record_path(record_id, p, sizeof(p));
    File f = LittleFS.open(p, FILE_READ);
    if (!f) return 0;
    size_t n = f.readBytes(out, cap);
    f.close();
    return n;
}

size_t store_read_image(const char* record_id, uint8_t frame_index,
                        uint8_t* out, size_t cap) {
    char p[64];
    image_path(record_id, frame_index, p, sizeof(p));
    File f = LittleFS.open(p, FILE_READ);
    if (!f) return 0;
    size_t n = f.readBytes((char*)out, cap);
    f.close();
    return n;
}

bool store_mark_uploaded(const char* record_id) {
    char p[64];
    marker_path(record_id, p, sizeof(p));
    File f = LittleFS.open(p, FILE_WRITE);
    if (!f) return false;
    f.write((const uint8_t*)"1", 1);
    f.close();
    return true;
}

bool store_remove(const char* record_id) {
    char p[64];
    record_path(record_id, p, sizeof(p));
    if (LittleFS.exists(p)) LittleFS.remove(p);

    marker_path(record_id, p, sizeof(p));
    if (LittleFS.exists(p)) LittleFS.remove(p);

    drop_images(record_id);
    return true;
}
