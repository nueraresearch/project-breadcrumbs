#include "records.h"
#include "config.h"

#include <Arduino.h>
#include <stdio.h>
#include <string.h>

// Survives deep sleep so record IDs stay monotonic across wake cycles.
RTC_DATA_ATTR static uint32_t s_counter = 0;
RTC_DATA_ATTR static uint32_t s_boot_token = 0;
RTC_DATA_ATTR static char s_deployment[24] = "UNSET";

const char* event_type_name(EventType t) {
    switch (t) {
        case EventType::LightTrigger:         return "LIGHT_TRIGGER";
        case EventType::MovementEvent:        return "MOVEMENT_EVENT";
        case EventType::LocationFix:          return "LOCATION_FIX";
        case EventType::ImageCaptureComplete: return "IMAGE_CAPTURE_COMPLETE";
        case EventType::ImageCapturePartial:  return "IMAGE_CAPTURE_PARTIAL";
        case EventType::LowBattery:           return "LOW_BATTERY";
        case EventType::PowerReset:           return "POWER_RESET";
        case EventType::SyncSuccess:          return "SYNC_SUCCESS";
        case EventType::SyncFailure:          return "SYNC_FAILURE";
        case EventType::ModuleRecovered:      return "MODULE_RECOVERED";
        case EventType::DeploymentClosed:     return "DEPLOYMENT_CLOSED";
    }
    return "UNKNOWN";
}

void record_set_deployment(const char* deployment_id) {
    strncpy(s_deployment, deployment_id, sizeof(s_deployment) - 1);
    s_deployment[sizeof(s_deployment) - 1] = '\0';
}

const char* record_deployment() { return s_deployment; }

void record_init(Record& r, EventType type) {
    memset(&r, 0, sizeof(r));

    // A boot token distinguishes power cycles from deep-sleep wakes. Without
    // it, a counter reset on cold boot would reissue IDs that already exist in
    // the buffer, and the uploader would suppress the new record as a duplicate.
    if (s_boot_token == 0) {
        s_boot_token = esp_random();
        if (s_boot_token == 0) s_boot_token = 1;
    }
    s_counter++;

    snprintf(r.record_id, sizeof(r.record_id), "%s-%08lx-%06lu",
             BREADCRUMBS_MODULE_ID,
             (unsigned long)s_boot_token,
             (unsigned long)s_counter);

    strncpy(r.module_id, BREADCRUMBS_MODULE_ID, sizeof(r.module_id) - 1);
    strncpy(r.deployment_id, s_deployment, sizeof(r.deployment_id) - 1);

    r.type = type;
    r.loc_method = LocationMethod::None;
    r.flags = 0;
}

static void json_escape_append(char* out, size_t cap, size_t* n, const char* s) {
    for (const char* p = s; *p && *n < cap; ++p) {
        // IDs are constrained to [A-Za-z0-9-] by construction; escape anything
        // unexpected rather than emit invalid JSON.
        if ((*p >= 'A' && *p <= 'Z') || (*p >= 'a' && *p <= 'z') ||
            (*p >= '0' && *p <= '9') || *p == '-' || *p == '_') {
            out[(*n)++] = *p;
        } else {
            if (*n + 6 >= cap) return;
            *n += snprintf(out + *n, cap - *n, "\\u%04x", (unsigned char)*p);
        }
    }
}

size_t record_to_json(const Record& r, char* out, size_t cap) {
    if (cap < 64) return 0;
    size_t n = 0;

    n += snprintf(out + n, cap - n, "{\"record_id\":\"");
    json_escape_append(out, cap, &n, r.record_id);
    n += snprintf(out + n, cap - n, "\",\"module_id\":\"");
    json_escape_append(out, cap, &n, r.module_id);
    n += snprintf(out + n, cap - n, "\",\"deployment_id\":\"");
    json_escape_append(out, cap, &n, r.deployment_id);

    n += snprintf(out + n, cap - n,
                  "\",\"event_type\":\"%s\",\"sensor_ts\":%lld,"
                  "\"clock_synced\":%s,\"battery_mv\":%u,"
                  "\"frame_count\":%u,\"flags\":%u",
                  event_type_name(r.type),
                  (long long)r.sensor_ts,
                  r.clock_synced ? "true" : "false",
                  (unsigned)r.battery_mv,
                  (unsigned)r.frame_count,
                  (unsigned)r.flags);

    // Emit lux only where it means something, so a movement record cannot be
    // mistaken for a trigger by a downstream consumer reading the field.
    if (r.type == EventType::LightTrigger) {
        n += snprintf(out + n, cap - n, ",\"lux\":%.1f", (double)r.lux);
    }

    n += snprintf(out + n, cap - n, ",\"location\":{");
    if (r.location_valid) {
        n += snprintf(out + n, cap - n,
                      "\"valid\":true,\"lat\":%.5f,\"lon\":%.5f,"
                      "\"method\":%u,\"accuracy_m\":%u",
                      r.lat, r.lon, (unsigned)r.loc_method,
                      (unsigned)r.loc_accuracy_m);
    } else {
        n += snprintf(out + n, cap - n, "\"valid\":false");
    }
    n += snprintf(out + n, cap - n, "}}");

    if (n >= cap) return 0;   // truncated; caller must treat as failure
    return n;
}
