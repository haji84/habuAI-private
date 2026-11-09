"""Synthetic-only independent readback tests for the native Drive inbox format.

No real owner's private key, account, GPS, records or Drive credentials.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from scripts.verify_device_inbox_readback import (
    InboxVerificationError, verify_ciphertext,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_device_inbox_readback.py"


def fixture(*, closed=True, wrong_sha=False, invalid_uuid=False):
    receiver = X25519PrivateKey.generate()
    source = (
        b'{"kind":"start","time":1790000000}\n'
        b'{"kind":"event","time":1790000002,"type":"sighting","species":"SYNTHETIC_ONLY","count":1}\n'
        + (b'{"kind":"stop","time":1790000003}\n' if closed else b'')
    )
    public = receiver.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    key_id = hashlib.sha256(public).digest()[:8].hex()
    aad = b"HABU-DEVICE-INBOX-V1|" + key_id.encode()
    ephemeral = X25519PrivateKey.generate()
    salt = os.urandom(32)
    nonce = os.urandom(12)
    symmetric = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=salt, info=aad
    ).derive(ephemeral.exchange(receiver.public_key()))
    payload = {
        "schema_version": "habu-device-original-v1",
        "session_id": "incorrect" if invalid_uuid else str(uuid.uuid4()),
        "source_sha256": ("0" * 64 if wrong_sha else hashlib.sha256(source).hexdigest()),
        "raw_jsonl_b64": base64.b64encode(source).decode(),
    }
    ciphertext = AESGCM(symmetric).encrypt(
        nonce, json.dumps(payload, separators=(",", ":")).encode(), aad
    )
    package = {
        "schema_version": "habu-device-inbox-v1",
        "algorithm": "X25519-HKDF-SHA256-AES-256-GCM",
        "recipient_key_id": key_id,
        "ephemeral_public_key_b64": base64.b64encode(
            ephemeral.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode(),
        "hkdf_salt_b64": base64.b64encode(salt).decode(),
        "nonce_b64": base64.b64encode(nonce).decode(),
        "ciphertext_b64": base64.b64encode(ciphertext).decode(),
    }
    return json.dumps(package, separators=(",", ":")).encode(), receiver.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )


class HabuInboxReadbackTests(unittest.TestCase):
    def test_valid_native_envelope_is_authenticated_and_checks_original_sha(self):
        envelope, key = fixture()
        outcome = verify_ciphertext(envelope, key)
        self.assertEqual(outcome["status"], "PRIVATE_DECRYPT_AND_SOURCE_SHA_PASS")
        self.assertTrue(outcome["source_closed"])
        self.assertFalse(outcome["gps_exposed"])
        self.assertNotIn(b"SYNTHETIC_ONLY", envelope)

    def test_wrong_receiver_key_and_ciphertext_tamper_fail_closed(self):
        envelope, key = fixture()
        other = fixture()[1]
        with self.assertRaisesRegex(InboxVerificationError, "KEY_ID_MISMATCH"):
            verify_ciphertext(envelope, other)
        modified = json.loads(envelope)
        raw = bytearray(base64.b64decode(modified["ciphertext_b64"]))
        raw[-1] ^= 1
        modified["ciphertext_b64"] = base64.b64encode(raw).decode()
        with self.assertRaisesRegex(InboxVerificationError, "AUTHENTICATION_FAILED"):
            verify_ciphertext(json.dumps(modified).encode(), key)

    def test_incomplete_source_and_fake_digest_are_not_accepted(self):
        for options, expected in [
            ({"closed": False}, "INCOMPLETE_SESSION"),
            ({"wrong_sha": True}, "SOURCE_SHA_MISMATCH"),
            ({"invalid_uuid": True}, "INVALID_PRIVATE_PAYLOAD"),
        ]:
            with self.subTest(expected=expected):
                envelope, key = fixture(**options)
                with self.assertRaisesRegex(InboxVerificationError, expected):
                    verify_ciphertext(envelope, key)

    def test_cli_does_not_print_source_key_or_sensitive_error(self):
        envelope, key = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            filename = Path(temporary) / "opaque.habuenc"
            filename.write_bytes(envelope)
            environment = dict(os.environ)
            environment["HABU_DEVICE_INBOX_PRIVATE_KEY_B64"] = base64.b64encode(key).decode()
            run = subprocess.run(
                [sys.executable, str(SCRIPT), str(filename)],
                env=environment, capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stdout.strip(), "PRIVATE_DECRYPT_AND_SOURCE_SHA_PASS")
            self.assertNotIn("SYNTHETIC_ONLY", run.stdout + run.stderr)
            self.assertNotIn(base64.b64encode(key).decode(), run.stdout + run.stderr)
            environment.pop("HABU_DEVICE_INBOX_PRIVATE_KEY_B64")
            missing = subprocess.run(
                [sys.executable, str(SCRIPT), str(filename)],
                env=environment, capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(missing.returncode, 2)
            self.assertIn("KEY_REQUIRED_IN_PRIVATE_RUNTIME", missing.stderr)
            self.assertNotIn(str(filename), missing.stderr)


if __name__ == "__main__":
    unittest.main()
