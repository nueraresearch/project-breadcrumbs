# Preliminary Bill of Materials — Functional Categories

**Revision:** 1.0  
**Status:** Category-level BOM; no final parts selected and no prices validated

This BOM identifies functional elements needed to develop a prototype. It is not a purchase-ready parts list. Exact components must be selected after requirements, interfaces, power budget, and prototype constraints are established.

| Subsystem | Item / category | Purpose | Selection status |
|---|---|---|---|
| Control | Low-power microcontroller or embedded controller | Sensor monitoring, event logic, image coordination | TBD |
| Camera | Embedded still-image camera module | Three-frame capture | TBD |
| Optics | Lens / camera aperture | Outward-facing field of view | TBD |
| Trigger | Light-sensitive sensor | Detect illumination change associated with opening | TBD |
| Trigger optics | Internal light path | Admit light from the opening into the sealed cavity | TBD |
| Motion | Accelerometer / inertial sensor | Movement logging and location-fix scheduling; never triggers imaging | Confirmed (D-31) |
| Location | GNSS and/or cellular positioning | Movement and recovery telemetry; primary research output | Cellular fallback confirmed (D-32); GNSS TBD |
| Communications | LTE-M or NB-IoT modem with nano-SIM or eSIM | Transmission of all records, including images | Confirmed (D-33) |
| Storage | Nonvolatile memory | Event records and image storage | TBD |
| Security | Secure element or equivalent key storage, if required | Device identity and cryptographic key protection | TBD |
| Power | Rechargeable cell in a holder, charged off-device | Module power, swapped at each 30-day boundary | Chemistry confirmed (D-35); capacity TBD |
| Power | Protection and regulation circuitry | Safe power management with no charging port on the sealed unit | TBD |
| Power | External charging dock | Charge cells outside the enclosure | TBD |
| Feedback | Status LED(s) | Device state indication | TBD |
| Enclosure | Reusable enclosure and mounting hardware | Protect and position components | TBD |
| Assembly | PCB, connectors, wiring, fasteners | Integration | TBD |
| Recovery | Return label / reward insert | Encourage hardware return | Program design TBD |
| Consumable | Outer retail package, one per deployment | Presents as an ordinary shipment; not reused | TBD |

## Cost status

The project proposal gives a preliminary pilot budget target of **$600–$900** for 10 modules and 30 deployment cycles. It is retained as a target, not a budget (D-51). The cost realism section of the design hardening plan estimates a comparable scope at roughly $3k–$5.5k excluding labour on a pro bono legal review, or $4.8k–$9k if counsel has to be paid, so the gap is expected to be materially wider than the target implies. Nothing here has been validated, and the figure may not cover engineering labour, shipping, connectivity, insurance, participant incentives, replacement parts, or data hosting.

Connectivity is no longer a metadata-only line item. Every module transmits all records, including images (D-33). A burst is under 1 MB and events are infrequent, so traffic is a few megabytes per module per month; the recurring cost is dominated by the plan and the modem rather than by the bytes.

Thirty deployments at thirty different addresses also changes the logistics cost: every cycle boundary is a retrieval at one household and a redeployment at another, so travel and scheduling are three times the work of a single-address schedule. The outer retail package is consumed once per deployment and has no cost line above.

No per-module price is approved. Build a supplier-backed costed BOM after selecting components and obtaining current quotes.

## Required next steps

1. Choose controller and camera platform based on capture latency and low-power standby.
2. Select light sensor and test its optical response in a representative package.
3. Choose between GNSS and cellular-only positioning, and test accuracy inside a sealed package.
4. Calculate cell capacity from measured standby, location-fix, and upload loads against a 30-day cycle.
5. Select storage capacity based on image count, image size, and retention policy.
6. Prototype enclosure and evaluate camera field of view.
7. Obtain current supplier quotes and add assembly, shipping, and contingency.
