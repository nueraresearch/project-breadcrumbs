// records.h — event taxonomy and record schema.
//
// The event type names mirror DATA_MODEL §3 exactly. Keep them in step: the
// analysis plan and the ingest schema both key off these strings.

#pragma once

#include <stdint.h>
#include <stddef.h>

enum class EventType : uint8_t {
    LightTrigger,
    MovementEvent,
    LocationFix,
    ImageCaptureComplete,
    ImageCapturePartial,
    LowBattery,
    PowerReset,
    SyncSuccess,
    SyncFailure,
    ModuleRecovered,
    DeploymentClosed,
};

const char* event_type_name(EventType t);

// Data quality flags (DATA_MODEL §5). Bit positions are part of the wire
// format; do not renumber.
enum RecordFlag : uint8_t {
    kFlagIncompleteBurst = 1 << 0,
    kFlagUncertainClock  = 1 << 1,
    kFlagFalseTrigger    = 1 << 2,
    kFlagDuplicate       = 1 << 3,
    kFlagMissingLocation = 1 << 4,
    kFlagOfflineBuffered = 1 << 5,
    kFlagUnknownRecovery = 1 << 6,
    kFlagDeviceMalfunction = 1 << 7,
};

enum class LocationMethod : uint8_t {
    None = 0,
    Gnss = 1,
    Cell = 2,
};

struct Record {
    // record_id is globally unique and survives module reuse. A module ID plus
    // a frame index collides across the ~6-12 deployments a module serves
    // (CAMERA_SUBSYSTEM §5), so it carries a boot-unique component.
    char        record_id[40];
    char        module_id[24];
    char        deployment_id[24];
    EventType   type;

    int64_t     sensor_ts;      // UTC seconds from the device clock
    bool        clock_synced;   // DATA_MODEL §4 — flagged, never discarded

    uint16_t    battery_mv;
    float       lux;            // meaningful on LightTrigger only
    uint8_t     frame_count;    // 0..3

    bool        location_valid;
    double      lat;
    double      lon;
    LocationMethod loc_method;
    uint16_t    loc_accuracy_m;

    uint8_t     flags;
};

// Serialise to a single-line JSON object, no trailing newline.
// Returns bytes written, or 0 if the buffer is too small.
size_t record_to_json(const Record& r, char* out, size_t cap);

// Populate the identity fields and a fresh record_id. Call immediately before
// storing; the ID embeds a monotonically increasing counter so two records
// written in the same second cannot collide.
void record_init(Record& r, EventType type);

// Deployment ID is set once per cycle by the provisioning step and kept in
// RTC memory across deep sleep.
void record_set_deployment(const char* deployment_id);
const char* record_deployment();
