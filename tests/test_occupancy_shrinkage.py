"""Controlled binary-unit examples; no real Habu fit or field performance."""
import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from test_research_selection import (fixture_digest, selection_fixture,
    insufficient_fixture, future_fixture, bind_selection)


class OccupancyShrinkageTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.find_spec("models.occupancy_shrinkage") if (ROOT / "src/models").exists() else None
        self.assertIsNotNone(spec, "area shrinkage model is missing")
        from models import occupancy_shrinkage
        self.module = occupancy_shrinkage

    def fit(self, selection=None):
        return self.module.fit_shrinkage(selection_fixture() if selection is None else selection)

    def predict(self, model, rows=None):
        rows = future_fixture() if rows is None else rows
        return self.module.predict_shrinkage(model, rows,
            cutoff_time="2026-10-14T18:00:00+09:00", universe_sha256=fixture_digest(rows))

    def test_beta_binomial_area_estimates_are_pooled_toward_global_prevalence(self):
        model = self.fit()["model"]
        self.assertAlmostEqual(model["global_probability"], 0.5)
        self.assertAlmostEqual(model["areas"]["utm52n_1km_400_3000"]["probability"], 4 / 7)
        self.assertAlmostEqual(model["areas"]["utm52n_1km_401_3000"]["probability"], 3 / 7)
        self.assertEqual(model["counts"]["accepted_rows"], 6)

    def test_global_beta_prior_changes_imbalanced_small_sample_prediction(self):
        value = selection_fixture()
        value["accepted"][-1].update(label=0, capture_event_ids=[])
        value["counts"].update(positives=2, negatives=4)
        model = self.fit(bind_selection(value))["model"]
        self.assertAlmostEqual(model["global_probability"], 3 / 8)
        self.assertAlmostEqual(model["areas"]["utm52n_1km_400_3000"]["probability"], 0.5)

    def test_unseen_area_uses_global_and_every_supplied_universe_row_is_scored(self):
        actual = self.predict(self.fit()["model"])
        self.assertEqual([r["row_id"] for r in actual["unit_predictions"]],
            ["future-a", "future-b", "future-unseen"])
        self.assertEqual([r["probability"] for r in actual["unit_predictions"]], [4 / 7, 3 / 7, 0.5])
        self.assertEqual(actual["universe_sha256"], fixture_digest(future_fixture()))
        self.assertNotIn("candidate_targets_100m_10min", actual)

    def test_insufficient_and_positive_only_input_returns_no_model(self):
        for value in (insufficient_fixture(), insufficient_fixture(positive_only=True)):
            actual = self.fit(value)
            self.assertEqual(actual["status"], "NEED_MORE_DATA")
            self.assertIsNone(actual["model"])
            self.assertTrue(actual["blockers"])

    def test_model_is_content_bound_reproducible_and_cannot_authorize_science(self):
        value = selection_fixture()
        before = copy.deepcopy(value)
        first, second = self.fit(value), self.fit(value)
        self.assertEqual(first, second)
        self.assertEqual(value, before)
        model = first["model"]
        self.assertEqual(model["selection_sha256"], value["selection_sha256"])
        self.assertEqual(model["model_sha256"], fixture_digest(
            {k: v for k, v in model.items() if k != "model_sha256"}))
        self.assertEqual(model["config_sha256"], fixture_digest(model["config"]))
        self.assertEqual(model["scientific_status"], "NOT_VALIDATED")
        self.assertFalse(model["production_activation_authorized"])
        self.assertFalse(first["official_issuance_authorized"])
        self.assertEqual(first["fit_evidence"]["independent_confirmation"], "NOT_PERFORMED")

    def test_changed_bound_selection_changes_model_identity(self):
        value = selection_fixture()
        first = self.fit(value)["model"]
        value["corpus_sha256"] = "d" * 64
        second = self.fit(bind_selection(value))["model"]
        self.assertNotEqual(first["model_sha256"], second["model_sha256"])
        self.assertEqual(first["areas"], second["areas"])

    def test_later_unused_source_metadata_remain_auditable_without_becoming_predictors(self):
        value = selection_fixture()
        value["source_sha256"]["evidence/unused-later.json"] = "e" * 64
        value["source_received_at"]["evidence/unused-later.json"] = "2026-10-16T00:00:00+09:00"
        fitted = self.fit(bind_selection(value))
        model = fitted["model"]
        self.assertEqual(model["source_received_at"], value["source_received_at"])
        self.assertEqual([r["probability"] for r in self.predict(model)["unit_predictions"]],
            [4 / 7, 3 / 7, 0.5])

    def test_malformed_selection_never_becomes_a_small_sample_fit(self):
        value = selection_fixture()
        value["accepted"][0]["label"] = None
        with self.assertRaises(ValueError):
            self.fit(bind_selection(value))

    def test_serialized_model_tampering_and_privilege_changes_are_rejected(self):
        original = self.fit()["model"]
        mutations = (
            lambda m: m.update(global_probability=0.9),
            lambda m: m.update(production_activation_authorized=True),
            lambda m: m["config"].update(area_prior_strength=100),
            lambda m: m["areas"]["utm52n_1km_400_3000"].update(probability=1.0),
            lambda m: m.update(scientific_status="VALIDATED"),
            lambda m: m.update(executable="anything"),
        )
        for mutate in mutations:
            for rehash in (False, True):
                changed = copy.deepcopy(original)
                mutate(changed)
                if rehash:
                    changed["model_sha256"] = fixture_digest(
                        {k: v for k, v in changed.items() if k != "model_sha256"})
                with self.subTest(mutate=mutate, rehash=rehash), self.assertRaises(ValueError):
                    self.predict(changed)

    def test_forecast_digest_or_outcome_fields_fail_before_scoring(self):
        model = self.fit()["model"]
        with self.assertRaises(ValueError):
            self.module.predict_shrinkage(model, future_fixture(),
                cutoff_time="2026-10-14T18:00:00+09:00", universe_sha256="e" * 64)
        rows = future_fixture()
        rows[0]["label"] = 1
        with self.assertRaises(ValueError):
            self.predict(model, rows)

    def test_model_fit_cutoff_is_strictly_before_forecast_cutoff_and_night(self):
        model = self.fit()["model"]
        rows = future_fixture()
        for row in rows:
            row["cutoff_time"] = model["fit_cutoff"]
        with self.assertRaises(ValueError):
            self.module.predict_shrinkage(model, rows, cutoff_time=model["fit_cutoff"],
                universe_sha256=fixture_digest(rows))

    def test_rehashed_model_cannot_claim_training_before_its_training_nights(self):
        model = self.fit()["model"]
        model["fit_cutoff"] = "2026-08-01T00:00:00+09:00"
        model["model_sha256"] = fixture_digest({k: v for k, v in model.items() if k != "model_sha256"})
        with self.assertRaises(ValueError):
            self.predict(model)

    def test_latest_actual_training_window_must_strictly_precede_serialized_fit_cutoff(self):
        original = self.fit()["model"]
        for cutoff in ("2026-09-03T07:01:00+09:00", "2026-09-03T20:00:00+09:00"):
            model = copy.deepcopy(original)
            model["fit_cutoff"] = cutoff
            model["model_sha256"] = fixture_digest({k: v for k, v in model.items() if k != "model_sha256"})
            with self.subTest(cutoff=cutoff), self.assertRaises(ValueError):
                self.predict(model)

    def test_training_window_max_is_aware_aligned_and_matches_latest_training_night(self):
        original = self.fit()["model"]
        for window in (None, True, "2026-09-03T20:00:00", "2026-09-03T20:05:00+09:00",
                       "2026-09-02T20:00:00+09:00"):
            model = copy.deepcopy(original)
            model["training_window_start_max"] = window
            model["model_sha256"] = fixture_digest({k: v for k, v in model.items() if k != "model_sha256"})
            with self.subTest(window=window), self.assertRaises(ValueError):
                self.predict(model)

    def test_actual_training_window_max_is_bound_and_accepts_equivalent_timezone(self):
        model = self.fit()["model"]
        self.assertEqual(model.get("training_window_start_max"), "2026-09-03T20:00:00+09:00")
        expected = self.predict(model)["unit_predictions"]
        model["training_window_start_max"] = "2026-09-03T11:00:00Z"
        model["model_sha256"] = fixture_digest({k: v for k, v in model.items() if k != "model_sha256"})
        self.assertEqual(self.predict(model)["unit_predictions"], expected)

    def test_hashing_predictions_does_not_apply_the_smaller_input_byte_limit(self):
        from models import research_selection
        model = self.fit()["model"]
        rows = []
        for index in range(25):
            row = copy.deepcopy(future_fixture()[0])
            row.update(row_id=f"full-{index}", utm_x_m=400050 + index * 100,
                features={}, feature_source_refs={}, feature_available_at={})
            rows.append(row)
        encoded = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False,
            separators=(",", ":"), allow_nan=False).encode("utf-8")
        input_bound = max(len(encoded(model)), len(encoded(rows)))
        # This lowers a capacity limit, without dropping any forecast unit.
        with patch.object(research_selection, "MAX_JSON_BYTES", input_bound):
            actual = self.predict(model, rows)
        self.assertEqual(len(actual["unit_predictions"]), 25)
        self.assertGreater(len(encoded(actual)), input_bound)


if __name__ == "__main__":
    unittest.main()
