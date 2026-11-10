#!/usr/bin/env python3
"""Tests for the plaintext-to-encrypted frame migration."""

import hashlib
import os
import tempfile
import unittest
from unittest import mock

import imagecrypt
import ingest
import migrate_images

KEY = bytes.fromhex("ab" * 32)
OTHER = bytes.fromhex("cd" * 32)

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200 + b"\xff\xd9"
OTHER_JPEG = b"\xff\xd8\xff\xe0" + b"\x11" * 200 + b"\xff\xd9"


def legacy_frame(data_dir, record_id, frame, blob, key=KEY,
                 hash_override=None):
    """A directory as it looked before frames were encrypted."""
    store = ingest.Store(data_dir, image_key=key)
    name = f"{record_id}_{frame:02d}.jpg"
    path = os.path.join(store.image_dir, name)
    with open(path, "wb") as fh:
        fh.write(blob)

    with store._conn() as conn:
        conn.execute(
            "INSERT INTO images (record_id, frame_index, image_id,"
            " secure_object_ref, integrity_hash, bytes, uploaded_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (record_id, frame, f"{record_id}-{frame}", name,
             hash_override if hash_override is not None
             else hashlib.sha256(blob).hexdigest(),
             len(blob), ingest.utcnow()))
    return store, name


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = os.path.join(self.tmp.name, "data")
        self.store, self.name = legacy_frame(self.data, "MOD000-1", 1, JPEG)

    def tearDown(self):
        self.tmp.cleanup()

    def _ref(self):
        return self.store.get_record  # placeholder, unused

    def _stored_ref(self, record_id="MOD000-1", frame=1):
        with self.store._conn() as conn:
            row = conn.execute(
                "SELECT secure_object_ref FROM images"
                " WHERE record_id=? AND frame_index=?",
                (record_id, frame)).fetchone()
        return row["secure_object_ref"]

    def test_plaintext_frame_is_encrypted_and_repointed(self):
        report = migrate_images.migrate(self.data, KEY)
        self.assertEqual(report["migrated"], 1)
        self.assertEqual(report["failed"], [])
        # A migrated frame is referenced, not orphaned: the orphan scan has to
        # see the references as they are after the loop, not before it.
        self.assertEqual(report["orphans"], [])

        ref = self._stored_ref()
        self.assertTrue(ref.endswith(".jpg.enc"))
        self.assertFalse(os.path.exists(
            os.path.join(self.store.image_dir, self.name)))

        raw = open(os.path.join(self.store.image_dir, ref), "rb").read()
        self.assertTrue(imagecrypt.is_encrypted(raw))
        self.assertNotIn(JPEG, raw)

    def test_migrated_frame_reads_back_through_the_store(self):
        migrate_images.migrate(self.data, KEY)
        self.assertEqual(self.store.read_image(self._stored_ref()), JPEG)

    def test_second_run_verifies_instead_of_rewriting(self):
        migrate_images.migrate(self.data, KEY)
        ref = self._stored_ref()
        before = open(os.path.join(self.store.image_dir, ref), "rb").read()

        report = migrate_images.migrate(self.data, KEY)
        self.assertEqual(report["migrated"], 0)
        self.assertEqual(report["verified"], 1)
        after = open(os.path.join(self.store.image_dir, ref), "rb").read()
        self.assertEqual(before, after)

    def test_dry_run_changes_nothing(self):
        report = migrate_images.migrate(self.data, KEY, dry_run=True)
        self.assertEqual(report["migrated"], 1)
        self.assertEqual(self._stored_ref(), self.name)
        self.assertTrue(os.path.exists(
            os.path.join(self.store.image_dir, self.name)))

    def test_hash_mismatch_is_refused(self):
        # The recorded hash is the only fact that predates the migration. A
        # frame that no longer matches it must not be sealed and repointed.
        store, name = legacy_frame(self.data, "MOD000-2", 2, OTHER_JPEG,
                                   hash_override="00" * 32)
        report = migrate_images.migrate(self.data, KEY)
        self.assertEqual(len(report["failed"]), 1)
        self.assertIn("MOD000-2[2]", report["failed"][0][0])
        self.assertTrue(os.path.exists(os.path.join(store.image_dir, name)))

    def test_missing_file_is_reported(self):
        store, name = legacy_frame(self.data, "MOD000-3", 1, JPEG)
        os.unlink(os.path.join(store.image_dir, name))
        report = migrate_images.migrate(self.data, KEY)
        self.assertEqual(len(report["missing"]), 1)

    def test_plaintext_can_be_kept_on_request(self):
        report = migrate_images.migrate(self.data, KEY, keep_plaintext=True)
        self.assertEqual(report["kept_plaintext"], 1)
        self.assertTrue(os.path.exists(
            os.path.join(self.store.image_dir, self.name)))
        self.assertTrue(self._stored_ref().endswith(".jpg.enc"))

    def test_orphan_plaintext_is_left_alone(self):
        orphan = os.path.join(self.store.image_dir, "MOD999-9_01.jpg")
        with open(orphan, "wb") as fh:
            fh.write(JPEG)
        report = migrate_images.migrate(self.data, KEY)
        self.assertTrue(any("MOD999-9_01.jpg" == o[0]
                            for o in report["orphans"]))
        self.assertTrue(os.path.exists(orphan))

    def test_reference_outside_the_image_directory_is_refused(self):
        with self.store._conn() as conn:
            conn.execute(
                "UPDATE images SET secure_object_ref='../escape.jpg'"
                " WHERE record_id='MOD000-1'")
        report = migrate_images.migrate(self.data, KEY)
        self.assertTrue(any("leave the image directory" in f[1]
                            for f in report["failed"]))

    def test_frame_encrypted_under_another_key_is_reported(self):
        store = ingest.Store(self.data, image_key=OTHER)
        store.store_image("MOD000-4", 1, JPEG)
        report = migrate_images.migrate(self.data, KEY)
        self.assertTrue(any("MOD000-4[1]" == f[0] for f in report["failed"]))

    def test_plaintext_that_is_not_a_jpeg_is_refused(self):
        store, name = legacy_frame(self.data, "MOD000-5", 1, b"not a frame")
        report = migrate_images.migrate(self.data, KEY)
        self.assertTrue(any("neither ciphertext nor a JPEG" in f[1]
                            for f in report["failed"]))
        self.assertTrue(os.path.exists(os.path.join(store.image_dir, name)))


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = os.path.join(self.tmp.name, "data")
        self.store, self.name = legacy_frame(self.data, "MOD000-1", 1, JPEG)

    def tearDown(self):
        self.tmp.cleanup()

    def test_refuses_without_a_key(self):
        with mock.patch.dict(os.environ, {"IMAGE_KEY": ""}):
            self.assertEqual(
                migrate_images.main(["--data-dir", self.data]), 2)
        # Fail closed: nothing was rewritten.
        self.assertTrue(os.path.exists(
            os.path.join(self.store.image_dir, self.name)))

    def test_successful_run_exits_zero(self):
        with mock.patch.dict(os.environ, {"IMAGE_KEY": KEY.hex()}):
            self.assertEqual(
                migrate_images.main(["--data-dir", self.data]), 0)

    def test_failure_exits_one(self):
        with mock.patch.dict(os.environ, {"IMAGE_KEY": KEY.hex()}):
            os.unlink(os.path.join(self.store.image_dir, self.name))
            self.assertEqual(
                migrate_images.main(["--data-dir", self.data]), 1)

    def test_a_missing_data_directory_is_a_configuration_error(self):
        with mock.patch.dict(os.environ, {"IMAGE_KEY": KEY.hex()}):
            self.assertEqual(migrate_images.main(
                ["--data-dir", os.path.join(self.tmp.name, "nope")]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
