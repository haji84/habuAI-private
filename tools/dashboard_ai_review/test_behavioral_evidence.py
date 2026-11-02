"""General typed reproduction tests, with trusted frozen fixtures only.

All proposals below are SYNTHETIC test inputs. They are not Qwen assertions.
"""
from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

import behavioral_evidence as be
import holdout_v1

CASE_BAD = holdout_v1.instances()[0]
CASE_GOOD = holdout_v1.instances()[1]


def make_claim(item=CASE_BAD, *, actual=None, required=None):
    from test_holdout_v1 import fixture_result
    lines = item["source"].splitlines()
    logic = next(i for i, x in enumerate(lines, 1)
                 if x.lstrip().startswith(("return ", "function check(")))
    observed = fixture_result(item)
    return {
        "schema": be.CLAIM_SCHEMA,
        "case_id": item["id"],
        "source_sha256": be.sha256_text(item["source"]),
        "input": copy.deepcopy(item["args"]),
        "claimed_actual": observed if actual is None else actual,
        "claimed_required": item["expected_good"] if required is None else required,
        "line": logic,
        "code_quote": lines[logic - 1].strip()[:140],
        "problem": "Synthetic claim that a fixed counterexample proves a defect",
        "impact": "An observable return differs from the required value",
    }


class ReproductionContractTests(unittest.TestCase):
    def test_frozen_adapter_reproduces_a_structured_behavioral_claim(self):
        proposal = make_claim()
        verdict = be.verify_frozen_synthetic_claim(proposal)
        self.assertEqual(verdict["status"], "REPRODUCED_STRUCTURED_BEHAVIOR")
        self.assertEqual(verdict["citation_status"], "SOURCE_ANCHORED_ONLY")
        self.assertEqual(verdict["narrative_semantics"], "NOT_AUTOMATICALLY_VERIFIED")
        self.assertFalse(verdict["formal_review_approved"])
        self.assertFalse(verdict["release_authorized"])

    def test_correct_code_is_not_a_bug_even_if_model_claims_one(self):
        verdict = be.verify_frozen_synthetic_claim(make_claim(CASE_GOOD, actual=1))
        self.assertEqual(verdict["status"], "NO_DEFECT_ON_TRUSTED_WITNESS")
        self.assertFalse(verdict["release_authorized"])

    def test_wrong_claimed_actual_is_contradicted_not_confirmed(self):
        verdict = be.verify_frozen_synthetic_claim(make_claim(actual=0))
        self.assertEqual(verdict["status"], "CLAIMED_RESULT_CONTRADICTED")

    def test_wrong_claimed_required_behavior_is_contradicted(self):
        verdict = be.verify_frozen_synthetic_claim(make_claim(required=1))
        self.assertEqual(verdict["status"], "CLAIMED_REQUIREMENT_CONTRADICTED")

    def test_bad_citation_does_not_get_a_fully_anchored_pass(self):
        model = make_claim()
        model["line"] = 99
        model["code_quote"] = "invented quoted line"
        verdict = be.verify_frozen_synthetic_claim(model)
        self.assertEqual(verdict["status"], "REPRODUCED_BEHAVIOR_BAD_CITATION")
        self.assertEqual(verdict["citation_status"], "CITATION_REJECTED")
        self.assertFalse(verdict["release_authorized"])

    def test_unstructured_qwen_prose_does_not_get_automatic_confirmation(self):
        src = {
            "case_id": CASE_BAD["id"],
            "problem": "The script incorrectly counts sightings as captures",
            "impact": "Incorrect statistics",
            "line": 3,
            "code_quote": "return int(kind != 'roadkill')",
        }
        verdict = be.verify_frozen_synthetic_claim(src)
        self.assertEqual(verdict["status"], "UNSTRUCTURED_CLAIM")
        self.assertFalse(verdict["release_authorized"])

    def test_model_is_not_allowed_to_change_witness_input(self):
        model = make_claim()
        model["input"] = ["capture"]
        with patch.object(be, "trusted_synthetic_witness") as runner:
            verdict = be.verify_frozen_synthetic_claim(model)
        self.assertEqual(verdict["status"], "UNTESTED_MODEL_INPUT")
        runner.assert_not_called()

    def test_model_cannot_relabel_which_source_was_executed(self):
        model = make_claim()
        model["source_sha256"] = "f" * 64
        with patch.object(be, "trusted_synthetic_witness") as runner:
            verdict = be.verify_frozen_synthetic_claim(model)
        self.assertEqual(verdict["status"], "SOURCE_OR_CASE_MISMATCH")
        runner.assert_not_called()

    def test_unknown_fixture_cannot_inject_model_code(self):
        model = make_claim()
        model["case_id"] = "deadbeefdeadbeef"
        model["new_source"] = "__import__('os').system('echo unwanted')"
        with patch.object(be, "trusted_synthetic_witness") as runner:
            verdict = be.verify_frozen_synthetic_claim(model)
        self.assertEqual(verdict["status"], "UNKNOWN_FROZEN_CASE")
        runner.assert_not_called()

    def test_text_filenames_are_never_used_as_execution_targets(self):
        model = make_claim()
        model["path"] = "../../private/secret.py"
        model["code"] = "raise AssertionError('model generated code ran')"
        verdict = be.verify_frozen_synthetic_claim(model)
        self.assertEqual(verdict["status"], "REPRODUCED_STRUCTURED_BEHAVIOR")
        self.assertEqual(verdict["narrative_semantics"], "NOT_AUTOMATICALLY_VERIFIED")

    def test_wrong_byte_type_does_not_collide_with_boolean(self):
        self.assertFalse(be.exact_equal(True, 1))
        self.assertFalse(be.exact_equal(1, 1.0))
        self.assertFalse(be.exact_equal([True], [1]))
        self.assertTrue(be.exact_equal({"a": [1, None]}, {"a": [1, None]}))

    def test_boolean_expected_cannot_be_replaced_by_int(self):
        bool_case = next(x for x in holdout_v1.instances()
                         if x["family"] == "seven_hour" and x["label"] == "positive")
        claim = make_claim(bool_case)
        claim["claimed_required"] = 1
        verdict = be.verify_frozen_synthetic_claim(claim)
        self.assertEqual(verdict["status"], "CLAIMED_REQUIREMENT_CONTRADICTED")

    def test_missing_claim_field_remains_inconclusive(self):
        x = make_claim()
        x.pop("claimed_actual")
        result = be.verify_frozen_synthetic_claim(x)
        self.assertEqual(result["status"], "MISSING_REPRODUCTION_FIELDS")

    def test_non_json_model_prediction_is_not_executed(self):
        x = make_claim()
        x["claimed_actual"] = float("nan")
        result = be.verify_frozen_synthetic_claim(x)
        self.assertEqual(result["status"], "NON_JSON_EVIDENCE")

    def test_a_trusted_witness_is_required_by_the_pure_verifier(self):
        proposal = make_claim()
        result = be.compare_behavior(proposal, {"schema": "unknown"},
                                     citation_ok=True)
        self.assertEqual(result["status"], "INVALID_WITNESS_SCHEMA")
        self.assertFalse(result["release_authorized"])

    def test_frozen_40_cases_replay_without_fabricating_qwen_accuracy(self):
        entries = holdout_v1.instances()
        self.assertEqual(len(entries), 40)
        reproduced = clean = 0
        for item in entries:
            with self.subTest(case=item["id"]):
                model_like = make_claim(item)
                verdict = be.verify_frozen_synthetic_claim(model_like)
                if item["label"] == "positive":
                    self.assertEqual(verdict["status"],
                                     "REPRODUCED_STRUCTURED_BEHAVIOR")
                    reproduced += 1
                else:
                    self.assertEqual(verdict["status"],
                                     "NO_DEFECT_ON_TRUSTED_WITNESS")
                    clean += 1
        self.assertEqual((reproduced, clean), (20, 20))
        # These are deliberately constructed ideal model-like inputs.
        # This test makes NO claim that Qwen generated these assertions.


if __name__ == "__main__":
    unittest.main()
