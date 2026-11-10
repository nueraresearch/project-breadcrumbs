# Re-identification Review — Published Bundle

**Status:** Review of the current `publish.py` output. Synthetic bundle only; no participant data. Not a legal opinion.
**Date:** 2026-11-10
**Related:** D-40, D-41, D-42, D-52, D-76; [`../governance/THREAT_MODEL.md`](../governance/THREAT_MODEL.md) T-13; [`../../server/README.md`](../../server/README.md) publication section.

## 1. Scope and method

The release step is a whitelist: `OUTPUT_FIELDS` in `publish.py` is the complete set of fields that may leave the building, location is a grid cell at a stated resolution, deployment identifiers are replaced by a keyed hash, and images are released only after an image decision. Those controls are real, and they remove the obvious identifiers.

This review asks a narrower question: **what does the bundle still let someone work out, if that someone lives in the same town?**

A bundle was generated from two synthetic deployments of one module, at a 1 km grid and a 30-day delay, with two adjudicated frames. Every field in `records.jsonl`, the manifest, and the image filenames was read. The perspective is a neighbour in a town of about 4,000 who knows who lives where, which porches had a box, when the carrier came, who was home, and what people look like. No participant data was used, and no real image was inspected; the test frame is a blank pattern.

## 2. What the bundle publishes

| Field | Example | Note |
|---|---|---|
| `record_id` | `MOD000-aa-000001` | copied verbatim from the device |
| `event_type` | `LIGHT_TRIGGER` | |
| `sensor_ts` | `1789090673` | second precision |
| `clock_synced`, `clock_uncertainty_s` | `true`, `43` | |
| `battery_mv` | `3350` | |
| `frame_count`, `flags` | `3`, `0` | |
| `caption` | "A package was opened." | fixed wording (D-42) |
| `deployment_key` | `bb57e3c2e7f8a841` | HMAC of the deployment id |
| `displacement_bucket`, `displacement_km` | `under 250 m`, `0.0` | |
| `grid_cell`, `grid_size_m` | `4183:-9365`, `1000` | absolute cell |
| `episode_key` | `seq_6d1037484a0b17f8` | hash of module and anchor record |
| manifest | counts | records, episodes, images, withheld categories |
| images | `MOD000-aa-000001_01.jpg` | EXIF stripped, adjudicated |

A sample line, synthetic:

```json
{"battery_mv": 3350, "caption": "A package was opened.", "clock_synced": true, "clock_uncertainty_s": 43, "deployment_key": "bb57e3c2e7f8a841", "displacement_bucket": "under 250 m", "displacement_km": 0.0, "episode_key": "seq_6d1037484a0b17f8", "event_type": "LIGHT_TRIGGER", "flags": 0, "frame_count": 3, "grid_cell": "4183:-9365", "grid_size_m": 1000, "record_id": "MOD000-aa-000001", "sensor_ts": 1789090673}
```

## 3. What the bundle withholds

No participant code, name, address, `deployment_id`, raw latitude or longitude, or EXIF. No image is released without a decision, and no frame that arrived after the decision. Images of a minor or a person with no connection to the opening are withheld and deleted, and the number withheld is published by category. Captions are fixed and checked against accusatory terms. These are the controls working as designed, and they are stated before the findings because the findings are about what remains.

## 4. Findings

| ID | Finding | Identifies | Severity | Depends on |
|---|---|---|---|---|
| R-01 | Released images show the opener's face | Person | Critical | D-40 publishes the opener |
| R-02 | Image backgrounds show a porch, house number, or interior | House, person | Critical | Camera geometry, no background redaction |
| R-03 | `record_id` carries the module identifier across deployments | Linkage | High | Device naming convention |
| R-04 | Exact timestamp plus stable key plus 1 km cell | House | High | Local knowledge |
| R-05 | Every movement fix publishes a cell, tracing a path | Neighbourhood, destination | Medium-high | D-76 publishes cells |
| R-06 | Battery voltage and clock uncertainty fingerprint the device | Linkage | Medium | Fields published at full precision |
| R-07 | Image filenames carry `record_id` | Linkage | Medium | Filename construction |
| R-08 | Record and episode ids survive a salt rotation | Longitudinal linkage | Medium | Unsalted ids |
| R-09 | The study name may appear in a frame | House | Low-medium | Label geometry |
| R-10 | Device appearance may appear in a frame | Device recognition | Low | Camera framing |
| R-11 | Small manifest counts confirm a known event | Confirmation | Low | Small n |
| R-12 | The delay has no floor and accepts zero | Control gap | Medium | CLI accepts any integer |
| R-13 | Salt leak plus structured deployment ids recovers keys | Control gap | Low-medium | 64-bit truncation, low-entropy input |
| R-14 | A withheld image does not withhold the event record | House, person | Medium-high | D-52 covers images only |
| R-15 | Sequence numbers reveal event counts and order | Pattern | Low | Raw record ids |

### R-01 Released faces (critical, person)

The opener is published by design: D-52 withholds minors and people with no connection to the opening, not the adult who opens the box. In a town of about 4,000, a face is effectively a name to anyone who knows the person. No name field is needed. Publication is permanent. This is the strongest person identifier in the bundle, and it is intentional rather than a defect; the review records it so the decision is not mistaken for anonymity.

### R-02 Image backgrounds (critical, house or person)

The camera is inside the box, aimed at the opening. When the lid opens, the frame contains the opener and whatever is behind them. Opened on the volunteer's porch, that background can include the volunteer's door, house number, distinctive wall, mailbox, street sign, or a car and plate. Carried away and opened indoors, it can include the opener's room: furniture, photographs, documents, a screen. The image decision is about who is depicted; the current categories do not include a background-identifier check, and `publish.py` strips metadata but does not crop or blur pixels. A single house number in a frame defeats D-41 at the image layer.

### R-03 Module identifier in `record_id` (high, linkage)

`record_id` is device-supplied and published verbatim. In the bundle, two different deployments — different hosts, different `deployment_key`, different cells — share the `MOD000` prefix (`MOD000-aa-000001`, `MOD000-aa-000003`). A reader can group the three deployments of one module, which is exactly the repeated-measures link D-53's one-deployment-per-host rule was meant to remove. If the module identifier is marked on or readable from the device, a finder can match the physical unit to its published history.

The middle token is not explained by `publish.py`. If the firmware encodes the deployment there as well, the HMAC on `deployment_key` is defeated more directly. `ingest.py` treats `record_id` as globally unique and device-supplied; it does not parse or rewrite it, and `publish.py` does not either.

`episode_key` is a deterministic hash of the module id and the anchor record id, so it does not break the link. It is stable across releases and across a salt rotation.

### R-04 Exact time, stable key, and cell (high with local knowledge, house)

`sensor_ts` is second-precision. `deployment_key` is stable while the salt is unchanged, and each release republishes older records. `grid_cell` is absolute. A neighbour who saw a box on a particular porch can match the timestamp of an opening to that porch. The cell is 1 km, but the number of participating houses in one cell is small. The bundle does not name the house; the neighbour does.

### R-05 Movement path (medium-high, neighbourhood or destination)

Every record with a valid fix publishes a cell, so a removal traces a sequence of 1 km cells over time. `displacement_km` is rounded to 100 m and bucketed, but the destination cell is still published. In a town this size, a 1 km cell is a neighbourhood; the path plus the time can narrow the destination to a few streets. This is the headline secondary outcome (D-47) and D-76 accepts the cell; the residual is stated, not removed.

### R-06 Device fingerprint (medium, linkage)

`battery_mv` (3350 in the sample) and `clock_uncertainty_s` (43) are constant across the module's deployments. Even if `record_id` were replaced, these fields can link deployments of the same unit. The analytic value of 1 mV precision is low; a 50 mV bucket would preserve device health without the fingerprint.

### R-07 Image filenames (medium, linkage)

The released files are named `<record_id>_<frame>.jpg`, so the JPEG itself carries the module link even if a viewer saves only the image and not the JSON. The metadata strip removes EXIF, not the filename.

### R-08 Stable record and episode ids across releases (medium, longitudinal)

`episode_key` is an unsalted hash of module id and anchor record id; `record_id` is the raw device id. Both survive a salt rotation, so rotating `PUBLISH_SALT` does not break episode-level or record-level linkage. The deployment key rotates; the rest does not. If longitudinal linkage is not wanted, the record id has to change too.

### R-09 Study name in pixels (low-medium, house, conditional)

The label carries the study name unique to the deployment. The camera is aimed at the opening; if the label or flap is in frame, the image contains the name a neighbour saw on the box. The name is not in the metadata, but pixels are not metadata. This is conditional on the geometry and should be checked in the bench images.

### R-10 Device appearance (low, device recognition)

If a frame shows the module, packaging, or mounting, the published image helps someone recognise future boxes (T-08). The camera is aimed at the opening rather than the interior, so this is likely small; it is listed because publication is permanent.

### R-11 Manifest small counts (low, confirmation)

`episodes_by_outcome` and `images_withheld_by_category` are aggregate, but with thirty deployments a count of one can confirm a locally known event. The counts are required by D-52's transparency rule; the residual is accepted.

### R-12 No minimum delay (medium, control gap)

`--delay-days` accepts any integer, including 0. D-41 requires a delay but does not set a figure, and the code's 30-day default is explicitly a placeholder. A run can publish immediately and record `delay_days: 0` in the manifest, which is honest but not a control. The grid has a floor; the delay does not.

### R-13 Salt and structured deployment ids (low-medium, control gap)

`deployment_key` is HMAC-SHA-256 of `deployment_id`, truncated to 16 hex characters. The deployment ids are structured (`DEP0001` and so on), so if `PUBLISH_SALT` leaks, all thirty keys can be computed and matched. The salt is the only barrier; the private annex is the link from deployment to address. Server compromise is already in the threat model; the specific consequence is that the HMAC is not a one-way guarantee against a low-entropy input.

### R-14 Withholding an image does not withhold the record (medium-high, house or person)

When an image is withheld for a minor or an unconnected person, the event record still publishes its timestamp, cell, and caption. The manifest reports the withheld count by category, but the event line remains. If the event is sensitive — the only opening in a cell was the withheld one — the metadata still places the opening. D-52 protects the image, not the event. This is a gap between what the rule promises and what the bundle shows.

### R-15 Sequence numbers and event counts (low, pattern)

The trailing number in `record_id` and the count of records per deployment reveal how many events a deployment produced and their order. Alone this identifies no one; with the module link it adds to the pattern.

### R-16 Permanence (property)

Publication is permanent and cannot be recalled (D-40). Every finding above is amplified by that: a face, a house number, or a destination cell cannot be un-published. The review treats this as a property of the system, not a field.

## 5. What a neighbour can conclude

A worked example using the synthetic bundle: cell `4183:-9365` covers roughly 37.576 to 37.585 N and 106.153 to 106.142 W at 1 km. The bundle shows a `LIGHT_TRIGGER` at `1789090673`, an `IMAGE_CAPTURE_COMPLETE` 15 seconds later, and 0 m displacement. If a neighbour in that cell saw a box on a porch and remembers it being opened that afternoon, the bundle confirms the porch. The cell did not name the house; the neighbour's knowledge did.

If the released frame shows a face, the neighbour can name the person. If it shows a hallway with a photograph on the wall, the neighbour may know the home. If it shows a house number, the volunteer's house is named. None of these required a coordinate.

## 6. What a remote reader cannot do

Without local knowledge, the bundle places an event in a 1 km cell at a time. That is a neighbourhood, not an address. `deployment_key` is a pseudonym; `record_id` is a device id, not a person; the manifest counts are aggregate. The risk this review describes is local re-identification, not a public doxxing from the JSON alone. The distinction matters for mitigation: coarsening further protects against the remote reader; image and background controls protect against the neighbour.

## 7. Recommendations

These are proposals, not approved changes. Some need an owner decision; none is implemented here.

- **P-01 Replace `record_id` in the bundle.** Publish a per-deployment pseudonym, for example an HMAC of the deployment id and record id, and keep the raw id in the private annex. Use the same pseudonym in image filenames. This breaks R-03, R-07, and the record half of R-08.
- **P-02 Bucket the device fields.** Publish `battery_mv` in 50 mV steps and `clock_uncertainty_s` in 5 s steps, or drop them. This reduces R-06.
- **P-03 Enforce a delay floor.** Refuse `--delay-days 0` and any figure below the one D-41 eventually sets. Until the owner sets a figure, the tool should refuse zero rather than accept it.
- **P-04 Add a background check to image adjudication.** The reviewer who must look before deciding (D-77) should also record whether the frame contains a house number, street sign, plate, named document, screen, or distinctive interior, and the frame should be cropped or withheld if it does. This addresses R-02 and R-09.
- **P-05 Decide whether interior backgrounds are publishable at all.** A person opening a package indoors is in their own home; a face crop or a background blur is a larger change than a checklist and needs an owner decision.
- **P-06 State the salt's lifetime.** If `PUBLISH_SALT` is stable across releases, say so in the manifest; if it rotates, note that record and episode ids still link across releases (R-08).
- **P-07 Add a bundle note.** A short statement that the bundle places a deployment in a 1 km cell and an event at a second, and that local knowledge can resolve that to a porch, is more honest than leaving the reader to infer it.
- **P-08 Check the label geometry.** If the study name can appear in a frame, either change the label position or treat the frame as identifying the deployment (R-09).
- **P-09 Decide the module-id question.** If the device is marked with its module identifier, the published record id is a physical link, not only a data link. The bench images and enclosure should be checked before the first deployment.

## 8. Limits

- The bundle is synthetic: one module, two deployments, two test frames. Thirty real deployments may produce different patterns.
- No real image was inspected. R-01, R-02, R-09, and R-10 are properties of the pipeline and geometry, not observations of a photograph.
- The review assumes a neighbour with local knowledge. A remote reader has less.
- The salt, the private annex, and the deployment ids are not in this repository, so the HMAC and annex linkage were reasoned about, not tested.
- Legal review of publication is separate (`PRIVACY_SAFETY_AND_REVIEW.md` §8).
