"""Synthetic-only native inbox integrity and independent phone-source checks."""
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
from scripts.verify_device_inbox_readback import InboxVerificationError, verify_ciphertext

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_device_inbox_readback.py"


def fixture(*, closed=True, wrong_sha=False, invalid_uuid=False, evidence=None):
    receiver = X25519PrivateKey.generate()
    source = (
        b'{"kind":"start","time":1790000000}\n'
        b'{"kind":"event","time":1790000002,"type":"sighting","species":"SYNTHETIC_ONLY","count":1}\n'
        + (b'{"kind":"stop","time":1790000003}\n' if closed else b'')
    )
    session = str(uuid.uuid4())
    source_sha = hashlib.sha256(source).hexdigest()
    # This expected identity comes from the original fixture, not decryption.
    if evidence is not None:
        evidence.update(expected_source_sha256=source_sha, expected_session_id=session)
    public = receiver.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    key_id = hashlib.sha256(public).digest()[:8].hex()
    aad = b"HABU-DEVICE-INBOX-V1|" + key_id.encode()
    ephemeral = X25519PrivateKey.generate()
    salt, nonce = os.urandom(32), os.urandom(12)
    symmetric = HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=aad).derive(
        ephemeral.exchange(receiver.public_key()))
    payload = {
        "schema_version": "habu-device-original-v1",
        "session_id": "incorrect" if invalid_uuid else session,
        "source_sha256": "0" * 64 if wrong_sha else source_sha,
        "raw_jsonl_b64": base64.b64encode(source).decode(),
    }
    encrypted = AESGCM(symmetric).encrypt(nonce, json.dumps(payload, separators=(",", ":")).encode(), aad)
    package = {
        "schema_version": "habu-device-inbox-v1",
        "algorithm": "X25519-HKDF-SHA256-AES-256-GCM",
        "recipient_key_id": key_id,
        "ephemeral_public_key_b64": base64.b64encode(ephemeral.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode(),
        "hkdf_salt_b64": base64.b64encode(salt).decode(),
        "nonce_b64": base64.b64encode(nonce).decode(),
        "ciphertext_b64": base64.b64encode(encrypted).decode(),
    }
    return json.dumps(package, separators=(",", ":")).encode(), receiver.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())


class HabuInboxReadbackTests(unittest.TestCase):
    def test_valid_native_envelope_does_not_claim_independent_original_match(self):
        envelope, key = fixture()
        outcome = verify_ciphertext(envelope, key)
        self.assertEqual(outcome["status"], "PRIVATE_PACKAGE_INTEGRITY_PASS")
        self.assertFalse(outcome["independent_original_matched"])
        self.assertTrue(outcome["source_closed"])
        self.assertFalse(outcome["gps_exposed"])
        self.assertNotIn(b"SYNTHETIC_ONLY", envelope)

    def test_independent_phone_hash_and_session_match(self):
        expected = {}
        envelope, key = fixture(evidence=expected)
        result = verify_ciphertext(envelope, key, **expected)
        self.assertEqual(result["status"], "PRIVATE_DECRYPT_AND_SOURCE_SHA_PASS")
        self.assertTrue(result["independent_original_matched"])
        self.assertFalse(result["drive_arrival_verified"])
        self.assertNotIn(expected["expected_source_sha256"], json.dumps(result))
        self.assertNotIn(expected["expected_session_id"], json.dumps(result))

    def test_wrong_phone_hash_is_rejected_even_when_internal_hash_is_valid(self):
        expected = {}
        envelope, key = fixture(evidence=expected)
        expected["expected_source_sha256"] = "0" * 64
        with self.assertRaisesRegex(InboxVerificationError, "EXPECTED_SOURCE_SHA_MISMATCH"):
            verify_ciphertext(envelope, key, **expected)

    def test_wrong_phone_session_is_rejected(self):
        expected = {}
        envelope, key = fixture(evidence=expected)
        expected["expected_session_id"] = str(uuid.uuid4())
        with self.assertRaisesRegex(InboxVerificationError, "EXPECTED_SESSION_MISMATCH"):
            verify_ciphertext(envelope, key, **expected)

    def test_partial_or_invalid_external_identity_is_not_accepted(self):
        envelope, key = fixture()
        cases = [{"expected_source_sha256": "a" * 64},
                 {"expected_session_id": str(uuid.uuid4())},
                 {"expected_source_sha256": "PRIVATE-INVALID", "expected_session_id": str(uuid.uuid4())},
                 {"expected_source_sha256": "a" * 64, "expected_session_id": "PRIVATE-INVALID"}]
        for expected in cases:
            with self.subTest(keys=list(expected)):
                with self.assertRaisesRegex(InboxVerificationError, "EXPECTED_SOURCE_IDENTITY_INVALID"):
                    verify_ciphertext(envelope, key, **expected)

    def test_wrong_receiver_key_and_ciphertext_tamper_fail_closed(self):
        envelope, key = fixture()
        with self.assertRaisesRegex(InboxVerificationError, "KEY_ID_MISMATCH"):
            verify_ciphertext(envelope, fixture()[1])
        modified = json.loads(envelope)
        raw = bytearray(base64.b64decode(modified["ciphertext_b64"]))
        raw[-1] ^= 1
        modified["ciphertext_b64"] = base64.b64encode(raw).decode()
        with self.assertRaisesRegex(InboxVerificationError, "AUTHENTICATION_FAILED"):
            verify_ciphertext(json.dumps(modified).encode(), key)

    def test_incomplete_source_and_fake_digest_are_not_accepted(self):
        for options, expected in [({"closed": False}, "INCOMPLETE_SESSION"),
                                  ({"wrong_sha": True}, "SOURCE_SHA_MISMATCH"),
                                  ({"invalid_uuid": True}, "INVALID_PRIVATE_PAYLOAD")]:
            with self.subTest(expected=expected):
                envelope, key = fixture(**options)
                with self.assertRaisesRegex(InboxVerificationError, expected):
                    verify_ciphertext(envelope, key)

    def test_cli_requires_independently_obtained_phone_identity(self):
        envelope, key = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "opaque.habuenc"
            path.write_bytes(envelope)
            env = dict(os.environ, HABU_DEVICE_INBOX_PRIVATE_KEY_B64=base64.b64encode(key).decode())
            run = subprocess.run([sys.executable, str(SCRIPT), str(path)], env=env,
                                 capture_output=True, text=True, timeout=15)
            self.assertEqual(run.returncode, 2)
            self.assertIn("EXPECTED_SOURCE_IDENTITY_REQUIRED", run.stderr)
            self.assertNotIn(str(path), run.stderr)

    def test_cli_does_not_print_source_key_or_sensitive_error(self):
        expected = {}
        envelope, key = fixture(evidence=expected)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "opaque.habuenc"
            path.write_bytes(envelope)
            env = dict(os.environ, HABU_DEVICE_INBOX_PRIVATE_KEY_B64=base64.b64encode(key).decode())
            command = [sys.executable, str(SCRIPT), str(path), "--expected-source-sha256",
                       expected["expected_source_sha256"], "--expected-session-id", expected["expected_session_id"]]
            run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stdout.strip(), "PRIVATE_DECRYPT_AND_SOURCE_SHA_PASS")
            for forbidden in ["SYNTHETIC_ONLY", base64.b64encode(key).decode(), str(path), *expected.values()]:
                self.assertNotIn(forbidden, run.stdout + run.stderr)
            env.pop("HABU_DEVICE_INBOX_PRIVATE_KEY_B64")
            missing = subprocess.run(command, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(missing.returncode, 2)
            self.assertIn("KEY_REQUIRED_IN_PRIVATE_RUNTIME", missing.stderr)
            self.assertNotIn(str(path), missing.stderr)


if __name__ == "__main__":
    unittest.main()
