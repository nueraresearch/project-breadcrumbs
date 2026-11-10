#!/usr/bin/env python3
"""Tests for frame encryption at rest. Standard library only."""

import os
import tempfile
import unittest

import imagecrypt
import ingest

KEY = bytes.fromhex("ab" * 32)
OTHER = bytes.fromhex("cd" * 32)

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200 + b"\xff\xd9"


class RoundTripTests(unittest.TestCase):
    def test_round_trip(self):
        sealed = imagecrypt.encrypt(KEY, JPEG)
        self.assertEqual(imagecrypt.decrypt(KEY, sealed), JPEG)

    def test_plaintext_is_not_in_the_ciphertext(self):
        sealed = imagecrypt.encrypt(KEY, JPEG)
        self.assertNotIn(JPEG, sealed)
        self.assertNotIn(b"\xff\xd8\xff\xe0", sealed)
        self.assertTrue(imagecrypt.is_encrypted(sealed))

    def test_same_frame_encrypts_differently_each_time(self):
        # A fresh nonce per frame: equal ciphertexts would leak that two
        # modules captured the same nothing.
        a = imagecrypt.encrypt(KEY, JPEG)
        b = imagecrypt.encrypt(KEY, JPEG)
        self.assertNotEqual(a, b)
        self.assertEqual(imagecrypt.decrypt(KEY, a),
                         imagecrypt.decrypt(KEY, b))

    def test_empty_frame(self):
        sealed = imagecrypt.encrypt(KEY, b"")
        self.assertEqual(imagecrypt.decrypt(KEY, sealed), b"")

    def test_large_frame(self):
        blob = os.urandom(64 * 1024)
        self.assertEqual(imagecrypt.decrypt(KEY, imagecrypt.encrypt(KEY, blob)),
                         blob)


class RejectionTests(unittest.TestCase):
    def test_wrong_key_is_refused(self):
        sealed = imagecrypt.encrypt(KEY, JPEG)
        with self.assertRaises(imagecrypt.CryptoError):
            imagecrypt.decrypt(OTHER, sealed)

    def test_tampering_is_refused(self):
        sealed = bytearray(imagecrypt.encrypt(KEY, JPEG))
        sealed[-1] ^= 0x01
        with self.assertRaises(imagecrypt.CryptoError):
            imagecrypt.decrypt(KEY, bytes(sealed))

    def test_tampering_with_the_nonce_is_refused(self):
        sealed = bytearray(imagecrypt.encrypt(KEY, JPEG))
        sealed[6] ^= 0xFF
        with self.assertRaises(imagecrypt.CryptoError):
            imagecrypt.decrypt(KEY, bytes(sealed))

    def test_truncation_is_refused(self):
        sealed = imagecrypt.encrypt(KEY, JPEG)
        with self.assertRaises(imagecrypt.CryptoError):
            imagecrypt.decrypt(KEY, sealed[:20])

    def test_plain_jpeg_is_not_accepted_as_ciphertext(self):
        with self.assertRaises(imagecrypt.CryptoError):
            imagecrypt.decrypt(KEY, JPEG)


class KeyTests(unittest.TestCase):
    def test_missing_key_is_reported(self):
        self.assertIsNone(imagecrypt.key_from_env({}))
        with self.assertRaises(imagecrypt.MissingKey):
            imagecrypt.parse_key("")

    def test_short_key_is_refused(self):
        with self.assertRaises(imagecrypt.CryptoError):
            imagecrypt.parse_key("00" * 16)

    def test_non_hex_key_is_refused(self):
        with self.assertRaises(imagecrypt.CryptoError):
            imagecrypt.parse_key("z" * 64)

    def test_valid_key_parses(self):
        key = imagecrypt.parse_key("00" * 32)
        self.assertEqual(len(key), 32)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = os.path.join(self.tmp.name, "data")

    def tearDown(self):
        self.tmp.cleanup()

    def test_store_refuses_without_a_key(self):
        # Fail closed: no key must not mean plaintext faces on disk.
        store = ingest.Store(self.data)
        with self.assertRaises(imagecrypt.MissingKey):
            store.store_image("MOD000-1", 1, JPEG)

    def test_stored_file_is_ciphertext(self):
        store = ingest.Store(self.data, image_key=KEY)
        digest = store.store_image("MOD000-2", 1, JPEG)

        path = os.path.join(store.image_dir, "MOD000-2_01.jpg.enc")
        raw = open(path, "rb").read()
        self.assertTrue(imagecrypt.is_encrypted(raw))
        self.assertNotIn(JPEG, raw)
        self.assertEqual(digest, __import__("hashlib").sha256(JPEG).hexdigest())

    def test_read_image_returns_the_original(self):
        store = ingest.Store(self.data, image_key=KEY)
        store.store_image("MOD000-3", 2, JPEG)
        self.assertEqual(store.read_image("MOD000-3_02.jpg.enc", None), JPEG)

    def test_read_image_checks_the_recorded_hash(self):
        store = ingest.Store(self.data, image_key=KEY)
        store.store_image("MOD000-4", 1, JPEG)
        with self.assertRaises(imagecrypt.CryptoError):
            store.read_image("MOD000-4_01.jpg.enc", "00" * 32)


if __name__ == "__main__":
    unittest.main(verbosity=2)
