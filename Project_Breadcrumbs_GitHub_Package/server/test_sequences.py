#!/usr/bin/env python3
"""Tests for movement-event sequence grouping. Standard library only."""

import os
import sqlite3
import tempfile
import unittest

import adjudicate
import ingest
import sequences

BASE = 1793500000


def ev(record_id, offset, event_type="MOVEMENT_EVENT", module="MOD000",
       synced=True, deployment="DEP0001"):
    return {
        "record_id": record_id,
        "module_id": module,
        "deployment_id": deployment,
        "event_type": event_type,
        "sensor_ts": BASE + offset,
        "clock_synced": 1 if synced else 0,
    }


def ids(seq):
    return sorted(seq["member_ids"])


class GroupingTests(unittest.TestCase):
    def test_contiguous_events_are_one_sequence(self):
        out = sequences.build([
            ev("a", 0, "LIGHT_TRIGGER"),
            ev("b", 30),
            ev("c", 60),
        ])
        self.assertEqual(len(out), 1)
        self.assertEqual(ids(out[0]), ["a", "b", "c"])
        self.assertTrue(out[0]["is_episode"])

    def test_gap_starts_a_new_sequence(self):
        out = sequences.build([
            ev("a", 0),
            ev("b", 60),
            ev("c", 60 + sequences.GAP_S + 1),
        ])
        self.assertEqual(len(out), 2)
        self.assertEqual(ids(out[0]), ["a", "b"])
        self.assertEqual(ids(out[1]), ["c"])

    def test_long_episode_is_capped_by_the_window(self):
        # Each record is within GAP_S of the last, but the run passes WINDOW_S.
        rows = [ev(f"r{i}", i * 120) for i in range(12)]
        out = sequences.build(rows)
        self.assertGreater(len(out), 1)
        for seq in out:
            self.assertLessEqual(
                seq["ended_ts"] - seq["started_ts"], sequences.WINDOW_S)

    def test_unsynced_record_is_a_singleton(self):
        out = sequences.build([
            ev("a", 0),
            ev("b", 30, synced=False),
            ev("c", 60),
        ])
        self.assertEqual(len(out), 2)
        # The synced pair still merges around it: an unsynced record cannot be
        # placed in time, but it does not break an episode either.
        self.assertEqual(ids(out[0]), ["a", "c"])
        self.assertEqual(ids(out[1]), ["b"])
        self.assertFalse([s for s in out if "b" in s["member_ids"]][0]["is_episode"])

    def test_device_events_never_join_an_episode(self):
        out = sequences.build([
            ev("a", 0, "LIGHT_TRIGGER"),
            ev("b", 10, "LOW_BATTERY"),
            ev("c", 20),
        ])
        episodes = [s for s in out if s["is_episode"]]
        self.assertEqual(len(episodes), 1)
        self.assertEqual(ids(episodes[0]), ["a", "c"])
        self.assertNotIn("b", episodes[0]["member_ids"])

        battery = [s for s in out if "b" in s["member_ids"]][0]
        self.assertFalse(battery["is_episode"])
        self.assertEqual(battery["member_count"] if "member_count" in battery
                         else len(battery["member_ids"]), 1)

    def test_modules_never_merge(self):
        out = sequences.build([
            ev("a", 0, module="MOD001"),
            ev("b", 10, module="MOD002"),
        ])
        self.assertEqual(len(out), 2)
        self.assertEqual({s["module_id"] for s in out}, {"MOD001", "MOD002"})

    def test_ids_are_deterministic_and_order_independent(self):
        rows = [ev("a", 0), ev("b", 30)]
        first = sequences.build(rows)
        second = sequences.build(list(reversed(rows)))
        self.assertEqual([s["sequence_id"] for s in first],
                         [s["sequence_id"] for s in second])

    def test_sequence_is_named_from_its_first_record(self):
        out = sequences.build([ev("later", 60), ev("first", 0)])
        self.assertEqual(out[0]["anchor_record_id"], "first")
        self.assertEqual(out[0]["sequence_id"],
                         sequences.sequence_id_for("MOD000", "first"))

    def test_empty_input(self):
        self.assertEqual(sequences.build([]), [])


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = os.path.join(self.tmp.name, "data")
        self.store = ingest.Store(self.data)
        self.db = os.path.join(self.data, "records.db")

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, record_id, offset, event_type="MOVEMENT_EVENT", **kw):
        rec = {
            "record_id": record_id,
            "module_id": kw.pop("module", "MOD000"),
            "deployment_id": "DEP0001",
            "event_type": event_type,
            "sensor_ts": BASE + offset,
            "clock_synced": True,
            "clock_uncertainty_s": 43,
            "frame_count": 0,
            "flags": 0,
            "location": {"valid": False},
        }
        self.store.insert_record(rec)

    def sync(self):
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        try:
            report = sequences.sync(conn)
            conn.commit()
            return report
        finally:
            conn.close()

    def rows(self, sql, params=()):
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    def test_sync_stores_the_episode(self):
        self.add("MOD000-1", 0, "LIGHT_TRIGGER")
        self.add("MOD000-2", 30)
        report = self.sync()
        self.assertEqual(report["created"], 1)
        rows = self.rows("SELECT * FROM sequences")
        self.assertEqual(rows[0]["member_count"], 2)
        self.assertEqual(rows[0]["rule_version"], sequences.RULE_VERSION)

    def test_sync_is_idempotent(self):
        self.add("MOD000-1", 0)
        self.sync()
        report = self.sync()
        self.assertEqual(report["created"], 0)
        self.assertEqual(report["stored"], 1)

    def test_late_record_extends_an_undecided_sequence(self):
        self.add("MOD000-1", 0)
        self.sync()
        self.add("MOD000-2", 45)
        report = self.sync()
        self.assertEqual(report["extended"], 1)
        rows = self.rows("SELECT member_count FROM sequences")
        self.assertEqual(rows[0]["member_count"], 2)

    def test_decided_sequence_membership_is_frozen(self):
        self.add("MOD000-1", 0, "LIGHT_TRIGGER")
        self.sync()
        seq_id = self.rows("SELECT sequence_id FROM sequences")[0]["sequence_id"]

        adj = adjudicate.Adjudicator(self.data, {"alice", "bob"})
        adj.vote_sequence(seq_id, "alice", "removal")
        adj.vote_sequence(seq_id, "bob", "removal")

        # A record that would have belonged to the episode arrives late.
        self.add("MOD000-2", 45)
        report = self.sync()
        self.assertEqual(report["frozen"], 1)
        rows = self.rows("SELECT member_count FROM sequences")
        self.assertEqual(rows[0]["member_count"], 1)

    def test_device_record_is_stored_but_not_an_episode(self):
        self.add("MOD000-1", 0, "SYNC_SUCCESS")
        self.sync()
        rows = self.rows("SELECT is_episode FROM sequences")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["is_episode"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
