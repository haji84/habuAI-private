"""Synthetic contract tests; no owner location or private records committed."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from research_nightcount_clock import compare_nightcount, compare_eventclock


def count_source():
    values = [1, 0, 2, 3, 2, 1, 4]
    return {
        "schema_version": "habu-research-nightcount-poisson-v1.2",
        "training_nights": [
            {"night": f"2026-10-{i+1:02d}", "count": k,
             "effort_hours_proxy": 4.0 + (i % 2)}
            for i, k in enumerate(values)
        ],
        "owner_captures": sum(values), "nights": len(values),
        "elapsed_session_hours_proxy": sum(4.0 + (i % 2) for i in range(len(values))),
    }


def clock_source():
    old, added = [3, 2, 5, 6, 4, 1], [1, 0, 1, 0, 0, 0]
    return {
        "schema_version": "habu-positive-event-clock-research-v1.2",
        "prior_histogram": old, "nov_increment_histogram": added,
        "new_histogram": [a+b for a,b in zip(old,added)],
        "alpha_per_bin": 1.0,
        "total_owner_recorded_capture_events_both_years": sum(old) + sum(added),
    }


class ResearchNightCountClockTests(unittest.TestCase):
    def test_chronological_count_comparison_never_promotes(self):
        report = compare_nightcount(count_source())
        self.assertEqual(report["sample_nights"], 7)
        self.assertEqual(report["sample_owner_captures"], 13)
        self.assertEqual(report["heldout_chronological_folds"], 2)
        self.assertEqual(report["assumed_ex_ante_duration_hours"], 5.0)
        self.assertFalse(report["holdout_actual_proxy_effort_used_as_predictor"])
        self.assertFalse(report["historical_source_availability_verified"])
        self.assertFalse(report["champion_promotion_allowed"])
        self.assertEqual(len(report["paired_comparisons"]), 2)
        self.assertTrue(all(x["formal_promotion_eligible"] is False
                            for x in report["paired_comparisons"]))
        self.assertEqual(report, compare_nightcount(count_source()))

    def test_chronology_count_and_total_tampering_reject(self):
        source = count_source()
        source["training_nights"][5]["night"] = source["training_nights"][4]["night"]
        with self.assertRaises(ValueError):
            compare_nightcount(source)
        source = count_source()
        source["training_nights"][3]["count"] = True
        with self.assertRaises(ValueError):
            compare_nightcount(source)
        source = count_source()
        source["owner_captures"] += 1
        with self.assertRaises(ValueError):
            compare_nightcount(source)
        source = count_source()
        source["elapsed_session_hours_proxy"] += 1
        with self.assertRaises(ValueError):
            compare_nightcount(source)

    def test_count_prediction_is_fixed_five_hour_scenario_not_actual_effort(self):
        source = count_source()
        a = compare_nightcount(source)
        # Mutating only a holdout night's elapsed effort (and consistent source total)
        # must not change that night's historical forecast, because it is not read.
        source["training_nights"][-1]["effort_hours_proxy"] += 2
        source["elapsed_session_hours_proxy"] += 2
        b = compare_nightcount(source)
        self.assertEqual(a["scores"]["assumed_5h_exposure_rate"]["n_evaluated_nights"],
                         b["scores"]["assumed_5h_exposure_rate"]["n_evaluated_nights"])
        self.assertNotEqual(a["parsed_source_sha256"], b["parsed_source_sha256"])
        # Last holdout influences only its own diagnostic actual, no later fold.
        # For the first holdout's actual duration, the second fold can differ.
        self.assertEqual(a["scores"], b["scores"])

    def test_eventclock_is_conditional_and_shrinkage_is_posthoc(self):
        report = compare_eventclock(clock_source())
        self.assertEqual(report["historical_events"], 21)
        self.assertEqual(report["evaluation_events"], 2)
        self.assertFalse(report["champion_promotion_allowed"])
        self.assertTrue(report["selection_was_posthoc"])
        self.assertEqual(report["rate_per_active_search_time"], "NOT_ESTIMATED")
        self.assertGreater(report["mean_negative_log_likelihood_per_event"]["uniform_six_bins"], 1.7)
        self.assertEqual(report, compare_eventclock(clock_source()))

    def test_eventclock_invalid_histograms_never_repair(self):
        source = clock_source()
        source["new_histogram"][1] += 1
        with self.assertRaises(ValueError):
            compare_eventclock(source)
        source = clock_source()
        source["prior_histogram"][0] = -1
        with self.assertRaises(ValueError):
            compare_eventclock(source)
        source = clock_source()
        source["nov_increment_histogram"] = [0] * 6
        source["new_histogram"] = source["prior_histogram"][:]
        source["total_owner_recorded_capture_events_both_years"] = 21
        with self.assertRaises(ValueError):
            compare_eventclock(source)


if __name__ == "__main__":
    unittest.main()
