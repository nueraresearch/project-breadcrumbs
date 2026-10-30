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
- **No adjudication.** `validation_status` defaults to `unreviewed`; there is no interface for marking a trigger as a false trigger.
- **No recovery records.** The recovery entity in the data model has no ingest path yet.
- **No TLS.** Put it behind a reverse proxy that terminates TLS; the firmware's `QHTTPPOST` assumes HTTPS.
- **No rate limiting.** A misbehaving device can fill the disk.
