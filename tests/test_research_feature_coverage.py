"""No weather-effect claims from heterogeneous, posthoc, sparse station records."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from research_feature_coverage import analyze_feature_coverage


def count_source():
    counts = [1, 0, 2, 3, 2, 1, 7]
    return {
        "schema_version": "habu-research-nightcount-poisson-v1.2",
        "nights": len(counts), "owner_captures": sum(counts),
        "elapsed_session_hours_proxy": sum(4.0+i%2 for i in range(len(counts))),
        "training_nights": [
            {"night": f"2026-10-{i+1:02d}", "count": count,
             "effort_hours_proxy": 4.0+i%2}
            for i, count in enumerate(counts)]
    }


def environmental_source():
    return {
        "schema_version": "habu-cooling-retrospective-audit-v1",
        "records": [
            {"night":"2026-10-03","owner_captures":2,
             "session_elapsed_proxy_h":4.0,
             "captured_not_no_capture_negative":True,
             "temp_source":"JMA_KONIYA_CALENDAR_DAY_MIN_NOT_HUNT_TIME",
             "station_day_min_c": 21.4},
            {"night":"2026-10-04","owner_captures":3,
             "session_elapsed_proxy_h":5.0,
             "captured_not_no_capture_negative":True,
             "temp_source":"JMA_KONIYA_HOURLY",
             "station_15_c":25.4,"station_20_c":22.0,
             "station_15_to_20_delta_c":-3.4},
            {"night":"2026-10-07","owner_captures":7,
             "session_elapsed_proxy_h":4.0,
             "captured_not_no_capture_negative":True,
             "temp_source":"JMA_KONIYA_CALENDAR_DAY_MIN_NOT_HUNT_TIME",
             "station_day_min_c":21.4},
        ],
    }


class ResearchFeatureCoverageTests(unittest.TestCase):
    def test_sparse_sources_are_analyzed_without_leakage_or_fake_fit(self):
        r = analyze_feature_coverage(count_source(), environmental_source())
        self.assertEqual(r["count_source_nights"],7)
        self.assertEqual(r["environment_matched_nights"],3)
        self.assertEqual(r["extreme_nights"],["2026-10-02","2026-10-07"])
        self.assertEqual(r["extreme_nights_without_environment"],["2026-10-02"])
        self.assertEqual(r["feature_coverage"]["station_day_min_c"]["matched_nights"],2)
        self.assertEqual(r["feature_coverage"]["station_15_to_20_delta_c"]["matched_nights"],1)
        self.assertTrue(r["distinct_feature_groups_not_poolable"])
        self.assertEqual(r["source_asof_eligibility"],"NOT_ESTABLISHED")
        self.assertEqual(r["actual_active_search_effort_eligibility"],"NOT_ESTABLISHED")
        self.assertEqual(r["formal_negative_labels_created"],0)
        self.assertFalse(r["causal_weather_effect_identified"])
        self.assertFalse(r["predictive_improvement_proven"])
        self.assertFalse(r["champion_promotion_allowed"])
        self.assertFalse(r["feature_coverage"]["station_day_min_c"]["forecast_ready"])

    def test_conflicting_count_and_proxy_fail_instead_of_silent_join(self):
        for key,value in (("owner_captures",999), ("session_elapsed_proxy_h",999.0),
                          ("captured_not_no_capture_negative",False)):
            with self.subTest(key=key):
                env=environmental_source()
                env["records"][0][key]=value
                with self.assertRaises(ValueError):
                    analyze_feature_coverage(count_source(),env)

    def test_incomparable_and_duplicate_sources_rejected(self):
        env=environmental_source()
        env["records"][0]["temp_source"]="UNSUPPORTED_AVG_SURFACE_TEMP"
        with self.assertRaises(ValueError):
            analyze_feature_coverage(count_source(),env)
        env=environmental_source()
        env["records"].append(copy.deepcopy(env["records"][0]))
        with self.assertRaises(ValueError):
            analyze_feature_coverage(count_source(),env)

    def test_missing_coverage_is_missing_not_zero(self):
        env=environmental_source()
        env["records"]=[]
        r=analyze_feature_coverage(count_source(),env)
        self.assertEqual(r["environment_matched_nights"],0)
        self.assertEqual(len(r["environment_missing_nights"]),7)
        self.assertEqual(r["formal_negative_labels_created"],0)
        self.assertIsNone(r["feature_coverage"]["station_20_c"]["mean_recorded_captures_when_feature_present"])


if __name__ == "__main__":
    unittest.main()
