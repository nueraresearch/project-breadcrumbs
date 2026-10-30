# Preliminary Bill of Materials — Functional Categories

**Revision:** 1.0  
**Status:** Category-level BOM; no final parts selected and no prices validated

This BOM identifies functional elements needed to develop a prototype. It is not a purchase-ready parts list. Exact components must be selected after requirements, interfaces, power budget, and prototype constraints are established.

| Subsystem | Item / category | Purpose | Selection status |
|---|---|---|---|
| Control | ESP32-S3 development board | Sensor monitoring, event logic, image coordination | Selected for prototype (D-57) |
| Camera | OV2640-class camera on the ESP32-S3 board | Three-frame capture | Selected for prototype (D-57) |
| Optics | Lens / camera aperture | Outward-facing field of view | TBD |
| Trigger | VEML7700-class digital light sensor with interrupt | Detect illumination change associated with opening | Selected (D-60) |
| Trigger optics | Internal light path | Admit light from the opening into the sealed cavity | TBD |
| Motion | Accelerometer / inertial sensor | Movement logging and location-fix scheduling; never triggers imaging | Confirmed (D-31) |
| Location | GNSS integrated in the BG95-M3, cellular fallback | Movement and recovery telemetry; primary research output | Selected (D-58) |
| Communications | Quectel BG95-M3 with a 1NCE SIM | Transmission of all records, including images | Selected (D-58, D-59) |
| Storage | 16 MB flash on the MCU board | Event records and image storage | Selected (D-66) |
| Security | ESP32-S3 secure boot and flash encryption | Device identity and cryptographic key protection | Selected (D-57) |
| Power | 18650 LiFePO4 cell, ~1500 mAh, in a holder | Module power, swapped at each 30-day boundary | Selected (D-61) |
| Power | Protection and regulation circuitry | Safe power management with no charging port on the sealed unit | TBD |
| Power | External charging dock | Charge cells outside the enclosure | TBD |
| Feedback | Status LED(s) | Device state indication | TBD |
| Enclosure | Foam cutouts inside the retail box | Protect and position components | Selected (D-67) |
| Assembly | Hand-assembled dev boards, wiring, fasteners | Integration | Selected (D-57) |
| Recovery | Return label / reward insert | Encourage hardware return | Program design TBD |
| Consumable | Outer retail package, one per deployment | Presents as an ordinary shipment; not reused | TBD |

## Cost status

The project proposal gives a preliminary pilot budget target of **$600–$900** for 10 modules and 30 deployment cycles. It is retained as a target, not a budget (D-51). The cost realism section of the design hardening plan estimates a comparable scope at roughly $3k–$5.5k excluding labour on a pro bono legal review, or $4.8k–$9k if counsel has to be paid, so the gap is expected to be materially wider than the target implies. Nothing here has been validated, and the figure may not cover engineering labour, shipping, connectivity, insurance, participant incentives, replacement parts, or data hosting.

Connectivity is no longer a metadata-only line item. Every module transmits all records, including images (D-33). A burst is under 1 MB and events are infrequent, so traffic is a few megabytes per module per month; the recurring cost is dominated by the plan and the modem rather than by the bytes.

Thirty deployments at thirty different addresses also changes the logistics cost: every cycle boundary is a retrieval at one household and a redeployment at another, so travel and scheduling are three times the work of a single-address schedule. The outer retail package is consumed once per deployment and has no cost line above.

Current small-quantity estimates put the parts at about **$66 per module** and about **$86 per deployable unit** with spares, against roughly $156 before. Part choices, the reasoning behind each line, and the levers deliberately rejected are in [`COST_REDUCTION_PLAN.md`](COST_REDUCTION_PLAN.md).

No price is quoted or approved. Build a supplier-backed costed BOM before ordering ten of anything.

## Required next steps

1. Choose controller and camera platform based on capture latency and low-power standby.
2. Select light sensor and test its optical response in a representative package.
3. Choose between GNSS and cellular-only positioning, and test accuracy inside a sealed package.
4. Calculate cell capacity from measured standby, location-fix, and upload loads against a 30-day cycle.
5. Select storage capacity based on image count, image size, and retention policy.
6. Prototype enclosure and evaluate camera field of view.
7. Obtain current supplier quotes and add assembly, shipping, and contingency.
