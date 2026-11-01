"""Offline contracts for SHA-only read-only review optimization."""
from io import BytesIO
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import cache as reviewer_cache


class CacheContractTests(unittest.TestCase):
    ARGS = dict(path="dashboard/index.html", number=2, total=3,
                owned="+example\n", prompt="OWNED DIFF SEGMENT:\n+example\nNEXT CONTEXT ONLY:\n+neighbor",
                segment_id="1" * 16, model="qwen2.5-coder:1.5b",
                digest="a" * 64, revision="b" * 64)

    def fingerprint(self, **changes):
        data = dict(self.ARGS)
        data.update(changes)
        return reviewer_cache.fingerprint(**data)

    def test_identity_is_bound_to_source_context_model_and_reviewer(self):
        original = self.fingerprint()
        self.assertEqual(len(original), 64)
        for change in (
            {"owned": "+Example\n"},
            {"prompt": self.ARGS["prompt"] + " changed neighbor"},
            {"number": 1},
            {"total": 4},
            {"path": "dashboard/field.html"},
            {"model": "different"},
            {"digest": "c" * 64},
            {"revision": "d" * 64},
            {"segment_id": "2" * 16},
        ):
            with self.subTest(change=change):
                self.assertNotEqual(original, self.fingerprint(**change))

    def test_valid_zero_finding_receipt_roundtrip_with_no_source_data(self):
        with tempfile.TemporaryDirectory() as root:
            cache = reviewer_cache.VerifiedZeroCache(root)
            key = self.fingerprint()
            self.assertFalse(cache.has(key, self.ARGS["segment_id"]))
            cache.remember(key, self.ARGS["segment_id"])
            persisted = (Path(root) / "index.json").read_text()
            self.assertNotIn("dashboard/index.html", persisted)
            self.assertNotIn("+example", persisted)
            self.assertNotIn("GPS", persisted)
            self.assertEqual(set(json.loads(persisted)), {"version", "entries"})
            self.assertEqual(json.loads(persisted)["entries"], {key: "1" * 16})
            self.assertEqual(reviewer_cache._read_index(Path(root) / "index.json"),
                             {key: "1" * 16})
            self.assertTrue(reviewer_cache.VerifiedZeroCache(root).has(key, "1" * 16))
            self.assertFalse(reviewer_cache.VerifiedZeroCache(root).has(key, "2" * 16))

    def test_corrupt_or_forged_index_is_treated_as_miss(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "index.json"
            for invalid in ("not-json", "{}", '{"version":true,"entries":{}}',
                            '{"version":1,"entries":{"/etc/passwd":"1"}}',
                            '{"version":1,"entries":{"%s":"not-a-receipt"}}' % ("a" * 64)):
                with self.subTest(invalid=invalid):
                    path.write_text(invalid)
                    self.assertEqual(reviewer_cache.VerifiedZeroCache(root).entries, {})
                    with self.assertRaises(ValueError):
                        reviewer_cache._read_index(path)
            path.write_bytes(b"0" * (reviewer_cache.MAX_CACHE_BYTES + 1))
            self.assertEqual(reviewer_cache.VerifiedZeroCache(root).entries, {})

    def test_nonlocal_invalid_model_digest_never_creates_cache_identity(self):
        response = {"models": [{"name": "qwen2.5-coder:1.5b", "digest": "a" * 64}]}
        with patch.object(reviewer_cache.urllib.request, "urlopen",
                          return_value=BytesIO(json.dumps(response).encode())) as model:
            self.assertEqual(reviewer_cache.model_digest("qwen2.5-coder:1.5b"), "a" * 64)
        self.assertEqual(model.call_args.args[0], reviewer_cache.LOCAL_TAGS_URL)
        for bad in ({"models": []}, {"models": [{"name": "qwen2.5-coder:1.5b", "digest": "bad"}]},
                    {"models": "not-array"}):
            with self.subTest(bad=bad):
                with patch.object(reviewer_cache.urllib.request, "urlopen",
                                  return_value=BytesIO(json.dumps(bad).encode())):
                    with self.assertRaises(ValueError):
                        reviewer_cache.model_digest("qwen2.5-coder:1.5b")

    def test_cache_disabled_without_directory(self):
        cache = reviewer_cache.VerifiedZeroCache(None)
        key = self.fingerprint()
        cache.remember(key, self.ARGS["segment_id"])
        self.assertFalse(cache.has(key, self.ARGS["segment_id"]))

    def test_index_does_not_follow_symlink(self):
        with tempfile.TemporaryDirectory() as root:
            src = Path(root) / "normal.json"
            src.write_text(json.dumps({"version": 1, "entries": {}}))
            link = Path(root) / "index.json"
            link.symlink_to(src)
            self.assertEqual(reviewer_cache.VerifiedZeroCache(root).entries, {})
            with self.assertRaises(ValueError):
                reviewer_cache.VerifiedZeroCache(root).remember(self.fingerprint(), "1" * 16)


if __name__ == "__main__":
    unittest.main()
