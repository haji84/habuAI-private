"""Synthetic computation tests; no fixture attests actual search or outcomes."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from master_contracts import digest
from test_research_selection import bind_selection, future_fixture, insufficient_fixture, selection_fixture


class ResearchCompetitionTests(unittest.TestCase):
    def run_core(self, selection=None, rows=None, **options):
        from research_model_adapter import prepare_research_candidates
        rows = future_fixture() if rows is None else rows
        return prepare_research_candidates(
            selection_fixture() if selection is None else selection, rows,
            cutoff_time="2026-10-14T18:00:00+09:00",
            joined_universe_sha256=options.pop("joined_universe_sha256", digest(rows)),
            budget_seconds=options.pop("budget_seconds", 30), **options)

    def test_three_distinct_recipes_use_every_same_future_unit_including_unseen(self):
        result = self.run_core()
        self.assertEqual(result["status"], "DIAGNOSTIC_CANDIDATES_PREPARED")
        self.assertEqual([c["candidate_id"] for c in result["candidates"]], ["uniform", "HB-A0", "HB-B1"])
        ids = {r["row_id"] for r in future_fixture()}
        for candidate in result["candidates"]:
            self.assertEqual(set(candidate["forecast_row_ids"]), ids)
            self.assertEqual(candidate["joined_universe_sha256"], digest(future_fixture()))
            self.assertEqual(candidate["forecast_units"], 3)
            self.assertEqual(candidate["model_sha256"], candidate["model"]["model_sha256"])
        self.assertEqual(result["candidates"][2]["model"]["status"], "DEVELOPMENT_CANDIDATE_FITTED")

    def test_uniform_preserves_smoothed_legacy_definition_and_hierarchy_score_semantics(self):
        selected = selection_fixture()
        row = selected["accepted"][1]
        row.update(label=1, capture_event_ids=["extra-synthetic-event"])
        selected["counts"].update(positives=4, negatives=2)
        result = self.run_core(bind_selection(selected))
        uniform = result["candidates"][0]
        self.assertEqual(uniform["model"]["probability"], 5 / 8)
        self.assertEqual({r["probability"] for r in uniform["prediction"]["unit_predictions"]}, {5 / 8})
        hierarchy = result["candidates"][2]["prediction"]
        self.assertTrue(all("probability" not in r for r in hierarchy["unit_scores"]))
        self.assertTrue(all("rank_score_diagnostic" in r for r in hierarchy["unit_scores"]))

    def test_receipt_never_claims_source_authentication_metrics_winner_or_replay_publication(self):
        result = self.run_core()
        self.assertEqual(result["scientific_status"], "NOT_VALIDATED")
        self.assertEqual(result["source_authentication"], "CALLER_DEPENDENCY_REQUIRED")
        self.assertEqual(result["replay_status"], "PREPARED_NOT_PUBLISHED_OR_TRUSTED_SEALED")
        self.assertFalse(result["official_issuance_authorized"])
        self.assertFalse(result["production_activation_authorized"])
        self.assertEqual(result["validation_status"], "NOT_VALIDATED")
        self.assertNotIn("winner", result)
        self.assertNotIn("metrics", result)
        self.assertEqual(result["receipt_sha256"], digest({k: v for k, v in result.items() if k != "receipt_sha256"}))

    def test_deterministic_and_input_objects_are_not_modified(self):
        selected, rows = selection_fixture(), future_fixture()
        originals = copy.deepcopy((selected, rows))
        self.assertEqual(self.run_core(selected, rows), self.run_core(selected, rows))
        self.assertEqual((selected, rows), originals)

    def test_valid_insufficient_data_never_invokes_a_fitter_or_fabricates_a_model(self):
        from research_model_adapter import prepare_research_candidates
        for selected in (insufficient_fixture(), insufficient_fixture(positive_only=True)):
            with self.subTest(rows=selected["counts"]["accepted_rows"]), \
                 patch("research_model_adapter.fit_shrinkage", side_effect=AssertionError("no fit")), \
                 patch("research_model_adapter.fit_hierarchy", side_effect=AssertionError("no fit")):
                result = self.run_core(selected)
                self.assertEqual(result["status"], "NEED_MORE_DATA")
                self.assertEqual(result["candidates"], [])
                self.assertTrue(result["blockers"])
        with self.assertRaises(ValueError):
            prepare_research_candidates(None, [], cutoff_time="2026-10-14T18:00:00+09:00",
                joined_universe_sha256=digest([]), budget_seconds=30)

    def test_all_forecast_validation_precedes_any_fit_even_with_insufficient_training(self):
        rows = future_fixture()
        rows[-1]["label"] = 1
        for selected in (selection_fixture(), insufficient_fixture()):
            with patch("research_model_adapter.fit_shrinkage", side_effect=AssertionError("no fit")), \
                 patch("research_model_adapter.fit_hierarchy", side_effect=AssertionError("no fit")), \
                 self.assertRaises(ValueError):
                self.run_core(selected, rows)
        with self.assertRaises(ValueError):
            self.run_core(joined_universe_sha256="d" * 64)

    def test_missing_duplicate_or_rebound_candidate_output_is_rejected_without_partial_result(self):
        from models.occupancy_shrinkage import predict_shrinkage
        for mutation in ("missing", "duplicate", "digest", "hash"):
            def bad(*args, **kwargs):
                value = predict_shrinkage(*args, **kwargs)
                if mutation == "missing":
                    value["unit_predictions"].pop()
                elif mutation == "duplicate":
                    value["unit_predictions"][-1] = copy.deepcopy(value["unit_predictions"][0])
                elif mutation == "digest":
                    value["universe_sha256"] = "a" * 64
                else:
                    value["prediction_sha256"] = "a" * 64
                    return value
                value["prediction_sha256"] = digest({k: v for k, v in value.items() if k != "prediction_sha256"})
                return value
            with self.subTest(mutation=mutation), patch("research_model_adapter.predict_shrinkage", side_effect=bad), self.assertRaises(ValueError):
                self.run_core()

    def test_third_model_failure_does_not_publish_prepared_first_two(self):
        with patch("research_model_adapter.rank_hierarchy", side_effect=ValueError("synthetic failure")), self.assertRaisesRegex(ValueError, "synthetic failure"):
            self.run_core()

    def test_rehashed_scores_cannot_change_bound_night_window_or_cell(self):
        from models.occupancy_shrinkage import predict_shrinkage
        for field, wrong in (("cell_x", 7777), ("window_start_jst", "1900-01-01T00:00:00+09:00"),
                             ("operational_night", "1900-01-01")):
            def bad(*args, **kwargs):
                value = predict_shrinkage(*args, **kwargs)
                value["unit_predictions"][0][field] = wrong
                value["prediction_sha256"] = digest({k: v for k, v in value.items() if k != "prediction_sha256"})
                return value
            with self.subTest(field=field), patch("research_model_adapter.predict_shrinkage", side_effect=bad), self.assertRaises(ValueError):
                self.run_core()
        from models.hierarchy_shrinkage import rank_hierarchy
        def wrong_hierarchy_cell(*args, **kwargs):
            value = rank_hierarchy(*args, **kwargs)
            value["unit_scores"][0]["cell_id"] = "utm52n_100m_7777_30000"
            value["prediction_sha256"] = digest({k: v for k, v in value.items() if k != "prediction_sha256"})
            return value
        with patch("research_model_adapter.rank_hierarchy", side_effect=wrong_hierarchy_cell), self.assertRaises(ValueError):
            self.run_core()

    def test_insufficient_data_sealing_also_checks_deadline_before_return(self):
        from research_model_adapter import ResearchBudgetExhausted, _seal
        clock = [0]
        def late(value, field):
            result = _seal(value, field)
            clock[0] = 31
            return result
        with patch("research_model_adapter.time.monotonic", side_effect=lambda: clock[0]), \
             patch("research_model_adapter._seal", side_effect=late), \
             self.assertRaises(ResearchBudgetExhausted):
            self.run_core(insufficient_fixture())

    def test_expired_shared_budget_raises_before_fit_and_after_last_model(self):
        from research_model_adapter import ResearchBudgetExhausted
        with patch("research_model_adapter.time.monotonic", side_effect=[0, 31]), \
             patch("research_model_adapter.fit_shrinkage", side_effect=AssertionError("no fit")), \
             self.assertRaises(ResearchBudgetExhausted):
            self.run_core()
        from models.hierarchy_shrinkage import rank_hierarchy
        clock = [0]
        def late(*args, **kwargs):
            value = rank_hierarchy(*args, **kwargs)
            clock[0] = 31
            return value
        with patch("research_model_adapter.time.monotonic", side_effect=lambda: clock[0]), \
             patch("research_model_adapter.rank_hierarchy", side_effect=late), \
             self.assertRaises(ResearchBudgetExhausted):
            self.run_core()

    def test_invalid_budget_is_rejected_without_changing_existing_maximum(self):
        for budget in (True, 0, -1, float("inf"), float("nan"), 301, "30"):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                self.run_core(budget_seconds=budget)

    def test_pure_computation_never_opens_any_source_or_confirmation_payload(self):
        with patch("builtins.open", side_effect=AssertionError("no filesystem reads")), \
             patch.object(Path, "open", side_effect=AssertionError("no filesystem reads")):
            self.assertEqual(self.run_core()["status"], "DIAGNOSTIC_CANDIDATES_PREPARED")


if __name__ == "__main__":
    unittest.main()
