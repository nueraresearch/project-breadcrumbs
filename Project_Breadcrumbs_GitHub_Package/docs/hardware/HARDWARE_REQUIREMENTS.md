# Reusable Monitoring Module — Hardware Requirements & Conceptual Architecture

**Revision:** 1.2  
**Status:** Requirements reflect owner decisions recorded 2026-10-30 (D-27 to D-51). Engineering design is not finalized.

**Revision note:** Revision 1.1 proposed a removal-first trigger. The owner rejected it: the camera and light sensor sit inside a sealed package and see nothing until the lid opens, so removal-triggered imaging would photograph the inside of a closed lid. Revision 1.2 restores the light trigger as the sole imaging gate and adds the movement and location telemetry that makes removal observable without a camera.

## 1. Design objective

Develop a compact, reusable monitoring module that can be installed inside a sealed research package and record defined package events for a voluntary community study.

The module should prioritize reliable event capture, recoverability, low operating cost, maintainability, and controlled data collection.

## 2. Confirmed project-level direction

From the project owner (D-01 to D-10, extended by D-27 to D-51):

- The module is reusable and recoverable.
- The program is voluntary; participants place packages on their own property with authorization.
- The study concerns theft-related package events, movement, and recovery patterns.
- The camera faces outward toward the person opening the package.
- The camera captures a three-shot burst when opening is detected.
- A light-sensitive sensor is the opening trigger.
- No audio and no continuous video.

Geometry and deployment decisions recorded 2026-10-30:

- The module is attached inside a closed retail-style package and shipped to the volunteer sealed. The volunteer receives a closed box and places it on their porch.
- The camera is **fixed at assembly**, aimed at the opening. It is blind while the lid is closed.
- The light sensor shares that cavity. The interior is effectively pitch black, so any detected light step is treated as the package opening.
- Deployment cycles run **30 days**, not 90.
- Movement is logged, with periodic location fixes. Movement never triggers imaging; only the light step does.
- All collected data, images included, is transmitted over a cellular link and released publicly.

These decisions establish design direction. They do not establish technical feasibility, and no performance figure here is validated until a test records it.

## 3. Functional architecture

### A. Event sensing

| Channel | Detects | Role |
|---|---|---|
| Light sensor (inside cavity) | Interior illumination step | **Sole imaging trigger.** Sealed box is dark; light means the lid opened |
| Accelerometer | Lift, tilt, sustained motion | Movement event log and location-fix scheduling. Never triggers imaging |
| Location (GNSS and/or cellular) | Position, coarse or precise | Movement and recovery telemetry |

Proposed functions:
- Sample the light sensor in deep sleep with a hardware comparator or interrupt.
- On a qualifying light step, wake, validate against threshold and duration, and start the burst.
- On motion, record a movement event and schedule a location fix at the configured interval.
- Record event timestamps and event type; apply debounce and lockout.

**Why the enclosed sensor is the right choice.** A light sensor exposed to the outside world must discriminate an opening from sunrise, cloud, passing headlights, and porch lights, which is where false-trigger problems come from. A sensor inside a sealed dark cavity has none of that. The step it sees is caused by the lid opening, and the design is correspondingly simpler and more reliable.

**Known limitation, accepted.** In true darkness — no porch light, no streetlight, no headlights — opening a dark box onto a dark porch produces no light step, so the event is not recorded. This is a property of the deployment site's lighting, not a fault in the sensor, and it should be reported as a scope limit rather than engineered around with a fill light.

### B. Imaging

- Outward-facing camera, fixed at assembly, framing the package opening.
- Three still images per qualifying trigger.
- No audio, no continuous video.
- Images associated with module ID, deployment ID, event ID, and timestamps.
- Encrypted at rest; transmitted after capture when a link is available.

The camera is expected to capture the face of the person opening the box. That is the design intent and it drives lens choice, mounting height, and exposure settings.

### C. Location

Recorded capability, and a primary research output rather than a secondary one:

- Location fix on each movement event, and at a configured interval while movement continues.
- Location fix at deployment and at recovery.
- Stored locally and transmitted with the event record.

GNSS is preferred where it acquires quickly; cellular cell-ID and timing-advance provide a coarse fallback and work indoors. The power cost of fixes is a first-order design constraint, not a detail.

### D. Communications

- Cellular link, LTE-M or NB-IoT, with a physical nano-SIM in a sealed tray or an eSIM.
- All collected records are transmitted: events, telemetry, and the image burst.
- Store-and-forward buffering when coverage is absent.
- Duplicate suppression and upload confirmation.

**Sizing note.** A three-frame burst at roughly 100–200 KB per frame is under 1 MB per event. At a few events per week, image transmission is a few megabytes per device per month, not a streaming problem. The cost that matters is the modem and the plan, not the bytes. Continuous image streaming would be a different design and is not proposed.

### E. Power management

- Rechargeable cell, sealed in the enclosure, charged off-device.
- Cells are swapped at recovery rather than charged in place: no connector, no port, no ingress path.
- Prototype uses standard cells in a holder; later revisions move to a higher-grade cell of the same form factor.
- Deep sleep between events, with the light comparator and accelerometer interrupt as the only always-on loads.
- Battery state recorded with every transmission.

A 30-day cycle with roughly 4 location fixes per day and a handful of image bursts is comfortably within a single 18650-class cell. This should be measured, not assumed, but it is not the constraint it would have been at 90 days.

### F. Physical enclosure

- Module bonded or clipped to the inside wall of the package, camera aligned with the opening at assembly.
- Sealed, no external connectors, no visible indicator during deployment.
- Ordinary appearance: the outer package looks like a retail shipment, not a research device.
- Recoverable: a return path routed to the project, never to the volunteer's home.
- The outer package is consumable; the module is the reusable asset.

## 4. Preliminary requirements table

Identifiers HW-01 to HW-12 are unchanged. HW-13 to HW-21 were proposed in revision 1.1 and are withdrawn — see §4.2.

### 4.1 Active requirements

| ID | Requirement | Status / verification |
|---|---|---|
| HW-01 | Module shall be reusable across deployment cycles | Proposed; cycle testing |
| HW-02 | Module shall have a unique device identifier | Proposed; data/firmware test |
| HW-03 | Opening trigger shall use a light-sensitive sensor **mounted inside the sealed cavity** | Confirmed; bench test |
| HW-04 | Trigger shall initiate a three-still-image sequence | Confirmed; timing test |
| HW-05 | Camera shall face outward toward the person opening the package | Confirmed; layout review |
| HW-06 | Device shall not record audio | Design constraint; hardware/firmware review |
| HW-07 | Device shall not continuously record video | Design constraint; firmware review |
| HW-08 | Device shall retain event records if offline, and forward them on reconnection | Proposed; offline test |
| HW-09 | Device shall record location observations on movement and at events | Confirmed capability; accuracy and power test |
| HW-10 | Device shall support secure data handling | Required design objective; security review |
| HW-11 | Device shall indicate relevant operating state, but not during deployment | Proposed; usability test |
| HW-12 | Device shall support safe recovery and redeployment | Proposed; operational test |
| HW-22 | Camera shall be fixed at assembly and cannot be re-aimed without visible damage | Proposed; mechanical check |
| HW-23 | Imaging shall be gated on the light trigger only; motion shall never start a burst | Required design constraint; firmware review and negative test |
| HW-24 | Device shall record movement events with timestamps without imaging | Proposed; bench test |
| HW-25 | Device shall obtain a location fix on movement and at a configured interval | Proposed; field accuracy test |
| HW-26 | Device shall transmit all records, including images, over a cellular link | Proposed; end-to-end test |
| HW-27 | Device shall have no charging or data connector accessible while sealed | Required design constraint; inspection |
| HW-28 | Device shall operate for a 30-day deployment cycle with margin | Proposed; duty-cycle measurement |
| HW-29 | Device shall store one deployment cycle of events and images before offload | Proposed; capacity test |
| HW-30 | Device shall expose no command path capable of initiating imaging | Required design constraint; code review and negative test |
| HW-31 | Device shall survive summer enclosure temperatures without cell surface exceeding 45 °C | Proposed; environmental chamber |
| HW-32 | Device shall be armed at placement, so carriage from the collection point is not recorded as a movement event | Proposed; bench and field test |

### 4.2 Withdrawn requirements

| ID | Withdrawn requirement | Reason |
|---|---|---|
| HW-13 | Inertial sensor as primary wake and removal evidence | Rejected. Camera is occluded when closed; removal imaging yields no frame. D-31 |
| HW-14 | Fused inertial/light event classification | Not needed. The trigger is unambiguous; movement is logged separately |
| HW-15 | 10 ms inertial wake path | Folded into HW-24 |
| HW-16 | Event capture in darkness without a light step | Superseded by the accepted night limitation, §3A |
| HW-17 | Both event classes retained separately | Replaced by ordinary event types; see DATA_MODEL §3 |
| HW-18 | Clock status per event | Retained as a data-quality flag, not a hardware requirement |
| HW-19 | No remote imaging path | Reissued as HW-30 |
| HW-20 | 45 °C cell limit | Reissued as HW-31 |
| HW-21 | Rigid accelerometer coupling | Retained as a mechanical note, §3F |

## 5. Trigger logic concept

1. MCU sleeps. The light comparator and accelerometer interrupt are the only active loads.
2. **Light path:** illumination rises above threshold inside the cavity and persists past the debounce window.
3. MCU wakes, confirms the event, and applies the lockout check.
4. Camera powers, settles, and captures three frames at the configured intervals.
5. Event record written with class, timestamps, and battery state.
6. **Motion path (independent):** accelerometer interrupt records a movement event and schedules a location fix. No imaging.
7. Records queue for transmission; the device returns to sleep.

Thresholds, debounce, lockout, arming delay, and location-fix interval must be set by measurement and fixed before field use.

## 6. Power budget sketch

Indicative only; to be replaced with bench measurements.

| Load | Duty | Note |
|---|---|---|
| MCU deep sleep | Continuous | Dominant baseline load |
| Light comparator | Continuous | Microamps; the reason this design is viable |
| Accelerometer (motion interrupt) | Continuous, low-power mode | Microamps at low output data rate |
| Location fix | ~4/day | The largest single energy consumer after imaging |
| Modem attach and upload | ~2/day | Registration bursts dominate; use PSM/eDRX |
| Camera burst | A few per week | Short, high current |

Location fixes, not the camera, are likely to set runtime. If a 30-day cycle comes up short, reduce fix frequency before reducing image quality.

## 7. Reliability and misuse controls

- No remote command to activate imaging. HW-30 makes this architectural: no command path exists.
- No audio capability; no facial recognition or biometric processing.
- Access to records is public by design (D-40). Controls therefore protect the volunteer, not the data: no home address, no precise location of a volunteer's property.
- Records distinguish sensor triggers from verified openings, and mark every event as alleged rather than established.
- The system must not provide instructions or features for pursuing, confronting, or identifying a person.

## 8. Engineering unknowns

- Light sensor part, threshold, and whether a comparator or an interrupt pin is used.
- Camera module, lens, and exposure behaviour when the lid opens onto a bright or dark scene.
- Whether the burst reliably captures a face at typical opening distance.
- Accelerometer part and motion threshold.
- GNSS versus cellular-only location, and the accuracy each provides indoors and on a porch.
- Modem choice, plan cost, and coverage at candidate sites.
- Cell capacity versus a 30-day cycle with 4 fixes per day.
- Thermal behaviour of a sealed package in summer sun.
- Enclosure and mounting method inside the outer package.
- Final unit cost and assembly effort.
