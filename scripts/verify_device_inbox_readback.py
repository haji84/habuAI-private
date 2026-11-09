#!/usr/bin/env python3
"""Read-only verifier for a Google Drive-downloaded HABU native inbox original.

The caller downloads only authenticated ciphertext to a trusted private volume,
then runs this *offline* using the receiver's private X25519 key in the runtime
environment. The key and decrypted GPS are never written, printed or uploaded.
This does NOT prove the file actually arrived in Drive: remote metadata/readback
must separately establish that.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import uuid

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

VERSION = "habu-device-inbox-v1"
PAYLOAD_VERSION = "habu-device-original-v1"
ALGORITHM = "X25519-HKDF-SHA256-AES-256-GCM"
AAD_PREFIX = b"HABU-DEVICE-INBOX-V1|"
MAX_ORIGINAL = 18 * 1024 * 1024
MAX_ENVELOPE = 38 * 1024 * 1024
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class InboxVerificationError(ValueError):
    """Fixed failure code, never source content, owner details or private paths."""


def _blocked(reason: str) -> None:
    raise InboxVerificationError(reason)


def _b64(value: object, expected: int | None = None) -> bytes:
    if not isinstance(value, str):
        _blocked("INVALID_ENVELOPE")
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        _blocked("INVALID_ENVELOPE")
    if expected is not None and len(data) != expected:
        _blocked("INVALID_ENVELOPE")
    return data


def _json(raw: bytes, code: str) -> dict:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        _blocked(code)
    if not isinstance(data, dict):
        _blocked(code)
    return data


def verify_ciphertext(ciphertext: bytes, private_key_raw: bytes, *,
                      expected_source_sha256: str | None = None,
                      expected_session_id: str | None = None) -> dict:
    """Verify package integrity, and optionally an independently obtained origin.

    A payload's own digest is not evidence of which phone original was sent.
    Expected values must come from the phone's saved original, never from this
    downloaded package. This still does not prove remote Google Drive arrival.
    """
    independent = expected_source_sha256 is not None or expected_session_id is not None
    if independent:
        try:
            if (not isinstance(expected_source_sha256, str)
                    or not HEX64.fullmatch(expected_source_sha256)
                    or not isinstance(expected_session_id, str)
                    or str(uuid.UUID(expected_session_id)) != expected_session_id):
                _blocked("EXPECTED_SOURCE_IDENTITY_INVALID")
        except (ValueError, AttributeError, TypeError):
            _blocked("EXPECTED_SOURCE_IDENTITY_INVALID")
    if not isinstance(ciphertext, bytes) or not 0 < len(ciphertext) <= MAX_ENVELOPE:
        _blocked("CIPHERTEXT_SIZE_INVALID")
    if not isinstance(private_key_raw, bytes) or len(private_key_raw) != 32:
        _blocked("KEY_INVALID")

    package = _json(ciphertext, "INVALID_ENVELOPE")
    if set(package) != {
        "schema_version", "algorithm", "recipient_key_id",
        "ephemeral_public_key_b64", "hkdf_salt_b64",
        "nonce_b64", "ciphertext_b64"
    } or package["schema_version"] != VERSION or package["algorithm"] != ALGORITHM:
        _blocked("INVALID_ENVELOPE")
    try:
        private_key = X25519PrivateKey.from_private_bytes(private_key_raw)
        public = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        key_id = hashlib.sha256(public).digest()[:8].hex()
        if package["recipient_key_id"] != key_id:
            _blocked("KEY_ID_MISMATCH")
        ephemeral = X25519PublicKey.from_public_bytes(
            _b64(package["ephemeral_public_key_b64"], 32)
        )
        salt = _b64(package["hkdf_salt_b64"], 32)
        nonce = _b64(package["nonce_b64"], 12)
        encrypted = _b64(package["ciphertext_b64"])
        if not 16 < len(encrypted) <= MAX_ENVELOPE:
            _blocked("CIPHERTEXT_SIZE_INVALID")
        aad = AAD_PREFIX + key_id.encode("ascii")
        key = HKDF(
            algorithm=hashes.SHA256(), length=32, salt=salt, info=aad
        ).derive(private_key.exchange(ephemeral))
        opened = AESGCM(key).decrypt(nonce, encrypted, aad)
    except InboxVerificationError:
        raise
    except Exception:
        _blocked("AUTHENTICATION_FAILED")

    # Decrypted content never enters stdout, disk or a public artifact.
    payload = _json(opened, "INVALID_PRIVATE_PAYLOAD")
    if set(payload) != {
        "schema_version", "session_id", "source_sha256", "raw_jsonl_b64"
    } or payload["schema_version"] != PAYLOAD_VERSION:
        _blocked("INVALID_PRIVATE_PAYLOAD")
    try:
        session_id = payload["session_id"]
        parsed_id = uuid.UUID(session_id)
        if session_id != str(parsed_id):
            _blocked("INVALID_PRIVATE_PAYLOAD")
        expected_sha = payload["source_sha256"]
        if not isinstance(expected_sha, str) or not HEX64.fullmatch(expected_sha):
            _blocked("INVALID_PRIVATE_PAYLOAD")
    except (ValueError, AttributeError, TypeError):
        _blocked("INVALID_PRIVATE_PAYLOAD")
    raw = _b64(payload["raw_jsonl_b64"])
    if not 0 < len(raw) <= MAX_ORIGINAL or not raw.endswith(b"\n"):
        _blocked("INVALID_PRIVATE_SOURCE")
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        _blocked("SOURCE_SHA_MISMATCH")
    try:
        lines = raw.splitlines()
        if len(lines) < 2:
            _blocked("INVALID_PRIVATE_SOURCE")
        rows = [_json(line, "INVALID_PRIVATE_SOURCE") for line in lines]
        if rows[0].get("kind") != "start" or rows[-1].get("kind") != "stop":
            _blocked("INCOMPLETE_SESSION")
        start, stop = rows[0].get("time"), rows[-1].get("time")
        if any(
            not isinstance(t, (int, float)) or isinstance(t, bool)
            or not math.isfinite(t)
            for t in (start, stop)
        ) or stop < start:
            _blocked("INVALID_PRIVATE_SOURCE")
        kinds = {"start", "stop", "fix", "gap", "event", "condition"}
        for row in rows:
            if row.get("kind") not in kinds:
                _blocked("INVALID_PRIVATE_SOURCE")
            t = row.get("time")
            if not isinstance(t, (int, float)) or isinstance(t, bool) or not math.isfinite(t):
                _blocked("INVALID_PRIVATE_SOURCE")
    except InboxVerificationError:
        raise
    except (ValueError, UnicodeError, TypeError):
        _blocked("INVALID_PRIVATE_SOURCE")

    if independent:
        if expected_source_sha256 != expected_sha:
            _blocked("EXPECTED_SOURCE_SHA_MISMATCH")
        if expected_session_id != session_id:
            _blocked("EXPECTED_SESSION_MISMATCH")

    return {
        "status": ("PRIVATE_DECRYPT_AND_SOURCE_SHA_PASS" if independent
                   else "PRIVATE_PACKAGE_INTEGRITY_PASS"),
        "independent_original_matched": independent,
        "drive_arrival_verified": False,
        "source_closed": True,
        "encrypted_package_authenticated": True,
        "plaintext_written": False,
        "gps_exposed": False,
    }


def verify_local_file(path: Path, *, expected_source_sha256: str | None = None,
                      expected_session_id: str | None = None) -> dict:
    raw_key = os.environ.get("HABU_DEVICE_INBOX_PRIVATE_KEY_B64")
    if not raw_key:
        _blocked("KEY_REQUIRED_IN_PRIVATE_RUNTIME")
    try:
        key = base64.b64decode(raw_key, validate=True)
    except (ValueError, binascii.Error):
        _blocked("KEY_INVALID")
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_ENVELOPE:
        _blocked("FILE_UNAVAILABLE_OR_OVERSIZE")
    return verify_ciphertext(path.read_bytes(), key,
                             expected_source_sha256=expected_source_sha256,
                             expected_session_id=expected_session_id)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline-only encrypted Habu inbox readback")
    parser.add_argument("encrypted_file", type=Path, help="Privately downloaded .habuenc file")
    parser.add_argument("--expected-source-sha256", help="SHA-256 independently read from phone original")
    parser.add_argument("--expected-session-id", help="Session UUID independently read from phone original")
    args = parser.parse_args()
    try:
        if not args.expected_source_sha256 or not args.expected_session_id:
            _blocked("EXPECTED_SOURCE_IDENTITY_REQUIRED")
        result = verify_local_file(args.encrypted_file,
                                  expected_source_sha256=args.expected_source_sha256,
                                  expected_session_id=args.expected_session_id)
        print(result["status"])
        return 0
    except InboxVerificationError as exc:
        print("BLOCKED:" + str(exc), file=sys.stderr)
        return 2
    except (OSError, TypeError):
        print("BLOCKED:FILE_UNAVAILABLE_OR_OVERSIZE", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
