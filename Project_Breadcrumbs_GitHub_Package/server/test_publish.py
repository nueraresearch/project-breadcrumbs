#!/usr/bin/env python3
"""Tests for the release step. Standard library only."""

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

import ingest
import publish

SALT = bytes.fromhex("00112233445566778899aabbccddeeff")
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" \
       b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00" + b"\x11" * 40 + b"\xff\xd9"
# The same frame with an EXIF (APP1) segment carrying a GPS-ish payload.
JPEG_WITH_EXIF = (b"\xff\xd8"
                  b"\xff\xe1\x00\x19Exif\x00\x00MM\x00*GPSLatitude\x00\x00"
                  b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00" + b"\x22" * 40 +
                  b"\xff\xd9")


def make_db(tmp):
    data = os.path.join(tmp, "data")
    os.makedirs(os.path.join(data, "images"), exist_ok=True)
    store = ingest.Store(data)
    return data, store


def insert(store, record_id, deployment_id="DEP0001",
           event_type="IMAGE_CAPTURE_COMPLETE", status=None,
           received=None, lat=None, lon=None, ts=1793500000):
    now = received or datetime.now(timezone.utc)
    rec = {
        "record_id": record_id,
        "module_id": "MOD000",
        "deployment_id": deployment_id,
        "event_type": event_type,
        "sensor_ts": ts,
        "clock_synced": True,
        "clock_uncertainty_s": 43,
        "battery_mv": 3350,
        "frame_count": 3,
        "flags": 0,
        "location": ({"valid": True, "lat": lat, "lon": lon,
                      "method": 1, "accuracy_m": 10}
                     if lat is not None else {"valid": False}),
    }
    store.insert_record(rec)

    conn = sqlite3.connect(os.path.join(store.data_dir, "records.db"))
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("UPDATE events SET received_timestamp=? WHERE record_id=?",
                 (stamp, record_id))
    if status is not None:
        conn.execute("UPDATE events SET validation_status=? WHERE record_id=?",
                     (status, record_id))
    conn.commit()
    conn.close()


def add_image(store, record_id, frame=1, blob=JPEG):
    store.store_image(record_id, frame, blob)


class CaptionTests(unittest.TestCase):
    def test_every_event_type_has_a_caption(self):
        for et in ingest.EVENT_TYPES:
            self.assertTrue(publish.caption_for(et))

    def test_no_caption_asserts_theft(self):
        for et in ingest.EVENT_TYPES:
            text = publish.caption_for(et).lower()
            for term in publish.BANNED_TERMS:
                self.assertNotIn(term, text,
                                 f"{et} caption contains {term!r}")

    def test_opening_caption_says_opened(self):
        self.assertIn("opened", publish.caption_for("LIGHT_TRIGGER").lower())

    def test_unknown_type_fails_closed(self):
        with self.assertRaises(publish.PublishError):
            publish.caption_for("PACKAGE_STOLEN")

    def test_check_rejects_accusatory_language(self):
        with self.assertRaises(publish.PublishError):
            publish.check_caption("A package was stolen.")
        with self.assertRaises(publish.PublishError):
            publish.check_caption("Do you know this person?")


class StripTests(unittest.TestCase):
    def test_removes_exif(self):
        out = publish.strip_jpeg_metadata(JPEG_WITH_EXIF)
        self.assertNotIn(b"Exif", out)
        self.assertNotIn(b"GPSLatitude", out)

    def test_result_is_still_a_jpeg(self):
        out = publish.strip_jpeg_metadata(JPEG_WITH_EXIF)
        self.assertTrue(out.startswith(b"\xff\xd8"))
        self.assertTrue(out.endswith(b"\xff\xd9"))

    def test_keeps_image_data(self):
        out = publish.strip_jpeg_metadata(JPEG_WITH_EXIF)
        self.assertIn(b"\x22" * 40, out)

    def test_rejects_non_jpeg(self):
        with self.assertRaises(publish.PublishError):
            publish.strip_jpeg_metadata(b"not an image")


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data, self.store = make_db(self.tmp.name)
        self.out = os.path.join(self.tmp.name, "published")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, **kw):
        kw.setdefault("release_images", False)
        return publish.publish(self.data, self.out, SALT, **kw)

    def _output(self):
        path = os.path.join(self.out, "records.jsonl")
        with open(path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def test_delay_withholds_recent_records(self):
        insert(self.store, "MOD000-aa-000001")           # now
        manifest = self._run(delay_days=30)
        self.assertEqual(manifest["counts"]["records_published"], 0)
        self.assertEqual(manifest["counts"]["records_withheld_delay"], 1)

    def test_old_records_publish(self):
        insert(self.store, "MOD000-aa-000002",
               received=datetime.now(timezone.utc) - timedelta(days=60))
        manifest = self._run(delay_days=30)
        self.assertEqual(manifest["counts"]["records_published"], 1)

    def test_no_coordinates_in_output(self):
        insert(self.store, "MOD000-aa-000003",
               received=datetime.now(timezone.utc) - timedelta(days=60),
               lat=37.5792, lon=-106.1453)
        self._run(delay_days=30)
        raw = open(os.path.join(self.out, "records.jsonl"),
                   encoding="utf-8").read()
        self.assertNotIn('"lat"', raw)
        self.assertNotIn('"lon"', raw)
        self.assertNotIn("37.5792", raw)
        self.assertNotIn("-106.1453", raw)

    def test_deployment_id_is_replaced_by_key(self):
        insert(self.store, "MOD000-aa-000004",
               received=datetime.now(timezone.utc) - timedelta(days=60))
        self._run(delay_days=30)
        rec = self._output()[0]
        self.assertNotIn("deployment_id", rec)
        self.assertIn("deployment_key", rec)
        self.assertEqual(len(rec["deployment_key"]), 16)
        self.assertNotEqual(rec["deployment_key"], "DEP0001")

    def test_same_deployment_same_key(self):
        old = datetime.now(timezone.utc) - timedelta(days=60)
        insert(self.store, "MOD000-aa-000005", received=old)
        insert(self.store, "MOD000-aa-000006", received=old)
        self._run(delay_days=30)
        keys = {r["deployment_key"] for r in self._output()}
        self.assertEqual(len(keys), 1)

    def test_displacement_is_bucketed(self):
        old = datetime.now(timezone.utc) - timedelta(days=60)
        insert(self.store, "MOD000-aa-000007", received=old,
               event_type="LOCATION_FIX", lat=37.5792, lon=-106.1453, ts=1)
        insert(self.store, "MOD000-aa-000008", received=old,
               event_type="LOCATION_FIX", lat=37.5900, lon=-106.1453, ts=2)
        self._run(delay_days=30)
        recs = self._output()
        buckets = {r["displacement_bucket"] for r in recs}
        self.assertEqual(len(buckets), 1)
        self.assertIn(list(buckets)[0],
                      [b[1] for b in publish.DISPLACEMENT_BUCKETS])

    def test_single_fix_has_no_displacement(self):
        insert(self.store, "MOD000-aa-000009",
               received=datetime.now(timezone.utc) - timedelta(days=60),
               event_type="LOCATION_FIX", lat=37.5, lon=-106.1)
        self._run(delay_days=30)
        self.assertIsNone(self._output()[0]["displacement_km"])

    def test_output_fields_are_whitelisted(self):
        insert(self.store, "MOD000-aa-000010",
               received=datetime.now(timezone.utc) - timedelta(days=60))
        self._run(delay_days=30)
        for key in self._output()[0]:
            self.assertIn(key, publish.OUTPUT_FIELDS)


class ImageReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data, self.store = make_db(self.tmp.name)
        self.out = os.path.join(self.tmp.name, "published")
        self.old = datetime.now(timezone.utc) - timedelta(days=60)

    def tearDown(self):
        self.tmp.cleanup()

    def test_unadjudicated_image_is_not_released(self):
        insert(self.store, "MOD000-bb-000001", received=self.old)
        add_image(self.store, "MOD000-bb-000001")
        m = publish.publish(self.data, self.out, SALT, release_images=True)
        self.assertEqual(m["counts"]["images_published"], 0)
        self.assertEqual(m["counts"]["images_withheld_unadjudicated"], 1)

    def test_reviewed_image_is_released_and_stripped(self):
        insert(self.store, "MOD000-bb-000002", received=self.old,
               status="reviewed")
        add_image(self.store, "MOD000-bb-000002", blob=JPEG_WITH_EXIF)
        m = publish.publish(self.data, self.out, SALT, release_images=True)
        self.assertEqual(m["counts"]["images_published"], 1)

        path = os.path.join(self.out, "images", "MOD000-bb-000002_01.jpg")
        blob = open(path, "rb").read()
        self.assertNotIn(b"Exif", blob)
        self.assertTrue(blob.startswith(b"\xff\xd8"))

    def test_withheld_category_is_counted(self):
        insert(self.store, "MOD000-bb-000003", received=self.old,
               status="withheld_minor")
        add_image(self.store, "MOD000-bb-000003")
        m = publish.publish(self.data, self.out, SALT, release_images=True)
        self.assertEqual(m["counts"]["images_published"], 0)
        self.assertEqual(m["counts"]["images_withheld_by_category"]["minor"], 1)

    def test_record_still_publishes_without_its_image(self):
        insert(self.store, "MOD000-bb-000004", received=self.old)
        add_image(self.store, "MOD000-bb-000004")
        m = publish.publish(self.data, self.out, SALT, release_images=True)
        self.assertEqual(m["counts"]["records_published"], 1)
        self.assertEqual(m["counts"]["images_published"], 0)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data, self.store = make_db(self.tmp.name)
        self.out = os.path.join(self.tmp.name, "published")

    def tearDown(self):
        self.tmp.cleanup()

    def test_manifest_records_policy(self):
        insert(self.store, "MOD000-cc-000001",
               received=datetime.now(timezone.utc) - timedelta(days=60))
        publish.publish(self.data, self.out, SALT, delay_days=45)
        with open(os.path.join(self.out, "manifest.json"), encoding="utf-8") as fh:
            m = json.load(fh)
        self.assertEqual(m["delay_days"], 45)
        self.assertEqual(m["policy_version"], publish.POLICY_VERSION)
        self.assertFalse(m["images_released"])

    def test_missing_database_is_an_error(self):
        with self.assertRaises(publish.PublishError):
            publish.publish(os.path.join(self.tmp.name, "nope"),
                            self.out, SALT)


class CliTests(unittest.TestCase):
    def test_refuses_without_salt(self):
        import subprocess
        here = os.path.dirname(os.path.abspath(__file__))
        env = {k: v for k, v in os.environ.items() if k != "PUBLISH_SALT"}
        out = subprocess.run(
            ["python3", os.path.join(here, "publish.py")],
            capture_output=True, text=True, env=env)
        self.assertEqual(out.returncode, 2)
        self.assertIn("PUBLISH_SALT", out.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
