# Project Breadcrumbs — Decision Log

This log separates user-confirmed project direction from preliminary proposals and unresolved items.

## A. Confirmed project direction from the project owner

| ID | Decision / direction | Notes |
|---|---|---|
| D-01 | Project name: Project Breadcrumbs | Community safety research pilot |
| D-02 | Organization: Nuera Research and Developmental Laboratories | As supplied by project owner |
| D-03 | Tagline: “Following patterns others miss.” | As supplied by project owner |
| D-04 | Central philosophy: “The goal isn't to catch people. The goal is to understand the system.” | Preserve as project framing |
| D-05 | Program is voluntary | Homeowners participate by choice |
| D-06 | Participants place packages on their own porches/property with authorization | Proposed bait-package research deployment |
| D-07 | Camera faces outward toward the person opening the package | User-selected design direction |
| D-08 | Camera captures a three-shot burst when package opening is detected | User-selected behavior |
| D-09 | A light-sensitive camera switch/sensor is preferred as the opening trigger | User-selected trigger direction |
| D-10 | Module is intended to be low-cost, reusable, and recoverable | Project design goals |

## B. Project proposal targets supplied by the owner

| Item | Target | Status |
|---|---:|---|
| Pilot duration | 90 days | Confirmed |
| Number of modules | 10 | Confirmed 2026-10-30 |
| Deployment cycles | 30 (10 modules × three 30-day cycles, one volunteer host each) | Confirmed 2026-10-30; supersedes the earlier ~120 figure |
| Pilot budget | $600–$900 | Target, not a budget. See D-51; programme estimate is roughly $3k–$5.5k with pro bono counsel |

## C. Preliminary engineering proposals (not yet approved)

- Digital ambient-light sensor rather than a simple LDR, subject to testing.
- Threshold, duration, and lockout logic to reduce false triggers.
- Example frame timing of 0, 1, and 2.5 seconds; not final.
- Local encrypted image storage.
- Secure transfer when connectivity is available.
- Optional movement sensor.
- Location capability, with method and frequency undecided.
- Rechargeable power system.
- Status indicator and serviceable enclosure.
- Aggregate reporting and restricted image access.

## D. Open decisions

Status as of 2026-10-30. Items settled by the owner decisions in section F are marked and cross-referenced; the rest remain open.

| # | Decision | Status |
|---|---|---|
| 1 | Exact camera module, lens, resolution, and low-light performance | **Open** |
| 2 | Light sensor type, threshold, and false-trigger acceptance criteria | **Partly settled.** Sensor sits inside the sealed cavity (D-28). Part and threshold open |
| 3 | Exact three-frame timing and camera wake latency | **Open.** Frame count fixed by D-08; timing unsettled |
| 4 | Whether movement sensing is in the first prototype | **Settled.** Yes, logging only; never triggers imaging (D-31) |
| 5 | Whether location is in the first pilot, and its method and update policy | **Settled in principle.** Location is a primary output (D-32). GNSS versus cellular-only, and fix interval, open |
| 6 | Communications method and recurring cost | **Settled.** Cellular LTE-M or NB-IoT, all records transmitted (D-33). Carrier, plan, and monthly cost open |
| 7 | Battery type, capacity, charging method, runtime target | **Settled.** Rechargeable, sealed, swapped off-device (D-35); 30-day cycle (D-34). Cell capacity open |
| 8 | Storage capacity, encryption, image retention | **Settled in principle.** One cycle of storage (D-36), sealed-box encryption (D-12), public retention (D-40). Capacity figure open |
| 9 | Enclosure dimensions, materials, weather resistance, mounting | **Open** |
| 10 | Recovery reward amount, terms, redemption | **Partly settled.** Reward equals documented replacement cost (D-38). Redemption process open |
| 11 | Exterior notice/disclosure policy | **Settled.** No exterior notice (D-39) |
| 12 | Participant consent materials and withdrawal process | **Open** |
| 13 | Numeric go/no-go thresholds | **Open.** Principle accepted (D-23); values not set |
| 14 | Costed BOM | **Open** |

## E. Proposed decisions arising from design review R1 (2026-10-30)

These were proposed by an independent desk review of the Revision 1.0 documents. See `docs/review/DESIGN_REVIEW_R1.md`. **None are approved.** They are listed here so the owner can accept, amend, or reject them through normal change control.

| ID | Proposed decision | Rationale | Supporting document |
|---|---|---|---|
| D-11 | Default communications posture is Tier B: event metadata leaves the device; images remain on-device until physical recovery | Preserves recovery timing without creating a remote imaging capability | Threat Model §6 |
| D-12 | Device-side encryption uses a per-device keypair sealing to a study public key; study private key held offline; crypto-shred on retirement | Theft of a module must not disclose its archive | Data Protection Controls §4 |
| D-13 | Adopt the retention defaults in Data Protection Controls §5 until superseded by an approved schedule | A blank control becomes whatever is convenient | Data Protection Controls §5 |
| D-14 | Three roles with a two-person rule for image access; MFA; no personal cloud or messaging-app transfer | Insider and careless disclosure are the most likely failure paths | Data Protection Controls §3 |
| D-15 | Research-only posture toward law enforcement: no proactive sharing, comply with valid process after counsel review, notify participants unless barred | Determines consent text, insurance, and participant risk; cannot be decided later | Data Protection Controls §7 |
| D-16 | Add an inertial (removal) trigger as a co-primary detection channel alongside the light sensor | Removal is the dominant theft pattern; a closed dark package admits little light at night | Hardening Plan §2 |
| D-17 | Battery: primary lithium or LiFePO4; no in-enclosure charging; thermal soak test as a release gate | A sealed sun-exposed enclosure is a battery safety problem first | Hardening Plan §4 |
| D-18 | Add a randomised inert-package control arm at the same sites | Separates measured theft from theft induced by the device | Hardening Plan §6 |
| D-19 | Pre-register the analysis plan, primary outcome, and exclusions before Phase 3 | Prevents post-hoc selection | Hardening Plan §6 |
| D-20 | Publication suppression: no cell with n < 5; no percentage with denominator < 20; no cross-tabs on `site_code` | The most likely public failure is a chart that identifies a house | Data Protection Controls §8 |
| D-21 | Firmware: signed images, secure boot, no remote-capture command path, unique `record_id` per image | Makes the privacy guarantee architectural rather than promissory | Hardening Plan §8 |
| D-22 | Operational security: publish the science, withhold the device fingerprint; keep an operations annex out of the public repository | A published device description teaches a thief to discard it | Threat Model §8 |
| D-23 | Adopt the numeric acceptance thresholds in Hardening Plan §10, fixed before testing | "Ready" must not be a matter of opinion | Hardening Plan §10 |
| D-24 | Revise the pilot budget to an indicative $5k–$9k, superseding the $600–$900 target pending a costed BOM | The original figure omits legal review, reward inserts, connectivity, and spares. Superseded by D-51 and D-54: with pro bono counsel the current estimate is ~$3k–$5.5k, or ~$4.8k–$9k if counsel is paid | Hardening Plan §9 |
| D-25 | Adopt the stop rules in Threat Model §9 with a named accountable lead | A pilot that cannot pause itself is not a pilot | Threat Model §9 |
| D-26 | Confirm or reject the proposed changes to D-08 and D-09 in Hardening Plan §13 | These alter owner-confirmed direction and require explicit approval either way | Hardening Plan §13 |

## F. Owner decisions recorded 2026-10-30 (D-27 to D-53)

Recorded from the owner's answers to the open-question list. These supersede the corresponding proposals in section E where noted.

| ID | Decision | Notes |
|---|---|---|
| D-27 | Camera is mounted inside the sealed package, fixed at assembly, aimed at the opening, and blind while the lid is closed | Volunteers receive a closed box; they do not open or aim it |
| D-28 | The light sensor sits inside the same cavity; the interior is effectively pitch black, so any light step is treated as the package opening | Removes ambient-light false triggers as a design problem |
| D-29 | The capture target is the face of the person opening the package | Drives lens, mounting height, and exposure choices |
| D-30 | In true darkness no light step occurs; night openings may go unrecorded. Accepted as a scope limit, not mitigated | Site lighting recorded as a sample characteristic |
| D-31 | Movement never triggers imaging. The accelerometer logs movement events and schedules location fixes only | Supersedes D-16, which proposed an inertial imaging trigger |
| D-32 | Location is a primary research output: a fix on each movement event and at a configured interval | Makes removal observable without a camera |
| D-33 | Communications are cellular (LTE-M or NB-IoT, SIM or eSIM). All collected records, including images, are transmitted | Supersedes D-11 (metadata-only) |
| D-34 | Deployment cycle length is 30 days, not 90 | Reduces cost, power demand, and exposure window. Owner confirmed the arithmetic 2026-10-30: a 90-day pilot is three 30-day cycles per module, so 10 modules yield 30 deployment cycles. The earlier ~120 figure was computed against 90-day cycles and is withdrawn |
| D-35 | Rechargeable cell, sealed in the enclosure, charged off-device by swapping cells. No charging or data port while sealed | Prototype uses standard cells; later revisions use a higher-grade cell of the same form factor |
| D-36 | Storage is sized for one deployment cycle with offload at every recovery | Expected well under 2 GB |
| D-37 | No supplemental illumination | Power, cost, and conspicuousness outweigh the benefit |
| D-38 | The recovery reward equals the documented replacement cost of the package contents | Set per deployment rather than as a fixed amount |
| D-39 | No exterior notice; the package is addressed and presented as an ordinary shipment | Disguise is part of the method |
| D-40 | All collected data, including images, is released publicly | Supersedes D-13, D-14, D-15, D-20 and D-22. Release is subject to D-41 (location precision) and D-42 (caption standard), both confirmed 2026-10-30 |
| D-41 | Published location data is reduced in precision and delayed, because a precise coordinate identifies the volunteer's home rather than the subject | **Confirmed 2026-10-30** |
| D-42 | Publication captions say the package was opened, not that a theft occurred; no naming, no identification requests, no guilt framing | **Confirmed 2026-10-30.** Owner's reasoning: the recording occurs inside private property (the box), and a person who opens a package not addressed to them has displaced their own privacy interest by doing so |
| D-43 | Initial site is Monte Vista, Colorado; expansion to other cities later. Town meeting approval is the gate to fielding | State confirmed 2026-10-30 |
| D-44 | Legal review is commissioned if counsel advises it is required; owner's position is that a silent camera inside a sealed package on private property raises no privacy issue for the opener | Recorded as the owner's position, not as legal advice |
| D-45 | The owner builds the prototypes; the company owns the data; the data is published | — |
| D-46 | The owner holds authority to pause the pilot | — |
| D-47 | **Resolved 2026-10-30:** primary outcome is time from deployment to removal, analysed as a survival curve. Post-removal displacement is the headline secondary; loss rate per 100 deployment-days is descriptive | Owner delegated the choice. Reasoning: a survival curve uses every deployment-day and handles censoring, whereas a proportion needs a denominator this sample cannot supply. Displacement is secondary because it is conditional on a removal occurring. Fixed in `docs/pilot/PRE_REGISTRATION_ANALYSIS_PLAN.md` |
| D-48 | No inert control arm. The owner judges the local problem is genuine and not device-induced; the limitation is recorded instead | Supersedes D-18 |
| D-49 | Multiple theories and questions may be pre-registered, in a dated file, before fielding | Supersedes D-19, which assumed a single primary outcome |
| D-50 | Outcome states are tracked separately: not lost, recovered and redeployable, recovered and needing refurbishment, lost and never recovered | — |
| D-51 | $600–$900 is retained as a target, not a budget. Budget to be revised against a costed BOM | Amends D-24 |
| D-52 | **Resolved 2026-10-30:** images that appear to depict a minor, or a person with no connection to the opening, are never published. They are flagged at adjudication, access-restricted, and deleted once the adjudication record is written. The number withheld is published by category | Owner delegated the choice. Publishing a child in a package-theft context is a different legal and ethical proposition from publishing an adult who opened the package, and publishing an uninvolved passer-by has no research value at all. Withholding is counted rather than silent, and deletion rather than indefinite hold limits breach exposure |
| D-53 | One deployment per volunteer. Each 30-day cycle is hosted by a different household, so 10 modules rotating three times require 30 volunteer hosts | Reduces the burden on any one household and gives every deployment a distinct site, which removes repeated-measures clustering. If 30 hosts cannot be recruited, the fallback is fewer cycles or a shorter pilot rather than repeated deployments at one address; that fallback is not yet decided |
| D-54 | Legal review is targeted as pro bono local counsel, and the budget assumes zero cost for it. A paid-counsel fallback of $1,500–3,000 is retained as a separate line rather than removed | A planning assumption, not an expectation. Pro bono must not reduce the scope the review covers, and a general practitioner may not be able to cover surveillance and privacy law; scope is to be confirmed in writing before the review starts |
| D-55 | Volunteers collect and return packages at the project's operating base in Monte Vista rather than at their own door. The address is held in the private operational annex and is not published in this repository | Cuts travel to one hub and puts briefing and consent in person. Two consequences: the device must be armed at placement, because carriage from the hub would otherwise register as a movement event (HW-32); and the base becomes a single physical point of failure (T-18) |
| D-56 | Pursue delivery-volume data from the local post office as external context for exposure | Sought as context, not as a sampling frame: the thirty deployments are not a random sample of deliveries, so the data cannot turn the results into a town theft rate. Daily figures are paired with removal dates and reported descriptively; no rate is computed from the pairing. Requires a written agreement and an aggregate scope only |
| D-57 | Prototype build uses an ESP32-S3 camera development board rather than a custom PCB, hand-assembled for all ten units | About $11 at single-unit pricing, with the camera interface and secure boot already present. A custom board can wait until bench tests justify it. Trade-offs: bulkier, and its USB connector must be removed or disabled to satisfy HW-27 |
| D-58 | Cellular is a Quectel BG95-M3, certified by FCC, PTCRB and AT&T, with integrated GNSS | One part replaces the modem and the separate GNSS receiver, so the $15–25 GNSS allowance disappears. Module certification does not automatically cover the host device; the integration guide must be followed |
| D-59 | Connectivity is a 1NCE lifetime SIM at $14 per device for ten years, 500 MB | About 4 MB a month against an estimated few MB of use. Monitor consumption and top up if exceeded. Replaces a budgeted $6 per device per quarter |
| D-60 | Light sensing uses a VEML7700-class digital sensor with interrupt; a photodiode and comparator are a later cost-down | Gives a settable threshold and a hardware interrupt without analogue tuning, which is worth more than $1 on a ten-unit prototype |
| D-61 | Power and storage are an 18650 LiFePO4 cell around 1500 mAh with protection, and a 32 GB microSD card | LiFePO4 tolerates the sealed-enclosure heat better than Li-ion; 32 GB is cheaper than a smaller card and one cycle needs far less |
| D-62 | Enclosure is a tray and foam insert inside the retail box, not a separate IP-rated enclosure | Saves about $11 and removes the problem of an enclosure that does not look like a parcel. The box is consumable and replaced every deployment |
| D-63 | Arming uses a reed switch and a supplied magnet: armed at placement, disarmed at retrieval | Deterministic and about $1. Avoids inferring placement from motion or a timer, which would mis-register carriage from the base (HW-32) |
| D-64 | Frame timing defaults to 0 / 0.5 / 1.5 s, with exposure bracketing if the sensor supports it | Better odds on the face than 0 / 1 / 2.5 s. Still to be confirmed against measured subject visibility |
| D-65 | Build cost target is ~$66 in parts and ~$86 per deployable module, against the previous ~$156 | Achieved by the choices above and below; all figures small-quantity estimates pending supplier quotes |
| D-66 | Storage is 16 MB of flash on the MCU board. No microSD card and no card slot | Saves $6, removes a connector and an opening in the sealed unit, and holds roughly twenty events. Trade-off: if uploads fail for a long stretch the buffer fills, so an eviction rule must be written rather than left to overflow |
| D-67 | One combined LTE and GNSS antenna, and foam cutouts instead of a machined tray | Saves $6 with no loss of required function. The retail box already provides structure and weather protection; a tray only adds cost |
| D-68 | Cellular is retained for the main pilot. The no-radio model stays available only as an optional Phase 0 validation build | The radio is the only way to observe removals that are never recovered. A community Wi-Fi scheme was considered and rejected: it would require storing volunteers' Wi-Fi credentials on a device designed to be stolen, and Wi-Fi cannot associate reliably from a moving vehicle |
| D-69 | Pilot SIM provider is Hologram, not 1NCE: about $63 for ten devices over three months against $140 for a ten-year 1NCE term. 1NCE remains the option if the study runs beyond a year | Amends D-59. Both work with the BG95-M3; the difference is commitment length, not capability. Per-megabyte pricing also removes the 4 MB/month ceiling risk |

### Resolution of the section E proposals

| Proposal | Status |
|---|---|
| D-11 Tier B metadata only | Superseded by D-33 |
| D-12 Sealed-box crypto, crypto-shred | Accepted |
| D-13 Retention defaults | Superseded by D-40 |
| D-14 Roles and two-person rule | Superseded by D-40 |
| D-15 Law-enforcement position | Superseded by D-40 |
| D-16 Inertial co-primary trigger | **Rejected** |
| D-17 Battery chemistry and thermal | Accepted in modified form as D-35 |
| D-18 Control arm | **Rejected** as D-48 |
| D-19 Pre-registration | Accepted, expanded as D-49 |
| D-20 Publication suppression | Superseded by D-40, subject to D-41 and D-42 |
| D-21 Signed firmware, no remote capture | Accepted as HW-30 |
| D-22 Ops/publication split | Superseded by D-40 |
| D-23 Numeric thresholds | Accepted; values still to be set before testing |
| D-24 Budget revision | Amended as D-51 |
| D-25 Stop rules | Accepted |
| D-26 Confirmation of D-08/D-09 changes | Resolved: D-09 change rejected, D-08 timing retained |

## G. Change control

When a decision is finalized:
- assign or update a decision ID;
- record the date and rationale;
- update affected requirements and documents;
- identify whether prototype or pilot documents need revision;
- retain prior revision history in Git.
