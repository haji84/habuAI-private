"""P0-independent descriptive PDCA: missing evidence limits only dependent claims."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pdca_pipeline

NIGHT = "2026-11-17"


def audit_fixture(*, capture=True, exposure=True):
    events = ([{"event_id": "owner-C1", "capture_count": 2,
                "datetime_jst": "2026-11-17T22:05:00+09:00",
                "night_date": NIGHT, "latitude": 28.15, "longitude": 129.30}]
              if capture else [])
    units = ([{"night_date": NIGHT, "window_start_jst": "2026-11-17T22:00:00+09:00",
               "cell_x": 1, "cell_y": 2, "point_count": 3,
               "observation": "UNKNOWN", "label": None}]
             if exposure else [])
    return {"status": "PARTIAL", "capture_audit": {"events": events},
            "observation_units": units,
            "input_requirements": [{"code": "SOURCE_ROLE_UNKNOWN",
                                    "kind": "DATA_BLOCKED"}]}


class IndependentResearchContinuationTests(unittest.TestCase):
    def test_no_p0_still_analyses_capture_and_unknown_exposure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = pdca_pipeline.run_pipeline(root, NIGHT, audited_evidence=audit_fixture())
            stages = {row["name"]: row["status"] for row in result["stages"]}
            self.assertEqual(result["overall_status"], "BLOCKED")
            self.assertEqual(result["prediction_scope"], "NOT_AVAILABLE")
            self.assertEqual(stages["load_frozen_predictions"], "BLOCKED")
            self.assertEqual(stages["research_capture_summary"], "PASS")
            self.assertEqual(stages["feature_analysis"], "PASS")
            self.assertEqual(stages["diagnostic_ablation"], "PARTIAL")
            self.assertIsNone(result["p0_score"])
            self.assertEqual(result["realtime_scores"], [])
            research = result["research_capture_summary"]
            self.assertEqual(research["recorded_capture_individuals"], 2)
            self.assertEqual(research["recorded_capture_events"], 1)
            self.assertEqual(research["capture_by_hour_jst"], {"22": 2})
            self.assertEqual(research["unknown_exposure_units"], 1)
            self.assertEqual(research["qualified_observed_units"], 0)
            self.assertFalse(research["recorded_zero_is_habu_absence"])
            self.assertIsNone(research["formal_prediction_accuracy"])
            self.assertNotIn("latitude", json.dumps(research))
            self.assertEqual(result["model_comparison"]["status"], "NOT_EVALUATED")
            self.assertIsNone(result["model_comparison"]["delta"])
            self.assertTrue(any(row["reason"] == "NO_FROZEN_PREDICTION"
                                for row in result["research_next_steps"]))
            report = (root / "reports" / "pdca" / NIGHT / "pdca_report.md").read_text(encoding="utf-8")
            self.assertIn("Research-only observations", report)
            self.assertIn("NOT_EVALUATED", report)

    def test_capture_only_research_continues_without_gpx(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = pdca_pipeline.run_pipeline(Path(tmp), NIGHT,
                                                audited_evidence=audit_fixture(exposure=False))
            stages = {row["name"]: row["status"] for row in result["stages"]}
            self.assertEqual(stages["load_actual_evidence"], "PARTIAL")
            self.assertEqual(stages["research_capture_summary"], "PASS")
            self.assertEqual(stages["build_exposure"], "PARTIAL")
            self.assertEqual(stages["feature_analysis"], "PARTIAL")
            self.assertEqual(result["research_capture_summary"]["recorded_capture_individuals"], 2)
            self.assertEqual(result["research_capture_summary"]["sampled_exposure_units"], 0)
            self.assertTrue(any(row["reason"] == "NO_GPX_EXPOSURE"
                                for row in result["research_next_steps"]))

    def test_gpx_without_captures_does_not_become_negative(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = pdca_pipeline.run_pipeline(Path(tmp), NIGHT,
                                                audited_evidence=audit_fixture(capture=False))
            research = result["research_capture_summary"]
            self.assertEqual(research["recorded_capture_individuals"], 0)
            self.assertEqual(research["unknown_exposure_units"], 1)
            self.assertEqual(research["qualified_observed_units"], 0)
            self.assertFalse(research["recorded_zero_is_habu_absence"])
            self.assertTrue(any(row["reason"] == "ALL_EXPOSURE_UNKNOWN"
                                for row in result["research_next_steps"]))


if __name__ == "__main__":
    unittest.main()
