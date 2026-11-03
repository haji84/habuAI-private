"""Exercise the real cache-save CLI against untrusted receipt JSON bytes."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.dashboard_ai_review.cache import VerifiedZeroCache

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/dashboard_ai_review/cache.py"
KEY = "a" * 64
SEGMENT = "b" * 16
SENTINEL = "SYNTHETIC_NON_HASH_SENTINEL"


class DashboardCacheReceiptCliTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.path = self.directory / "index.json"

    def cli(self, raw):
        self.path.write_bytes(raw)
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(CLI),
             "--validate-index", str(self.path)],
            text=True, encoding="utf-8", capture_output=True, timeout=20,
        )
        self.assertEqual(self.path.read_bytes(), raw)
        return result

    def assert_blocked(self, raw):
        result = self.cli(raw)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout.strip(),
                         "SHA_CACHE_SAVE_BLOCKED: absent or unsafe index")
        self.assertEqual(result.stderr, "")
        self.assertNotIn("SHA_CACHE_SAFE", result.stdout)
        self.assertNotIn(SENTINEL, result.stdout + result.stderr)
        # The ordinary reader also fails closed without persisting or echoing
        # rejected content. Validation does not sanitize the original file.
        output = StringIO()
        with redirect_stdout(output):
            cache = VerifiedZeroCache(str(self.directory))
        self.assertEqual(cache.entries, {})
        self.assertFalse(cache.has(KEY, SEGMENT))
        self.assertIn("SHA_CACHE_MISS", output.getvalue())
        self.assertNotIn(SENTINEL, output.getvalue())
        self.assertEqual(self.path.read_bytes(), raw)

    def test_duplicate_root_entries_cannot_hide_model_reply(self):
        raw = ('{"version":1,"entries":{"raw_model_reply":"' + SENTINEL
               + '"},"entries":{"' + KEY + '":"' + SEGMENT + '"}}').encode()
        self.assert_blocked(raw)

    def test_duplicate_nested_receipt_cannot_hide_model_reply(self):
        raw = ('{"version":1,"entries":{"' + KEY + '":"' + SENTINEL
               + '","' + KEY + '":"' + SEGMENT + '"}}').encode()
        self.assert_blocked(raw)

    def test_duplicate_version_and_escaped_key_are_rejected(self):
        for raw in [
            ('{"version":"' + SENTINEL + '","version":1,"entries":{}}').encode(),
            (r'{"version":1,"entries":{"raw_model_reply":"'
             + SENTINEL + r'"},"\u0065ntries":{}}').encode(),
        ]:
            with self.subTest(raw_kind=raw[:30]):
                self.assert_blocked(raw)

    def test_malformed_nonobject_and_private_fields_are_rejected(self):
        for raw in [
            b"{", b"null", b"[]", b"42", b'"\xff"',
            json.dumps({"version": 1, "entries": {},
                        "raw_model_reply": SENTINEL}).encode(),
            json.dumps({"version": 1,
                        "entries": {"raw_model_reply": SENTINEL}}).encode(),
        ]:
            with self.subTest(length=len(raw)):
                self.assert_blocked(raw)

    def test_nonfinite_constants_are_rejected(self):
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                self.assert_blocked(
                    ('{"version":1,"entries":{"' + KEY + '":' + constant + '}}').encode()
                )

    def test_deep_json_is_a_sanitized_cache_miss(self):
        raw = ('{"version":1,"entries":' + "[" * 1500
               + '"' + SENTINEL + '"' + "]" * 1500 + "}").encode()
        self.assert_blocked(raw)

    def test_good_hash_index_and_empty_index_pass_without_rewriting(self):
        for entries in ({}, {KEY: SEGMENT}):
            with self.subTest(entries=len(entries)):
                raw = json.dumps({"version": 1, "entries": entries},
                                 sort_keys=True, separators=(",", ":")).encode() + b"\n"
                result = self.cli(raw)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(),
                                 f"SHA_CACHE_SAFE: {len(entries)} hash-only receipts")
                self.assertEqual(result.stderr, "")

    def test_normal_writer_remains_hash_only_and_readable_by_cli(self):
        with redirect_stdout(StringIO()):
            cache = VerifiedZeroCache(str(self.directory))
        cache.remember(KEY, SEGMENT)
        raw = self.path.read_bytes()
        self.assertEqual(json.loads(raw), {"version": 1, "entries": {KEY: SEGMENT}})
        with redirect_stdout(StringIO()):
            reloaded = VerifiedZeroCache(str(self.directory))
        self.assertTrue(reloaded.has(KEY, SEGMENT))
        self.assertFalse(reloaded.has(KEY, "c" * 16))
        result = self.cli(raw)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SHA_CACHE_SAFE: 1 hash-only receipts", result.stdout)


if __name__ == "__main__":
    unittest.main()
