"""Contract tests: PR #33-shaped two-window OSM snapshot -> PR #32 join -> model.

All values and model weights below are synthetic. Passing tests NEVER validates
real forecasting skill, trusted source availability, Champion or ORIGINAL P0.
"""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from master_contracts import canonical_bytes, digest
from prospective_spacetime import VERSION, infer_candidate

NIGHT = "2026-10-14"
CUTOFF = NIGHT + "T18:00:00+09:00"
NOW = datetime.fromisoformat(NIGHT + "T18:30:00+09:00")
READY = NIGHT + "T17:00:00+09:00"
NAMES = ("road_axial_cos", "road_axial_sin", "road_length_m")


def save(root, name, value):
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(value) + b"\n"
    p.write_bytes(data)
    return {"path": name, "sha256": hashlib.sha256(data).hexdigest(),
            "available_at": READY}


class SpacetimeCandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.universe = {
            "schema_version": "1.0", "source_type": "EX_ANTE_FORECAST",
            "geographic_domain": {
                "crs": "EPSG:32652", "islands": ["奄美大島", "加計呂麻島"],
                "source_class": "osm_auxiliary",
                "official_road_eligibility": "NOT_VALIDATED",
            },
            "rows": [
                {
                    "row_id": f"utm52n_100m_{4000+i}_{30000}@w{i}",
                    "operational_night": NIGHT, "cutoff_time": CUTOFF,
                    "window_start_jst": f"{NIGHT}T21:{i*10:02d}:00+09:00",
                    "utm_x_m": 400050 + i * 100, "utm_y_m": 3000050,
                } for i in range(2)
            ],
        }
        self.features = [
            {"schema_version": "1.0", "feature_name": name,
             "use_role": "static_predictor", "operational_night": NIGHT,
             "cutoff_time": CUTOFF, "available_at": READY,
             "values": {r["row_id"]: (
                 (5.0 + i * 5) if name == "road_length_m" else
                 (1.0 if name == "road_axial_cos" else 0.0)
             ) for i, r in enumerate(self.universe["rows"])}}
            for name in NAMES
        ]
        self.model = {
            "schema_version": "1.0",
            "model_type": "linear_logit_100m_10min",
            "implementation_version": VERSION,
            "qualification": "UNVALIDATED_CANDIDATE",
            "coefficients": {"road_length_m": 0.3,
                             "road_axial_cos": 0.0, "road_axial_sin": 0.0},
            "intercept": -2.0, "threshold": 0.5, "max_candidates": 1,
            "feature_schema_sha256": digest(sorted(NAMES)),
            "training_cutoff": "2026-09-01T12:00:00+09:00",
            "training_data_sha256": "a" * 64,
            "produced_outputs": ["unit_probability", "spatiotemporal_ranking"],
            "time_basis": "jst_clock_cyclic",
            "time_coefficients": {"sin": 0.4, "cos": -0.3},
        }
        self.publish()

    def publish(self):
        self.model["model_sha256"] = digest({
            k: v for k, v in self.model.items() if k != "model_sha256"})
        self.mref = save(self.root, "models/candidates/linear.json", self.model)
        self.uref = save(self.root, "features/sandbox/universe.json", self.universe)
        refs = [save(self.root, f"features/sandbox/{f['feature_name']}.json", f)
                for f in self.features]
        snapshot = {
            "schema_version": "2.0", "operational_night": NIGHT,
            "cutoff_time": CUTOFF, "universe": self.uref,
            "features": refs,
            "feature_schema_sha256": digest(sorted(NAMES)),
            "qualification": "AUXILIARY_ROADS_INPUT_ONLY_NOT_OFFICIAL",
        }
        self.sref = save(self.root, "features/sandbox/snapshot.json", snapshot)

    def infer(self, **kw):
        return infer_candidate(
            self.root, self.sref["path"], self.sref["sha256"],
            NIGHT, kw.get("now", NOW), self.mref["path"],
            kw.get("model_sha", self.mref["sha256"]),
            budget_seconds=kw.get("budget", 30.0),
        )

    def test_real_input_validator_join_and_time_specific_inference(self):
        result = self.infer()
        self.assertFalse(result["official_issuance_authorized"])
        self.assertEqual(result["prediction_class"], "CANDIDATE_DIAGNOSTIC_NOT_ORIGINAL")
        self.assertEqual(result["formal_100m_10min_status"], "NOT_VALIDATED")
        self.assertEqual(len(result["unit_predictions"]), 2)
        first, second = result["unit_predictions"]
        self.assertLess(first["candidate_probability"], second["candidate_probability"])
        self.assertEqual(second["window_start_jst"], NIGHT + "T21:10:00+09:00")
        self.assertEqual(len(result["candidate_targets_100m_10min"]), 1)
        self.assertEqual(result["candidate_targets_100m_10min"][0]["row_id"], second["row_id"])
        self.assertEqual(set(result["consumed_sha256"]), {
            self.mref["path"], self.sref["path"], self.uref["path"],
            *(f"features/sandbox/{name}.json" for name in NAMES),
        })
        self.assertFalse((self.root / "predictions/original").exists())

    def test_future_clock_terms_distinguish_same_road_cell_across_windows(self):
        # Equal spatial features and same cell. Only known-ahead clock changes.
        self.universe["rows"][1]["utm_x_m"] = self.universe["rows"][0]["utm_x_m"]
        for feature in self.features:
            values = feature["values"]
            values[self.universe["rows"][1]["row_id"]] = values[self.universe["rows"][0]["row_id"]]
        self.publish()
        p = self.infer()["unit_predictions"]
        self.assertNotEqual(p[0]["candidate_probability"], p[1]["candidate_probability"])
        self.assertEqual(p[0]["cell_x_100m"], p[1]["cell_x_100m"])

    def test_model_hash_and_self_digest_are_both_required(self):
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.infer(model_sha="0" * 64)
        self.model["intercept"] = 9
        self.mref = save(self.root, self.mref["path"], self.model)
        with self.assertRaisesRegex(ValueError, "content digest"):
            self.infer()

    def test_feature_changes_probability_only_with_new_bound_snapshot(self):
        before = self.infer()["unit_predictions"]
        self.features[0]["values"][self.universe["rows"][0]["row_id"]] = 7.0
        self.publish()
        after = self.infer()["unit_predictions"]
        if self.features[0]["feature_name"] == "road_axial_cos":
            self.assertEqual(before, after)  # zero-weight feature cannot change results
        else:
            self.assertNotEqual(before, after)

    def test_feature_schema_mismatch_fails_closed(self):
        self.model["coefficients"] = {"road_length_m": 0.2}
        self.model["feature_schema_sha256"] = digest(["road_length_m"])
        self.publish()
        with self.assertRaisesRegex(ValueError, "registered model"):
            self.infer()

    def test_outcome_leak_is_rejected(self):
        self.universe["rows"][0]["capture_count"] = 4
        self.publish()
        with self.assertRaisesRegex(ValueError, "Post-outcome"):
            self.infer()

    def test_future_information_and_expired_window_rejected(self):
        self.model["training_cutoff"] = CUTOFF
        self.publish()
        with self.assertRaisesRegex(ValueError, "training cutoff"):
            self.infer()
        self.model["training_cutoff"] = "2026-09-01T12:00:00+09:00"
        self.publish()
        with self.assertRaisesRegex(ValueError, "expired"):
            self.infer(now=datetime.fromisoformat(NIGHT + "T21:00:00+09:00"))

    def test_privileged_or_unbounded_model_rejected(self):
        for update in [
            {"qualification": "PRODUCTION"},
            {"produced_outputs": ["OFFICIAL_P0"]},
            {"max_candidates": 101},
            {"threshold": float("nan")},
        ]:
            with self.subTest(update=update):
                self.model.update(update)
                if isinstance(self.model["threshold"], float) and self.model["threshold"] != self.model["threshold"]:
                    # JSON canonical writer itself refuses NaN.
                    with self.assertRaises(ValueError):
                        self.publish()
                else:
                    self.publish()
                    with self.assertRaises(ValueError):
                        self.infer()
                self.model.update({
                    "qualification": "UNVALIDATED_CANDIDATE",
                    "produced_outputs": ["unit_probability", "spatiotemporal_ranking"],
                    "max_candidates": 1, "threshold": 0.5,
                })

    def test_corrupt_feature_bytes_are_not_ignored(self):
        path = self.root / f"features/sandbox/{NAMES[0]}.json"
        path.write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.infer()

    def test_cutoff_budget_and_model_source_are_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "budget"):
            self.infer(budget=0)
        with self.assertRaisesRegex(ValueError, "budget"):
            self.infer(budget=301)
        with self.assertRaisesRegex(ValueError, "models/candidates"):
            infer_candidate(self.root, self.sref["path"], self.sref["sha256"],
                            NIGHT, NOW, "data/raw/fake.json", self.mref["sha256"])
        self.assertFalse((self.root / "predictions/original").exists())


if __name__ == "__main__":
    unittest.main()
