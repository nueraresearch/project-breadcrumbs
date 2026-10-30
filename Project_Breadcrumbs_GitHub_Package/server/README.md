# Ingest — receiving records and images

**Status:** Working and tested. Unlike the firmware, this runs here: `python3 -m unittest test_ingest.py` passes 20 tests.

**Related:** [`../docs/data/DATA_MODEL.md`](../docs/data/DATA_MODEL.md), [`../firmware/`](../firmware/)

## 1. What it does

Accepts the JSON records and JPEG frames the module produces, validates them against the documented data model, and stores them in SQLite plus a flat image directory.

Standard library only — no requirements file, no lockfile, nothing to audit but the one module. The pilot produces a few hundred records over 90 days; a framework would be more code to trust, not less.

## 2. Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/records` | One record object, or an array of them |
| `POST` | `/v1/records/{record_id}/images/{frame}` | One JPEG frame, `frame` in 1–3 |
| `GET` | `/v1/records/{record_id}` | The stored record plus its image metadata |
| `GET` | `/healthz` | Liveness and row counts |

**There is no endpoint that causes a device to do anything.** HW-30 requires that no command path can initiate imaging; the simplest way to honour that server-side is to have no such path. A test asserts that `/v1/records/x/commands/capture` returns 404. The absence is the feature.

## 3. Running it

```bash
cd server
INGEST_TOKEN=$(openssl rand -hex 16) python3 ingest.py --port 8787 --data-dir data
```

Binds `127.0.0.1` by default. Pass `--host 0.0.0.0` only when the device has to reach it from outside, and set `INGEST_TOKEN` when you do — without it the endpoint accepts unauthenticated writes, and it says so on startup rather than failing quietly.

```bash
python3 -m unittest test_ingest.py -v
```

## 4. Behaviour worth knowing

**Duplicates are expected, not errors.** The device retries until it sees a 2xx (HW-08), so the same `record_id` arriving twice returns 200 with `duplicates: 1` and stores nothing new. A *different* body under an existing `record_id` is reported separately as a `conflict`, because that means two devices agree on an ID they should not.

**Images may arrive before their record.** Frames are keyed by `(record_id, frame_index)` rather than by an event row, so upload ordering never loses a frame.

**`sensor_ts: 0` means never synced, not 1970.** The firmware sends 0 until the modem has set the clock. The validator rejects `sensor_ts: 0` with `clock_synced: true` as self-contradictory, and accepts unsynced records with a zero timestamp — which is what a record captured before the first uplink actually is.

**Truncated JPEGs are refused.** A partial upload on a marginal link is rejected with 400 rather than stored, because a file that will not open is worse than a retry.

**IDs are checked before they become filenames.** `record_id` must match `[A-Za-z0-9_-]{1,64}`; anything else is a 400, which is the path-traversal guard.

**Nothing about a request body is logged.** Records carry volunteer location, so the handler suppresses its own access log unless `INGEST_VERBOSE` is set.

## 5. What is stored

`data/records.db` holds `modules`, `deployments`, `events`, `images` and `ingest_log`. `data/images/` holds the frames as `{record_id}_{frame}.jpg`, written to a temp file and renamed, so a crash cannot leave a truncated JPEG that looks valid.

`data/` is gitignored. It must never be committed: this repository is public.

## 6. What this does not do

- **No publication pipeline.** Records are stored raw with full location precision. Reducing precision and delaying release (D-41) is a separate step that has not been written, and the stored data must not be published as-is.
- **No adjudication in the service.** `validation_status` defaults to `unreviewed` and only `adjudicate.py` writes it, by design: review is a separate act from receipt.
- **No recovery records.** The recovery entity in the data model has no ingest path yet.
- **No TLS.** Put it behind a reverse proxy that terminates TLS; the firmware's `QHTTPPOST` assumes HTTPS.
- **No rate limiting.** A misbehaving device can fill the disk.

## Publication

`publish.py` produces the publishable copy. It is a separate step rather than part of ingest, because release is a decision rather than a consequence of receipt.

```
PUBLISH_SALT=$(python3 -c 'import os;print(os.urandom(16).hex())') \
  python3 publish.py --data-dir data --out published
```

**Nothing is published unless it is on the whitelist.** `OUTPUT_FIELDS` in `publish.py` is the complete set of fields that may leave the building. A column added to the database later cannot leak, because it is never copied.

- **No coordinates, at any setting.** Displacement is published as a coarse bucket (`under 250 m` through `over 5 km`) plus a distance rounded to 100 m. That answers the displacement question without saying where a volunteer lives (D-41).
- **Delay.** Records newer than `--delay-days` are held and publish on a later run (D-41). The figure is a placeholder: D-41 requires a delay but does not set one, so the manifest records whichever value produced a bundle.
- **Deployment keys.** `deployment_id` is replaced by a keyed hash, so events can be grouped by deployment without naming a household. The salt is never written to the output. Losing it means published keys can no longer be linked back, so keep it with the project records and not with the data.
- **Captions** come from a fixed table keyed by event type, and each is checked against `BANNED_TERMS` before writing (D-42). An event type with no approved caption fails the run rather than receiving an invented one.
- **Images are released only when adjudicated** (D-52). A record that has not been reviewed publishes its metadata but not its frames, and the count is reported. Withheld images are counted by category and never described.

Every released frame has its metadata stripped by walking the JPEG markers and dropping APP1 to APP15 and comments; the result is re-checked for the JFIF start and EOI end markers. A frame that does not parse is refused rather than published as-is.

The run writes `records.jsonl`, `images/` and a `manifest.json` recording the policy version, delay and counts, so a published bundle always states the rules that produced it.

`validation_status` is not the image signal. Publication asks the `adjudications` table directly, so a record reviewed as an event without anyone having looked at its frames still publishes no frames. That is the fail-closed behaviour rather than a bug.

## Adjudication

`adjudicate.py` is the review step. It is separate from ingest because review is an act rather than a side effect of receipt, and separate from publication because publishing decides *how* something is released while adjudication decides *whether*.

Two reviews, kept apart on purpose.

**Event classification** ([PRE_REGISTRATION_ANALYSIS_PLAN §6](../docs/pilot/PRE_REGISTRATION_ANALYSIS_PLAN.md)) — two reviewers independently call each movement event removal, handling or indeterminate, **from telemetry alone**. A disagreement goes to a third reviewer, whose verdict is applied; a disagreement without a third is retained as `indeterminate` rather than forced into a class. A reviewer who has already viewed that record's images is **refused**, which is the enforceable half of "reviewers do not see images while adjudicating". The reason is not tidiness: the classification has to remain available for modules whose images were never recovered, and that is the case the analysis actually turns on.

**Image adjudication** (D-52) — a named reviewer looks at the frames and records `publish`, or `withhold` with a fixed category (`minor` or `unconnected`). Withheld frames are deleted as soon as the adjudication record is written; what survives is the SHA-256 of each frame, the category, the reviewer and the date. Image rows stay as tombstones with an empty `secure_object_ref`, so the audit trail still records that a frame existed. A legal hold suspends deletion for that record only and must carry an expiry date, because an open-ended hold is how deletion quietly stops happening.

```bash
ADJUDICATORS=alice,bob INGEST_DATA=data python3 adjudicate.py pending
```

| Command | Purpose |
|---|---|
| `pending` | Records with no event verdict, or with frames and no image decision |
| `show ID` | Telemetry only; never touches a frame |
| `view-images ID --reviewer N` | Copies frames out for review and logs the access |
| `decide-event ID --reviewer N --outcome ...` | Classification from telemetry |
| `decide-image ID --reviewer N --decision ...` | Publish or withhold the frames |
| `status` | Counts by status, and withheld counts by category |

**Image access is restricted to a named list.** `ADJUDICATORS` must be set; without it, image viewing and image decisions are refused rather than allowed. Every view writes an `image_access` entry to the ingest log, which is what makes the blindness rule checkable rather than aspirational.

`validation_status` is written only here, and only with the documented vocabulary: `unreviewed`, `reviewed`, `false_trigger`, `indeterminate`.

One consequence worth stating: a record adjudicated as a false trigger does not publish under the normal caption. `publish.py` gives it "A sensor trigger was recorded that review did not classify as an opening", because carrying the ordinary wording would publish a claim that the review directly contradicts.
