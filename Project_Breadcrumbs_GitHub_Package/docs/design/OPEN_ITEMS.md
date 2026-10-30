# Open Items Register

**Status:** Living document. Updated whenever an item closes.  
**Supersedes:** section D of [`../../DECISION_LOG.md`](../../DECISION_LOG.md) as the complete list of what is undefined. Section D keeps the original fourteen items and their status; this register adds everything the later decisions created.

## How to use this

Each row closes with **evidence**, not with an assertion. "Decided" without a document, a part number, a signature, or a test result does not close a row.

Items are grouped by what they block. Nothing in group A can be worked around by starting group B.

## A. Blocks building the first module

| ID | Item | Why it blocks | Status |
|---|---|---|---|
| A-01 | Camera module, lens, resolution | Determines whether a face is legible at one metre | **Decided** — ESP32-S3 board with OV2640 (D-57); lens confirmed on bench |
| A-02 | Light sensor part, threshold, debounce, lockout | The entire imaging path depends on this decision | **Part decided** — VEML7700-class (D-60); threshold to be measured |
| A-03 | Frame timing and exposure strategy | Third frame may photograph an empty porch; first may be blown out | **Decided** — 0 / 0.5 / 1.5 s (D-64), confirmed on bench |
| A-04 | MCU and camera interface | Sets wake latency, power floor, and what the firmware can do | **Decided** — ESP32-S3 (D-57) |
| A-05 | Cell capacity and chemistry specifics | 30-day cycle at four location fixes a day is assumed, not measured | **Decided** — 18650 LiFePO4, ~1500 mAh (D-61); runtime to be measured |
| A-06 | Storage size | One cycle of events and images | **Decided** — 32 GB microSD (D-61) |
| A-07 | Location method: GNSS, cellular-only, or both | Accuracy inside a sealed package is unknown | **Decided** — integrated GNSS in the BG95-M3, cellular fallback (D-58) |
| A-08 | Modem, SIM or eSIM, carrier, plan | Coverage at Monte Vista addresses is unknown | **Decided** — BG95-M3 and 1NCE lifetime SIM (D-58, D-59); coverage to be tested on site |
| A-09 | Enclosure, mounting, thermal path | The 45 °C limit is a design input, not a test result | **Decided** — tray and foam insert in the retail box (D-62); thermal test outstanding |
| A-10 | Arming mechanism (HW-32) | Carriage from the base must not register as a removal event | **Decided** — reed switch and magnet (D-63) |
| A-11 | Key provisioning and firmware security | Sealed-box encryption and no-remote-capture are architectural claims until built | **Decided** — ESP32-S3 secure boot and flash encryption (D-57); provisioning procedure still to be written |
| A-12 | Assembly and sealing procedure | Defines how a box is built, by whom, and how it stays sealed | **Decided in principle** — hand-assembled dev boards (D-57); step-by-step procedure to be written |
| A-13 | Test rig and who runs AT-01 to AT-15 | Acceptance thresholds need evidence before fielding | **Owner** — rig design and operator still to be named |

**Critical path:** A-01 and A-04 together, because the camera choice constrains the MCU and the power budget. Nothing else in group A can be fixed until those two are.

## B. Blocks the first deployment

| ID | Item | Why it blocks | Status |
|---|---|---|---|
| B-01 | Consent form text and withdrawal mechanics | Required before any household is recruited | Open |
| B-02 | Recruitment plan for 30 hosts, and the fallback if short | Thirty households is the largest logistical risk in the design | Open |
| B-03 | Town meeting approval | The stated gate to fielding (D-43) | Open |
| B-04 | Legal review engagement and scope confirmation | Pro bono is the target; scope must be agreed in writing first (D-54) | Open |
| B-05 | Ethics review determination | Unknown whether it applies; budgeted at $0–2,000 | Open |
| B-06 | Insurance | Required before deployment on private property | Open |
| B-07 | Base security and appointment process | The operating base is a single point of failure (T-18) | Open |
| B-08 | Chain of custody at collection and return | Sealed box changes hands three times per cycle | Open |
| B-09 | Incident response contacts and who can invoke stop rules | Stop rules without an authority are decoration | Open |
| B-10 | Participant briefing materials | Volunteers must know what the box does and what to do if approached | Open |
| B-11 | Documented replacement cost per package type | The reward is defined as this cost (D-38); nothing documents it yet | Open |
| B-12 | Lost-device procedure | Defines the recovery window and what counts as unrecovered | Open |

## C. Blocks publication

| ID | Item | Why it blocks | Status |
|---|---|---|---|
| C-01 | Data platform: ingest, vault, publication pipeline | Nothing exists. Images arrive by cellular and have nowhere to go | Open |
| C-02 | Adjudication reviewers named, rubric written | Two reviewers plus a tiebreak are required by the analysis plan | Open |
| C-03 | Pre-registration dated, signed, committed | Must precede the first deployment | Open |
| C-04 | Publication venue and format | Determines captions, tables, and what can be shown | Open |
| C-05 | Caption templates implementing D-42 | "Package opened", no names, no identification requests | Open |
| C-06 | Retention and deletion implementation | The schedule exists; the mechanism does not | Open |
| C-07 | Postal data agreement | Context only; the study proceeds without it (D-56) | Open |

**C-01 is the quiet blocker.** It has no hardware dependency and no external approval, so it is the item most likely to be left until data is already arriving with nowhere to land.

## D. External and administrative

| ID | Item | Why it blocks | Status |
|---|---|---|---|
| D-01 | Pilot start date | Every consent, agreement, and schedule refers to it | Open |
| D-02 | Budget approval | The $600–$900 target is not the estimated cost (D-51) | Open |
| D-03 | Post office response | See [`../pilot/POST_OFFICE_DATA_REQUEST.md`](../pilot/POST_OFFICE_DATA_REQUEST.md) | Open |

## What is *not* on this list

Deliberately excluded, so the register does not become a wish list:

- **A control arm.** Rejected (D-48).
- **Fill lighting for night openings.** Rejected as a scope limit (D-30, D-37).
- **Remote imaging or any command path.** Architecturally excluded (HW-30).
- **A town-level theft rate.** Not estimable from this design, and not attempted.

## The three that decide the schedule

If only three items can be worked at once:

1. **A-01 / A-04** — camera and controller. Everything in the hardware budget and power budget hangs off this pair.
2. **B-04** — legal scope. It gates recruitment, because you cannot ask thirty households to host a box before someone qualified has said the design is defensible.
3. **C-01** — the data platform. It is unglamorous, unblocked, and the only item that gets harder every day it is deferred.
