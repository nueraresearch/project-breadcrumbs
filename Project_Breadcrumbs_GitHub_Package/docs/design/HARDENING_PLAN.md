# Design Hardening Plan

**Status:** Proposed engineering and methods changes. None are approved; items that alter owner-confirmed decisions are marked **[requires owner approval]**.
**Companion documents:** [`../review/DESIGN_REVIEW_R1.md`](../review/DESIGN_REVIEW_R1.md), [`../governance/THREAT_MODEL.md`](../governance/THREAT_MODEL.md), [`../governance/DATA_PROTECTION_CONTROLS.md`](../governance/DATA_PROTECTION_CONTROLS.md)

## 1. How to use this document

Findings from the review are addressed here in priority order. P0 items change what gets built and must be resolved before the BOM is frozen. P1 items can be resolved during prototyping. P2 items are refinements.

| Priority | Items | Consequence of deferring |
|---|---|---|
| **P0** | H-01 trigger architecture, H-02 comms tier, H-03 thermal safety, H-04 capture latency and power | Rework of hardware, enclosure, and power after assembly; invalid data |
| **P1** | H-05 method and control arm, H-06 key architecture, H-07 firmware and identity, H-08 cost realism | Weak analysis, unusable results, budget failure mid-pilot |
| **P2** | H-09 data integrity details, H-10 enclosure and tamper, H-11 documentation | Repairs and confusion, not failure |

## 2. H-01 — Detect removal, not just opening (P0) — **rejected 2026-10-30**

> **Outcome:** rejected by the owner (D-31). The proposal assumed a camera that could observe a removal. The camera is mounted inside a sealed package and is occluded until the lid opens (D-27), so a removal-triggered burst would photograph the inside of a closed lid. Removal is instead observed through location telemetry (D-32), which the design now includes as a primary output. The reasoning below is retained as a record of the review, not as a live recommendation.

**Finding B-01.** The design observes a person opening the package on the porch. The common pattern is lift-and-carry, which produces no interior light change and therefore no event at all. The pilot would then report recovery statistics over a sample that systematically excludes many of the thefts that occurred — and would not know it had done so.

**Proposed detection architecture — three channels, fused:**

| Channel | Detects | Role |
|---|---|---|
| Inertial (accelerometer) | Lift, tilt, sustained motion, repeated handling | **Primary** wake and event |
| Light | Interior illumination step consistent with opening | Corroboration and classification |
| Magnetic reed or pull-tab (optional) | A lid physically opened | High-confidence opening signal, where geometry allows |

The distinction that matters is **classification versus detection**. The accelerometer says "this package moved" and wakes the system cheaply and immediately. The light sensor then says whether what followed looks like an opening. This yields two event classes rather than one:

- `REMOVAL_SUSPECTED` — moved beyond threshold, no light step.
- `OPENING_SUSPECTED` — light step with or without prior movement.

Both are retained. A pilot that can distinguish "taken away" from "opened here" is answering a materially different and more interesting question than one that cannot, and it recovers validity when the device is never seen again.

**Night behaviour must be decided, not assumed.** In a dark porch and a closed package, opening admits very little light, so the light channel is weakest when opportunity is highest. Three options:

1. Accept that night openings are largely undetected, and state it as a scope limit in every report. Cheapest, honest, and probably correct for a feasibility pilot.
2. Rely on the inertial channel for night events, capturing a burst on movement with whatever ambient light exists plus a brief, low-power fill light. Effective, but the fill light makes the device conspicuous.
3. Require a lit porch for participation. Reduces the sample and biases it toward a particular kind of house.

**Recommendation: option 1 for the pilot, with option 2 prototyped and measured.** Do not silently ship option 3 by recruiting only from well-lit streets.

**[requires owner approval]** This extends confirmed decision D-09 (light sensor preferred as trigger) rather than replacing it. The light sensor remains the classification signal; it simply stops being the sole gate.

## 3. H-02 — Choose the communications tier (P0) — **decided 2026-10-30**

> **Outcome:** the owner chose cellular telemetry transmitting all records including images (D-33), not the metadata-only tier recommended below. Reasons that favour the owner's choice: image bursts are small (under 1 MB per event) and infrequent, so the bytes are cheap; a 30-day cycle makes power manageable; and location data, which is a primary output (D-32), requires a radio in any case. The Tier B reasoning below is retained for the record. Its one live constraint still applies: no remote capture command may exist (HW-30), because a device that can be asked for images can be asked for them at any time.

**Finding B-02.** Tier A preserves privacy and destroys the primary observation for unrecovered devices. Tier C preserves the observation and creates a remote camera. Neither is currently chosen.

**Recommendation — superseded by D-33 (cellular, all records transmitted).** Tier B as originally proposed: event class, timestamp, module ID, battery, and coarse state leave the device; images do not. Full comparison and consequences in [`THREAT_MODEL.md`](../governance/THREAT_MODEL.md) §6.

Consequences to accept explicitly if Tier B is adopted:

- A radio, antenna, SIM or eSIM, and a recurring data cost enter the BOM.
- Duty-cycled attachment is required to avoid the standby current of a registered modem; keep the radio deregistered between syncs.
- The device acquires a network identity. It is not a person identifier, but it is a customer-identifying record with the carrier and must be treated as such.
- A device that can transmit metadata can also be asked to transmit more. The absence of an image-transmission path must be enforced in firmware and verifiable, not merely promised.

## 4. H-03 — Battery chemistry and thermal safety (P0) — **decided 2026-10-30**

> **Outcome:** the owner chose a rechargeable cell, sealed in the enclosure, charged off-device by swapping (D-35). That is a modified form of the recommendation below: the thermal argument against in-enclosure charging still holds, and the design honours it by putting no port on the deployed unit. The thermal design rules below remain in force regardless of chemistry.

**Finding B-05.** A sealed, dark enclosure in direct summer sun is a battery environment before it is an electronics environment. A porch-facing package can exceed 60 °C internally.

| Option | Advantage | Disadvantage | Verdict |
|---|---|---|---|
| Li-ion rechargeable, in-enclosure charging | Convenient cycling | Worst thermal behaviour; charging in a sealed hot enclosure; a charging port is an ingress and tamper point | **Not recommended** |
| LiFePO4 rechargeable, external charging only | Tolerant chemistry; long cycle life | Lower energy density; needs a charger in the ops kit | **Selected form (D-35)**: rechargeable, charged externally |
| Primary lithium (CR123A / AA), non-rechargeable | No charging circuitry, no port, no charge-state hazard; simplest failure mode | Consumable cost; must be sourced and disposed of properly | Not selected (D-35) |
| Alkaline | Cheap, no transport restrictions | Poor cold and high-drain behaviour; leakage | Not recommended |

**Required design rules:**

- No charging connector on the deployed unit. Cells are charged or replaced off-device.
- Protection circuit and a thermal cut-off on the cell.
- Cell positioned away from the sun-facing surface, with an internal air gap.
- Vent path that does not admit water; do not fully seal a cell enclosure.
- Surface temperature specification and a 60 °C ambient soak test as a gating acceptance criterion (H-09).
- Cells with a documented UN 38.3 test summary if shipped.

## 5. H-04 — Capture latency versus battery life (P0)

**Finding M-06.** The 0 / 1 / 2.5 s timings assume a camera ready to capture in well under a second. That assumption is a power decision, not a timing decision, and the trade-off is not currently visible.

| Mode | Camera state | First frame | Standby current (indicative) | Runtime on 2000 mAh (indicative) |
|---|---|---|---|---|
| A — cold start | Camera unpowered | 0.6–1.5 s | ~0.1–0.2 mA system | 12–18 months |
| B — warm standby | Camera in low-power standby | 0.15–0.4 s | ~2 mA system | 25–45 days |
| C — continuous | Streaming or periodic frames | < 0.1 s | Tens of mA | Days |

Mode C is excluded by decision: it violates the no-continuous-capture constraint.

These are indicative order-of-magnitude figures for a planning discussion, not measurements. They must be replaced with bench results in [`../pilot/TEST_AND_VALIDATION_PLAN.md`](../pilot/TEST_AND_VALIDATION_PLAN.md) group D.

**The trade-off in one sentence:** keeping the camera warm buys roughly 400–1300 ms of latency and costs roughly an order of magnitude of battery life.

**Recommendation: Mode A.** Wake on the light step, then power and capture. Accept 0.6–1.5 s to the first frame. A person opening a package stays in view for one to several seconds, so a sub-second first frame matters less than it appears. The 30-day cycle (D-34) widens the margin considerably: warm standby at 25–45 days would cover a single cycle with almost nothing spare, and it would leave no headroom for location fixes, which are now the larger load (D-32).

**What to change about the burst:** keep three frames (D-08), but move the second and third earlier — the current 1.0 s and 2.5 s spacing is generous for the moment that matters. Prototype 0 / 0.5 / 1.5 s against 0 / 1.0 / 2.5 s and choose on measured subject-visibility, not on preference. If the subject is usually gone by 2.5 s, the third frame is a photograph of a porch.

**[requires owner approval]** Timing changes are proposals against D-08's specified example timings, which the decision log already marks as illustrative rather than final.

## 6. H-05 — Make the study able to detect induced theft (P1)

**Finding M-02.** A volunteer sample of households that already suspect theft will produce a number, and that number will not be the neighbourhood theft rate. It will be the theft rate at houses that volunteered, during the weeks they were watching. Without a comparator, no reviewer can tell whether the modules measured theft or attracted it.

**Proposed design changes:**

1. **Control arm.** At each participating site, alternate between an instrumented package and an inert package of similar mass and appearance, randomised by a pre-generated schedule. The inert package still has a return label and a reward insert, so the only difference is instrumentation. Difference in loss rate between arms estimates the device's own effect.
2. **Randomised deployment windows.** Randomise start day and duration within the approved range rather than deploying "whenever we visit". This removes a strong source of confounding.
3. **Pre-registration.** Write the analysis plan, the primary outcome, the exclusion rules, and the thresholds into a dated file in this repository *before* Phase 3. Any later deviation is documented with its reason. The primary outcome is settled (D-47) and the plan is drafted in [`../pilot/PRE_REGISTRATION_ANALYSIS_PLAN.md`](../pilot/PRE_REGISTRATION_ANALYSIS_PLAN.md).
4. **Correct the unit of analysis.** Cycles are clustered within modules and sites. Report site-level summaries and cluster-aware uncertainty; do not compute confidence intervals as if 30 independent events were observed. With 30 cycles across 30 host households, cycles are no longer repeated measures on one address. The unit of observation is the deployment and the object of study is the removal event, so report events against exposure and report household counts only for completeness. Self-selection still means this is a case series, not a sample of the town. Treat anything reported per cycle as descriptive, not inferential.
5. **Handle informative missingness explicitly.** A device that is never recovered is not missing at random — it is the outcome. Report a denominator table showing attempted, deployed, retrieved, recovered, and never-seen, and never compute a rate whose denominator silently excludes the lost cases.
6. **Suppress small cells.** No published percentage with a denominator under 20; no cell under n = 5.

**What this costs:** roughly one extra package per cycle, plus a modest amount of scheduling discipline. It is the cheapest available increase in the study's evidential value.

## 7. H-06 — Key architecture (P1)

**Finding M-05.** "Local encrypted image storage" is satisfied by a folder password, which protects against nothing in the relevant threat model.

Adopt the sealed-box architecture in [`DATA_PROTECTION_CONTROLS.md`](../governance/DATA_PROTECTION_CONTROLS.md) §4: device holds only a public key, wraps to a study key held offline, crypto-shred on retirement. The property to verify on the bench is narrow and testable: *given physical possession of a module and unlimited time, an attacker without the study key cannot recover any prior image.* That test is a gate, not a nice-to-have.

## 8. H-07 — Firmware, identity, and the no-remote-capture guarantee (P1)

| Control | Requirement |
|---|---|
| Remote capture | No command path exists. Not disabled — absent. Verified by code review and by a test that attempts it and fails. |
| Firmware update | Signed images only; secure boot; rollback to a known-good signed image; version recorded per event. |
| Debug access | Disabled on production units; enabling it is a maintenance procedure with a record. |
| Identity | `module_id` is stable for the life of the device. **Every image and event additionally carries a `deployment_id` and a globally unique `record_id`**, because `module_id` + `frame_index` alone collides across the three deployments a module serves in a 90-day pilot, and across more over its service life. |
| Clock | RTC with a stated maximum drift of 2 s/day; resynchronised at every retrieval; drift recorded as a data-quality flag; an event with unknown clock is never silently treated as accurate. |
| Storage | Append-only event log, per-record hash chained to the previous record, so deletion or reordering is detectable. |
| Reset | Reset after retrieval clears keys and images, and writes a reset record before clearing. |

## 9. H-08 — Cost realism (P1)

**Finding M-01.** The $600–$900 target is not achievable for the described scope. This is worth stating plainly now, because the alternative is discovering it during procurement.

**Rough order of magnitude, per module, US, small batch, 2026.** Part choices and the reasoning behind each line are in [`../hardware/COST_REDUCTION_PLAN.md`](../hardware/COST_REDUCTION_PLAN.md).

| Item | Est. USD | Note |
|---|---:|---|
| ESP32-S3 camera board | 11 | Dev board with OV2640 (D-57) |
| Light sensor + accelerometer | 3 | VEML7700-class (D-60) |
| Storage | 6 | 32 GB microSD (D-61) |
| Modem + antennas | 34 | BG95-M3 with carrier, LTE and GNSS antennas (D-58) |
| Battery + protection | 9 | 18650 LiFePO4, holder, protection (D-61) |
| Enclosure and mount | 7 | Tray and foam insert plus retail box (D-62) |
| PCB + assembly | 0 | None; dev boards arrive assembled (D-57) |
| Reed switch and magnet | 1 | Arming (D-63) |
| Harness, connectors, misc | 5 | — |
| **Subtotal** | **~76** | |
| Spares and attrition (+30%) | 23 | Devices are expected to be lost |
| **Per deployable module** | **~99** | |

**Programme level, 10 modules, 90 days:**

| Item | Est. USD |
|---|---:|
| 10 modules at ~99 | 990 |
| Connectivity, 10 × 1NCE lifetime SIM | 140 |
| Reward inserts (~50% of 30 cycles, at documented replacement cost) | TBD |
| Legal review — target, pro bono local counsel | 0 |
| Legal review — fallback if pro bono falls through | 1,500–3,000 (excluded from the target total) |
| Ethics review | 0–2,000 |
| Shipping and insurance | 400 |
| Participant materials, printing, ops kit | 150 |
| Hosting and tooling | 200 |
| Contingency (20%) | 380–780 |
| **Indicative total, pro bono target** | **~2,300–4,700**, excluding the reward line |
| **Indicative total, paid counsel** | **~4,100–8,300**, excluding the reward line |

**Call it $2.3k–$4.7k on the pro bono assumption, and $4.1k–$8.3k if counsel has to be paid**, excluding labour and the reward line. Assumptions: US pricing, small batch, no GNSS, cellular telemetry with image transmission. Adding GNSS adds $15–25 per module. Image bursts are small — under 1 MB per event — and infrequent, so transmitting them adds a few megabytes per module per month rather than multiplying connectivity cost; the modem and the plan dominate. A design that streamed images continuously would multiply cost by roughly five to ten, and that is not this design. Shipping was priced for repeat visits to a few addresses; thirty distinct host households will cost more.

This is a planning ROM at roughly ±50%, not a quotation. Its purpose is to show the gap between the target and the design, and to identify the two line items that are not hardware at all: legal and ethics review together may exceed the hardware budget.

**The choice has since been made.** The owner chose the fuller scope: cellular telemetry, image transmission, and a reward (D-33, D-38). The budget therefore has to be revised upward to meet the design rather than the design cut down to meet the target. D-51 records the $600–$900 figure as a target, not a budget.

## 10. H-09 — Acceptance thresholds (P1)

**Finding M-08.** Thresholds must be numeric, approved before testing, and measured by a stated method. All values below are proposals for approval, not results. Set them before Phase 1 and do not revise them after seeing data without recording the revision and its reason.

| ID | Criterion | Proposed threshold | Method |
|---|---|---|---|
| AT-01 | False triggers, benign porch, continuous 24 h | ≤ 1 per 24 h (target ≤ 0.3) | 72 h capture at 3 sites |
| AT-02 | False triggers, adversarial lighting | Measured, reported | 30 min headlight sweep + shadow + porch-light cycling |
| AT-03 | Opening detection, daylight | ≥ 90% of 30 scripted trials | Bench + porch |
| AT-04 | Opening detection, night | **Declared out of scope (D-30)**; measured and reported, not gated | 30 trials in true darkness; report the measured rate with the scope statement attached |
| AT-05 | Removal registration | ≥ 95% of 20 lift trials produce a movement event and a location fix | Scripted lifts with varied speed; imagery is not expected and is not tested here |
| AT-06 | First frame latency | ≤ 800 ms p50, ≤ 1500 ms p95 | Bench, 100 triggers |
| AT-07 | Burst completion | ≥ 95% of triggers produce exactly 3 frames | Bench + field |
| AT-08 | Subject visible in ≥ 1 frame | ≥ 70% of 50 adjudicated real events | Human adjudication, recorded rubric |
| AT-09 | Battery runtime | ≥ 35 days at four location fixes and two uploads per day, 20% reserve | Duty-cycle measurement; must cover one 30-day cycle with margin |
| AT-10 | Thermal | No cell surface > 45 °C in 60 °C ambient soak; no swelling | Environmental chamber |
| AT-11 | Data integrity | 100% of images hash-verified; 0 losses in 100 power-cut cycles | Automated test rig |
| AT-12 | Stolen-device resistance | Zero recoverable images without study key | Documented attack attempt |
| AT-13 | Clock drift | ≤ 2 s/day; resync verified at retrieval | Bench over 7 days |
| AT-14 | Recovery workflow | 5 complete cycles, 2 operators, 0 data errors | Dry run |
| AT-15 | Privacy controls | 100% of access events logged; revocation under 1 h | Drill |

AT-12 is the one most likely to be passed by redefinition, and it must not be. AT-04 is no longer a threshold: night blindness is a declared scope limit (D-30), so the test exists to size the limitation rather than to pass it.

## 11. H-10 — Enclosure, field of view, and tamper (P2)

- **Field of view fixed mechanically at assembly.** Downgrade the pin/shim so the camera cannot be re-aimed without visible damage. A participant who can aim the camera is a participant who can point it at a neighbour; the threat model rates that as critical and a promise in the consent form does not mitigate it.
- **Bounded aperture.** Size the aperture and use a fixed-focus lens so the useful range ends near the package-opening area. Optical limiting is more reliable than a policy about where to point.
- **Light leaks.** Test seams under bright illumination; a leak is a false trigger source and the test plan already identifies it, but it should be a design requirement rather than a test discovery.
- **Tamper evidence.** A single-use seal, photographed at deployment and at retrieval. The photograph is a record, not a forensic claim.
- **Appearance.** Ordinary. No logos, no visible LEDs during deployment, no serial visible externally. A device that looks like a research device is a device that gets discarded.
- **Recoverability.** A return path routed to a project address, never to the participant's home.

## 12. H-11 — Revised phase gates (P1)

| Phase | Entry gate | Exit gate |
|---|---|---|
| 0 — Readiness | Review accepted | Legal position recorded; ethics determination in writing; all P0 items resolved |
| 1 — Prototype | Costed BOM; components selected | AT-01 to AT-08, AT-11 to AT-13 pass on bench |
| 2 — Onboarding | AT-09, AT-10, AT-14, AT-15 pass; consent approved | 2 pilot sites fully onboarded, dry run clean |
| 3 — Field | Pre-registration filed; stop rules signed | 90 days or early stop; data reconciled |
| 4 — Analysis | Denomination table complete | Report with limitations; deletion executed and verified |

No phase may be entered with an open blocking finding from [`DESIGN_REVIEW_R1.md`](../review/DESIGN_REVIEW_R1.md).

## 13. Summary of proposed changes to confirmed decisions

Recorded here for the owner's review; nothing in this list takes effect until it appears as an approved entry in `DECISION_LOG.md`.

All four items below were decided by the owner on 2026-10-30.

| Decision | Outcome | Note |
|---|---|---|
| D-09 | **Rejected.** The light sensor remains the sole imaging gate | The camera is occluded inside the sealed box, so a removal-triggered burst would capture nothing. D-31 |
| D-08 | **Accepted.** Three-shot burst retained; timing still to be chosen on measured face visibility | Timing is not settled, but the frame count is |
| Communications | **Rejected the proposed Tier B.** Cellular telemetry transmitting all records, images included. D-33 | Removal is observed through location data, not imagery |
| Reward | **Accepted in modified form.** Reward equals the documented replacement cost of the contents. D-38 | Set per deployment rather than as a fixed figure |
