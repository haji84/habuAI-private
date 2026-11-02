"""Hermetic tests: source grounding and semantic repro must stay separate."""
from __future__ import annotations

import json
import unittest

import holdout_v1
import review
import synthetic_claims

EXAMPLE = holdout_v1.instances()[0]


def claim(item, line, quote, problem="A concrete error is alleged in this check"):
    return {
        "path": item["path"], "line": line, "code_quote": quote,
        "problem": problem, "impact": "This might produce an incorrect result",
    }


class SyntheticClaimReceiptTests(unittest.TestCase):
    def test_grounded_claim_is_still_unverified_semantically(self):
        src = EXAMPLE["source"].splitlines()
        return_line = next(n for n, code in enumerate(src, 1)
                           if code.lstrip().startswith("return "))
        row = claim(EXAMPLE, return_line, src[return_line - 1].strip())
        raw = {"findings": [row]}
        parsed = review.parse_findings(json.dumps(raw), EXAMPLE["path"])
        result = synthetic_claims.claim_receipts(EXAMPLE, raw, parsed)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["anchor_status"], "SOURCE_ANCHORED_ONLY")
        self.assertEqual(result[0]["fixture_witness"], "FIXTURE_VIOLATES_STATED_RULE")
        self.assertEqual(result[0]["semantic_status"],
                         "UNVERIFIED_REQUIRES_CLAIM_SPECIFIC_COUNTEREXAMPLE")
        self.assertNotIn("REPRODUCED_CLAIM", result[0]["semantic_status"])

    def test_unmatched_quote_is_rejected_without_calling_it_false_bug(self):
        row = claim(EXAMPLE, 2, "not actually on the source line")
        raw = {"findings": [row]}
        parsed = review.parse_findings(json.dumps(raw), EXAMPLE["path"])
        result = synthetic_claims.claim_receipts(EXAMPLE, raw, parsed)
        self.assertEqual(result[0]["anchor_status"], "CITATION_REJECTED")
        self.assertEqual(result[0]["anchor_reason"],
                         "QUOTED_TEXT_NOT_ON_SOURCE_LINE")
        self.assertEqual(result[0]["semantic_status"],
                         "UNVERIFIED_REQUIRES_CLAIM_SPECIFIC_COUNTEREXAMPLE")

    def test_model_style_complaint_is_not_a_confirmed_bug(self):
        clean = next(x for x in holdout_v1.instances() if x["label"] == "negative")
        source = clean["source"].splitlines()
        row = claim(clean, 2, source[1], "The function lacks a docstring")
        raw = {"findings": [row]}
        parsed = review.parse_findings(json.dumps(raw), clean["path"])
        result = synthetic_claims.claim_receipts(clean, raw, parsed)
        self.assertEqual(result[0]["fixture_witness"], "FIXTURE_PASSES_FIXED_WITNESS")
        self.assertEqual(result[0]["semantic_status"],
                         "UNVERIFIED_REQUIRES_CLAIM_SPECIFIC_COUNTEREXAMPLE")
        self.assertNotEqual(result[0]["semantic_status"], "CONFIRMED_BUG")

    def test_bad_model_field_is_not_executed_or_trusted(self):
        raw = {"findings": [{
            "path": EXAMPLE["path"], "line": 2, "code_quote": 12,
            "problem": 0, "impact": None,
        }]}
        result = synthetic_claims.claim_receipts(EXAMPLE, raw, [])
        self.assertEqual(result[0]["anchor_status"],
                         "MODEL_FINDING_REJECTED_BY_PARSER")
        self.assertEqual(result[0]["model_problem"], "")
        self.assertEqual(result[0]["model_impact"], "")
        self.assertEqual(result[0]["model_code_quote"], "")

    def test_only_frozen_synthetic_case_can_produce_receipt(self):
        bad = dict(EXAMPLE, path="dashboard/field-core.js")
        with self.assertRaisesRegex(ValueError, "frozen synthetic"):
            synthetic_claims.claim_receipts(bad, {"findings": []}, [])
        with self.assertRaisesRegex(ValueError, "Unbounded"):
            synthetic_claims.claim_receipts(
                EXAMPLE, {"findings": [{}] * 4}, []
            )

    def test_log_bounded_and_ascii_escaped_with_fake_secret_redacted(self):
        phrase = "ghp_" + ("Q" * 24)
        raw = {
            "findings": [claim(
                EXAMPLE, 1, "hello",
                "model text\n::warning::" + phrase + "日本語",
            )]
        }
        got = synthetic_claims.claim_receipts(EXAMPLE, raw, [])
        line = synthetic_claims.log_receipt(got[0])
        self.assertTrue(line.startswith("HOLDOUT_CLAIM_TEXT: "))
        self.assertEqual(len(line.splitlines()), 1)
        self.assertNotIn(phrase, line)
        self.assertNotIn("::warning::"+phrase, line)
        self.assertIn("[REDACTED]", line)
        self.assertNotIn("日本語", line)  # ensure_ascii converts to unicode escapes
        self.assertEqual(json.loads(line.split(": ", 1)[1])["claim_id"],
                         got[0]["claim_id"])

    def test_no_model_label_or_witness_supplied_in_prompt(self):
        visible = holdout_v1.public_prompt_instance(EXAMPLE)
        self.assertEqual(set(visible), {"path", "patch"})
        self.assertNotIn("expected_good", visible)
        self.assertNotIn("label", visible)
        self.assertNotIn("args", visible)


if __name__ == "__main__":
    unittest.main()
