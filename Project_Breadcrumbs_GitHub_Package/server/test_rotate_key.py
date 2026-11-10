#!/usr/bin/env python3
"""Tests for image key rotation."""

import hashlib
import os
import tempfile
import unittest
from unittest import mock

import imagecrypt
import ingest
import rotate_key

OLD = bytes.fromhex("ab" * 32)
NEW = bytes.fromhex("cd" * 32)
OTHER = bytes.fromhex("ef" * 32)

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200 + b"\xff\xd9"


class RotationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = os.path.join(self.tmp.name, "data")
        self.store = ingest.Store(self.data, image_key=OLD)
        self.store.store_image("MOD000-1", 1, JPEG)
        self.ref = self._ref("MOD000-1", 1)

    def tearDown(self):
        self.tmp.cleanup()

    def _ref(self, record_id, frame):
        with self.store._conn() as conn:
            return conn.execute(
                "SELECT secure_object_ref FROM images"
                " WHERE record_id=? AND frame_index=?",
                (record_id, frame)).fetchone()["secure_object_ref"]

    def _row(self, record_id="MOD000-1", frame=1):
        with self.store._conn() as conn:
            return dict(conn.execute(
                "SELECT secure_object_ref, integrity_hash, bytes FROM images"
                " WHERE record_id=? AND frame_index=?",
                (record_id, frame)).fetchone())

    def _bytes(self, ref):
        with open(os.path.join(self.store.image_dir, ref), "rb") as fh:
            return fh.read()

    def _read_with(self, key):
        return ingest.Store(self.data, image_key=key).read_image(self.ref)

    # -- the rotation itself ---------------------------------------------

    def test_frame_is_reencrypted_under_the_new_key(self):
        report = rotate_key.rotate(self.data, NEW, OLD)
        self.assertEqual(report["rotated"], 1)
        self.assertEqual(report["failed"], [])
        self.assertEqual(self._read_with(NEW), JPEG)

    def test_the_old_key_no_longer_opens_it(self):
        rotate_key.rotate(self.data, NEW, OLD)
        with self.assertRaises(imagecrypt.CryptoError):
            self._read_with(OLD)

    def test_rows_do_not_change(self):
        before = self._row()
        rotate_key.rotate(self.data, NEW, OLD)
        self.assertEqual(self._row(), before)

    def test_ciphertext_changes(self):
        before = self._bytes(self.ref)
        rotate_key.rotate(self.data, NEW, OLD)
        self.assertNotEqual(self._bytes(self.ref), before)

    def test_second_run_verifies_instead_of_rewriting(self):
        rotate_key.rotate(self.data, NEW, OLD)
        sealed = self._bytes(self.ref)
        report = rotate_key.rotate(self.data, NEW, OLD)
        self.assertEqual(report["rotated"], 0)
        self.assertEqual(report["already_new"], 1)
        self.assertEqual(self._bytes(self.ref), sealed)

    def test_a_partially_rotated_directory_is_finished(self):
        ingest.Store(self.data, image_key=NEW).store_image(
            "MOD000-2", 1, JPEG)
        report = rotate_key.rotate(self.data, NEW, OLD)
        self.assertEqual(report["rotated"], 1)
        self.assertEqual(report["already_new"], 1)
        self.assertEqual(
            ingest.Store(self.data, image_key=NEW).read_image(
                self._ref("MOD000-2", 1)), JPEG)

    def test_dry_run_changes_nothing(self):
        sealed = self._bytes(self.ref)
        report = rotate_key.rotate(self.data, NEW, OLD, dry_run=True)
        self.assertEqual(report["rotated"], 1)
        self.assertEqual(self._bytes(self.ref), sealed)
        self.assertEqual(self._read_with(OLD), JPEG)

    # -- refusals ---------------------------------------------------------

    def test_hash_mismatch_is_left_under_the_old_key(self):
        with self.store._conn() as conn:
            conn.execute("UPDATE images SET integrity_hash=?",
                         ("00" * 32,))
        report = rotate_key.rotate(self.data, NEW, OLD)
        self.assertEqual(report["rotated"], 0)
        self.assertEqual(len(report["failed"]), 1)
        # Still readable with the key it was already under.
        self.assertEqual(self._read_with(OLD), JPEG)

    def test_missing_old_key_is_reported_rather_than_failed(self):
        report = rotate_key.rotate(self.data, NEW, None)
        self.assertEqual(len(report["need_previous"]), 1)
        self.assertEqual(report["rotated"], 0)
        self.assertEqual(self._read_with(OLD), JPEG)

    def test_a_frame_under_a_third_key_is_reported(self):
        ingest.Store(self.data, image_key=OTHER).store_image(
            "MOD000-3", 1, JPEG)
        report = rotate_key.rotate(self.data, NEW, OLD)
        self.assertTrue(any("MOD000-3[1]" == f[0] for f in report["failed"]))

    def test_plaintext_frame_points_at_the_migration(self):
        path = os.path.join(self.store.image_dir, "MOD000-4_01.jpg")
        with open(path, "wb") as fh:
            fh.write(JPEG)
        with self.store._conn() as conn:
            conn.execute(
                "INSERT INTO images (record_id, frame_index, image_id,"
                " secure_object_ref, integrity_hash, bytes, uploaded_at)"
                " VALUES (?,?,?,?,?,?,?)",
                ("MOD000-4", 1, "MOD000-4-1", "MOD000-4_01.jpg",
                 hashlib.sha256(JPEG).hexdigest(), len(JPEG),
                 ingest.utcnow()))
        report = rotate_key.rotate(self.data, NEW, OLD)
        self.assertTrue(any("migrate_images.py" in f[1]
                            for f in report["failed"]))

    def test_a_failed_write_leaves_the_original_untouched(self):
        sealed = self._bytes(self.ref)
        bad = imagecrypt.MAGIC + b"\x00" * 80
        with mock.patch.object(rotate_key.imagecrypt, "encrypt",
                               lambda key, blob: bad):
            report = rotate_key.rotate(self.data, NEW, OLD)
        self.assertEqual(report["rotated"], 0)
        self.assertEqual(len(report["failed"]), 1)
        self.assertEqual(self._bytes(self.ref), sealed)
        self.assertEqual(self._read_with(OLD), JPEG)


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = os.path.join(self.tmp.name, "data")
        store = ingest.Store(self.data, image_key=OLD)
        store.store_image("MOD000-1", 1, JPEG)

    def tearDown(self):
        self.tmp.cleanup()

    def test_fails_while_a_frame_is_still_on_the_old_key(self):
        report = rotate_key.verify(self.data, NEW)
        self.assertEqual(report["verified"], 0)
        self.assertEqual(len(report["failed"]), 1)

    def test_passes_after_rotation(self):
        rotate_key.rotate(self.data, NEW, OLD)
        report = rotate_key.verify(self.data, NEW)
        self.assertEqual(report["verified"], 1)
        self.assertEqual(report["failed"], [])

    def test_reports_a_hash_mismatch(self):
        rotate_key.rotate(self.data, NEW, OLD)
        store = ingest.Store(self.data, image_key=NEW)
        with store._conn() as conn:
            conn.execute("UPDATE images SET integrity_hash=?", ("00" * 32,))
        self.assertEqual(len(rotate_key.verify(self.data, NEW)["failed"]), 1)


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = os.path.join(self.tmp.name, "data")
        ingest.Store(self.data, image_key=OLD).store_image(
            "MOD000-1", 1, JPEG)

    def tearDown(self):
        self.tmp.cleanup()

    def env(self, new=NEW, old=OLD):
        values = {"IMAGE_KEY": new.hex() if new else ""}
        if old:
            values[rotate_key.PREVIOUS_KEY_ENV] = old.hex()
        return mock.patch.dict(os.environ, values)

    def test_requires_the_new_key(self):
        with self.env(new=None):
            self.assertEqual(rotate_key.main(["--data-dir", self.data]), 2)

    def test_successful_rotation_exits_zero(self):
        with self.env():
            self.assertEqual(rotate_key.main(["--data-dir", self.data]), 0)
        self.assertEqual(rotate_key.verify(self.data, NEW)["verified"], 1)

    def test_missing_old_key_exits_one(self):
        with self.env(old=None):
            self.assertEqual(rotate_key.main(["--data-dir", self.data]), 1)

    def test_verify_only_fails_before_rotation(self):
        with self.env():
            self.assertEqual(
                rotate_key.main(["--data-dir", self.data,
                                 "--verify-only"]), 1)

    def test_verify_only_passes_after_rotation(self):
        rotate_key.rotate(self.data, NEW, OLD)
        with self.env():
            self.assertEqual(
                rotate_key.main(["--data-dir", self.data,
                                 "--verify-only"]), 0)

    def test_verify_only_needs_no_previous_key(self):
        rotate_key.rotate(self.data, NEW, OLD)
        with self.env(old=None):
            self.assertEqual(
                rotate_key.main(["--data-dir", self.data,
                                 "--verify-only"]), 0)

    def test_dry_run_and_verify_only_are_exclusive(self):
        with self.env(), self.assertRaises(SystemExit):
            rotate_key.main(["--data-dir", self.data,
                             "--dry-run", "--verify-only"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
