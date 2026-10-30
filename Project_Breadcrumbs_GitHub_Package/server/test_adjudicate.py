#!/usr/bin/env python3
"""Tests for adjudication. Standard library only."""

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta

import adjudicate
import ingest

REVIEWERS = {"alice", "bob", "carol"}
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" \
       b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00" + b"\x11" * 40 + b"\xff\xd9"


def make_record(record_id, module="MOD000", event_type="IMAGE_CAPTURE_COMPLETE"):
    return {
        "record_id": record_id,
        "module_id": module,
        "deployment_id": "DEP0001",
        "event_type": event_type,
        "sensor_ts": 1793500000,
        "clock_synced": True,
        "clock_uncertainty_s": 43,
        "battery_mv": 3350,
        "frame_count": 3,
        "flags": 0,
        "location": {"valid": False},
    }


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = os.path.join(self.tmp.name, "data")
        self.store = ingest.Store(self.data)
        self.adj = adjudicate.Adjudicator(self.data, REVIEWERS)

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, record_id, **kw):
        self.store.insert_record(make_record(record_id, **kw))
        return record_id

    def add_image(self, record_id, frame=1):
        self.store.store_image(record_id, frame, JPEG)

    def status_of(self, record_id):
        conn = sqlite3.connect(os.path.join(self.data, "records.db"))
        row = conn.execute(
            "SELECT validation_status FROM events WHERE record_id=?",
            (record_id,)).fetchone()
        conn.close()
        return row[0]


class EventAdjudicationTests(Base):
    def test_single_reviewer_does_not_resolve(self):
        rid = self.add("MOD000-a-000001", event_type="MOVEMENT_EVENT")
        res = self.adj.vote_event(rid, "alice", "removal")
        self.assertEqual(res["state"], "awaiting_second")
        self.assertEqual(self.status_of(rid), "unreviewed")

    def test_two_agreeing_reviewers_resolve(self):
        rid = self.add("MOD000-a-000002", event_type="MOVEMENT_EVENT")
        self.adj.vote_event(rid, "alice", "removal")
        res = self.adj.vote_event(rid, "bob", "removal")
        self.assertEqual(res["state"], "resolved")
        self.assertEqual(self.status_of(rid), "reviewed")

    def test_disagreement_needs_third(self):
        rid = self.add("MOD000-a-000003", event_type="MOVEMENT_EVENT")
        self.adj.vote_event(rid, "alice", "removal")
        res = self.adj.vote_event(rid, "bob", "handling")
        self.assertEqual(res["state"], "needs_third")
        # Retained as indeterminate rather than forced into a class (§6).
        self.assertEqual(self.status_of(rid), "indeterminate")

    def test_third_reviewer_decides(self):
        rid = self.add("MOD000-a-000004", event_type="MOVEMENT_EVENT")
        self.adj.vote_event(rid, "alice", "removal")
        self.adj.vote_event(rid, "bob", "handling")
        res = self.adj.vote_event(rid, "carol", "removal")
        self.assertEqual(res["state"], "resolved_by_third")
        self.assertEqual(self.status_of(rid), "reviewed")

    def test_false_trigger_is_its_own_status(self):
        rid = self.add("MOD000-a-000005")
        self.adj.vote_event(rid, "alice", "false_trigger")
        self.adj.vote_event(rid, "bob", "false_trigger")
        self.assertEqual(self.status_of(rid), "false_trigger")

    def test_only_documented_statuses_are_written(self):
        rid = self.add("MOD000-a-000006")
        self.adj.vote_event(rid, "alice", "removal")
        self.adj.vote_event(rid, "bob", "removal")
        self.assertIn(self.status_of(rid), adjudicate.VALID_STATUSES)

    def test_bad_outcome_rejected(self):
        rid = self.add("MOD000-a-000007")
        with self.assertRaises(adjudicate.AdjudicationError):
            self.adj.vote_event(rid, "alice", "theft")

    def test_unknown_record_rejected(self):
        with self.assertRaises(adjudicate.AdjudicationError):
            self.adj.telemetry("MOD000-nope-000000")


class BlindnessTests(Base):
    """§6: the event classification must not be informed by the images."""

    def test_reviewer_who_viewed_images_cannot_decide_event(self):
        rid = self.add("MOD000-b-000001", event_type="MOVEMENT_EVENT")
        self.add_image(rid)
        self.adj.view_images(rid, "alice", os.path.join(self.tmp.name, "r"))
        with self.assertRaises(adjudicate.AdjudicationError) as cm:
            self.adj.vote_event(rid, "alice", "removal")
        self.assertIn("blind", str(cm.exception))

    def test_other_reviewer_is_unaffected(self):
        rid = self.add("MOD000-b-000002", event_type="MOVEMENT_EVENT")
        self.add_image(rid)
        self.adj.view_images(rid, "alice", os.path.join(self.tmp.name, "r"))
        self.adj.vote_event(rid, "bob", "removal")
        self.adj.vote_event(rid, "carol", "removal")
        self.assertEqual(self.status_of(rid), "reviewed")

    def test_telemetry_contains_no_image_reference(self):
        rid = self.add("MOD000-b-000003", event_type="MOVEMENT_EVENT")
        self.add_image(rid)
        out = self.adj.telemetry(rid)
        blob = json.dumps(out)
        self.assertNotIn("secure_object_ref", blob)
        self.assertNotIn("_01.jpg", blob)
        self.assertIn("frames_on_disk", out)

    def test_show_never_writes_frames(self):
        rid = self.add("MOD000-b-000004")
        self.add_image(rid)
        before = os.listdir(self.data)
        self.adj.telemetry(rid)
        self.assertEqual(sorted(before), sorted(os.listdir(self.data)))


class ImageAccessTests(Base):
    def test_viewing_requires_allowlist_membership(self):
        rid = self.add("MOD000-c-000001")
        self.add_image(rid)
        with self.assertRaises(adjudicate.AdjudicationError):
            self.adj.view_images(rid, "mallory", os.path.join(self.tmp.name, "r"))

    def test_no_allowlist_means_no_image_access(self):
        rid = self.add("MOD000-c-000002")
        self.add_image(rid)
        open_adj = adjudicate.Adjudicator(self.data, allowed_reviewers=None)
        with self.assertRaises(adjudicate.AdjudicationError):
            open_adj.view_images(rid, "alice", os.path.join(self.tmp.name, "r"))

    def test_access_is_logged(self):
        rid = self.add("MOD000-c-000003")
        self.add_image(rid)
        self.adj.view_images(rid, "alice", os.path.join(self.tmp.name, "r"))
        conn = sqlite3.connect(os.path.join(self.data, "records.db"))
        row = conn.execute(
            "SELECT kind, detail FROM ingest_log WHERE kind='image_access'"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertIn(rid, row[1])
        self.assertIn("alice", row[1])

    def test_view_copies_frames_out(self):
        rid = self.add("MOD000-c-000004")
        self.add_image(rid, 1)
        self.add_image(rid, 2)
        out = os.path.join(self.tmp.name, "review")
        files = self.adj.view_images(rid, "alice", out)
        self.assertEqual(len(files), 2)
        self.assertTrue(all(os.path.exists(f) for f in files))


class ImageDecisionTests(Base):
    def setUp(self):
        super().setUp()
        self.rid = self.add("MOD000-d-000001")
        self.add_image(self.rid, 1)
        self.add_image(self.rid, 2)

    def test_withhold_requires_a_category(self):
        with self.assertRaises(adjudicate.AdjudicationError):
            self.adj.decide_image(self.rid, "alice", "withhold")

    def test_withheld_frames_are_destroyed(self):
        res = self.adj.decide_image(self.rid, "alice", "withhold",
                                    category="minor")
        self.assertEqual(res["images_destroyed"], 2)
        self.assertEqual(
            [f for f in os.listdir(os.path.join(self.data, "images"))
             if f.startswith(self.rid)], [])

    def test_hashes_survive_destruction(self):
        self.adj.decide_image(self.rid, "alice", "withhold", category="minor")
        conn = sqlite3.connect(os.path.join(self.data, "records.db"))
        hashes = conn.execute(
            "SELECT image_hashes FROM adjudications WHERE record_id=?"
            " AND kind='image'", (self.rid,)).fetchone()[0]
        conn.close()
        self.assertEqual(len(json.loads(hashes)), 2)

    def test_image_rows_become_tombstones(self):
        self.adj.decide_image(self.rid, "alice", "withhold", category="minor")
        conn = sqlite3.connect(os.path.join(self.data, "records.db"))
        refs = [r[0] for r in conn.execute(
            "SELECT secure_object_ref FROM images WHERE record_id=?",
            (self.rid,)).fetchall()]
        conn.close()
        self.assertEqual(len(refs), 2)
        self.assertTrue(all(r == "" for r in refs))

    def test_legal_hold_suspends_deletion(self):
        until = (date.today() + timedelta(days=30)).isoformat()
        res = self.adj.decide_image(self.rid, "alice", "withhold",
                                    category="minor",
                                    legal_hold_until=until)
        self.assertEqual(res["images_destroyed"], 0)
        kept = [f for f in os.listdir(os.path.join(self.data, "images"))
                if f.startswith(self.rid)]
        self.assertEqual(len(kept), 2)

    def test_expired_legal_hold_allows_deletion(self):
        until = (date.today() - timedelta(days=1)).isoformat()
        res = self.adj.decide_image(self.rid, "alice", "withhold",
                                    category="minor", legal_hold_until=until)
        self.assertEqual(res["images_destroyed"], 2)

    def test_legal_hold_needs_a_date(self):
        with self.assertRaises(adjudicate.AdjudicationError):
            self.adj.decide_image(self.rid, "alice", "withhold",
                                  category="minor", legal_hold_until="forever")

    def test_publish_keeps_the_frames(self):
        res = self.adj.decide_image(self.rid, "alice", "publish")
        self.assertEqual(res["images_destroyed"], 0)
        kept = [f for f in os.listdir(os.path.join(self.data, "images"))
                if f.startswith(self.rid)]
        self.assertEqual(len(kept), 2)

    def test_image_decision_requires_allowlist(self):
        with self.assertRaises(adjudicate.AdjudicationError):
            self.adj.decide_image(self.rid, "mallory", "publish")


class StatusTests(Base):
    def test_status_counts_withheld_by_category(self):
        a = self.add("MOD000-e-000001")
        b = self.add("MOD000-e-000002")
        self.add_image(a)
        self.add_image(b)
        self.adj.decide_image(a, "alice", "withhold", category="minor")
        self.adj.decide_image(b, "alice", "withhold", category="unconnected")
        s = self.adj.status()
        self.assertEqual(s["withheld_by_category"]["minor"], 1)
        self.assertEqual(s["withheld_by_category"]["unconnected"], 1)

    def test_pending_lists_unreviewed(self):
        self.add("MOD000-e-000003")
        self.assertTrue(self.adj.pending())


class CliTests(unittest.TestCase):
    def test_missing_database_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(adjudicate.AdjudicationError):
                adjudicate.Adjudicator(tmp)

    def test_cli_refuses_unknown_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "data")
            ingest.Store(data).insert_record(make_record("MOD000-f-000001"))
            env = {"INGEST_DATA": data, "ADJUDICATORS": "alice"}
            old = dict(os.environ)
            os.environ.clear()
            os.environ.update(env)
            try:
                with self.assertRaises(SystemExit) as cm:
                    adjudicate.main(["decide-event", "MOD000-f-000001",
                                     "--reviewer", "alice",
                                     "--outcome", "theft"])
                self.assertEqual(cm.exception.code, 2)
            finally:
                os.environ.clear()
                os.environ.update(old)


if __name__ == "__main__":
    unittest.main(verbosity=2)
