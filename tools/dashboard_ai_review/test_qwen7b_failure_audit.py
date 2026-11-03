"""Fixed 7B failure analysis with executable synthetic oracles, not model scoring."""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import qwen7b_failure_audit as qa

ORIGINAL = qa.load_ledger()


class RevealedQwenSevenBNineCaseTests(unittest.TestCase):
    def test_all_nine_actual_model_mistakes_reproduce_with_fixed_executable_oracles(self):
        result = qa.audit_revealed_failures(ORIGINAL)
        self.assertEqual(result["executed_fixed_witnesses"], 9)
        self.assertEqual(result["false_alert_cases_on_fixed_witnesses"], 3)
        self.assertEqual(result["missed_fixed_defects"], 6)
        self.assertEqual(result["decision"], "QUALITY_HOLD")
        self.assertEqual(result["unseen_cases"], 0)
        self.assertFalse(result["quality_qualified"])
        self.assertFalse(result["independent_review_approved"])
        self.assertFalse(result["release_authorized"])

    def test_all_three_false_alarms_are_normal_cases_with_witness_pass(self):
        data = qa.audit_revealed_failures(ORIGINAL)["cases"]
        false = [x for x in data
                 if x["classification"] == "FALSE_ALERT_ON_FIXED_WITNESS"]
        self.assertEqual({x["family"] for x in false}, {
            "capture_kind", "seven_hour", "boolean_not_count"})
        for item in false:
            with self.subTest(case=item["family"]):
                self.assertEqual(item["raw_model_alerts"], 1)
                self.assertEqual(item["source_citation_only"], 1)
                self.assertFalse(item["prose_independently_verified"])

    def test_all_six_missed_cases_really_violate_fixed_requirement(self):
        data = qa.audit_revealed_failures(ORIGINAL)["cases"]
        missed = [x for x in data
                  if x["classification"] == "MISSED_FIXED_WITNESS"]
        self.assertEqual({x["family"] for x in missed}, {
            "species_filter", "event_id_dedup", "gap_inclusive",
            "save_ack", "free_route_export", "distinct_same_time"})
        for item in missed:
            with self.subTest(case=item["family"]):
                self.assertEqual(item["raw_model_alerts"], 0)
                self.assertEqual(item["source_citation_only"], 0)
                self.assertFalse(item["prose_independently_verified"])

    def test_changed_corpus_or_model_scope_fails_before_witness_execution(self):
        for change in ({"head": "1" * 40},
                       {"frozen_holdout_blob": "e" * 40},
                       {"model_digest": "0" * 64},
                       {"run_id": 1},
                       {"independent_review": True},
                       {"known_diagnostic_only": False}):
            with self.subTest(change=change):
                modified = copy.deepcopy(ORIGINAL)
                modified["source"].update(change)
                runner = Mock()
                with self.assertRaises(ValueError):
                    qa.audit_revealed_failures(modified, runner=runner)
                runner.assert_not_called()

    def test_missing_unknown_duplicate_or_forged_case_is_refused(self):
        for variant in ("missing", "unknown", "duplicate"):
            with self.subTest(variant=variant):
                modified = copy.deepcopy(ORIGINAL)
                if variant == "missing":
                    modified["cases"].pop()
                if variant == "unknown":
                    modified["cases"][0]["case_id"] = "e" * 16
                if variant == "duplicate":
                    modified["cases"][1]["case_id"] = modified["cases"][0]["case_id"]
                with self.assertRaises(ValueError):
                    qa.audit_revealed_failures(modified)

    def test_original_model_log_evidence_blob_is_immutable(self):
        # The archived nine source receipts must match the Git blob that was
        # created from run 41414177747 before any model-quality edits.
        self.assertEqual(len(ORIGINAL["cases"]), 9)
        self.assertEqual(qa.LEDGER_GIT_BLOB,
                         "823222fc16bb397708d7cf0a91658aaadb9dd842")
        self.assertEqual(qa.load_ledger(), ORIGINAL)
        with tempfile.TemporaryDirectory() as directory:
            modified = Path(directory) / "forged.json"
            modified.write_text(qa.LEDGER.read_text(encoding="utf-8")
                                .replace("false", "true", 1), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "LEDGER_TAMPERED"):
                qa.load_ledger(modified)

    def test_model_corpus_sha256_falsification_is_blocked(self):
        modified = copy.deepcopy(ORIGINAL)
        modified["source"]["frozen_holdout_sha256"] = "0" * 64
        runner = Mock()
        with self.assertRaisesRegex(ValueError, "UNAUTHORIZED"):
            qa.audit_revealed_failures(modified, runner=runner)
        runner.assert_not_called()

    def test_model_raw_alerts_cannot_be_relabelled_as_abstentions(self):
        modified = copy.deepcopy(ORIGINAL)
        target = next(x for x in modified["cases"] if x["category"] == "FALSE_ALERT")
        target["model_raw_findings"] = 0
        with self.assertRaises(ValueError):
            qa.audit_revealed_failures(modified)

    def test_fabricated_model_source_quote_is_rejected(self):
        modified = copy.deepcopy(ORIGINAL)
        target = next(x for x in modified["cases"] if x["category"] == "FALSE_ALERT")
        target["model_claims"][0]["code_quote"] = "invented wrong line number"
        with self.assertRaisesRegex(ValueError, "CITATION"):
            qa.audit_revealed_failures(modified)

    def test_model_patch_hash_drift_is_refused(self):
        modified = copy.deepcopy(ORIGINAL)
        modified["cases"][0]["model_patch_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "MODEL_PATCH"):
            qa.audit_revealed_failures(modified)

    def test_real_witness_must_match_stored_claimed_observation_exactly(self):
        modified = copy.deepcopy(ORIGINAL)
        modified["cases"][0]["observed_return"] = True
        with self.assertRaisesRegex(ValueError, "WITNESS_OBSERVATION"):
            qa.audit_revealed_failures(modified)

    def test_python_boolean_and_integer_are_not_conflated(self):
        modified = copy.deepcopy(ORIGINAL)
        target = next(x for x in modified["cases"]
                      if x["family"] == "boolean_not_count")
        target["required_return"] = 0  # bool False != integer 0
        with self.assertRaisesRegex(ValueError, "FROZEN_CASE"):
            qa.audit_revealed_failures(modified)

    def test_model_generated_alternate_inputs_never_go_to_execution_runner(self):
        from test_holdout_v1 import fixture_result
        observed_cases = []
        def trusted(item):
            observed_cases.append((item["id"], item["args"]))
            return fixture_result(item)
        data = qa.audit_revealed_failures(ORIGINAL, runner=trusted)
        self.assertEqual(len(observed_cases), 9)
        self.assertEqual(data["executed_fixed_witnesses"], 9)
        self.assertEqual(
            {x[0] for x in observed_cases},
            {row["case_id"] for row in ORIGINAL["cases"]})
        # No model-proposed input code or shell command is executed.

    def test_no_false_green_from_test_only_execution(self):
        result = qa.audit_revealed_failures(ORIGINAL)
        self.assertEqual(result["reproduced_7b_issued_structured_claims"], 0)
        self.assertEqual(result["model_prose_semantically_approved"], 0)
        self.assertEqual(result["decision"], "QUALITY_HOLD")


if __name__ == "__main__":
    unittest.main()
