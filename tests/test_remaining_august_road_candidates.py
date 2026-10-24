"""Review-only 11-night post-hoc OSM road/GPS case validation."""
import sys
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from audit_remaining_august_road_candidates import analyze_remaining,REST

class RealRemainingElevenNights(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary,cls.rows=analyze_remaining(ROOT)
        cls.by_night={n["night"]:n for n in cls.summary["nightly_reports"]}

    def test_independent_real_gpx_inventory_and_road_alignment(self):
        self.assertEqual(len(REST),11)
        self.assertNotIn("2026-08-31",REST)
        self.assertEqual(len(set(REST)),11)
        s=self.summary
        self.assertEqual(s["night_count"],11)
        self.assertEqual(s["original_gpx_point_total"],213809)
        self.assertEqual(s["quality_kept_samples"],208239)
        self.assertEqual(s["sampled_spacetime_unit_count"],8277)
        self.assertEqual(s["paired_recorded_session_nights"],8)
        self.assertEqual(s["owner_confirmed_august_monthly_count"],47)
        self.assertEqual(s["capture_statement_count"],30)
        self.assertEqual(s["match_count"],30)
        self.assertGreater(s["gps_road_match_count"],0)
        self.assertEqual(sum(row["sampled_spacetime_units"] for row in self.by_night.values()),8277)
        for n in self.by_night.values():
            self.assertEqual(sum(n["activity_classes"].values()),n["sampled_spacetime_units"])
            self.assertGreater(n["gpx_points"],0)
            self.assertTrue(n["gpx_sha256"])
            self.assertFalse(n["capture_outcomes_complete"])

    def test_compact_ci_receipt_matches_recomputed_actual_sources(self):
        receipt=json.loads((ROOT/"evidence/recovered_sources/2026-08-remaining-11-road-search-review-ci-receipt.json").read_text(encoding="utf-8"))
        t=receipt["counts"]
        self.assertEqual(t["night_count"],11)
        self.assertEqual(t["archived_gpx_points"],self.summary["original_gpx_point_total"])
        self.assertEqual(t["quality_retained_points"],self.summary["quality_kept_samples"])
        self.assertEqual(t["osm_road_matched_gps_samples"],self.summary["gps_road_match_count"])
        self.assertEqual(t["sampled_100m_10min_bins"],self.summary["sampled_spacetime_unit_count"])
        self.assertEqual(t["noncapture_review_candidates"],self.summary["review_noncapture_candidate_count"])
        self.assertEqual(t["noncapture_review_candidates"],3065)
        self.assertEqual(t["paired_search_window_nights"],self.summary["paired_recorded_session_nights"])
        self.assertEqual(t["matched_capture_statements"],30)
        self.assertEqual(t["formal_negative_training_rows"],0)
        self.assertTrue(receipt["all_observations_remain_unknown"])
        for record in receipt["nights"]:
            live=self.by_night[record["night"]]
            self.assertEqual(record["gpx_sha256"],live["gpx_sha256"])
            self.assertEqual(record["osm_road_nearby_samples"],live["road_matched_samples"])
            self.assertEqual(record["noncapture_review_candidates"],live["noncapture_review_candidates"])
            self.assertEqual(record["observed_100m_10min_bins"],live["sampled_spacetime_units"])
        self.assertEqual(len(receipt["nights"]),11)

    def test_session_gaps_avoid_search_claims(self):
        missing={"2026-08-12","2026-08-13","2026-08-29"}
        self.assertEqual({x["night"] for x in self.by_night.values() if not x["paired_session"]},missing)
        self.assertTrue(all(x["noncapture_review_candidates"]==0 for x in self.by_night.values() if x["night"] in missing))
        self.assertTrue(all(not x["noncapture_review_candidate"] for x in self.rows if x["night"] in missing))

    def test_capture_multiplicity_and_missing_zero_night(self):
        self.assertEqual(self.by_night["2026-08-19"]["source_capture_event_mentions"],5)
        self.assertEqual(self.by_night["2026-08-19"]["capture_statement_quantity_candidate_sum"],6)
        self.assertEqual(self.by_night["2026-08-19"]["owner_dashboard_night_count"],6)
        self.assertEqual(self.by_night["2026-08-21"]["source_capture_event_mentions"],0)
        self.assertIsNone(self.by_night["2026-08-21"]["owner_dashboard_night_count"])
        self.assertFalse(self.by_night["2026-08-21"]["capture_outcomes_complete"])

    def test_only_review_candidates_and_never_formal_labels(self):
        s=self.summary
        self.assertEqual(s["scientifically_certified_road_search_segments"],0)
        self.assertEqual(s["formal_positive_training_rows"],0)
        self.assertEqual(s["formal_negative_training_rows"],0)
        self.assertTrue(s["no_original_P0_backfilled"])
        self.assertFalse(s["input_osm"]["historical_aug31_pre_exploration_available"])
        self.assertEqual(len(self.rows),8277)
        self.assertTrue(all(r["observation"]=="UNKNOWN" and r["label"] is None for r in self.rows))
        self.assertTrue(all(not r["actual_search_road_segment_verified"] for r in self.rows))
        self.assertTrue(all(not r["owner_capture_outcome_complete"] for r in self.rows))
        self.assertEqual(s["review_noncapture_candidate_count"],sum(r["noncapture_review_candidate"] for r in self.rows))
        self.assertTrue(all(r["activity_candidate"]=="LIKELY_SLOW_SEARCH_REVIEW" and
                            r["nearby_habu_event"]=="NONE_RECORDED"
                            for r in self.rows if r["noncapture_review_candidate"]))

if __name__=="__main__":
    unittest.main()
