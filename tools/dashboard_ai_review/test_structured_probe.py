"""RED-first behavioral model-claim bridge tests, frozen *synthetic* fixtures only.

The model-like claims below are TEST DOUBLE output, not Qwen measurements.
Never use these tests as observed model precision/recall evidence.
"""
import hashlib
import json
import unittest

import behavioral_evidence as be
import holdout_v1
from test_holdout_v1 import fixture_result

import structured_probe

BAD = holdout_v1.instances()[0]
GOOD = holdout_v1.instances()[1]


def claimed(item=BAD):
    source_lines = item["source"].splitlines()
    n = next(i for i, line in enumerate(source_lines, 1)
             if line.strip().startswith("return "))
    return {
        "case_id": item["id"],
        "source_sha256": be.sha256_text(item["source"]),
        "path": item["path"],
        "line": n,
        "code_quote": source_lines[n - 1].strip(),
        "problem": "The synthetic code returns the wrong result on a fixed input",
        "impact": "The result differs from the independently defined requirement",
        "input_json": json.dumps(item["args"], ensure_ascii=False),
        "actual_json": json.dumps(fixture_result(item), ensure_ascii=False),
        "required_json": json.dumps(item["expected_good"], ensure_ascii=False),
    }


def encoded(*claims):
    return json.dumps({"findings": list(claims)}, ensure_ascii=False)


class ModelEmittedClaimEvidenceTests(unittest.TestCase):
    def test_empty_findings_means_no_claim_not_proven_clean(self):
        output = structured_probe.assess_model_output(BAD, encoded())
        self.assertEqual(output["status"], "NO_MODEL_CLAIMS")
        self.assertEqual(output["raw_findings"], 0)
        self.assertFalse(output["release_authorized"])

    def test_full_model_emitted_typed_witness_is_checked_by_trusted_executor(self):
        output = structured_probe.assess_model_output(BAD, encoded(claimed()))
        self.assertEqual(output["status"], "ADVISORY_ONLY")
        self.assertEqual(output["claims"][0]["status"], "REPRODUCED_STRUCTURED_BEHAVIOR")
        self.assertEqual(len(output["claims"][0]["evidence_sha256"]), 64)
        self.assertFalse(output["claims"][0]["narrative_verified"])
        self.assertFalse(output["release_authorized"])

    def test_warnings_on_correct_code_are_rejected_even_with_correct_quote(self):
        result = structured_probe.assess_model_output(GOOD, encoded(claimed(GOOD)))
        self.assertEqual(result["claims"][0]["status"], "NO_DEFECT_ON_TRUSTED_WITNESS")
        self.assertFalse(result["release_authorized"])

    def test_no_automatic_completion_of_missing_model_assertions(self):
        x = claimed()
        x.pop("actual_json")
        result = structured_probe.assess_model_output(BAD, encoded(x))
        self.assertEqual(result["status"], "INVALID_MODEL_RESPONSE")
        self.assertEqual(result["raw_findings"], 1)
        self.assertFalse(result["release_authorized"])

    def test_wrong_source_hash_is_not_repaired_by_a_bridge(self):
        x = claimed()
        x["source_sha256"] = "0" * 64
        result = structured_probe.assess_model_output(BAD, encoded(x))
        self.assertEqual(result["claims"][0]["status"], "SOURCE_OR_CASE_MISMATCH")

    def test_wrong_model_selected_input_is_never_executed(self):
        x = claimed()
        x["input_json"] = '["capture"]'
        result = structured_probe.assess_model_output(BAD, encoded(x))
        self.assertEqual(result["claims"][0]["status"], "UNTESTED_MODEL_INPUT")

    def test_wrong_claimed_actual_is_contradicted(self):
        x = claimed()
        x["actual_json"] = "false"
        result = structured_probe.assess_model_output(BAD, encoded(x))
        self.assertEqual(result["claims"][0]["status"], "CLAIMED_RESULT_CONTRADICTED")

    def test_comment_citation_never_establishes_verified_bug(self):
        x = claimed()
        x["line"] = 1
        x["code_quote"] = "# Requirement: only capture events count"
        result = structured_probe.assess_model_output(BAD, encoded(x))
        self.assertNotEqual(result["claims"][0]["status"],
                            "REPRODUCED_STRUCTURED_BEHAVIOR")

    def test_nan_and_repeated_json_keys_fail_closed(self):
        x = claimed()
        for bad in ("NaN", '{"x":1,"x":2}', "Infinity"):
            with self.subTest(bad=bad):
                x["actual_json"] = bad
                result = structured_probe.assess_model_output(BAD, encoded(x))
                self.assertEqual(result["status"], "INVALID_MODEL_RESPONSE")

    def test_falsehood_not_confirmed_by_python_equality_coercion(self):
        x = claimed()
        x["actual_json"] = "true"
        result = structured_probe.assess_model_output(BAD, encoded(x))
        self.assertEqual(result["claims"][0]["status"], "CLAIMED_RESULT_CONTRADICTED")

    def test_unknown_or_model_changed_case_id_denied(self):
        x = claimed()
        x["case_id"] = "deadbeefdeadbeef"
        result = structured_probe.assess_model_output(BAD, encoded(x))
        self.assertEqual(result["claims"][0]["status"], "SOURCE_OR_CASE_MISMATCH")

    def test_model_claims_are_not_execution_credentials(self):
        x = claimed()
        x["trusted_origin"] = "pinned_synthetic_holdout_v1"
        result = structured_probe.assess_model_output(BAD, encoded(x))
        self.assertEqual(result["status"], "INVALID_MODEL_RESPONSE")
        self.assertFalse(result["release_authorized"])


if __name__ == "__main__":
    unittest.main()
