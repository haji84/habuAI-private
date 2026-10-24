"""Fauna field-note to actual-GPX road-source binding with no model-label leakage."""
import json
import hashlib
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src"))
from audit_aug31_road_search_candidates import RoadMatcher
from gpx_audit import utm52n
from audit_august_fauna_sighting_context import (
    _time_window,nearest_gpx,source_category,restore_compound_sighting_blocks,analyze_sightings,
    STRICT_MAX_METRES,STRICT_MAX_SECONDS
)

class SyntheticOriginalEventMatching(unittest.TestCase):
    @staticmethod
    def fake_event(category,when="2026-08-31T21:43:00+09:00",lat=28.15,lon=129.3004,kind="sighting"):
        return {"event_type":kind,"species_or_native_note":category,
                "timestamp_interpreted_jst":when,
                "coordinates":{"latitude":lat,"longitude":lon}}

    @staticmethod
    def matcher(double=False):
        line={"type":"Feature","properties":{"normal_route":True,"osm_way_id":1,"highway":"track"},
              "geometry":{"type":"LineString","coordinates":[[129.30,28.15],[129.301,28.15]]}}
        if double:
            extra=json.loads(json.dumps(line));extra["properties"]["osm_way_id"]=2
            return RoadMatcher([line,extra])
        return RoadMatcher([line])

    @staticmethod
    def sample(when,lat=28.15,lon=129.3004,hdop=2.0):
        ptime=datetime.fromisoformat(when)
        x,y=utm52n(lat,lon)
        return {"time_utc":ptime,"x":x,"y":y,"hdop":hdop,"speed_mps":3,
                "sample_utm_cell":[int(x//100),int(y//100)],
                "sample_10min_window":_time_window(ptime)}

    def test_species_source_never_confuses_himehabu_with_habu(self):
        self.assertEqual(source_category(self.fake_event("ハブ"))[0],"HABU_SIGHTING")
        self.assertEqual(source_category(self.fake_event("ヒメハブ"))[0],"HIMEHABU_SIGHTING_NOT_HABU")
        self.assertEqual(source_category(self.fake_event("カエル"))[0],"OTHER_FAUNA_SIGHTING")
        self.assertEqual(source_category(self.fake_event("アカマタ、アマミタカチホヘビ"))[1],"アカマタ、アマミタカチホヘビ")
        self.assertEqual(source_category(self.fake_event(None))[0],"UNCLASSIFIED_SIGHTING")
        self.assertEqual(source_category(self.fake_event("ハブ",kind="roadkill"))[0],"ROADKILL_NOT_A_SIGHTING")
        self.assertEqual(source_category(self.fake_event("ハブ",kind="capture"))[0],"NOT_FAUNA_SIGHTING")

    def test_close_original_gpx_same_time_road_is_review_only(self):
        point=self.sample("2026-08-31T12:43:10+00:00")
        e=self.fake_event("オットンガエル")
        m=nearest_gpx(e,[point],[point["time_utc"]],self.matcher())
        self.assertEqual(m["status"],"CLOSE_GPX_SOURCE_OBSERVATION")
        self.assertTrue(m["strict_gps_source_alignment"])
        self.assertTrue(m["same_original_100m_10min_bin"])
        self.assertTrue(m["auxiliary_osm_same_way"])
        self.assertEqual(m["source_osm_way_candidate"],1)

    def test_threshold_and_missing_coordinates_never_invent_gpx(self):
        p=self.sample("2026-08-31T12:43:10+00:00")
        e=self.fake_event("ネズミ",lon=129.304)
        m=nearest_gpx(e,[p],[p["time_utc"]],self.matcher())
        self.assertEqual(m["status"],"NO_ACTUAL_GPX_WITHIN_100M_10MIN")
        e=self.fake_event("ネズミ");e["coordinates"]=None
        m=nearest_gpx(e,[p],[p["time_utc"]],self.matcher())
        self.assertEqual(m["status"],"NO_SOURCE_EVENT_COORDINATE")
        late=self.sample("2026-08-31T12:55:00+00:00")
        e=self.fake_event("ネズミ")
        m=nearest_gpx(e,[late],[late["time_utc"]],self.matcher())
        self.assertEqual(m["status"],"NO_ACTUAL_GPX_WITHIN_100M_10MIN")

    def test_missing_hdop_or_ambiguous_road_never_strong_alignment(self):
        bad=self.sample("2026-08-31T12:43:10+00:00",hdop=None)
        e=self.fake_event("カエル")
        m=nearest_gpx(e,[bad],[bad["time_utc"]],self.matcher())
        self.assertFalse(m["strict_gps_source_alignment"])
        self.assertEqual(m["status"],"BROAD_GPX_SPACETIME_ONLY")
        good=self.sample("2026-08-31T12:43:10+00:00")
        ambiguous=nearest_gpx(e,[good],[good["time_utc"]],self.matcher(double=True))
        self.assertTrue(ambiguous["strict_gps_source_alignment"])
        self.assertFalse(ambiguous["auxiliary_osm_same_way"])

    def test_source_point_near_mapped_road_without_gpx_same_bin_not_supported(self):
        p=self.sample("2026-08-31T12:49:55+00:00")
        e=self.fake_event("カエル",when="2026-08-31T21:43:00+09:00")
        result=nearest_gpx(e,[p],[p["time_utc"]],self.matcher())
        self.assertEqual(result["status"],"BROAD_GPX_SPACETIME_ONLY")
        self.assertFalse(result["strict_gps_source_alignment"])

class EmbeddedNativeSightingRecoveryTests(unittest.TestCase):
    def test_two_original_coordinates_are_separate_observations_not_inferred_gpx(self):
        source=(
            "2026/08/22 1:03\n目撃\n\n1匹\nオットンガエル\n"
            "ウェット\n28.1736707293488\n129.3956944839441\n\n"
            "あ2026/08/22 1:07\n目撃\n\n1匹\nオットンガエル\n"
            "ウェット\n28.17478672324291\n129.3978476419541\n"
        )
        parent={
            "event_type":"sighting","source_block":source,
            "block_sha256":hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "source_line":5716,"operational_night":"2026-08-21",
            "timestamp_native":"2026/08/22 1:03"
        }
        records,repairs=restore_compound_sighting_blocks([parent])
        self.assertEqual(len(records),2)
        self.assertEqual(len(repairs),1)
        self.assertEqual({r["timestamp_native"] for r in records},
                         {"2026/08/22 1:03","2026/08/22 1:07"})
        self.assertEqual({r["operational_night"] for r in records},{"2026-08-21"})
        self.assertEqual(len({r["block_sha256"] for r in records}),2)
        self.assertTrue(all(hashlib.sha256(r["source_block"].encode("utf-8")).hexdigest()==r["block_sha256"] for r in records))
        self.assertTrue(records[1]["source_block"].startswith("あ2026/08/22 1:07"))
        self.assertTrue(records[1]["source_parse_stripped_spurious_prefix"])
        self.assertFalse(records[0]["source_parse_stripped_spurious_prefix"])
        self.assertNotEqual(records[0]["coordinates"],records[1]["coordinates"])
        self.assertTrue(all(r["original_parent_block_sha256"]==parent["block_sha256"] for r in records))
        self.assertTrue(all(r["species_or_native_note"]=="オットンガエル" for r in records))
        self.assertFalse(repairs[0]["native_original_bytes_modified"])

    def test_comments_with_embedded_clock_are_not_sighting_splits(self):
        p={"event_type":"weather_or_context","source_block":"なう(2026/08/22 01:20:54)雨",
           "block_sha256":"source-note", "source_line":2}
        events,repairs=restore_compound_sighting_blocks([p])
        self.assertEqual(events,[p]);self.assertEqual(repairs,[])

class RealAugustFaunaEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary,cls.events,cls.packet_context=analyze_sightings(ROOT)

    def test_native_sightings_all_12_nights_and_reaction_class_separation(self):
        s=self.summary
        self.assertEqual(s["scope"]["actual_gpx_nights"],12)
        self.assertEqual(s["scope"]["august_source_sighting_statements_all_nights"],916)
        self.assertEqual(s["source"]["original_timestamp_line_sighting_blocks_in_august"],915)
        self.assertEqual(s["source"]["original_timestamp_line_sighting_blocks_with_actual_gpx"],704)
        self.assertEqual(s["totals"]["native_compound_sighting_repairs"],1)
        self.assertEqual(s["scope"]["source_sighting_statements_with_actual_gpx_nights"],705)
        self.assertEqual(s["totals"]["source_sightings"],705)
        self.assertEqual(s["totals"]["roadkill_entries_not_misclassified_as_sightings"],11)
        self.assertEqual(s["totals"]["habu_roadkill_reactions_separate_from_captures"],3)
        self.assertEqual(s["totals"]["sightings_with_missing_unique_source_coordinate"],0)
        self.assertEqual(s["totals"]["habu_sightings_explicit"],0)
        self.assertEqual(s["totals"]["himehabu_sightings_distinct"],9)
        self.assertEqual(s["totals"]["other_fauna_sightings"],696)
        self.assertEqual(s["totals"]["unknown_species_sightings"],0)
        self.assertEqual(len(self.events),705+11)
        self.assertEqual(len({r["source_block_sha256"] for r in self.events}),len(self.events))
        self.assertEqual(len(self.summary["by_night"]),12)
        expected={
            "2026-08-12":53,"2026-08-13":35,"2026-08-15":58,"2026-08-17":34,
            "2026-08-19":52,"2026-08-21":55,"2026-08-23":73,"2026-08-24":76,
            "2026-08-27":73,"2026-08-28":113,"2026-08-29":40,"2026-08-31":43}
        self.assertEqual({x["night"]:x["source_sighting_statements"] for x in s["by_night"]},expected)
        self.assertEqual(s["scope"]["owner_confirmed_monthly_captures"],47)

    def test_actual_source_to_gpx_osm_and_candidate_packet_correlations(self):
        t=self.summary["totals"]
        self.assertGreater(t["sightings_matched_100m_10min_actual_gpx"],0)
        self.assertGreater(t["sightings_strict_35m_90s_known_hdop"],0)
        self.assertGreater(t["sightings_matching_same_unambiguous_auxiliary_osm_way"],0)
        self.assertGreater(t["candidate_cells_with_strict_same_gpx_osm_sighting_observation"],0)
        self.assertGreater(t["candidate_review_groups_with_strict_fauna_observation"],0)
        self.assertLessEqual(t["candidate_cells_with_strict_same_gpx_osm_sighting_observation"],3491)
        self.assertLessEqual(t["candidate_review_groups_with_strict_fauna_observation"],774)
        self.assertEqual(len(self.packet_context),774)
        self.assertEqual(t["strict_sighting_anchor_event_count_in_candidate_cells"],
                         sum(x["strict_source_gpx_osm_sighting_anchor_count"] for x in self.packet_context))
        self.assertEqual(t["candidate_review_groups_with_strict_fauna_observation"],
                         sum(x["review_priority_biological_observation_context"] for x in self.packet_context))
        self.assertTrue(all(g["review_status"]=="SOURCE_SIGHTING_CONTEXT_ONLY" for g in self.packet_context))

    def test_missing_paired_session_never_used_as_strict_road_search(self):
        src={"2026-08-12","2026-08-13","2026-08-29"}
        self.assertTrue(all(e["source_event_within_recorded_session"] is None
                            for e in self.events if e["night"] in src))
        self.assertTrue(all(not e["same_source_bin_has_strict_gpx_and_osm_alignment"]
                            for e in self.events if e["night"] in src))

    def test_prevent_sighting_to_habu_or_training_negative_promotion(self):
        self.assertFalse(self.summary["scientific_training_eligible"])
        self.assertEqual(self.summary["totals"]["scientifically_certified_road_search_segments"],0)
        self.assertEqual(self.summary["totals"]["scientific_positive_training_rows_added"],0)
        self.assertEqual(self.summary["totals"]["scientific_negative_training_rows_added"],0)
        self.assertTrue(all(e["observation"]=="UNKNOWN" and e["training_label"] is None for e in self.events))
        self.assertTrue(all(not e["confirmed_search_effort_for_entire_road_segment"] for e in self.events))
        self.assertTrue(all(not e["capture_outcome_ledger_complete"] for e in self.events))
        self.assertFalse(self.summary["source"]["original_field_device_signed_witness"])
        self.assertTrue(self.summary["source"]["osm_used_only_retrospectively"])
        self.assertTrue(any(e["category"]=="HIMEHABU_SIGHTING_NOT_HABU" for e in self.events))
        self.assertTrue(any(e["source_event_type"]=="roadkill" for e in self.events))

if __name__=="__main__":
    unittest.main()
