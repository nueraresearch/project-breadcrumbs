#!/usr/bin/env python3
"""Project Breadcrumbs — rotate the image encryption key.

Frames are sealed under `IMAGE_KEY`. Changing that value without touching the
stored files makes every one of them unreadable, so rotation is a re-encryption
job rather than a configuration change: each frame is decrypted with whatever
key currently opens it, checked against the SHA-256 already recorded, sealed
under the new key, and written back over the old file.

**Why a batch tool instead of a previous key the server accepts.** Teaching the
read path to try a retired key would keep that key valid for as long as it sits
in the environment — possibly forever, because nothing forces anyone to remove
it. Rotation that must finish, and ends with a check that the new key alone
opens every frame, makes dropping the old key an explicit step with evidence.

**Nothing else changes.** File names, `secure_object_ref`, `integrity_hash` and
`bytes` all stay as they are, because the plaintext does not change. Only the
key that opens the ciphertext does.

**Interruptions are safe.** Each frame is written to a temporary file in the
same directory, read back, decrypted and compared with the recorded hash, and
only then renamed over the original. A crash leaves that frame under the old
key, never half-written and never under a key nobody has. Re-running continues
from wherever it stopped; a frame already on the new key is verified and left
alone.

**Stop the ingest server first.** It rewrites files the server would be
reading, and a re-upload landing mid-run would be sealed under whatever key the
server was started with.

Usage:
    export IMAGE_KEY=<new key>            # what the server will run with
    export IMAGE_KEY_PREVIOUS=<old key>   # only for the rotation run

    python3 rotate_key.py --data-dir data --dry-run
    python3 rotate_key.py --data-dir data

    # prove the old key is no longer needed, then remove it
    python3 rotate_key.py --data-dir data --verify-only
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import sys
import tempfile

import imagecrypt

PREVIOUS_KEY_ENV = "IMAGE_KEY_PREVIOUS"


def key_from(env, name=imagecrypt.KEY_ENV):
    value = (env or os.environ).get(name, "")
    if not value.strip():
        return None
    return imagecrypt.parse_key(value, name)


def _resolve(image_dir: str, ref: str) -> str:
    """Same guard as migrate_images.py: a row must not point outside."""
    if (not ref or os.path.isabs(ref) or os.path.basename(ref) != ref
            or ref in (".", "..")):
        raise ValueError("reference would leave the image directory")
    return os.path.join(image_dir, ref)


def _write_verified(path: str, sealed: bytes, key: bytes,
                    digest: str) -> None:
    """Writes beside the original, proves it decrypts, then replaces it.

    The rename is the last step on purpose: until it happens the frame is
    still under the key it was already under, so a failure anywhere above
    loses nothing.
    """
    directory = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".part")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(sealed)
            fh.flush()
            os.fsync(fh.fileno())
        with open(tmp, "rb") as fh:
            back = imagecrypt.decrypt(key, fh.read())
        if hashlib.sha256(back).hexdigest() != digest:
            raise imagecrypt.CryptoError(
                "written frame does not decrypt to the original")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _rows(data_dir):
    data_dir = os.path.abspath(data_dir)
    image_dir = os.path.join(data_dir, "images")
    db_path = os.path.join(data_dir, "records.db")
    if not os.path.isdir(image_dir):
        raise FileNotFoundError(f"no image directory at {image_dir}")
    if not os.path.isfile(db_path):
        raise FileNotFoundError(f"no records.db at {db_path}")
    return data_dir, image_dir, db_path


def _each_frame(image_dir, rows):
    """Yields (label, ref, path, expected_hash, blob) or a problem tuple."""
    for row in rows:
        label = f"{row['record_id']}[{row['frame_index']}]"
        ref = (row["secure_object_ref"] or "").strip()
        expected = row["integrity_hash"] or ""
        try:
            path = _resolve(image_dir, ref)
        except ValueError as exc:
            yield label, ref, None, expected, None, str(exc)
            continue
        if not os.path.isfile(path):
            yield label, ref, path, expected, None, None
            continue
        with open(path, "rb") as fh:
            yield label, ref, path, expected, fh.read(), None


def rotate(data_dir: str, new_key: bytes, old_key: bytes | None = None, *,
           dry_run: bool = False) -> dict:
    """Re-encrypts every frame under `new_key`. Returns a report."""
    data_dir, image_dir, db_path = _rows(data_dir)
    report = {"rotated": 0, "already_new": 0, "missing": [], "failed": [],
              "need_previous": []}

    conn = sqlite3.connect(db_path, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT record_id, frame_index, secure_object_ref, integrity_hash"
            " FROM images ORDER BY record_id, frame_index").fetchall()
    finally:
        conn.close()

    for label, ref, path, expected, blob, problem in _each_frame(image_dir, rows):
        if problem:
            report["failed"].append((label, f"{ref!r}: {problem}"))
            continue
        if blob is None:
            report["missing"].append((label, ref))
            continue

        if not imagecrypt.is_encrypted(blob):
            report["failed"].append(
                (label, f"{ref}: not encrypted; run migrate_images.py first"))
            continue

        plain = None
        which = None
        try:
            plain = imagecrypt.decrypt(new_key, blob)
            which = "new"
        except imagecrypt.CryptoError:
            pass

        if plain is None and old_key is not None:
            try:
                plain = imagecrypt.decrypt(old_key, blob)
                which = "old"
            except imagecrypt.CryptoError:
                pass

        if plain is None:
            if old_key is None:
                report["need_previous"].append(
                    (label, f"{ref}: opens with neither the current key nor "
                            f"any key given; {PREVIOUS_KEY_ENV} is not set"))
            else:
                report["failed"].append(
                    (label, f"{ref}: opens with neither key"))
            continue

        # The hash is the invariant rotation must preserve: it is what proves
        # the plaintext survived the trip. A frame that no longer matches it
        # is left under the key it already has rather than re-sealed into
        # something that looks verified.
        digest = hashlib.sha256(plain).hexdigest()
        if expected and digest != expected:
            report["failed"].append(
                (label, f"{ref}: plaintext does not match the recorded hash; "
                        f"left as it was"))
            continue

        if which == "new":
            report["already_new"] += 1
            continue

        if dry_run:
            report["rotated"] += 1
            continue

        try:
            _write_verified(path, imagecrypt.encrypt(new_key, plain),
                            new_key, digest)
        except (OSError, imagecrypt.CryptoError) as exc:
            report["failed"].append(
                (label, f"{ref}: {exc}; still under the old key"))
            continue

        report["rotated"] += 1

    return report


def verify(data_dir: str, key: bytes) -> dict:
    """Checks that `key` alone opens every frame, without changing anything."""
    data_dir, image_dir, db_path = _rows(data_dir)
    report = {"verified": 0, "missing": [], "failed": []}

    conn = sqlite3.connect(db_path, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT record_id, frame_index, secure_object_ref, integrity_hash"
            " FROM images ORDER BY record_id, frame_index").fetchall()
    finally:
        conn.close()

    for label, ref, path, expected, blob, problem in _each_frame(image_dir, rows):
        if problem:
            report["failed"].append((label, f"{ref!r}: {problem}"))
            continue
        if blob is None:
            report["missing"].append((label, ref))
            continue
        if not imagecrypt.is_encrypted(blob):
            report["failed"].append(
                (label, f"{ref}: not encrypted; run migrate_images.py first"))
            continue
        try:
            plain = imagecrypt.decrypt(key, blob)
        except imagecrypt.CryptoError as exc:
            report["failed"].append(
                (label, f"{ref}: does not open with the current key ({exc})"))
            continue
        if expected and hashlib.sha256(plain).hexdigest() != expected:
            report["failed"].append(
                (label, f"{ref}: opens but does not match its recorded hash"))
            continue
        report["verified"] += 1

    return report


def _print_list(title, items):
    if not items:
        return
    print(f"\n  {title}:")
    for first, second in items:
        print(f"    {first}  {second}")


def _print_rotation(report, data_dir, dry_run):
    verb = "would rotate" if dry_run else "rotated"
    print(f"Image key rotation — {os.path.abspath(data_dir)}")
    if dry_run:
        print("  dry run: nothing is written")
    print(f"  {verb:<19}{report['rotated']}")
    print(f"  {'already on the new key':<19}{report['already_new']}")
    print(f"  {'missing':<19}{len(report['missing'])}")
    print(f"  {'need the old key':<19}{len(report['need_previous'])}")
    print(f"  {'failed':<19}{len(report['failed'])}")
    _print_list("need the old key", report["need_previous"])
    _print_list("missing", report["missing"])
    _print_list("failed", report["failed"])
    if report["rotated"] and not dry_run:
        print("\n  Run --verify-only with only the new key before retiring the "
              "old one.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Re-encrypt stored frames under a new IMAGE_KEY.")
    ap.add_argument("--data-dir",
                    default=os.environ.get("INGEST_DATA", "data"))
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true",
                       help="report what would rotate, change nothing")
    group.add_argument("--verify-only", action="store_true",
                       help="check the current key opens every frame")
    args = ap.parse_args(argv)

    try:
        new_key = key_from(os.environ)
        old_key = key_from(os.environ, PREVIOUS_KEY_ENV)
    except imagecrypt.CryptoError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if new_key is None:
        print(f"error: {imagecrypt.KEY_ENV} is not set; it must hold the key "
              f"the server will use.", file=sys.stderr)
        return 2

    try:
        if args.verify_only:
            report = verify(args.data_dir, new_key)
            print(f"Key check — {os.path.abspath(args.data_dir)}")
            print(f"  {'verified':<12}{report['verified']}")
            print(f"  {'missing':<12}{len(report['missing'])}")
            print(f"  {'failed':<12}{len(report['failed'])}")
            _print_list("missing", report["missing"])
            _print_list("failed", report["failed"])
            if report["failed"] or report["missing"]:
                print(f"\n  Not every frame opens with the current "
                      f"{imagecrypt.KEY_ENV}; do not retire the old key yet.")
                return 1
            print(f"\n  Every stored frame opens with the current "
                  f"{imagecrypt.KEY_ENV} and matches its recorded hash.")
            return 0

        if old_key is not None and old_key == new_key:
            print(f"warning: {PREVIOUS_KEY_ENV} equals {imagecrypt.KEY_ENV}; "
                  f"there is nothing to rotate.", file=sys.stderr)

        report = rotate(args.data_dir, new_key, old_key,
                        dry_run=args.dry_run)
    except (OSError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _print_rotation(report, args.data_dir, args.dry_run)

    if report["failed"] or report["missing"] or report["need_previous"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
