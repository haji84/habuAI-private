"""Science-safe local motion adjudication for 75 original wildlife review packets."""
import sys
import unittest
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src"))
from gpx_audit import utm52n
from audit_august_75_fauna_motion_review import (
    ActivityReviewError,_count_temporal_clusters,_nearby_grid_points,
    _motion_context,audit_priority_packets,motion_classification
)

class MovementContextContractTests(unittest.TestCase):
    def test_all_motion_conditions_are_context_not_approved_search(self):
        self.assertEqual(motion_classification([3.0]*6,10,6),"LOW_SPEED_MOVEMENT_NEAR_LOGGED_FAUNA")
        self.assertEqual(motion_classification([0.1]*6,10,6),"STATIONARY_NEAR_LOGGED_FAUNA")
        self.assertEqual(motion_classification([16.0]*6,10,6),"FAST_PASSAGE_NEAR_LOGGED_FAUNA")
        self.assertEqual(motion_classification([1.0,0.2,12.0,5.0,0.8,18.0],10,6),"MIXED_MOVEMENT_NEAR_LOGGED_FAUNA")
        self.assertEqual(motion_classification([3.0]*6,3.0,6),"INSUFFICIENT_CONTIGUOUS_GPX_MOTION")
        self.assertEqual(motion_classification([3.0,None,None,None,3.0,3.0],12,6),"INSUFFICIENT_CONTIGUOUS_GPX_MOTION")
        self.assertEqual(motion_classification([3.0]*4,12,4),"INSUFFICIENT_CONTIGUOUS_GPX_MOTION")

    def test_revisit_time_clusters_not_invented_repeat_road_passes(self):
        at=datetime(2026,8,31,12,0,tzinfo=timezone.utc)
        rows=[{"time_utc":at+timedelta(seconds=s)} for s in (0,1,3,100,105,260)]
        self.assertEqual(_count_temporal_clusters(rows,split_seconds=90),3)
        self.assertEqual(_count_temporal_clusters([],split_seconds=90),0)

    def test_grid_neighborhood_radius_no_interpolated_points(self):
        at=datetime(2026,8,31,12,0,tzinfo=timezone.utc)
        close={"time_utc":at,"x":10050.0,"y":20050.0,"sequence":1}
        far={"time_utc":at,"x":10250.0,"y":20050.0,"sequence":2}
        grid={(100,200):[close],(102,200):[far]}
        result=_nearby_grid_points(grid,(10040.0,20040.0),50)
        self.assertEqual(len(result),1)
        self.assertIs(result[0],close)

    def test_logged_fauna_source_not_auto_owner_search_even_with_stopped_car(self):
        at=datetime(2026,8,31,12,10,tzinfo=timezone.utc)
        lat,lon=28.15,129.3004
        x,y=utm52n(lat,lon)
        cell=(int(x//100),int(y//100))
        points=[{"time_utc":at+timedelta(seconds=i*2),
                 "x":x,"y":y,"speed_mps":0.0,"sequence":i,
                 "hdop":2.0,"segment_break_before":False} for i in range(8)]
        index={"source_gpx_sha256":"shatest","strict_quality_grid":{cell:points}}
        sighting={"source_event_type":"sighting",
                  "same_source_bin_has_strict_gpx_and_osm_alignment":True,
                  "candidate_id":"prior-cell","candidate_review_group_id":"prior-group",
                  "night":"2026-08-31","source_block_sha256":"original-block",
                  "source_line":41,"timestamp_native":"2026/08/31 21:10",
                  "source_coordinates":{"latitude":lat,"longitude":lon},
                  "category":"OTHER_FAUNA_SIGHTING","organism_note_exact":"オットンガエル",
                  "gpx":{"source_osm_way_candidate":123,"auxiliary_osm_same_way":True}}
        class FakeMatcher:
            @staticmethod
            def match_xy(a,b):
                return {"status":"AUXILIARY_ROAD_MATCH_REVIEW","way_id":123}
        result=_motion_context(sighting,index,FakeMatcher())
        self.assertEqual(result["local_motion_context"],"STATIONARY_NEAR_LOGGED_FAUNA")
        self.assertEqual(result["source_100m_cell_gpx_time_clusters_not_confirmed_repeat_passes"],1)
        self.assertFalse(result["independently_certified_habu_targeted_search"])
        self.assertFalse(result["observed_entire_road_cell_as_searched"])
        self.assertEqual(result["training_observation"],"UNKNOWN")
        self.assertIsNone(result["training_label"])
        self.assertFalse(result["formal_negative_eligible"])
        invalid=dict(sighting,same_source_bin_has_strict_gpx_and_osm_alignment=False)
        with self.assertRaises(ActivityReviewError):
            _motion_context(invalid,index,FakeMatcher())

class RealSeventyFiveFaunaPacketAdjudication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary,cls.groups,cls.events=audit_priority_packets(ROOT)

    def test_all_existing_75_packets_and_99_logged_sightings_evaluated(self):
        s=self.summary
        self.assertEqual(s["source_strict_fauna_anchor_events_considered"],99)
        self.assertEqual(s["unique_strict_sighting_candidate_cells"],94)
        self.assertEqual(s["high_priority_original_review_packets"],75)
        self.assertEqual(s["original_total_review_candidates_unmodified"],3491)
        self.assertEqual(s["original_total_review_packets_unmodified"],774)
        self.assertEqual(len(self.groups),75)
        self.assertEqual(len(self.events),99)
        self.assertEqual(sum(g["independent_original_fauna_note_count"] for g in self.groups),99)
        self.assertEqual(set(s["priority_group_ids_without_spatial_data"]),
                         {g["review_group_id"] for g in self.groups})
        self.assertEqual(len(set(s["priority_group_ids_without_spatial_data"])),75)
        self.assertEqual(sum(s["motion_event_classes"].values()),99)
        self.assertEqual(sum(s["review_packet_motion_classes"].values()),75)
        self.assertGreaterEqual(sum(e["same_auxiliary_osm_way_gpx_points_in_window"] for e in self.events),0)

    def test_point_observation_is_not_evidence_of_full_habu_search_or_no_capture(self):
        s=self.summary
        self.assertEqual(s["owner_confirmed_august_captures"],47)
        self.assertEqual(s["owner_confirmed_season_total_through_oct20"],243)
        self.assertEqual(s["road_search_units_independently_certified"],0)
        self.assertFalse(s["capture_outcome_completeness_certified"])
        self.assertFalse(s["official_training_eligible"])
        self.assertEqual(s["formal_positive_training_rows"],0)
        self.assertEqual(s["formal_negative_training_rows"],0)
        self.assertTrue(s["all_review_group_observations_remain_unknown"])
        self.assertTrue(all(e["source_logged_fauna_observation_at_point"] for e in self.events))
        self.assertTrue(all(not e["independently_certified_habu_targeted_search"] for e in self.events))
        self.assertTrue(all(not e["complete_capture_outcomes_for_cell"] for e in self.events))
        self.assertTrue(all(e["training_observation"]=="UNKNOWN" and e["training_label"] is None for e in self.events))
        self.assertTrue(all(g["source_proves_zero_habu_captures"] is False for g in self.groups))
        self.assertTrue(all(not g["capture_result_ledger_complete"] for g in self.groups))
        self.assertTrue(all(g["model_negative_rows"]==0 and g["model_positive_rows"]==0 for g in self.groups))
        self.assertFalse(s["source_osm_historical_exante_available"])

    def test_original_source_and_pernight_packet_counts(self):
        s=self.summary
        self.assertEqual(s["source_native_habu_text_sha256"],
                         "130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c")
        self.assertEqual(sum(n["priority_review_packets"] for n in s["nights_with_strict_source_observations"]),75)
        self.assertEqual(sum(n["strict_original_sighting_events"] for n in s["nights_with_strict_source_observations"]),99)
        self.assertTrue(all(e["source_gpx_sha256"] if "source_gpx_sha256" in e else e["actual_gpx_source_sha256"] for e in self.events))
        self.assertTrue(all(g["eligibility"]=="HUMAN_OR_INDEPENDENT_EVIDENCE_REQUIRED" for g in self.groups))

if __name__=="__main__":
    unittest.main()
