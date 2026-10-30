# Camera Subsystem — Outward-Facing, Opening-Triggered Three-Image Capture

**Revision:** 1.2  
**Status:** Proposed subsystem definition; not built or validated. Reflects owner decisions D-27 to D-51.

**Revision note:** Revision 1.1 proposed that motion detect and light classify. The owner rejected it on physical grounds: the camera is inside a sealed box and sees nothing until the lid opens, so a motion-triggered burst would photograph the inside of a closed lid. Revision 1.2 restores the light trigger as the only imaging gate and records the geometry that makes it reliable.

## 1. Purpose

The camera subsystem documents the moment a package is opened by someone other than its addressee, during an authorized, voluntary research deployment. It is event-triggered still photography, not surveillance.

## 2. Geometry and placement

This is the part of the design that was previously underspecified, and it is what makes the rest work.

- The module is mounted **inside** the package, bonded or clipped to the wall, with the camera aligned to the opening at assembly.
- The volunteer receives a **closed, sealed box** and places it on their porch. They do not open it, adjust it, or aim it.
- While closed, the camera is occluded by the lid. It cannot see the porch, the street, neighbours, or passers-by. Its field of view exists only when the box is open.
- The camera is fixed at assembly. It cannot be re-aimed without visible damage.
- The lens is chosen to frame a person at the opening: face and upper body at roughly arm's length to one metre.

**What this geometry buys, stated plainly.** A porch camera films everything that happens on a porch, all day, whether or not anything is wrong. This device films only the inside of its own package, only at the moment someone opens it. That is a materially narrower collection than an ordinary doorbell camera, and it is the strongest privacy property in the design.

**What it costs.** If the package is taken without being opened, the camera records nothing. That case is handled by telemetry, not imagery: the module logs movement and reports location, so the study still observes that the package left and roughly when. Imagery answers "who opened it"; the radio answers "did it leave". See [`HARDWARE_REQUIREMENTS.md`](HARDWARE_REQUIREMENTS.md) §3C.

## 3. Trigger

**Trigger: light-sensitive sensor mounted inside the sealed cavity (D-09, confirmed).**

Concept:
- The interior of a closed package is effectively pitch black.
- A light-sensitive element with a comparator or interrupt detects a rise in illumination.
- A rise that persists past the debounce window is treated as the lid opening.
- Threshold, debounce, and lockout are set by measurement.

**Why an enclosed sensor is more reliable than an exposed one.** An exposed light sensor has to distinguish an opening from sunrise, cloud shadow, headlights, and porch lighting, and that is where false-trigger engineering effort goes. A sensor inside a sealed dark cavity sees none of those. Any light it detects arrived because the box opened. The design is simpler, and the false-trigger problem largely disappears rather than being tuned away.

**Accepted limitation.** In true darkness the interior is already black and opening the box admits no light, so the event is not recorded. This depends on site lighting, not on the sensor. It should be reported as a scope limit, and site lighting should be recorded as a sample characteristic so the limitation can be quantified later. Adding a fill light would fix it at the cost of power, budget, and conspicuousness, and is not proposed.

**A second limitation, worth stating once.** The trigger proves light entered the box. It does not prove who opened it, why, or that a crime occurred. A volunteer opening their own package to check on it, a household member, or a person retrieving a misdelivered box all produce the same record. Captions and reports must say "package opened" and not "package stolen".

## 4. Three-image sequence

Three stills per qualifying trigger. The count is confirmed (D-08) and unchanged.

Timing interacts with the trigger in a way worth making explicit: at the instant the lid lifts, the sensor is looking at a scene that has just gone from black to brightly lit. Auto-exposure needs a moment. The first frame will be somewhat later than the light step, and the first few frames risk being overexposed.

| Schedule | Frame 1 | Frame 2 | Frame 3 | Note |
|---|---|---|---|---|
| Current example | 0.0 s after capture ready | +1.0 s | +2.5 s | Third frame may miss a person who has stepped back |
| Alternative | 0.0 s | +0.5 s | +1.5 s | Better odds on the face; less time to settle exposure |

Prototype both and choose on measured face visibility, not preference. If the camera supports it, bracket exposure across the burst so that one frame is usable regardless of how bright the opening scene is.

No continuous video and no audio recording.

## 5. Image handling

Each image carries:
- module ID and deployment ID;
- a globally unique `record_id` (module ID plus frame index collides across the ~6–12 deployments each module serves in a 30-day-cycle pilot);
- event ID and frame index (1–3);
- trigger timestamp and clock-synchronisation status;
- actual capture timestamp;
- integrity hash;
- transmission status.

Images are encrypted at rest with a key held by the study, and transmitted over the cellular link as part of the event record (D-33). Transmission is store-and-forward: if coverage is absent, the burst queues and is sent when the link returns.

**Metadata stripping before release.** Photographs taken by a phone carry GPS coordinates. These will not, but the location fix attached to the event identifies the volunteer's property. Images released publicly must have embedded metadata removed, and event location must be published at reduced precision. This is the one place where "publish everything" needs a carve-out, and the reason is the volunteer rather than the subject: the coordinate belongs to the person who lent you their porch.

## 6. Privacy position and release standard

Owner position (D-29, D-40, D-44): the package is addressed to someone who is not the opener, on private property, and the person opening it has chosen to open a package that is not theirs. The project publishes its data as public-benefit research.

That position is defensible for a silent, event-gated camera inside a sealed package on private property. Two risks survive it, and neither is about privacy law:

1. **Presumption of guilt.** A photograph of a person opening a box is not evidence of theft, and publishing it as though it were is the fastest route to a defamation claim and to harming someone who was, for example, returning a misdelivered parcel. Publications should caption events as alleged, avoid names, and never invite the public to identify anyone.
2. **Misidentification.** Once an image is public, someone will recognise a face and someone else will name them. The project cannot control that, but it can decline to host it: no comment sections, no "do you know this person", no bounty framing attached to a face.

Both are cheap to honour and expensive to litigate.

Retention: data is published and retained (D-40). No deletion schedule for published material is proposed; the practical control is the release standard above, applied before publication rather than after.

## 7. Verification tests

**Trigger (test group A):**
- Opening detection rate across 30 scripted lid-openings in daylight.
- Detection in a dark room with no light source: expected to fail, recorded as the scope limit.
- Detection with a porch light on and off.
- False triggers over 24 h with the box closed, sealed, and sitting in direct sun and rain.
- Arming-delay behaviour: no event from the operator sealing or placing the box.

**Capture (group B):**
- Time from light step to first captured frame.
- Actual spacing between the three frames under both schedules.
- Face visibility at 0.5 m and 1 m, in daylight and porch light, scored by a recorded rubric.
- Exposure behaviour when the lid opens onto a bright scene; check for blown first frame.
- Confirmation of exactly three stills per event and no video.
- Negative test: no command path can initiate imaging.

**Storage, power, environment (groups C, D, F):**
- Integrity across power loss during capture.
- Standby current with the comparator and accelerometer active.
- Energy per location fix and per upload; 30-day cycle projection.
- Thermal soak at 60 °C ambient.
- Torrential rain and condensation check on the sealed module.
- Field of view confirmed to exclude the street when the lid is closed.

## 8. Open decisions

- Camera module, lens, and whether exposure bracketing is feasible.
- Whether the first frame is delayed deliberately to let exposure settle.
- Frame timing: 0 / 1.0 / 2.5 s versus 0 / 0.5 / 1.5 s.
- Light sensor part and whether a comparator or interrupt pin is used.
- Storage capacity (expected small, offloaded every cycle).
- Resolution and compression target, balancing face detail against upload volume.
- Whether images upload immediately or on a nightly schedule.
- Location precision used in published records.
- Publication caption and identification policy.
