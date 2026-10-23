"""Real 8/12 and 9/2 source-derived events must be kept apart from training labels."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import recover_two_habu_nights as recovery


class TwoNightSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = recovery.recover(ROOT)
        cls.by_night={r["operational_night"]:r for r in cls.result["nights"]}

    def test_original_recovered_source_and_gpx_is_actual_not_synthetic(self):
        r=self.result
        self.assertEqual(r["status"],"SOURCE_EVENT_CANDIDATES_RECOVERED_NOT_TRAINING_APPROVED")
        self.assertFalse(r["original_native_log_file_bytes_verified"])
        self.assertFalse(r["official_original_prediction_issued"])
        self.assertEqual(r["eligible_verified_negative_rows"],0)
        self.assertEqual(r["eligible_final_model_training_rows"],0)
        self.assertEqual(set(self.by_night),{"2026-08-12","2026-09-02"})
        self.assertEqual(self.by_night["2026-08-12"]["actual_gpx_points"],25453)
        self.assertEqual(self.by_night["2026-09-02"]["actual_gpx_points"],12032)
        self.assertEqual(self.by_night["2026-08-12"]["actual_gpx_sha256"],
                         "1b390060aa8f553e55cbd9f6d2e8f45dbb9859a5fe6f22edc9e8daf0aa00cded")
        self.assertEqual(self.by_night["2026-09-02"]["actual_gpx_sha256"],
                         "a31e9ccdbc8f82b19681774546f3ae9a2c2aa8459334f231884e48008cfba307")

    def test_capture_events_and_roadkill_are_separate(self):
        aug=self.by_night["2026-08-12"]
        sep=self.by_night["2026-09-02"]
        self.assertEqual(aug["capture_event_mentions"],4)
        self.assertEqual(sep["capture_event_mentions"],2)
        self.assertEqual(aug["baseline_owner_capture_count"],4)
        self.assertEqual(sep["baseline_owner_capture_count"],2)
        self.assertEqual(aug["roadkill_event_count"],2)
        self.assertEqual(sep["roadkill_event_count"],3)
        self.assertEqual(aug["habu_roadkill_count_explicit"],0)
        self.assertEqual(sep["habu_roadkill_count_explicit"],1)
        self.assertEqual(aug["sighting_event_count"],53)
        self.assertEqual(sep["sighting_event_count"],23)
        self.assertEqual(aug["exploration_start_markers"],0)
        self.assertEqual(aug["exploration_end_markers"],1)
        self.assertEqual(sep["exploration_start_markers"],1)
        self.assertEqual(sep["exploration_end_markers"],0)
        for night in (aug,sep):
            self.assertFalse(night["exact_count_each_capture_confirmed_from_native_text"])
            self.assertFalse(night["owner_identity_verified_by_independent_individual_ids"])
            self.assertEqual(night["negative_labels"],"UNKNOWN_NOT_GENERATED")
            for e in night["events"]:
                self.assertEqual(e["explicit_exact_personal_capture_count"],None if e["event_type"]=="capture" else 0)
                self.assertEqual(e["capture_statement_lower_bound"],1 if e["event_type"]=="capture" else 0)
                self.assertEqual(hashlib.sha256(e["raw_extracted_text_block"].encode()).hexdigest(),
                                 e["source_block_sha256"])

    def test_times_07_jst_boundary_and_source_coordinates(self):
        aug=[e for e in self.by_night["2026-08-12"]["events"] if e["event_type"]=="capture"]
        sep=[e for e in self.by_night["2026-09-02"]["events"] if e["event_type"]=="capture"]
        self.assertEqual([e["field_log_time"] for e in aug],
             ["2026/08/12 22:28","2026/08/12 23:12","2026/08/13 1:42","2026/08/13 2:01"])
        self.assertEqual([e["field_log_time"] for e in sep],
             ["2026/09/02 22:57","2026/09/03 0:57"])
        self.assertAlmostEqual(aug[0]["coordinates"]["lat"],28.16443546510732)
        self.assertAlmostEqual(sep[0]["coordinates"]["lat"],28.1910010219236)
        self.assertTrue(all(e["coordinates"] is not None for e in aug+sep))
        self.assertEqual(self.by_night["2026-08-12"]["actual_gpx_capture_event_matches"],4)
        self.assertEqual(self.by_night["2026-09-02"]["actual_gpx_capture_event_matches"],2)

    def test_roadkill_habu_is_not_a_personal_capture(self):
        sep=self.by_night["2026-09-02"]
        roadkill=[x for x in sep["events"] if x["event_type"]=="roadkill" and x["species_or_native_note"]=="ハブ"]
        self.assertEqual(len(roadkill),1)
        self.assertEqual(roadkill[0]["field_log_time"],"2026/09/03 0:01")
        self.assertEqual(roadkill[0]["capture_statement_lower_bound"],0)
        self.assertEqual(roadkill[0]["explicit_exact_personal_capture_count"],0)

    def test_count_words_small_medium_are_not_numbers(self):
        for rec in self.result["nights"]:
            for row in rec["events"]:
                if row["event_type"]=="capture":
                    self.assertIsNone(row["source_quantity_literal"])
                    self.assertIn("ハブ捕獲",row["species_or_native_note"])


if __name__=="__main__":
    unittest.main()
