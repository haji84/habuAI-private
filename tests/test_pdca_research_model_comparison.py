"""Research model comparison is readable but never production validation."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from master_orchestrator import summarize_research_model_comparison


class ResearchComparisonSummaryTests(unittest.TestCase):
    def test_no_evaluation_is_explicit_not_evaluated(self):
        result = summarize_research_model_comparison(None)
        self.assertEqual(result["status"], "NOT_EVALUATED")
        self.assertFalse(result["production_promotion_allowed"])
        self.assertEqual(result["candidates"], [])

    def test_paired_research_delta_is_not_future_validation(self):
        result = summarize_research_model_comparison({
            "candidates": [
                {"family": "uniform", "fold_nights": ["2026-11-10"],
                 "mean_brier": 0.27, "comparison": {"status": "NOT_VALIDATED"}},
                {"family": "observed_unit_prevalence", "fold_nights": ["2026-11-10"],
                 "mean_brier": 0.22,
                 "comparison": {"mean_brier_improvement": 0.05,
                                "uncertainty": {"interval_95": [-0.02, 0.09]}}},
            ]
        })
        self.assertEqual(result["status"], "RESEARCH_DIAGNOSTIC")
        self.assertFalse(result["production_promotion_allowed"])
        self.assertEqual(result["candidates"][1]["paired_research_mean_brier_improvement_vs_uniform"], 0.05)
        self.assertEqual(result["candidates"][1]["research_bootstrap_interval_95"], [-0.02, 0.09])
        self.assertFalse(result["candidates"][1]["validated_future_night_improvement"])

    def test_missing_and_nonfinite_scores_never_become_improvements(self):
        result = summarize_research_model_comparison({
            "candidates": [{"family": "uniform", "mean_brier": float("nan"),
                            "comparison": {"mean_brier_improvement": float("inf"),
                                           "uncertainty": {"interval_95": [0.0, float("nan")]}}}]
        })
        self.assertEqual(result["status"], "NOT_EVALUATED")
        self.assertIsNone(result["candidates"][0]["research_mean_brier"])
        self.assertIsNone(result["candidates"][0]["paired_research_mean_brier_improvement_vs_uniform"])
        self.assertIsNone(result["candidates"][0]["research_bootstrap_interval_95"])


if __name__ == "__main__":
    unittest.main()
