"""August recovered candidate source links must remain not eligible for training."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reconcile_august_field_candidates as audit


class AugustCandidateActualGPS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # All four 4-6MB GPX sources are read once per test class.
        cls.real_report = audit.reconcile(ROOT)

    def test_eleven_capture_statements_match_real_gpx_but_stay_unverified(self):
        r = self.real_report
        self.assertEqual(r["candidate_event_mentions_total"], 11)
        self.assertEqual(r["gpx_proximity_matched_capture_mentions"], 11)
        self.assertEqual(set(r["gpx_nights"]), {
            "2026-08-12", "2026-08-13", "2026-08-15", "2026-08-17"})
        self.assertEqual(
            [len(r["gpx_nights"][night]["capture_candidate_statements"])
             for night in sorted(r["gpx_nights"])], [4, 2, 3, 2])
        self.assertEqual(r["formally_eligible_training_rows"], 0)
        self.assertEqual(r["exact_owner_capture_positive_individuals"], 0)
        self.assertEqual(r["observed_negative_units"], 0)
        self.assertFalse(r["independent_original_binary_verification"])
        self.assertTrue(r["unknown_passage_not_negative"])

    def test_workbook_role_conflict_and_null_quantities_not_hidden(self):
        for night in self.real_report["gpx_nights"].values():
            for row in night["capture_candidate_statements"]:
                self.assertIsNone(row["explicit_exact_individual_count"])
                self.assertEqual(row["minimum_possible_individuals"], 1)
                self.assertFalse(row["owner_capture_verified"])
                self.assertTrue(row["workbook_role_conflict"])
                self.assertFalse(row["training_positive_eligible"])
                self.assertLessEqual(row["absolute_time_delta_s"], audit.MAX_MATCH_SECONDS)
                self.assertLessEqual(row["spatial_distance_m"], audit.MAX_MATCH_DISTANCE_M)

    def test_roadkill_and_himehabu_remain_non_capture(self):
        r=self.real_report
        self.assertEqual(sum(len(n["reaction_controls"]) for n in r["gpx_nights"].values()),4)
        kinds=[x["category"] for n in r["gpx_nights"].values() for x in n["reaction_controls"]]
        self.assertEqual(kinds.count("HABU_ROADKILL_NONCAPTURE"),2)
        self.assertEqual(kinds.count("OTHER_SPECIES_SIGHTING_NONCAPTURE"),2)
        self.assertTrue(all(not x["training_positive_eligible"]
            for n in r["gpx_nights"].values() for x in n["reaction_controls"]))

    def test_missing_search_markers_do_not_prove_exposure(self):
        r=self.real_report["gpx_nights"]
        self.assertEqual(len(r["2026-08-13"]["search_markers"]), 0)
        for night in r.values():
            self.assertFalse(night["complete_search_exposure_verified"])
            self.assertFalse(night["exhaustive_owner_capture_ledger_verified"])
            self.assertEqual(night["eligible_negative_units"],0)

    def test_mutated_recovered_source_blocks_training(self):
        # Test a patched content-digest, not a fabricated original source.
        original=audit.digest_file
        def corrupted(path):
            if path.name=="august-extracted.txt": return "0"*64
            return original(path)
        with patch.object(audit,"digest_file",side_effect=corrupted):
            with self.assertRaises(audit.IntakeError):
                audit._read_review(ROOT)

    def test_source_role_or_quantity_cannot_be_promoted_by_review_changes(self):
        original=audit._read_review
        def forged(root):
            payload, source, sha = original(root)
            payload = copy.deepcopy(payload)
            payload["capture_candidates"][0]["exact_individual_count"] = 1
            return payload,source,sha
        with patch.object(audit,"_read_review",side_effect=forged):
            with self.assertRaises(audit.IntakeError):
                audit.reconcile(ROOT)

    def test_recovered_source_is_not_original_txt(self):
        self.assertEqual(
            self.real_report["representation"],
            "derived_recovered_read_content_not_original_txt_bytes")
        self.assertTrue(all(
            n["source_status"]=="RECOVERED_LOG_MATCHED_NOT_CANONICAL"
            for n in self.real_report["gpx_nights"].values()
        ))


if __name__ == "__main__":
    unittest.main()
