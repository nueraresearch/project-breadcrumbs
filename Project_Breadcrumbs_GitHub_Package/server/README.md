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

`data/records.db` holds `modules`, `deployments`, `events`, `images` and `ingest_log`. `data/images/` holds the frames encrypted as `{record_id}_{frame}.jpg.enc`, written to a temp file and renamed, so a crash cannot leave a truncated file that looks valid.

`data/` is gitignored. It must never be committed: this repository is public.

## 6. What this does not do

- **No precision of its own.** The service stores what the device reports, at full precision. Coarsening happens only in `publish.py`, which will not run without a stated grid resolution and a delay (D-41, D-76). The stored data must not be published as-is.
- **No adjudication in the service.** `validation_status` defaults to `unreviewed` and only `adjudicate.py` writes it, by design: review is a separate act from receipt.
- **No recovery records.** The recovery entity in the data model has no ingest path yet.
- **No TLS.** Put it behind a reverse proxy that terminates TLS; the firmware's `QHTTPPOST` assumes HTTPS.
- **No rate limiting.** A misbehaving device can fill the disk.

## Publication

`publish.py` produces the publishable copy. It is a separate step rather than part of ingest, because release is a decision rather than a consequence of receipt.

```
PUBLISH_SALT=$(python3 -c 'import os;print(os.urandom(16).hex())') \
  python3 publish.py --data-dir data --out published --grid-m 1000
```

**Nothing is published unless it is on the whitelist.** `OUTPUT_FIELDS` in `publish.py` is the complete set of fields that may leave the building. A column added to the database later cannot leak, because it is never copied.

- **Location is a grid cell, never a point.** A record with a valid fix carries `grid_cell` at the resolution given by `--grid-m`, plus `grid_size_m`. Displacement is still published as a bucket (`under 250 m` through `over 5 km`) and a distance rounded to 100 m (D-41).
- **The resolution has no default.** `--grid-m` is required and the run refuses anything below 1 km (D-76). A precision nobody chose is how a coarsening rule quietly turns back into a precise trace, and the manifest records the figure so a bundle states the precision that produced it.
- **What a cell still gives away.** At 1 km a cell covers a large share of a town of about 4,000 people, so the deployment cell places a volunteer's neighbourhood. That is the accepted trade rather than an oversight: without a position, the headline secondary outcome cannot be mapped at all.
- **Counts are reported by episode as well as by record.** One opening produces a light trigger, a capture record and several movement events, so `records_published` overstates removals. The manifest also reports `episodes_total`, `episodes_published` (every record of the episode is in this bundle), `episodes_partial` (the episode straddles the delay cutoff), `episodes_withheld_delay`, `episodes_by_outcome`, and `removals_published`. That last figure is the one the analysis plan's primary outcome needs; counting records instead would inflate it by however many movement events each opening generated.
- **Episodes are named in the output.** A record belonging to an opening carries `episode_key`, so the counts can be reproduced from the bundle rather than taken on trust. Device records carry none.
- **Delay.** Records newer than `--delay-days` are held and publish on a later run (D-41). The figure is a placeholder: D-41 requires a delay but does not set one, so the manifest records whichever value produced a bundle.
- **Deployment keys.** `deployment_id` is replaced by a keyed hash, so events can be grouped by deployment without naming a household. The salt is never written to the output. Losing it means published keys can no longer be linked back, so keep it with the project records and not with the data.
- **Captions** come from a fixed table keyed by event type, and each is checked against `BANNED_TERMS` before writing (D-42). An event type with no approved caption fails the run rather than receiving an invented one.
- **Images are released only when adjudicated** (D-52). A record that has not been reviewed publishes its metadata but not its frames, and the count is reported. Withheld images are counted by category and never described.

Every released frame has its metadata stripped by walking the JPEG markers and dropping APP1 to APP15 and comments; the result is re-checked for the JFIF start and EOI end markers. A frame that does not parse is refused rather than published as-is.

The run writes `records.jsonl`, `images/` and a `manifest.json` recording the policy version, delay, grid resolution and counts, so a published bundle always states the rules that produced it.

`validation_status` is not the image signal. Publication asks the `adjudications` table directly, so a record reviewed as an event without anyone having looked at its frames still publishes no frames. That is the fail-closed behaviour rather than a bug.

## Adjudication

`adjudicate.py` is the review step. It is separate from ingest because review is an act rather than a side effect of receipt, and separate from publication because publishing decides *how* something is released while adjudication decides *whether*.

Two reviews, kept apart on purpose.

### Sequences first

§6 asks reviewers to classify a movement-event *sequence*, and §3 defines a removal in terms of movement events, but neither says where one episode ends. `sequences.py` supplies it: records from one module merge while consecutive movement-bearing records are within `GAP_S` (180 s) and the run stays inside `WINDOW_S` (900 s).

Both figures are **this implementation's assumption**, not plan values. `firmware/bench/analyze_sequences.py` derives them from scripted openings — twice the largest observed internal pause, one and a half times the longest span — and prints them for pasting here. It has not been run against a real opening, because none has been recorded, so the values above remain reasoning rather than measurement. Every sequence row records the `rule_version` that produced it, so a published bundle states which rule it used. Membership freezes as soon as a reviewer votes: a verdict must not end up attached to records that reviewer never saw.

Device records — battery, sync, reset — never join an episode, because an administrative alert must not reach a reviewer as evidence of a removal. A record whose clock has never synced is adjudicated alone: ±18 minutes cannot separate a thirty-minute handling window from a removal, and grouping on that clock would invent an ordering.

**Event classification** ([PRE_REGISTRATION_ANALYSIS_PLAN §6](../docs/pilot/PRE_REGISTRATION_ANALYSIS_PLAN.md)) — two reviewers independently call each movement-event sequence removal, handling or indeterminate, **from telemetry alone**. A disagreement goes to a third reviewer, whose verdict is applied; a disagreement without a third is retained as `indeterminate` rather than forced into a class. A reviewer who has already viewed that record's images is **refused**, which is the enforceable half of "reviewers do not see images while adjudicating". The reason is not tidiness: the classification has to remain available for modules whose images were never recovered, and that is the case the analysis actually turns on.

**Image adjudication** (D-52) — a named reviewer looks at the frames and records `publish`, or `withhold` with a fixed category (`minor` or `unconnected`). Withheld frames are deleted as soon as the adjudication record is written; what survives is the SHA-256 of each frame, the category, the reviewer and the date. Image rows stay as tombstones with an empty `secure_object_ref`, so the audit trail still records that a frame existed. A legal hold suspends deletion for that record only and must carry an expiry date, because an open-ended hold is how deletion quietly stops happening.

A `publish` decision covers the frames that existed when it was written. Their hashes are stored with the decision, and publication releases only a frame whose hash is in that set: a frame that arrived afterwards, or one re-uploaded under the same index with different bytes, has not been looked at and is counted as unreviewed instead. Without that, a late upload would be published on the strength of a review that never saw it.

```bash
INGEST_DATA=data python3 sequences.py          # group, then show episodes
ADJUDICATORS=alice,bob INGEST_DATA=data python3 adjudicate.py pending
```

| Command | Purpose |
|---|---|
| `pending` | Episodes with no verdict, then records with frames and no image decision |
| `show ID` | Telemetry for one record, or a whole episode by `seq_…` id; never touches a frame |
| `view-images ID --reviewer N` | Copies frames out for review and logs the access |
| `decide-event ID --reviewer N --outcome ...` | Classification from telemetry, on the sequence `ID` belongs to |
| `decide-image ID --reviewer N --decision ...` | Publish or withhold the frames |
| `status` | Counts by status, episodes open and decided, withheld by category |

**Image access is restricted to a named list.** `ADJUDICATORS` must be set; without it, image viewing and image decisions are refused rather than allowed. Every view writes an `image_access` entry to the ingest log, which is what makes the blindness rule checkable rather than aspirational.

`validation_status` is written only here, and only with the documented vocabulary: `unreviewed`, `reviewed`, `false_trigger`, `indeterminate`.

One consequence worth stating: a record adjudicated as a false trigger does not publish under the normal caption. `publish.py` gives it "A sensor trigger was recorded that review did not classify as an opening", because carrying the ordinary wording would publish a claim that the review directly contradicts.

## Image encryption at rest

Captured frames are the most sensitive thing the pilot holds, and they used to sit on the ingest machine as ordinary JPEGs. They are now encrypted before they reach the disk, under a key supplied by `IMAGE_KEY` in the environment.

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"   # make a key
export IMAGE_KEY=<64 hex characters>
```

The cipher is built from the standard library, because the server is dependency-free on purpose and `cryptography` is not available on a borrowed machine: SHA-256 in counter mode for the keystream, HMAC-SHA256 over header and ciphertext, encrypt-then-MAC, a fresh 16-byte nonce per frame. It is a well-understood construction, but it is not AES and nobody has reviewed it. If a dependency becomes acceptable, replace `imagecrypt.py` rather than extend it.

**What this protects.** A copy of the data directory: a backup, a synced folder, a disk sent for repair, an old disk that was not wiped.

**What it does not protect.** A stolen machine with the key on it. If `IMAGE_KEY` lives in the same checkout, on the same disk, or in a note beside the laptop, the thief has both halves and this achieves nothing. Whole-disk encryption covers theft; this covers the copies nobody remembers exist. The key belongs in the project's password manager.

**Losing the key destroys the frames.** There is no recovery path, and that includes frames under legal hold. Keep a second copy wherever the deployment credentials live.

**Fail closed.** With no `IMAGE_KEY`, image uploads return 503 and nothing is written. A frame that did get stored cannot be read without it either: `view-images`, `decide-image`, and `publish.py` all refuse rather than skip. A malformed key stops the server at startup instead of quietly disabling encryption. Stored files are named `.jpg.enc`, so an unencrypted frame cannot be mistaken for a stored one.

Records and hashes are unaffected. `integrity_hash` is the SHA-256 of the *plaintext*, so every stored frame stays verifiable after decryption, and a file that decrypts to something else is refused rather than released.

**Review copies are plaintext.** `view-images` writes decrypted JPEGs into the output folder, because a reviewer has to look at them. That folder is as sensitive as the originals: delete it when the review is written up, and do not leave it in a synced directory.

### Migrating a directory written before encryption

An older data directory holds ordinary `.jpg` files and `images` rows that point at them, so every read now fails with a message naming `migrate_images.py`. That tool converts the directory in place: it reads each frame the row points at, checks its SHA-256 against the `integrity_hash` already recorded, encrypts it, writes and re-reads the result, repoints the row, commits, and only then removes the plaintext.

```bash
INGEST_DATA=data IMAGE_KEY=... python3 migrate_images.py --data-dir data --dry-run
INGEST_DATA=data IMAGE_KEY=... python3 migrate_images.py --data-dir data
```

**Stop the ingest server first.** The migration rewrites files and rows a running server would be reading, and a re-upload arriving mid-run could replace a `(record_id, frame_index)` between the read and the update.

**The hash check is the point.** `integrity_hash` is the only fact in the directory that predates the migration, so a frame whose bytes no longer match it is refused and left on disk rather than sealed with a verified-looking provenance. A plaintext file with no `images` row is reported and left alone for the same reason: there is no hash to check it against. Both make the run exit non-zero.

**Re-running is safe, and useful.** A frame that is already encrypted is decrypted and checked against its hash rather than skipped, so a second run doubles as proof that the key opens everything in the directory. `--keep-plaintext` leaves the originals in place for a cautious first pass; the tool says so at the end rather than letting the copies be forgotten.

### Rotating the image key

Changing `IMAGE_KEY` on its own makes every stored frame unreadable. Rotation is a re-encryption job: each frame is decrypted with whatever key currently opens it, checked against the `integrity_hash` already recorded, sealed under the new key, and renamed over the old file. Nothing else changes — the same file name, the same hash, the same `images` row — because the plaintext is the same.

```bash
export IMAGE_KEY=<new 64 hex>            # what the server will run with
export IMAGE_KEY_PREVIOUS=<old 64 hex>   # only for the rotation run

python3 rotate_key.py --data-dir data --dry-run
python3 rotate_key.py --data-dir data

# prove the old key is no longer needed, then remove it
python3 rotate_key.py --data-dir data --verify-only
unset IMAGE_KEY_PREVIOUS
```

**Stop ingest first.** The rotation rewrites files the server would be reading, and a frame uploaded mid-run would be sealed under whichever key the server was started with.

**Why not let the server accept a previous key.** Teaching the read path to try a retired key would keep that key valid for as long as it stayed in the environment, with nothing forcing its removal. A rotation that has to finish, followed by a check that the new key alone opens every frame, makes retiring the old key an explicit step with evidence rather than a configuration edit someone may forget.

**Every frame is proven before it is replaced.** The new ciphertext is written to a temporary file beside the original, read back, decrypted and compared with the recorded hash, and only then renamed over it. An interrupted run leaves that frame under the old key — never half-written, never under a key nobody holds — and re-running finishes the job. A frame already on the new key is verified and left alone, so a partially rotated directory needs one command rather than a repair.

**Refusals.** A frame whose plaintext no longer matches its recorded hash is left under the key it already has, because re-sealing it would give a swapped frame a verified-looking provenance. A frame that opens with neither key is reported, never deleted. A plaintext frame points at `migrate_images.py`.

**Backups taken before the rotation still need the old key.** Once `--verify-only` passes, the live directory no longer uses it, but a backup made beforehand is still sealed under it. Keep the retired key wherever those backups are kept, or destroy the backups as well.
