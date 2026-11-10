#!/usr/bin/env python3
"""Tests for the study-name generator (D-78)."""

import os
import random
import stat
import tempfile
import unittest

import namegen

BLOCKLIST = {"Alice Adams", "Project Reviewer"}


def make_pool(**overrides):
    params = {
        "placements": 3,
        "pool_size": 6,
        "blocklist": set(BLOCKLIST),
        "rng": random.Random(7),
    }
    params.update(overrides)
    return namegen.NamePool.create(**params)


class PoolTests(unittest.TestCase):
    def test_pool_has_the_requested_size_and_unique_names(self):
        pool = make_pool()
        names = pool.state["available"]
        self.assertEqual(len(names), 6)
        self.assertEqual(len(set(names)), 6)

    def test_pool_names_are_ascii_and_label_sized(self):
        pool = make_pool()
        for name in pool.state["available"]:
            self.assertTrue(name.isascii())
            self.assertLessEqual(len(name), namegen.MAX_NAME_LENGTH)

    def test_pool_must_be_at_least_twice_the_placements(self):
        with self.assertRaises(namegen.NameGenError):
            make_pool(placements=3, pool_size=5)

    def test_blocklist_is_case_insensitive_and_whole_name(self):
        pool = make_pool(placements=20, pool_size=40,
                         blocklist={"alice adams"})
        self.assertNotIn("Alice Adams", pool.state["available"])

    def test_empty_blocklist_is_refused(self):
        with self.assertRaises(namegen.NameGenError):
            make_pool(blocklist=set())

    def test_pool_source_is_recorded(self):
        pool = make_pool()
        self.assertEqual(pool.state["pool_source"], namegen.POOL_SOURCE)


class AssignmentTests(unittest.TestCase):
    def test_issue_records_a_name_and_removes_it_from_available(self):
        pool = make_pool()
        name = pool.issue("DEP-001")
        assignment = pool.state["assignments"]["DEP-001"]
        self.assertEqual(assignment["name"], name)
        self.assertEqual(assignment["status"], "issued")
        self.assertIn(name, [e["name"] for e in assignment["events"]])
        self.assertNotIn(name, pool.state["available"])

    def test_a_deployment_cannot_be_issued_twice(self):
        pool = make_pool()
        pool.issue("DEP-001")
        with self.assertRaises(namegen.NameGenError):
            pool.issue("DEP-001")

    def test_a_deployment_id_is_validated(self):
        pool = make_pool()
        with self.assertRaises(namegen.NameGenError):
            pool.issue("bad id with spaces")

    def test_assignment_is_random_not_a_deployment_hash(self):
        first = make_pool(rng=random.Random(1))
        second = make_pool(rng=random.Random(2))
        first_names = [first.issue(f"DEP-{i}") for i in range(3)]
        second_names = [second.issue(f"DEP-{i}") for i in range(3)]
        self.assertNotEqual(first_names, second_names)

    def test_confirm_passed_records_the_host_check(self):
        pool = make_pool()
        name = pool.issue("DEP-001")
        result = pool.confirm("DEP-001", passed=True)
        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["name"], name)
        assignment = pool.state["assignments"]["DEP-001"]
        self.assertEqual(assignment["host_check"], "passed")
        self.assertTrue(assignment["confirmed_at"])

    def test_confirm_passed_is_idempotent(self):
        pool = make_pool()
        pool.issue("DEP-001")
        pool.confirm("DEP-001", passed=True)
        before = len(pool.state["assignments"]["DEP-001"]["events"])
        pool.confirm("DEP-001", passed=True)
        after = len(pool.state["assignments"]["DEP-001"]["events"])
        self.assertEqual(before, after)

    def test_failed_check_retires_the_name_and_allows_a_reissue(self):
        pool = make_pool()
        first = pool.issue("DEP-001")
        result = pool.confirm("DEP-001", passed=False)
        self.assertEqual(result["status"], "reissue_required")
        self.assertEqual(result["retired"], first)
        self.assertIn(first, [r["name"] for r in pool.state["retired"]])
        self.assertIsNone(pool.state["assignments"]["DEP-001"]["name"])
        second = pool.issue("DEP-001")
        self.assertNotEqual(second, first)
        self.assertEqual(
            pool.state["assignments"]["DEP-001"]["status"], "issued"
        )

    def test_retire_removes_the_name_and_blocks_reissue(self):
        pool = make_pool()
        name = pool.issue("DEP-001")
        retired = pool.retire("DEP-001", "deployment cancelled")
        self.assertEqual(retired, name)
        self.assertEqual(
            pool.state["assignments"]["DEP-001"]["status"], "retired"
        )
        with self.assertRaises(namegen.NameGenError):
            pool.issue("DEP-001")

    def test_retire_requires_a_reason(self):
        pool = make_pool()
        pool.issue("DEP-001")
        with self.assertRaises(namegen.NameGenError):
            pool.retire("DEP-001", "   ")

    def test_pool_exhaustion_is_an_error_not_a_reuse(self):
        pool = make_pool(placements=3, pool_size=6)
        for i in range(6):
            pool.issue(f"DEP-{i}")
        with self.assertRaises(namegen.NameGenError):
            pool.issue("DEP-6")


class PersistenceTests(unittest.TestCase):
    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "study_names.json")
            pool = make_pool()
            name = pool.issue("DEP-001")
            pool.save(path)
            loaded = namegen.NamePool.load(path, rng=random.Random(3))
            self.assertEqual(
                loaded.state["assignments"]["DEP-001"]["name"], name
            )
            self.assertEqual(
                loaded.state["available"], pool.state["available"]
            )

    @unittest.skipUnless(os.name == "posix", "POSIX permissions")
    def test_state_file_is_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "study_names.json")
            make_pool().save(path)
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)

    def test_wrong_version_is_refused(self):
        pool = make_pool()
        pool.state["version"] = 99
        with self.assertRaises(namegen.NameGenError):
            namegen.NamePool(pool.state)

    def test_missing_state_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(namegen.NameGenError):
                namegen.NamePool.load(os.path.join(tmp, "missing.json"))


class CheckTests(unittest.TestCase):
    def test_check_accepts_a_fresh_pool(self):
        pool = make_pool()
        result = pool.check(BLOCKLIST)
        self.assertEqual(result["pool_size"], 6)
        self.assertEqual(result["available"], 6)
        self.assertEqual(result["issued"], 0)

    def test_check_counts_retired_names(self):
        pool = make_pool()
        first = pool.issue("DEP-001")
        pool.confirm("DEP-001", passed=False)
        second = pool.issue("DEP-001")
        result = pool.check(BLOCKLIST)
        self.assertEqual(result["available"], 4)
        self.assertEqual(result["retired"], 1)
        self.assertNotEqual(first, second)

    def test_check_detects_a_duplicate(self):
        pool = make_pool()
        pool.state["available"][1] = pool.state["available"][0]
        with self.assertRaises(namegen.NameGenError):
            pool.check(BLOCKLIST)

    def test_check_detects_a_blocklisted_name(self):
        pool = make_pool()
        pool.state["available"][0] = "Alice Adams"
        with self.assertRaises(namegen.NameGenError):
            pool.check(BLOCKLIST)

    def test_check_detects_a_confirmed_assignment_without_a_passed_check(self):
        pool = make_pool()
        pool.issue("DEP-001")
        pool.state["assignments"]["DEP-001"]["status"] = "confirmed"
        with self.assertRaises(namegen.NameGenError):
            pool.check(BLOCKLIST)


if __name__ == "__main__":
    unittest.main()
