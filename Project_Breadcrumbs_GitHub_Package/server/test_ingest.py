#!/usr/bin/env python3
"""Tests for the ingest endpoint. Standard library only: python3 -m unittest."""

import hashlib
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

import ingest

TOKEN = "test-token"
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200 + b"\xff\xd9"


def sample_record(**over):
    rec = {
        "record_id": "MOD000-1a2b3c4d-000001",
        "module_id": "MOD000",
        "deployment_id": "DEP0001",
        "event_type": "IMAGE_CAPTURE_COMPLETE",
        "sensor_ts": 1793500000,
        "clock_synced": True,
        "clock_uncertainty_s": 43,
        "battery_mv": 3350,
        "frame_count": 3,
        "flags": 0,
        "location": {"valid": False},
    }
    rec.update(over)
    return rec


class IngestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.httpd = ingest.create_server("127.0.0.1", 0, cls.tmp.name, TOKEN)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.tmp.cleanup()

    # -- helpers ----------------------------------------------------------

    def request(self, method, path, body=None, headers=None, token=True):
        url = f"http://127.0.0.1:{self.port}{path}"
        hdrs = dict(headers or {})
        if token:
            hdrs["Authorization"] = f"Bearer {TOKEN}"
        data = body
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode()
            hdrs.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                return exc.code, json.loads(raw or b"{}")
            except json.JSONDecodeError:
                return exc.code, {"raw": raw.decode(errors="replace")}

    # -- auth -------------------------------------------------------------

    def test_rejects_missing_token(self):
        status, _ = self.request("POST", "/v1/records",
                                 sample_record(), token=False)
        self.assertEqual(status, 401)

    def test_rejects_wrong_token(self):
        status, _ = self.request("POST", "/v1/records", sample_record(),
                                 headers={"Authorization": "Bearer nope"},
                                 token=False)
        self.assertEqual(status, 401)

    # -- records ----------------------------------------------------------

    def test_accepts_and_round_trips(self):
        rec = sample_record(record_id="MOD000-1a2b3c4d-000101")
        status, body = self.request("POST", "/v1/records", rec)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["accepted"], 1)

        status, stored = self.request("GET", f"/v1/records/{rec['record_id']}")
        self.assertEqual(status, 200)
        self.assertEqual(stored["event_type"], "IMAGE_CAPTURE_COMPLETE")
        self.assertEqual(stored["clock_uncertainty_s"], 43)
        self.assertEqual(stored["flags"], 0)

    def test_duplicate_is_idempotent(self):
        rec = sample_record(record_id="MOD000-1a2b3c4d-000102")
        self.request("POST", "/v1/records", rec)
        status, body = self.request("POST", "/v1/records", rec)
        self.assertEqual(status, 200)
        self.assertEqual(body["accepted"], 0)
        self.assertEqual(body["duplicates"], 1)

    def test_conflicting_duplicate_is_reported(self):
        rec = sample_record(record_id="MOD000-1a2b3c4d-000103")
        self.request("POST", "/v1/records", rec)
        changed = dict(rec, event_type="MOVEMENT_EVENT")
        status, body = self.request("POST", "/v1/records", changed)
        self.assertEqual(body["conflicts"], 1)
        self.assertEqual(body["accepted"], 0)

    def test_batch_accepts_array(self):
        recs = [sample_record(record_id=f"MOD000-1a2b3c4d-00020{i}")
                for i in range(3)]
        status, body = self.request("POST", "/v1/records", recs)
        self.assertEqual(status, 200)
        self.assertEqual(body["accepted"], 3)

    # -- validation -------------------------------------------------------

    def test_rejects_unknown_event_type(self):
        status, body = self.request(
            "POST", "/v1/records",
            sample_record(record_id="MOD000-1a2b3c4d-000301",
                          event_type="PACKAGE_STOLEN"))
        self.assertEqual(status, 400)
        self.assertIn("taxonomy", json.dumps(body))

    def test_rejects_frozen_clock_contradiction(self):
        status, _ = self.request(
            "POST", "/v1/records",
            sample_record(record_id="MOD000-1a2b3c4d-000302",
                          sensor_ts=0, clock_synced=True))
        self.assertEqual(status, 400)

    def test_accepts_unsynced_record(self):
        status, body = self.request(
            "POST", "/v1/records",
            sample_record(record_id="MOD000-1a2b3c4d-000303",
                          sensor_ts=0, clock_synced=False,
                          clock_uncertainty_s=0))
        self.assertEqual(status, 200, body)

    def test_rejects_bad_coordinates(self):
        status, _ = self.request(
            "POST", "/v1/records",
            sample_record(record_id="MOD000-1a2b3c4d-000304",
                          location={"valid": True, "lat": 91.0, "lon": 0.0,
                                    "method": 1, "accuracy_m": 10}))
        self.assertEqual(status, 400)

    def test_rejects_path_traversal_in_record_id(self):
        status, _ = self.request(
            "POST", "/v1/records",
            sample_record(record_id="../../etc/passwd"))
        self.assertEqual(status, 400)

    def test_rejects_oversized_body(self):
        blob = b"x" * (ingest.MAX_RECORD_BYTES + 10)
        status, _ = self.request("POST", "/v1/records", blob,
                                 headers={"Content-Type": "application/json"})
        self.assertEqual(status, 413)

    # -- images -----------------------------------------------------------

    def test_image_upload_and_hash(self):
        rid = "MOD000-1a2b3c4d-000401"
        self.request("POST", "/v1/records", sample_record(record_id=rid))
        status, body = self.request(
            "POST", f"/v1/records/{rid}/images/2", JPEG,
            headers={"Content-Type": "image/jpeg"})
        self.assertEqual(status, 201, body)
        self.assertEqual(body["sha256"], hashlib.sha256(JPEG).hexdigest())

        status, stored = self.request("GET", f"/v1/records/{rid}")
        self.assertEqual(len(stored["images"]), 1)
        self.assertEqual(stored["images"][0]["frame_index"], 2)

    def test_image_before_record_is_allowed(self):
        rid = "MOD000-1a2b3c4d-000402"
        status, _ = self.request(
            "POST", f"/v1/records/{rid}/images/1", JPEG,
            headers={"Content-Type": "image/jpeg"})
        self.assertEqual(status, 201)

    def test_image_rejects_non_jpeg(self):
        rid = "MOD000-1a2b3c4d-000403"
        status, _ = self.request(
            "POST", f"/v1/records/{rid}/images/1", b"not an image",
            headers={"Content-Type": "image/jpeg"})
        self.assertEqual(status, 415)

    def test_image_rejects_truncated_jpeg(self):
        rid = "MOD000-1a2b3c4d-000404"
        status, _ = self.request(
            "POST", f"/v1/records/{rid}/images/1", JPEG[:-2],
            headers={"Content-Type": "image/jpeg"})
        self.assertEqual(status, 400)

    def test_image_rejects_bad_frame_index(self):
        rid = "MOD000-1a2b3c4d-000405"
        status, _ = self.request(
            "POST", f"/v1/records/{rid}/images/4", JPEG,
            headers={"Content-Type": "image/jpeg"})
        self.assertEqual(status, 400)

    # -- misc -------------------------------------------------------------

    def test_health(self):
        status, body = self.request("GET", "/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertIn("records", body)

    def test_unknown_route(self):
        status, _ = self.request("GET", "/v1/capture")
        self.assertEqual(status, 404)

    def test_no_capture_endpoint(self):
        """HW-30: the server must have no path that starts imaging."""
        for method in ("POST", "GET"):
            status, _ = self.request(method, "/v1/records/x/commands/capture",
                                     {} if method == "POST" else None)
            self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
