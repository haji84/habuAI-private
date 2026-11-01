"""Hermetic contracts for the GitHub-hosted reviewer (no model or network needed)."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import review


class ReviewContractTests(unittest.TestCase):
    def test_model_endpoint_is_local_and_code_selection_excludes_raw_gps(self):
        self.assertEqual(review.OLLAMA_URL, "http://127.0.0.1:11434/api/chat")
        self.assertNotIn(".gpx", review.SOURCE_SUFFIXES)
        self.assertNotIn(".jsonl", review.SOURCE_SUFFIXES)
        self.assertNotIn(".ndjson", review.SOURCE_SUFFIXES)

    def test_finding_is_bound_to_one_file_and_valid_positive_line(self):
        rows = review.parse_findings(json.dumps({"findings": [
            {"path": "mobile/a.kt", "line": 7, "problem": "This accepts fixes before start",
             "impact": "Track gets stale GPS points"},
            {"path": "elsewhere/a.kt", "line": 3, "problem": "Cross-file hallucination",
             "impact": "Should be rejected"},
            {"path": "mobile/a.kt", "line": -1, "problem": "Invalid negative line",
             "impact": "Should be rejected"},
            {"path": "mobile/a.kt", "line": 2, "problem": "tiny", "impact": "short"}
        ]}), "mobile/a.kt")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["line"], 7)

    def test_qualification_requires_actual_candidate_finding(self):
        self.assertFalse(review.qualification_passes([]))
        self.assertTrue(review.qualification_passes([
            {"problem": "The grace period allows fixes before tracking starts.",
             "impact": "Old GPS points enter a new exploration session."}
        ]))
        self.assertFalse(review.qualification_passes([
            {"problem": "Wrong capitalization of a variable",
             "impact": "Not a confirmed GPS session bug."}
        ]))

    def test_malformed_model_output_must_not_count_as_pass(self):
        for value in ("not-json", "{}", '{"findings":null}', "[]"):
            with self.subTest(value=value):
                with self.assertRaises((ValueError, json.JSONDecodeError)):
                    review.parse_findings(value, "mobile/a.kt")

    def test_exact_sha_and_file_allowlist_and_priority(self):
        base = "a" * 40
        head = "b" * 40

        def git_mock(*args):
            if args[0] == "rev-parse":
                return head
            if args[0] == "merge-base":
                return base
            if args[0] == "diff" and "--name-only" in args:
                return "\n".join([
                    "mobile/android/app/src/main/java/org/habuai/field/MainActivity.kt",
                    "mobile/android/app/src/main/java/org/habuai/field/LocationTrackingService.kt",
                    "mobile/gps/private-track.gpx",
                    "mobile/points.jsonl",
                    ".env",
                    "docs/strategy.md",
                    "tests/test_native_background_gps_contract.py",
                ])
            raise AssertionError(args)

        with patch.object(review, "git", side_effect=git_mock):
            selected = review.source_paths(base, head)
        self.assertEqual(len(selected), 3)
        self.assertTrue(selected[0].endswith("LocationTrackingService.kt"))
        self.assertFalse(any(".gpx" in p or ".env" in p for p in selected))

    def test_refuses_unknown_commit_and_different_checked_out_head(self):
        with self.assertRaises(ValueError):
            review.source_paths("bad", "b" * 40)
        with patch.object(review, "git", return_value="a" * 40):
            with self.assertRaisesRegex(ValueError, "HEAD"):
                review.source_paths("a" * 40, "b" * 40)

    def test_summary_sanitizes_untrusted_model_text(self):
        result = review.safe_md("<img src=x onerror=alert(1)>| surprise\nnext")
        self.assertNotIn("<img", result)
        self.assertNotIn("|", result)
        self.assertNotIn("\n", result)

    def test_summary_is_local_and_does_not_require_gh_token(self):
        with tempfile.TemporaryDirectory() as directory:
            output = os.path.join(directory, "summary.md")
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": output}):
                review.write_summary(["STATUS: HOLD", "No merge or upload"])
            with open(output, encoding="utf-8") as handle:
                result = handle.read()
        self.assertIn("STATUS: HOLD", result)


if __name__ == "__main__":
    unittest.main()
