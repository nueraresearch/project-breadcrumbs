#!/usr/bin/env python3
"""Tests for adjudication. Standard library only."""

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta

import adjudicate
import imagecrypt
import ingest

REVIEWERS = {"alice", "bob", "carol"}
TEST_KEY = bytes.fromhex("cd" * 32)
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
        self.store = ingest.Store(self.data, image_key=TEST_KEY)
        self.adj = adjudicate.Adjudicator(self.data, REVIEWERS,
                                          image_key=TEST_KEY)

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
        open_adj = adjudicate.Adjudicator(self.data, allowed_reviewers=None,
                                          image_key=TEST_KEY)
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

    def test_decision_with_no_frames_is_refused(self):
        bare = self.add("MOD000-d-000009")
        with self.assertRaises(adjudicate.AdjudicationError):
            self.adj.decide_image(bare, "alice", "publish")

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


class EncryptionAtRestTests(Base):
    def test_frame_on_disk_is_ciphertext(self):
        rid = self.add("MOD000-i-000001")
        self.add_image(rid)
        files = [f for f in os.listdir(os.path.join(self.data, "images"))
                 if f.startswith(rid)]
        raw = open(os.path.join(self.data, "images", files[0]), "rb").read()
        self.assertTrue(imagecrypt.is_encrypted(raw))
        self.assertNotIn(JPEG, raw)

    def test_view_decrypts_to_the_original_frame(self):
        rid = self.add("MOD000-i-000002")
        self.add_image(rid)
        files = self.adj.view_images(rid, "alice",
                                     os.path.join(self.tmp.name, "r"))
        self.assertEqual(open(files[0], "rb").read(), JPEG)

    def test_review_without_a_key_is_refused(self):
        rid = self.add("MOD000-i-000003")
        self.add_image(rid)
        keyless = adjudicate.Adjudicator(self.data, REVIEWERS)
        if keyless.image_key is not None:
            self.skipTest("IMAGE_KEY is set in this environment")
        with self.assertRaises(adjudicate.AdjudicationError):
            keyless.view_images(rid, "alice", os.path.join(self.tmp.name, "r2"))


class SequenceAdjudicationTests(Base):
    """§6 classifies the sequence. One opening is not several questions."""

    def add_at(self, record_id, offset, event_type="MOVEMENT_EVENT"):
        rec = make_record(record_id, event_type=event_type)
        rec["sensor_ts"] = 1793500000 + offset
        self.store.insert_record(rec)
        return record_id

    def episode(self):
        return [self.add_at("MOD000-g-000001", 0, "LIGHT_TRIGGER"),
                self.add_at("MOD000-g-000002", 20, "IMAGE_CAPTURE_COMPLETE"),
                self.add_at("MOD000-g-000003", 40)]

    def test_one_episode_is_one_classification(self):
        ids = self.episode()
        self.adj.vote_event(ids[0], "alice", "removal")
        # The second vote is cast on a different record of the same episode.
        self.adj.vote_event(ids[2], "bob", "removal")
        for rid in ids:
            self.assertEqual(self.status_of(rid), "reviewed")

    def test_episode_needs_one_reviewer_not_one_per_record(self):
        ids = self.episode()
        res = self.adj.vote_event(ids[0], "alice", "removal")
        self.assertEqual(res["state"], "awaiting_second")
        self.assertEqual(res["records"], ids)

    def test_all_records_share_the_verdict(self):
        ids = self.episode()
        self.adj.vote_event(ids[1], "alice", "false_trigger")
        self.adj.vote_event(ids[1], "bob", "false_trigger")
        for rid in ids:
            self.assertEqual(self.status_of(rid), "false_trigger")

    def test_viewing_any_frame_disqualifies_the_reviewer(self):
        ids = self.episode()
        self.add_image(ids[2], 1)
        self.adj.view_images(ids[2], "alice", os.path.join(self.tmp.name, "r"))
        with self.assertRaises(adjudicate.AdjudicationError) as cm:
            self.adj.vote_event(ids[0], "alice", "removal")
        self.assertIn("blind", str(cm.exception))

    def test_context_fix_is_shown_but_is_not_a_member(self):
        ids = self.episode()
        fix = self.add_at("MOD000-g-000010", 30, "LOCATION_FIX")
        detail = self.adj.sequence_detail(self.adj.sequence_of(ids[0]))
        self.assertEqual(len(detail["members"]), 3)
        self.assertNotIn(fix, [m["record_id"] for m in detail["members"]])
        self.assertEqual([f["record_id"] for f in detail["context_fixes"]],
                         [fix])

    def test_pending_lists_the_episode_once(self):
        ids = self.episode()
        rows = self.adj.pending()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["member_count"], 3)

        self.adj.vote_event(ids[0], "alice", "removal")
        self.adj.vote_event(ids[0], "bob", "removal")
        self.assertEqual(self.adj.pending(), [])

    def test_status_reports_episodes(self):
        ids = self.episode()
        self.adj.vote_event(ids[0], "alice", "removal")
        self.adj.vote_event(ids[0], "bob", "removal")
        s = self.adj.status()
        self.assertEqual(s["episodes"]["total"], 1)
        self.assertEqual(s["episodes"]["decided"], 1)
        self.assertEqual(s["episodes"]["open"], 0)

    def test_unsynced_record_is_classified_alone(self):
        self.add_at("MOD000-h-000001", 0)
        rec = make_record("MOD000-h-000002", event_type="MOVEMENT_EVENT")
        rec["clock_synced"] = False
        rec["clock_uncertainty_s"] = 1080
        self.store.insert_record(rec)
        self.assertNotEqual(self.adj.sequence_of("MOD000-h-000001"),
                            self.adj.sequence_of("MOD000-h-000002"))


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
