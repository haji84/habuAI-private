"""The August certification queue is evidence review only, not a learning label."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from build_august_evidence_review_queue import build_review_queue

class AugustEvidenceReviewQueueTests(unittest.TestCase):
    def test_real_august_12_nights_remain_unknown(self):
        r=build_review_queue(ROOT)
        self.assertFalse(r["official_model_training_allowed"])
        self.assertEqual(r["count_integrity"]["baseline_august"],45)
        self.assertFalse(r["count_integrity"]["proposed_august_47_certified"])
        self.assertEqual(len(r["count_integrity"]["aug31_capture_statement_candidates"]),2)
        t=r["totals"]
        self.assertEqual(t["nights"],12)
        self.assertEqual(t["gp_samples"],231715)
        self.assertEqual(t["position_time_units"],8965)
        self.assertEqual(t["within_session_candidate_units"],6694)
        self.assertEqual(t["paired_session_nights"],9)
        self.assertEqual(t["certified_searched_road_units"],0)
        self.assertEqual(t["eligible_negative_units"],0)
        self.assertEqual(t["eligible_positive_units"],0)
        self.assertEqual(len(r["nights"]),12)
        self.assertEqual({n["night"] for n in r["nights"] if not n["explicit_start_end_pair"]},
                         {"2026-08-12","2026-08-13","2026-08-29"})
        self.assertTrue(all(n["disposition"]=="UNKNOWN_NOT_MODEL_ELIGIBLE" for n in r["nights"]))
        self.assertTrue(all(n["searched_road_sections_certified"] is False for n in r["nights"]))
        self.assertTrue(all(n["capture_outcomes_complete"] is False for n in r["nights"]))
        self.assertTrue(all("ROAD_SEGMENT_ACTIVE_SEARCH_ATTESTATION" in n["blocking_proof"] for n in r["nights"]))
        self.assertIn("ZERO_CAPTURE_RECORD_NOT_COMPLETE_OUTCOME_PROOF",
                      next(n for n in r["nights"] if n["night"]=="2026-08-21")["blocking_proof"])
        self.assertIn("TWO_CAPTURE_MENTIONS_OWNER_AND_UNIQUENESS_UNRESOLVED",
                      next(n for n in r["nights"] if n["night"]=="2026-08-31")["blocking_proof"])

    def test_forged_positive_in_gps_input_never_promotes(self):
        import build_august_evidence_review_queue as module
        from audit_august_sampled_exposure import audit
        report,rows=audit(ROOT)
        rows[0]=dict(rows[0],observation="observed_negative",formal_negative_eligible=True)
        with patch.object(module,"audit",return_value=(report,rows)):
            with self.assertRaisesRegex(ValueError,"UNAPPROVED_MODEL_LABEL"):
                module.build_review_queue(ROOT)

if __name__=="__main__":unittest.main()
