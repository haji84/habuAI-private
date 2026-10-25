"""Candidate model learns measured exposed road-time units, never hindsight weather."""
import copy
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import prospective_candidate_model as p


def history_rows():
    rows = []
    base = datetime.fromisoformat("2026-10-01T00:00:00+09:00")
    for n in range(7):
        date = (base + timedelta(days=n)).date().isoformat()
        later = (base + timedelta(days=n+1)).date().isoformat()
        for cell in range(4):
            rows.append({
                "operational_night": date,
                "cell_id": f"utm52n_100m_{5000+cell}_{31000+n}",
                "window_start_jst": date + "T21:00:00+09:00",
                "forecast_cutoff": date + "T18:00:00+09:00",
                "features_available_at": date + "T17:00:00+09:00",
                "weather_source_role": "EX_ANTE_FORECAST",
                "features_source_sha256": "a"*64,
                "exposure_proof": "GPX_PASSAGE_VALIDATED",
                "outcome_source_sha256": "b"*64,
                "owner_capture_count": 1 if cell == n % 4 else 0,
                "outcome_available_at": later + "T09:00:00+09:00",
                "temperature_c": 21.0+cell, "humidity_pct": 85.0,
                "precipitation_mm": 0.1*n, "slope_deg": 12.0+cell,
                "tpi_m": -3.0+cell, "road_length_m": 30.0+cell,
                "wind_cross_road_proxy": 0.5,
            })
    return rows


class CandidateTests(unittest.TestCase):
    def test_training_temporal_holdout_and_prospective_rank(self):
        model = p.train_candidate(history_rows(),
                                  training_cutoff="2026-10-10T00:00:00+09:00")
        self.assertEqual(len(model["train_nights"]), 5)
        self.assertEqual(len(model["untouched_holdout_nights"]), 2)
        self.assertFalse(model["production_activation_authorized"])
        self.assertFalse(model["official_stage1_recall_computed"])
        self.assertGreaterEqual(model["holdout_brier_diagnostic"], 0)
        future = copy.deepcopy(history_rows()[0])
        future.update(operational_night="2026-10-24",
                      window_start_jst="2026-10-24T21:00:00+09:00",
                      forecast_cutoff="2026-10-24T16:00:00+09:00",
                      features_available_at="2026-10-24T15:00:00+09:00")
        for k in ("exposure_proof", "owner_capture_count", "outcome_available_at",
                  "outcome_source_sha256"):
            future.pop(k)
        forecast = p.rank_future(model, [future],
                                 issued_at="2026-10-24T17:00:00+09:00",
                                 operational_night="2026-10-24")
        self.assertEqual(len(forecast["targets_100m_10min"]), 1)
        self.assertEqual(forecast["area_rank_top10"][0]["area_1km"],
                         "utm52n_1km_500_3100")
        self.assertFalse(forecast["formal_100m_10min_eligible"])
        self.assertFalse(forecast["production_p0_freeze_allowed"])
        self.assertEqual(forecast["route_candidates_A_B_C"], "NOT_PRODUCED")

    def test_future_weather_leakage_cannot_enter_train(self):
        rows = history_rows()
        rows[0]["features_available_at"] = "2026-10-01T20:00:00+09:00"
        with self.assertRaises(p.CandidateInputError):
            p.train_candidate(rows, training_cutoff="2026-10-10T00:00:00+09:00")

    def test_unvisited_zero_is_unknown_not_negative(self):
        rows = history_rows()
        rows[0]["exposure_proof"] = "UNKNOWN"
        with self.assertRaises(p.CandidateInputError):
            p.train_candidate(rows, training_cutoff="2026-10-10T00:00:00+09:00")

    def test_recent_label_is_not_training_input(self):
        rows = history_rows()
        rows[0]["outcome_available_at"] = "2026-10-11T00:00:00+09:00"
        with self.assertRaises(p.CandidateInputError):
            p.train_candidate(rows, training_cutoff="2026-10-10T00:00:00+09:00")

    def test_no_two_night_training_shortcut(self):
        with self.assertRaises(p.CandidateInputError):
            p.train_candidate(history_rows()[:20],
                              training_cutoff="2026-10-10T00:00:00+09:00")

    def test_sightings_are_never_automatically_captures(self):
        rows = history_rows()
        rows[0].pop("owner_capture_count")
        rows[0]["sighting_count"] = 1
        with self.assertRaises(p.CandidateInputError):
            p.train_candidate(rows, training_cutoff="2026-10-10T00:00:00+09:00")

    def test_models_cannot_rank_preissuance_targets(self):
        model = p.train_candidate(history_rows(),
                                  training_cutoff="2026-10-10T00:00:00+09:00")
        future = copy.deepcopy(history_rows()[0])
        future.update(operational_night="2026-10-24",
                      window_start_jst="2026-10-24T16:00:00+09:00",
                      forecast_cutoff="2026-10-24T15:00:00+09:00",
                      features_available_at="2026-10-24T14:00:00+09:00")
        for key in ("exposure_proof", "owner_capture_count", "outcome_available_at", "outcome_source_sha256"):
            future.pop(key)
        with self.assertRaises(p.CandidateInputError):
            p.rank_future(model, [future],
                          issued_at="2026-10-24T17:00:00+09:00",
                          operational_night="2026-10-24")

    def test_training_fingerprint_reproducible(self):
        one = p.train_candidate(history_rows(), training_cutoff="2026-10-10T00:00:00+09:00")
        two = p.train_candidate(history_rows(), training_cutoff="2026-10-10T00:00:00+09:00")
        self.assertEqual(one["model_sha256"], two["model_sha256"])


if __name__ == "__main__":
    unittest.main()
