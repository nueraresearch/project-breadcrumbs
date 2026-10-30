# Project Breadcrumbs — Preliminary Data Model

**Status:** Conceptual schema; implementation not selected

## 1. Design principles

- Use pseudonymous participant and site codes in operational datasets.
- Keep direct participant contact details separate from event data.
- Collect location as a primary research output (D-32), but publish it at reduced precision and with a delay (D-41).
- Use unique IDs and timestamps consistently.
- Distinguish sensor observations from human-verified outcomes.
- Track missing, delayed, and failed records explicitly.
- Do not encode a person's identity or inferred guilt in event records.

## 2. Core entities

### Module
| Field | Meaning |
|---|---|
| module_id | Stable unique device identifier |
| hardware_revision | Physical design revision |
| firmware_revision | Firmware build |
| status | Available, deployed, maintenance, lost, retired |
| created_at | Module registration time |

### Participant
| Field | Meaning |
|---|---|
| participant_code | Pseudonymous participant identifier |
| consent_version | Agreement version |
| consent_timestamp | Recorded authorization time |
| status | Active, withdrawn, suspended |

Contact information should be stored separately with restricted access.

### Deployment
| Field | Meaning |
|---|---|
| deployment_id | Unique deployment identifier |
| module_id | Assigned module |
| participant_code | Pseudonymous participant |
| site_code | Pseudonymous deployment site |
| start_timestamp | Deployment start |
| end_timestamp | Deployment end |
| status | Prepared, deployed, retrieved, recovered, lost, failed |
| outcome_state | Not lost, recovered and redeployable, recovered and needing refurbishment, lost and never recovered (D-50) |
| location_record_ref | Deployment location reference; published at reduced precision (D-41) |

### Event
| Field | Meaning |
|---|---|
| event_id | Unique event identifier |
| record_id | Globally unique record identifier; survives module reuse |
| deployment_id | Related deployment |
| module_id | Reporting module |
| event_type | Light trigger, movement, power, communications, recovery |
| sensor_timestamp | Device-reported timestamp |
| received_timestamp | Server receipt time |
| trigger_metadata | Threshold and diagnostic information |
| validation_status | Unreviewed, reviewed, false trigger, indeterminate |

### Image
| Field | Meaning |
|---|---|
| image_id | Unique image identifier |
| event_id | Related event |
| frame_index | 1, 2, or 3 |
| capture_timestamp | Actual capture time |
| secure_object_ref | Restricted storage reference |
| integrity_hash | Integrity verification value |
| access_class | Restricted classification |
| retention_until | Approved deletion date |

### Recovery
| Field | Meaning |
|---|---|
| recovery_id | Unique recovery record |
| deployment_id | Related deployment |
| recovery_timestamp | Recovery time |
| recovery_status | Recovered, unrecovered, later returned |
| device_condition | Functional, damaged, failed |
| recovery_method | Controlled category; avoid unnecessary personal data |

### Delivery volume context

Aggregate postal data, held separately from event records and joined by date only (D-56).

| Field | Meaning |
|---|---|
| context_date | Calendar date the volume covers |
| route_or_area | The route or area the aggregate describes; never a recipient |
| package_volume | Packages carried that day or week, as supplied |
| granularity | Daily or weekly, whichever was obtainable |
| source_agreement_ref | Reference to the written agreement under which it was supplied |

No recipient-level field exists in this table and none is to be added. The data is reported alongside removal dates as context; it is not used as a denominator for any rate.

## 3. Event taxonomy

Recommended initial event types:
- `LIGHT_TRIGGER` — interior illumination step; the sole imaging gate
- `MOVEMENT_EVENT` — accelerometer threshold exceeded; logged only, never triggers imaging
- `LOCATION_FIX` — position observation with method and accuracy
- `IMAGE_CAPTURE_COMPLETE`
- `IMAGE_CAPTURE_PARTIAL`
- `LOW_BATTERY`
- `POWER_RESET`
- `SYNC_SUCCESS`
- `SYNC_FAILURE`
- `MODULE_RECOVERED`
- `DEPLOYMENT_CLOSED`

A `LIGHT_TRIGGER` is a sensor observation, not proof of opening or theft. A `MOVEMENT_EVENT` is not proof of theft either: wind, a courier, or the participant can move a package.

## 4. Timestamp policy

Store timestamps in UTC in machine-readable records and retain the device's clock-synchronization status. For analysis, convert to local time using the deployment site's time zone. Record clock drift and missing timestamps.

**Clock uncertainty is carried explicitly.** Each record also carries `clock_uncertainty_s`, the estimated error bound at the moment of capture. The device sleeps between events, so its clock is a free-running oscillator disciplined only when the modem syncs; the bound grows with time since the last sync and shrinks once the drift rate has been measured. A record with a wide bound is still usable for ordering events, and is not usable as a precise event time. Carrying the bound is what lets the analysis decide which is which, rather than assuming every timestamp is equally good.

## 5. Data quality flags

Use explicit flags for:
- incomplete image burst;
- uncertain clock;
- sensor false trigger;
- duplicate upload;
- missing location;
- offline-buffered record;
- unknown recovery time;
- device malfunction.

## 6. Public reporting

Collected data, including images, is published (D-40). The limits below protect the volunteer and the person depicted, and are applied before release rather than on request afterwards:

- No participant name, home address, or precise private-location trace (D-41). Location is reduced in precision and delayed.
- Captions state that a package was opened, never that a theft occurred; no names, no identification requests, no guilt framing (D-42).
- Event-level data may be published rather than aggregated, but site-level statistics must not permit re-identification of a volunteer's property.
- Images may be published as captured, with embedded metadata stripped.
