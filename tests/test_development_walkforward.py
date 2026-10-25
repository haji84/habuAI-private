"""Synthetic development outcomes must use the same scoped eligibility gates."""
import unittest

import test_training_corpus as corpus_tests
from development_walkforward import evaluate_development_folds


class DevelopmentEligibilityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = corpus_tests.AuditedTrainingTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.heldout = self.fixture.add_development_holdout(observation="observed_negative")

    def evaluate(self):
        self.fixture.publish()
        return evaluate_development_folds(
            self.fixture.root, self.fixture.path, self.fixture.sha,
            ("2026-10-20",), ("road_length_m",), "2026-10-21T22:00:00+09:00",
        )

    def test_only_source_bound_search_and_complete_outcomes_can_be_scored(self):
        result = self.evaluate()
        self.assertEqual(result["eligible_evaluated_nights"], 1)
        self.assertEqual(result["folds"][0]["observed_units"], 1)
        self.assertFalse(result["official_accuracy_evaluated"])
        self.assertEqual(result["independent_confirmation"], "NOT_PERFORMED")

    def test_passage_is_not_scored_as_a_confirmed_negative(self):
        self.heldout["search_role"] = "PASSAGE"
        with self.assertRaisesRegex(ValueError, "independent scope"):
            self.evaluate()

    def test_missing_search_or_completeness_receipt_blocks_scoring(self):
        for key in ("active_search_ref", "complete_outcome_ref"):
            with self.subTest(missing=key):
                saved = self.heldout.pop(key)
                with self.assertRaisesRegex(ValueError, "independent scope"):
                    self.evaluate()
                self.heldout[key] = saved

    def test_wrong_cell_scope_does_not_certify_a_heldout_negative(self):
        self.fixture.change_scope_receipt(self.heldout, "complete_outcome_ref", lambda receipt:
                                         receipt["scope"].update(cell_x=4101))
        with self.assertRaisesRegex(ValueError, "NEGATIVE_SCOPE_MISMATCH"):
            self.evaluate()

    def test_qualification_equal_to_evaluation_time_is_not_usable(self):
        self.fixture.change_scope_receipt(self.heldout, "active_search_ref", lambda receipt:
                                         receipt.update(qualified_at="2026-10-21T22:00:00+09:00"))
        with self.assertRaisesRegex(ValueError, "NEGATIVE_SCOPE_NOT_READY"):
            self.evaluate()

    def test_outcome_source_cannot_supply_a_heldout_predictor(self):
        self.heldout["feature_source_refs"]["road_length_m"] = [self.heldout["outcome_source_ref"]]
        with self.assertRaisesRegex(ValueError, "feature-role"):
            self.evaluate()

    def test_heldout_feature_equal_to_fold_cutoff_is_not_usable(self):
        self.heldout["feature_available_at"]["road_length_m"] = "2026-10-20T06:59:59.999999+09:00"
        with self.assertRaisesRegex(ValueError, "FEATURE_NOT_READY_FOR_FIT"):
            self.evaluate()


if __name__ == "__main__":
    unittest.main()
