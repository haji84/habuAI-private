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


class ExactModelSchemaTests(unittest.TestCase):
    def _capture_request(self, evidence_case):
        from unittest.mock import patch
        import review
        seen = []

        class SyntheticOllama:
            def __init__(self, req):
                seen.append(json.loads(req.data.decode("utf-8")))

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, *_args):
                return json.dumps({
                    "done": True, "model": review.MODEL, "done_reason": "stop",
                    "message": {"role": "assistant", "content": '{"findings":[]}'},
                    "prompt_eval_count": 15,
                }).encode("utf-8")

        with patch.object(review.urllib.request, "urlopen",
                          side_effect=lambda req, timeout: SyntheticOllama(req)):
            reply = review.ask_model(
                BAD["path"], BAD["patch"], evidence_case=evidence_case)
        self.assertEqual(json.loads(reply), {"findings": []})
        return seen[0]

    def test_typed_mode_requires_model_generated_witness_fields(self):
        model_request = self._capture_request(
            (BAD["id"], be.sha256_text(BAD["source"])))
        fields = model_request["format"]["properties"]["findings"]["items"]
        for key in ("case_id", "source_sha256", "input_json",
                    "actual_json", "required_json"):
            self.assertIn(key, fields["required"])
        prompt = model_request["messages"][1]["content"]
        self.assertIn(BAD["id"], prompt)
        self.assertIn(be.sha256_text(BAD["source"]), prompt)
        self.assertNotIn("expected_good", prompt)
        self.assertNotIn("fixed_fixture_label", prompt)

    def test_original_review_mode_is_unchanged_without_typed_opt_in(self):
        original = self._capture_request(None)
        fields = original["format"]["properties"]["findings"]["items"]
        self.assertNotIn("input_json", fields["properties"])
        self.assertNotIn("source_sha256", fields["properties"])

    def test_generic_toy_witness_is_not_leaked_into_future_review_prompts(self):
        model_request = self._capture_request(
            (BAD["id"], be.sha256_text(BAD["source"])))
        prompt = model_request["messages"][1]["content"]
        # The preceding controlled experiment showed a small model copying
        # unrelated demonstration input and output into other cases.
        self.assertNotIn("input_json is '[4]'", prompt)
        self.assertNotIn("actual_json is '5'", prompt)
        self.assertNotIn("required_json is '6'", prompt)
        self.assertIn("input_json must be a JSON-encoded ARRAY", prompt)

    def test_invalid_synthetic_scope_denied_before_network(self):
        import review
        from unittest.mock import patch
        with patch.object(review.urllib.request, "urlopen") as request:
            with self.assertRaisesRegex(ValueError, "Invalid synthetic"):
                review.ask_model(BAD["path"], BAD["patch"],
                                 evidence_case=("not-a-case", "0" * 64))
            request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
