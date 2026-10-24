"""Real Aug31 GPX/OSM road review, negative-proof gates and synthetic geometry cases."""
import json
import math
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src"))
from gpx_audit import utm52n
from audit_aug31_road_search_candidates import (
    RoadDiagnosticError,RoadMatcher,_point_segment_distance,_candidate_activity,
    analyze,load_osm_matcher,NIGHT
)

class RoadCandidateGeometryTests(unittest.TestCase):
    def test_distance_point_to_segment_not_infinite_extension(self):
        self.assertAlmostEqual(_point_segment_distance(5,3,(0,0),(10,0)),3)
        self.assertAlmostEqual(_point_segment_distance(20,0,(0,0),(10,0)),10)
        self.assertAlmostEqual(_point_segment_distance(10,20,(0,0),(0,0)),math.hypot(10,20))

    @staticmethod
    def feature(way,offset=0,normal=True):
        return {"type":"Feature","properties":{"osm_way_id":way,"normal_route":normal,"highway":"track"},
                "geometry":{"type":"LineString","coordinates":[
                    [129.30,28.150+offset],[129.301,28.150+offset]]}}

    def test_excludes_not_normal_route_without_pretending_a_map_match(self):
        features=[self.feature(1,normal=False),self.feature(2,offset=0.003)]
        matcher=RoadMatcher(features)
        x,y=utm52n(28.15,129.3004)
        self.assertEqual(matcher.match_xy(x,y)["status"],"NO_AUXILIARY_ROAD_WITHIN_35M")

    def test_matches_a_single_auxiliary_way_and_rejects_ambiguous_junction(self):
        x,y=utm52n(28.15,129.3004)
        good=RoadMatcher([self.feature(1)])
        hit=good.match_xy(x,y)
        self.assertEqual(hit["status"],"AUXILIARY_ROAD_MATCH_REVIEW")
        self.assertEqual(hit["way_id"],1)
        other=RoadMatcher([self.feature(1),self.feature(2)])
        ambiguous=other.match_xy(x,y)
        self.assertEqual(ambiguous["status"],"AMBIGUOUS_MULTIPLE_ROADS")
        self.assertIsNone(ambiguous["way_id"])

    def test_search_fast_stop_are_review_not_evidence(self):
        t=datetime(2026,8,31,12,tzinfo=timezone.utc)
        def pack(speed):
            return [{"time_utc":t+timedelta(seconds=i*2),"inside_session":True,
                     "road_status":"AUXILIARY_ROAD_MATCH_REVIEW",
                     "way_id":1,"hdop":2.0,"speed_mps":speed} for i in range(7)]
        self.assertEqual(_candidate_activity(pack(3.0),None),"LIKELY_SLOW_SEARCH_REVIEW")
        self.assertEqual(_candidate_activity(pack(13.0),None),"LIKELY_TRANSIT_REVIEW")
        self.assertEqual(_candidate_activity(pack(0.0),None),"STATIONARY_NOT_SEARCH_PROOF")
        self.assertEqual(_candidate_activity(pack(3.0),"CAPTURE"),"CAPTURE_VICINITY_REVIEW")
        self.assertEqual(_candidate_activity(pack(3.0),"HABU_SIGHTING"),"HABU_SIGHTING_VICINITY_REVIEW")
        low=pack(3.0)
        for row in low:row["road_status"]="NO_AUXILIARY_ROAD_WITHIN_35M"
        self.assertEqual(_candidate_activity(low,None),"GPS_ROAD_MATCH_INSUFFICIENT")
        for row in low:row["inside_session"]=False
        self.assertEqual(_candidate_activity(low,None),"OUTSIDE_RECORDED_SESSION")

class RealAug31RoadEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result,cls.rows=analyze(ROOT)

    def test_byte_verified_real_sources_and_owner_count_preserved(self):
        p=self.result
        self.assertEqual(p["operational_night"],NIGHT)
        self.assertEqual(p["capture_statements"]["count"],2)
        self.assertTrue(p["capture_statements"]["both_gpx_matched"])
        self.assertEqual(len(set(p["capture_statements"]["source_event_sha256s"])),2)
        self.assertEqual(p["capture_statements"]["owner_confirmed_monthly_august_count"],47)
        self.assertEqual(p["capture_statements"]["aug31_daily_aggregate_count"],2)
        self.assertFalse(p["capture_statements"]["individual_capture_identity_certified"])
        self.assertFalse(p["input_provenance"]["historical_aug31_pre_exploration_available"])
        self.assertFalse(p["input_provenance"]["official_road_network_certified"])
        self.assertFalse(p["input_provenance"]["native_log_byte_verified"])
        self.assertEqual(p["gps_metrics"]["gpx_source_points"],17906)
        self.assertEqual(p["gps_metrics"]["legacy_qc_kept"],16980)
        self.assertEqual(p["sampled_100m_10min_units"],688)
        self.assertEqual(len(self.rows),688)

    def test_all_noncaptures_stay_candidates_not_training_negatives(self):
        p=self.result
        self.assertEqual(p["formal_positive_training_rows"],0)
        self.assertEqual(p["formal_negative_training_rows"],0)
        self.assertEqual(p["certified_searched_road_segments"],0)
        self.assertFalse(p["complete_owner_capture_outcomes_certified"])
        self.assertTrue(all(r["observation"]=="UNKNOWN" for r in self.rows))
        self.assertTrue(all(not r["formal_negative_eligible"] and not r["verified_search_effort"] for r in self.rows))
        self.assertTrue(all(not r["verified_capture_outcome_completeness"] for r in self.rows))
        self.assertEqual(sum(r["sample_count"] for r in self.rows),16980)
        self.assertEqual(sum(p["road_activity_candidate_counts"].values()),688)
        self.assertGreater(p["gps_metrics"]["road_matched_samples"],0)
        self.assertGreater(sum(r["event_nearby"]=="CAPTURE" for r in self.rows),0)
        self.assertEqual(
            p["noncapture_review_candidate_count"],
            sum(r["noncapture_candidate"]=="NO_OWNER_CAPTURE_RECORDED_REVIEW" for r in self.rows))
        for row in self.rows:
            if row["noncapture_candidate"]=="NO_OWNER_CAPTURE_RECORDED_REVIEW":
                self.assertEqual(row["event_nearby"],"NONE_RECORDED")
                self.assertEqual(row["activity_candidate"],"LIKELY_SLOW_SEARCH_REVIEW")

if __name__=="__main__":
    unittest.main()
