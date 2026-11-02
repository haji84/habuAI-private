"""Offline contracts for the owner-approved Qwen 7B *research* trial.

Never downloads a model or calls Ollama. Frozen cases and thresholds unchanged.
"""
from __future__ import annotations

import io
from contextlib import redirect_stdout
import time
import unittest
from unittest.mock import patch

import compare_qwen7b as c
import quality


class SevenBComparisonBoundaries(unittest.TestCase):
    def test_model_is_fixed_to_approved_7b_and_digest_is_pinned(self):
        self.assertEqual(c.MODEL, "qwen2.5-coder:7b")
        self.assertTrue(c.validate_model_digest("dae161e27b0e" + "a" * 52))
        for digest in ("d7372fd82851" + "a" * 52, "dae161e27b0e", "z" * 64):
            with self.subTest(digest=digest):
                with self.assertRaises(ValueError):
                    c.validate_model_digest(digest)

    def test_probe_uses_exact_synthetic_diff_and_seven_b_only(self):
        fixture = quality.CASES[0]
        calls = []
        receipt = []
        with patch.object(c.review, "ask_model",
                          side_effect=lambda *args, **kwargs:
                          calls.append((args, kwargs)) or '{"findings":[]}'):
            with redirect_stdout(io.StringIO()):
                result = c.model_caller(max_seconds=300,
                                        started_at=time.monotonic(),
                                        receipts=receipt)(
                                            fixture["path"], fixture["patch"])
        self.assertEqual(result, '{"findings":[]}')
        self.assertEqual(len(receipt), 1)
        self.assertEqual(receipt[0]["status"], "COMPLETED")
        self.assertEqual(len(receipt[0]["answer_sha256"]), 64)
        self.assertEqual(calls[0][1], {"model": c.MODEL})
        self.assertEqual(calls[0][0], (fixture["path"], fixture["patch"]))

    def test_private_or_arbitrary_paths_never_enter_model(self):
        fixture = quality.CASES[0]
        examples = ["data/raw/GPS.gpx", "dashboard/private/locations.js",
                    "fixture/../raw.py", "scripts/secret.py"]
        with patch.object(c.review, "ask_model") as ask:
            for path in examples:
                with self.subTest(path=path):
                    with self.assertRaisesRegex(ValueError, "NON_SYNTHETIC"):
                        c.model_caller(max_seconds=300,
                                       started_at=time.monotonic(), receipts=[])(
                                           path, fixture["patch"])
            ask.assert_not_called()

    def test_context_forgery_and_truncated_patch_fail_closed(self):
        fixture = quality.CASES[0]
        call = c.model_caller(max_seconds=300,
                              started_at=time.monotonic(), receipts=[])
        with self.assertRaises(ValueError):
            call(fixture["path"], "diff --git a/fixture/no.py b/fixture/no.py\n")
        with self.assertRaises(ValueError):
            call(fixture["path"], fixture["patch"] + "a" * 4000)

    def test_expired_budget_denies_without_inference(self):
        fixture = quality.CASES[0]
        with patch.object(c.review, "ask_model") as ask:
            with self.assertRaisesRegex(TimeoutError, "BUDGET"):
                c.model_caller(max_seconds=60, started_at=time.monotonic()-70,
                               receipts=[])(fixture["path"], fixture["patch"])
            ask.assert_not_called()

    def test_budget_cannot_be_infinite_or_extended_silently(self):
        for value in (0, 59, 4801, 100000, 1.5, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    c.model_caller(max_seconds=value, started_at=0, receipts=[])

    def test_baseline_evaluation_sources_are_immutable(self):
        self.assertEqual(c.FROZEN_BLOB,
                         "daac52dfed89cb946e736aed49ed109a56307ffa")
        self.assertEqual(c.FROZEN_SHA256,
                         "6a679c26f775970a2d55e53e8d3870c6c9cbd8320c530b77725de83af7e8fc8a")
        self.assertEqual(len(quality.CASES), 6)
        self.assertEqual(sum(x["kind"] == "positive" for x in quality.CASES), 2)
        self.assertEqual(sum(x["kind"] == "negative" for x in quality.CASES), 4)

    def test_invalid_head_is_not_accepted_as_a_frozen_source(self):
        for invalid in ("x" * 40, "deadbeef", "", "a" * 41):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "INVALID_EXPECTED_HEAD"):
                    c.require_frozen_source(invalid)

    def test_metric_summary_excludes_raw_model_claim_text(self):
        keys = ("total", "completed", "incomplete", "known_bug_cases",
                "known_clean_cases", "total_raw_findings",
                "total_location_anchored_findings",
                "grounding_rejected_findings", "parse_dropped_findings",
                "clean_false_alert_cases", "clean_false_alert_rate",
                "zero_finding_responses", "possible_anchored_bug_cases",
                "proxy_precision_ceiling", "proxy_recall_ceiling",
                "pair_selective_raw_alerts", "pair_selective_anchored_proxy",
                "proxy_gate")
        fake = {name: 0 for name in keys}
        fake["cases"] = [{"secret": "fake_private_value"}]
        fake["raw_response"] = "fake_private_value"
        result = c.safe_holdout_summary(fake)
        self.assertEqual(set(result), set(keys))
        self.assertNotIn("fake_private_value", str(result))

    def test_no_qualified_result_from_model_free_or_old_holdout(self):
        from pathlib import Path
        source = Path(c.__file__).read_text("utf-8")
        self.assertIn('"unseen_cases": 0', source)
        self.assertIn('"quality_qualified": False', source)
        self.assertIn('"release_authorized": False', source)
        self.assertIn("DIAGNOSTIC_MEASURED_QUALITY_HOLD", source)


if __name__ == "__main__":
    unittest.main()
