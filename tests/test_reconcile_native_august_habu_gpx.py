"""True user-native August source is not the workbook or the older saved read."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import reconcile_native_august_habu_gpx as nat

class NativeAugustRawEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=nat.make_actual_join(ROOT)

    def test_original_source_has_byte_for_byte_identity(self):
        text,meta=nat.load_original(ROOT)
        self.assertEqual(meta["source_bytes"],111323)
        self.assertEqual(meta["sha256"],"3c541bcbd994e1da397e083a9b094520926ebc9647879e4b001edbf9471c7eed")
        self.assertEqual(len(text.splitlines()),10016)
        self.assertTrue(text.startswith("ハブログ"))
        self.assertTrue(text.endswith("エリア探索終了"))

    def test_first_four_overlap_events_are_aliases_not_new_captures(self):
        s=self.report
        self.assertEqual(s["legacy_extracted_capture_aliases_found"],11)
        self.assertTrue(s["legacy_aliases_not_double_counted"])
        self.assertEqual(s["gpx_files"],13)
        self.assertEqual(s["august_gpx_files"],12)
        self.assertEqual(s["september_gpx_files"],1)
        self.assertTrue(s["original_source_event_block_count"]>=30)

    def test_all_gpx_nights_have_original_event_and_reaction_review_state(self):
        rec={x["night"]:x for x in self.report["gpx_nights"]}
        self.assertEqual(len(rec["2026-08-12"]["capture_candidates"]),4)
        self.assertEqual(len(rec["2026-08-13"]["capture_candidates"]),2)
        self.assertEqual(len(rec["2026-08-15"]["capture_candidates"]),3)
        self.assertEqual(len(rec["2026-08-17"]["capture_candidates"]),2)
        self.assertEqual(len(rec["2026-08-19"]["capture_candidates"]),5)
        self.assertEqual(len(rec["2026-08-23"]["capture_candidates"]),3)
        self.assertEqual(len(rec["2026-08-24"]["capture_candidates"]),3)
        self.assertEqual(len(rec["2026-08-27"]["capture_candidates"]),3)
        self.assertEqual(len(rec["2026-08-28"]["capture_candidates"]),4)
        self.assertEqual(len(rec["2026-08-29"]["capture_candidates"]),1)
        self.assertEqual(len(rec["2026-08-21"]["capture_candidates"]),0)
        self.assertEqual(len(rec["2026-08-31"]["capture_candidates"]),0)
        self.assertEqual(len(rec["2026-09-02"]["capture_candidates"]),0)
        # Zero capture mentions in an incomplete log is NOT a zero-capture training label.
        self.assertTrue(all(x["unknown_without_complete_search_reporting"] for x in rec.values()))
        self.assertEqual(sum(len(x["capture_candidates"]) for x in rec.values()),30)

    def test_exact_two_individuals_in_one_event_is_preserved(self):
        rec={x["night"]:x for x in self.report["gpx_nights"]}
        group=rec["2026-08-19"]["capture_candidates"]
        explicitly_numbered=[x for x in group if x["quantity_exact_when_explicit"] is not None]
        self.assertEqual(len(explicitly_numbered),1)
        self.assertEqual(explicitly_numbered[0]["quantity_exact_when_explicit"],2)
        self.assertIn("2026/08/20 1:44", explicitly_numbered[0]["native_timestamp"])
        self.assertFalse(explicitly_numbered[0]["training_positive_eligible"])
        self.assertEqual(self.report["formal_training_positive_individuals"],0)
        self.assertEqual(self.report["formal_training_negative_units"],0)

    def test_existing_source_does_not_issue_p0_or_walkforward(self):
        s=self.report
        self.assertFalse(s["model_learning_generated"])
        self.assertFalse(s["official_walkforward_run"])
        self.assertFalse(s["official_p0_issued"])
        self.assertFalse(s["canonical_capture_db_changed"])
        self.assertTrue(s["scientific_unknown_label_remains"])
        for night in s["gpx_nights"]:
            self.assertFalse(night["dashboard_claim_used_as_ground_truth"])
            self.assertFalse(night["full_night_outcome_ledger_verified"])
            self.assertFalse(night["search_effort_complete_and_detection_verified"])
            self.assertEqual(night["eligible_negative_roadtime_units"],0)

    def test_original_byte_tampering_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            p=root/nat.RAW
            p.parent.mkdir(parents=True)
            p.write_bytes((ROOT/nat.RAW).read_bytes()+b"\n")
            receipt=root/nat.META
            receipt.parent.mkdir(parents=True)
            receipt.write_bytes((ROOT/nat.META).read_bytes())
            with self.assertRaises(nat.OriginalLogError):
                nat.load_original(root)

if __name__=="__main__":
    unittest.main()
