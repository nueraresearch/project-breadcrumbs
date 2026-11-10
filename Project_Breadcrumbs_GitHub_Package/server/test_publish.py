#!/usr/bin/env python3
"""Tests for the release step. Standard library only."""

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

import adjudicate
import ingest
import publish

REVIEWERS = {"alice", "bob"}

SALT = bytes.fromhex("00112233445566778899aabbccddeeff")
TEST_KEY = bytes.fromhex("ab" * 32)
OTHER_KEY = bytes.fromhex("cd" * 32)
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
    store = ingest.Store(data, image_key=TEST_KEY)
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


def adjudicate_image(data, record_id, decision, category=None):
    adj = adjudicate.Adjudicator(data, REVIEWERS, image_key=TEST_KEY)
    # D-52: the decision must follow a look at the frames it covers.
    adj.view_images(record_id, "alice",
                    os.path.join(os.path.dirname(data), "review"))
    adj.decide_image(record_id, "alice", decision, category=category)


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

    def test_false_trigger_caption_does_not_claim_an_opening(self):
        text = publish.caption_for("LIGHT_TRIGGER", "false_trigger").lower()
        self.assertNotIn("opened", text)
        publish.check_caption(text)

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
        kw.setdefault("grid_m", 1000)
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

    def test_false_trigger_record_gets_amended_caption(self):
        rid = "MOD000-aa-000011"
        insert(self.store, rid,
               received=datetime.now(timezone.utc) - timedelta(days=60))
        adj = adjudicate.Adjudicator(self.data, REVIEWERS,
                                     image_key=TEST_KEY)
        adj.vote_event(rid, "alice", "false_trigger")
        adj.vote_event(rid, "bob", "false_trigger")
        self._run(delay_days=30)
        rec = self._output()[0]
        self.assertNotIn("opened", rec["caption"].lower())

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

    def _publish(self, **kw):
        kw.setdefault("release_images", True)
        kw.setdefault("image_key", TEST_KEY)
        kw.setdefault("grid_m", 1000)
        return publish.publish(self.data, self.out, SALT, **kw)

    def test_unadjudicated_image_is_not_released(self):
        insert(self.store, "MOD000-bb-000001", received=self.old)
        add_image(self.store, "MOD000-bb-000001")
        m = self._publish()
        self.assertEqual(m["counts"]["images_published"], 0)
        self.assertEqual(m["counts"]["images_withheld_unadjudicated"], 1)

    def test_reviewed_image_is_released_and_stripped(self):
        insert(self.store, "MOD000-bb-000002", received=self.old)
        add_image(self.store, "MOD000-bb-000002", blob=JPEG_WITH_EXIF)
        adjudicate_image(self.data, "MOD000-bb-000002", "publish")
        m = self._publish()
        self.assertEqual(m["counts"]["images_published"], 1)

        path = os.path.join(self.out, "images", "MOD000-bb-000002_01.jpg")
        blob = open(path, "rb").read()
        self.assertNotIn(b"Exif", blob)
        self.assertTrue(blob.startswith(b"\xff\xd8"))

    def test_withheld_category_is_counted(self):
        insert(self.store, "MOD000-bb-000003", received=self.old)
        add_image(self.store, "MOD000-bb-000003")
        adjudicate_image(self.data, "MOD000-bb-000003", "withhold", "minor")
        m = self._publish()
        self.assertEqual(m["counts"]["images_published"], 0)
        self.assertEqual(m["counts"]["images_withheld_by_category"]["minor"], 1)

    def test_frame_arriving_after_the_decision_is_not_published(self):
        rid = "MOD000-bb-000006"
        insert(self.store, rid, received=self.old)
        add_image(self.store, rid, 1)
        adjudicate_image(self.data, rid, "publish")
        # A second frame arrives after the reviewer wrote the decision.
        add_image(self.store, rid, 2, blob=JPEG_WITH_EXIF)

        m = self._publish()
        self.assertEqual(m["counts"]["images_published"], 1)
        self.assertEqual(m["counts"]["images_withheld_unreviewed"], 1)
        self.assertFalse(os.path.exists(
            os.path.join(self.out, "images", f"{rid}_02.jpg")))

    def test_replaced_frame_is_not_published(self):
        rid = "MOD000-bb-000007"
        insert(self.store, rid, received=self.old)
        add_image(self.store, rid, 1)
        adjudicate_image(self.data, rid, "publish")
        # Same slot, different bytes: the reviewer saw the first version.
        add_image(self.store, rid, 1, blob=JPEG_WITH_EXIF)

        m = self._publish()
        self.assertEqual(m["counts"]["images_published"], 0)
        self.assertEqual(m["counts"]["images_withheld_unreviewed"], 1)

    def test_wrong_key_refuses_to_publish(self):
        insert(self.store, "MOD000-bb-000005", received=self.old)
        add_image(self.store, "MOD000-bb-000005")
        adjudicate_image(self.data, "MOD000-bb-000005", "publish")
        with self.assertRaises(publish.PublishError):
            self._publish(image_key=OTHER_KEY)

    def test_record_still_publishes_without_its_image(self):
        insert(self.store, "MOD000-bb-000004", received=self.old)
        add_image(self.store, "MOD000-bb-000004")
        m = self._publish()
        self.assertEqual(m["counts"]["records_published"], 1)
        self.assertEqual(m["counts"]["images_published"], 0)


class GridTests(unittest.TestCase):
    """D-76: a cell, never a point, at a resolution somebody stated."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data, self.store = make_db(self.tmp.name)
        self.out = os.path.join(self.tmp.name, "published")
        self.old = datetime.now(timezone.utc) - timedelta(days=60)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, **kw):
        kw.setdefault("grid_m", 1000)
        return publish.publish(self.data, self.out, SALT, **kw)

    def _output(self):
        with open(os.path.join(self.out, "records.jsonl"),
                  encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def test_location_becomes_a_cell_not_a_point(self):
        insert(self.store, "MOD000-gg-000001", received=self.old,
               lat=37.5792, lon=-106.1453)
        self._run()
        rec = self._output()[0]
        self.assertIn("grid_cell", rec)
        self.assertEqual(rec["grid_size_m"], 1000)
        self.assertNotIn("lat", rec)
        self.assertNotIn("lon", rec)

    def test_nearby_fixes_share_a_cell(self):
        insert(self.store, "MOD000-gg-000002", received=self.old,
               lat=37.5792, lon=-106.1453, ts=1)
        insert(self.store, "MOD000-gg-000003", received=self.old,
               lat=37.5795, lon=-106.1450, ts=2)
        self._run()
        self.assertEqual(len({r["grid_cell"] for r in self._output()}), 1)

    def test_distant_fixes_differ(self):
        insert(self.store, "MOD000-gg-000004", received=self.old,
               lat=37.5792, lon=-106.1453, ts=1)
        insert(self.store, "MOD000-gg-000005", received=self.old,
               lat=37.6250, lon=-106.1453, ts=2)
        self._run()
        self.assertEqual(len({r["grid_cell"] for r in self._output()}), 2)

    def test_a_finer_grid_is_refused(self):
        insert(self.store, "MOD000-gg-000006", received=self.old,
               lat=37.5792, lon=-106.1453)
        with self.assertRaises(publish.PublishError):
            self._run(grid_m=250)

    def test_resolution_must_be_stated(self):
        insert(self.store, "MOD000-gg-000007", received=self.old,
               lat=37.5792, lon=-106.1453)
        with self.assertRaises(publish.PublishError):
            publish.publish(self.data, self.out, SALT)

    def test_manifest_records_the_resolution(self):
        insert(self.store, "MOD000-gg-000008", received=self.old)
        self._run(grid_m=2000)
        with open(os.path.join(self.out, "manifest.json"),
                  encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["grid_m"], 2000)

    def test_records_without_a_fix_have_no_cell(self):
        insert(self.store, "MOD000-gg-000009", received=self.old)
        self._run()
        self.assertIsNone(self._output()[0]["grid_cell"])
        self.assertEqual(self._output()[0]["grid_size_m"], 1000)


class EpisodeCountTests(unittest.TestCase):
    """The removal figure is per episode; a record count would overstate it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data, self.store = make_db(self.tmp.name)
        self.out = os.path.join(self.tmp.name, "published")
        self.old = datetime.now(timezone.utc) - timedelta(days=60)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, **kw):
        kw.setdefault("grid_m", 1000)
        return publish.publish(self.data, self.out, SALT, **kw)

    def _output(self):
        with open(os.path.join(self.out, "records.jsonl"),
                  encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def _opening(self, rid0, rid1, rid2, received):
        insert(self.store, rid0, event_type="LIGHT_TRIGGER", ts=100,
               received=received)
        insert(self.store, rid1, ts=115, received=received)
        insert(self.store, rid2, event_type="MOVEMENT_EVENT", ts=140,
               received=received)

    def test_three_records_are_one_episode(self):
        self._opening("MOD000-hh-000001", "MOD000-hh-000002",
                      "MOD000-hh-000003", self.old)
        c = self._run()["counts"]
        self.assertEqual(c["records_published"], 3)
        self.assertEqual(c["episodes_total"], 1)
        self.assertEqual(c["episodes_published"], 1)

    def test_a_second_opening_is_a_second_episode(self):
        self._opening("MOD000-hh-000011", "MOD000-hh-000012",
                      "MOD000-hh-000013", self.old)
        insert(self.store, "MOD000-hh-000020", event_type="LIGHT_TRIGGER",
               ts=1000, received=self.old)
        c = self._run()["counts"]
        self.assertEqual(c["episodes_total"], 2)
        self.assertEqual(c["episodes_published"], 2)

    def test_removal_is_counted_once_for_the_analysis(self):
        self._opening("MOD000-hh-000021", "MOD000-hh-000022",
                      "MOD000-hh-000023", self.old)
        adj = adjudicate.Adjudicator(self.data, REVIEWERS, image_key=TEST_KEY)
        adj.vote_event("MOD000-hh-000021", "alice", "removal")
        adj.vote_event("MOD000-hh-000021", "bob", "removal")

        c = self._run()["counts"]
        self.assertEqual(c["records_published"], 3)
        self.assertEqual(c["removals_published"], 1)
        self.assertEqual(c["episodes_by_outcome"]["removal"], 1)

    def test_unadjudicated_episode_is_unresolved(self):
        self._opening("MOD000-hh-000031", "MOD000-hh-000032",
                      "MOD000-hh-000033", self.old)
        c = self._run()["counts"]
        self.assertEqual(c["episodes_by_outcome"]["unresolved"], 1)
        self.assertEqual(c["removals_published"], 0)

    def test_episode_straddling_the_delay_is_partial(self):
        insert(self.store, "MOD000-hh-000041", event_type="LIGHT_TRIGGER",
               ts=100, received=self.old)
        insert(self.store, "MOD000-hh-000042", ts=115)      # too recent
        c = self._run(delay_days=30)["counts"]
        self.assertEqual(c["episodes_total"], 1)
        self.assertEqual(c["episodes_published"], 0)
        self.assertEqual(c["episodes_partial"], 1)

    def test_fully_held_episode_is_not_published(self):
        insert(self.store, "MOD000-hh-000051", event_type="LIGHT_TRIGGER",
               ts=100)
        c = self._run(delay_days=30)["counts"]
        self.assertEqual(c["episodes_withheld_delay"], 1)
        self.assertEqual(c["episodes_published"], 0)

    def test_bundle_names_the_episode(self):
        self._opening("MOD000-hh-000061", "MOD000-hh-000062",
                      "MOD000-hh-000063", self.old)
        insert(self.store, "MOD000-hh-000070", event_type="LOW_BATTERY",
               ts=200, received=self.old)
        self._run()
        recs = {r["record_id"]: r for r in self._output()}
        keys = {recs[f"MOD000-hh-00006{i}"]["episode_key"] for i in (1, 2, 3)}
        self.assertEqual(len(keys), 1)
        self.assertNotIn(None, keys)
        # A device record is not part of an opening and carries no key.
        self.assertIsNone(recs["MOD000-hh-000070"]["episode_key"])


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
        publish.publish(self.data, self.out, SALT, delay_days=45, grid_m=1000)
        with open(os.path.join(self.out, "manifest.json"), encoding="utf-8") as fh:
            m = json.load(fh)
        self.assertEqual(m["delay_days"], 45)
        self.assertEqual(m["grid_m"], 1000)
        self.assertEqual(m["grid_floor_m"], publish.MIN_GRID_M)
        self.assertEqual(m["policy_version"], publish.POLICY_VERSION)
        self.assertFalse(m["images_released"])

    def test_missing_database_is_an_error(self):
        with self.assertRaises(publish.PublishError):
            publish.publish(os.path.join(self.tmp.name, "nope"),
                            self.out, SALT)


class CliTests(unittest.TestCase):
    def test_cli_refuses_a_grid_below_the_floor(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "data")
            store = ingest.Store(data, image_key=TEST_KEY)
            insert(store, "MOD000-ee-000001",
                   received=datetime.now(timezone.utc) - timedelta(days=60))
            old = os.environ.get("PUBLISH_SALT")
            os.environ["PUBLISH_SALT"] = SALT.hex()
            try:
                code = publish.main(["--data-dir", data,
                                     "--out", os.path.join(tmp, "out"),
                                     "--grid-m", "250", "--no-images"])
            finally:
                if old is None:
                    os.environ.pop("PUBLISH_SALT", None)
                else:
                    os.environ["PUBLISH_SALT"] = old
            self.assertEqual(code, 1)

    def test_refuses_without_salt(self):
        import subprocess
        here = os.path.dirname(os.path.abspath(__file__))
        env = {k: v for k, v in os.environ.items() if k != "PUBLISH_SALT"}
        out = subprocess.run(
            ["python3", os.path.join(here, "publish.py"),
             "--grid-m", "1000"],
            capture_output=True, text=True, env=env)
        self.assertEqual(out.returncode, 2)
        self.assertIn("PUBLISH_SALT", out.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
