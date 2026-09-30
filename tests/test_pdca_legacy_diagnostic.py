import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import pdca_pipeline


class PDCALegacyDiagnosticTests(unittest.TestCase):
    def test_valid_legacy_diagnostic_is_loaded_without_becoming_official_kpi(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"reports"/"legacy_chronological_walkforward.json"
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps({
                "evaluation_class":"LEGACY_10M_CHRONOLOGICAL_DIAGNOSTIC",
                "official_100m_10min_kpi":False,
                "future_leakage_guard":True,
                "available_nights":["2026-08-13","2026-08-15","2026-08-17"],
                "summary":{"completed_folds":1,"mean_brier":0.1},
                "group_ablation":[
                    {"omitted_group":"weather","mean_brier_delta_vs_full":-0.02},
                    {"omitted_group":"biology","mean_brier_delta_vs_full":0.03}
                ],
                "top_standardized_coefficients":[],
                "warning":"diagnostic only"
            }),encoding="utf-8")

            d=pdca_pipeline.load_legacy_chronological_diagnostic(root)
            self.assertEqual(d["status"],"VALID")
            self.assertFalse(d["official_100m_10min_kpi"])
            self.assertTrue(d["future_leakage_guard"])

            h=pdca_pipeline.legacy_candidate_hypotheses(d)
            by_group={x["feature_group"]:x for x in h}
            self.assertEqual(
                by_group["weather"]["candidate_action"],
                "candidate_for_respecification_or_regularization"
            )
            self.assertEqual(
                by_group["biology"]["candidate_action"],
                "retain_and_retest_in_current_100m_model"
            )
            self.assertTrue(all(x["decision_status"]=="HYPOTHESIS_ONLY" for x in h))


    def test_missing_optional_legacy_diagnostic_does_not_create_hypotheses(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            self.assertIsNone(pdca_pipeline.load_legacy_chronological_diagnostic(root))
            self.assertEqual(pdca_pipeline.legacy_candidate_hypotheses(None),[])

    def test_invalid_contract_is_not_used_for_hypotheses(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"reports"/"legacy_chronological_walkforward.json"
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps({
                "evaluation_class":"LEGACY_10M_CHRONOLOGICAL_DIAGNOSTIC",
                "official_100m_10min_kpi":False,
                "future_leakage_guard":False,
                "group_ablation":[
                    {"omitted_group":"weather","mean_brier_delta_vs_full":-0.02}
                ]
            }),encoding="utf-8")
            d=pdca_pipeline.load_legacy_chronological_diagnostic(root)
            self.assertEqual(d["status"],"INVALID")
            self.assertEqual(pdca_pipeline.legacy_candidate_hypotheses(d),[])


if __name__=="__main__":
    unittest.main()
