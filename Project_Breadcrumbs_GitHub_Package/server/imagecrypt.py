#!/usr/bin/env python3
"""Project Breadcrumbs — image encryption at rest.

A module sits on a porch and photographs whatever opened the package. Those
frames are the most sensitive thing this project holds, and until now they sat
on the ingest machine as ordinary JPEGs. A stolen laptop, a copied backup
directory, or a decommissioned disk would have exposed them.

**Why not a library.** The ingest server is dependency-free on purpose: it runs
on a borrowed machine and has no lockfile to rot. `cryptography` would be the
usual answer and it is not available here, so this module builds a stream
cipher from SHA-256 and authenticates with HMAC-SHA256, both from the standard
library. That is a well-understood construction — hash the key, a nonce and a
counter to produce keystream, XOR, then authenticate the whole thing — but it
is not AES and it has not been reviewed by anyone. If a dependency becomes
acceptable, replace this file rather than extend it.

**Encrypt, then authenticate.** The tag covers the header and the ciphertext,
and decryption verifies it before producing a single plaintext byte. A wrong
key and a corrupted file are therefore indistinguishable, which is the point:
neither yields output.

**What this does and does not protect.** The key comes from `IMAGE_KEY` in the
environment. If the key is stored beside the data — in the same git checkout,
on the same disk, in a note taped to the laptop — then this protects nothing
against a stolen machine, because the thief has both halves. It protects
against a copy of the data directory: a backup, a synced folder, a disk that
went out for repair, an old disk that was not wiped. Whole-disk encryption
covers theft; this covers the copies nobody remembers exist.

**Losing the key destroys the frames.** There is no recovery path, and that
includes frames under legal hold. The key belongs in the project's password
manager, with a second copy wherever the deployment credentials are kept.

Format, versioned so a later change is detectable rather than mistaken for
corruption:

    magic "BCRY1" | nonce (16) | ciphertext | tag (32)

Usage:
    python3 -c "import secrets; print(secrets.token_hex(32))"   # make a key
    export IMAGE_KEY=<64 hex characters>
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

MAGIC = b"BCRY1"
KEY_ENV = "IMAGE_KEY"
KEY_BYTES = 32
NONCE_BYTES = 16
MAC_BYTES = 32


class CryptoError(Exception):
    pass


class MissingKey(CryptoError):
    pass


def parse_key(text: str) -> bytes:
    text = (text or "").strip()
    if not text:
        raise MissingKey(f"{KEY_ENV} is not set")
    try:
        key = bytes.fromhex(text)
    except ValueError:
        raise CryptoError(f"{KEY_ENV} must be hexadecimal")
    if len(key) != KEY_BYTES:
        raise CryptoError(
            f"{KEY_ENV} must be {KEY_BYTES} bytes "
            f"({KEY_BYTES * 2} hex characters), got {len(key)}")
    return key


def key_from_env(env=None):
    """The configured key, or None when none is set.

    A malformed key raises rather than returning None: silently treating a
    typo as "no key" would either refuse every upload or, worse, be papered
    over later by a fallback.
    """
    value = (env or os.environ).get(KEY_ENV, "")
    if not value.strip():
        return None
    return parse_key(value)


def _subkeys(key: bytes):
    # Separate keys for the keystream and the tag, so the same primitive is
    # never asked to both hide the plaintext and prove the ciphertext intact.
    enc = hashlib.sha256(b"breadcrumbs-enc\x00" + key).digest()
    mac = hashlib.sha256(b"breadcrumbs-mac\x00" + key).digest()
    return enc, mac


def _keystream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out += hashlib.sha256(
            enc_key + nonce + counter.to_bytes(8, "big")).digest()
        counter += 1
    return bytes(out[:length])


def _xor(data: bytes, stream: bytes) -> bytes:
    if not data:
        return b""
    # Big-integer XOR: one operation instead of a Python loop per byte. Frames
    # are up to 4 MiB, which is comfortable at this size.
    n = len(data)
    return (int.from_bytes(data, "big")
            ^ int.from_bytes(stream[:n], "big")).to_bytes(n, "big")


def is_encrypted(blob: bytes) -> bool:
    return blob.startswith(MAGIC)


def encrypt(key: bytes, plaintext: bytes) -> bytes:
    enc_key, mac_key = _subkeys(key)
    nonce = secrets.token_bytes(NONCE_BYTES)
    body = MAGIC + nonce + _xor(plaintext,
                                _keystream(enc_key, nonce, len(plaintext)))
    tag = hmac.new(mac_key, body, hashlib.sha256).digest()
    return body + tag


def decrypt(key: bytes, blob: bytes) -> bytes:
    # Checked before the length, so a plaintext frame from an older data
    # directory gets the actionable message rather than "truncated".
    if not is_encrypted(blob):
        raise CryptoError(
            "not an encrypted frame; a data directory written before "
            "encryption was enabled needs migrate_images.py")
    if len(blob) < len(MAGIC) + NONCE_BYTES + MAC_BYTES:
        raise CryptoError("ciphertext is truncated")

    body, tag = blob[:-MAC_BYTES], blob[-MAC_BYTES:]
    enc_key, mac_key = _subkeys(key)
    expected = hmac.new(mac_key, body, hashlib.sha256).digest()

    # Verified before decryption, so a wrong key cannot produce output that
    # something downstream might treat as a photograph.
    if not hmac.compare_digest(tag, expected):
        raise CryptoError(
            "frame failed its authentication check (wrong key or altered file)")

    nonce = body[len(MAGIC):len(MAGIC) + NONCE_BYTES]
    ciphertext = body[len(MAGIC) + NONCE_BYTES:]
    return _xor(ciphertext, _keystream(enc_key, nonce, len(ciphertext)))
