"""The motion-review adapter never turns diagnostic fauna evidence into labels."""
from __future__ import annotations

import copy
import hashlib
import importlib
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def fixture(group="group-slow", motion="LOCAL_SLOW_OR_STOPPED_FAUNA_CONTEXT_PRIORITY"):
    raw_log, raw_gpx = b"original field log\n", b"original GPX\n"
    block = hashlib.sha256(group.encode()).hexdigest()
    packet = {
        "review_group_id": group,
        "night": "2026-08-17",
        "independent_original_fauna_note_count": 1,
        "source_event_block_sha256s": [block],
        "matched_candidate_ids": ["candidate-1"],
        "review_motion_priority": motion,
        "independently_verified_habu_search_on_entire_road": False,
        "capture_result_ledger_complete": False,
        "source_proves_zero_habu_captures": False,
        "model_positive_rows": 0,
        "model_negative_rows": 0,
    }
    anchor = {
        "review_group_id": group,
        "night": "2026-08-17",
        "candidate_id": "candidate-1",
        "source_block_sha256": block,
        "original_source_line": 12,
        "organism_category": "OTHER_FAUNA_SIGHTING",
        "source_field_log_sha256": hashlib.sha256(raw_log).hexdigest(),
        "actual_gpx_source_sha256": hashlib.sha256(raw_gpx).hexdigest(),
        "source_logged_fauna_observation_at_point": True,
        "independently_certified_habu_targeted_search": False,
        "complete_capture_outcomes_for_cell": False,
        "training_observation": "UNKNOWN",
        "training_label": None,
        "formal_positive_eligible": False,
        "formal_negative_eligible": False,
    }
    blobs = {
        "evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt": raw_log,
        "data/raw/gpx/2026-08-17__legacy.gpx": raw_gpx,
    }
    return packet, anchor, blobs


class MotionPacketEligibilityTests(unittest.TestCase):
    def review(self, packets, anchors, blobs):
        self.assertIsNotNone(importlib.util.find_spec("observation_eligibility_v1"),
                             "The UNKNOWN-safe packet adapter is missing")
        module = importlib.import_module("observation_eligibility_v1")
        return module.review_motion_packets(packets, anchors, blobs)

    def test_slow_fauna_is_unknown_without_independent_search_and_outcomes(self):
        p, a, blobs = fixture()
        result = self.review([p], [a], blobs)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["target_semantics"], "SOURCE_QUALIFIED_OWNER_CAPTURE_BINARY")
        review = result["packet_reviews"][0]
        self.assertIsNone(review["training_label"])
        self.assertEqual(review["training_observation"], "UNKNOWN")
        self.assertIn("INDEPENDENT_SCOPED_ACTIVE_HABU_SEARCH_PROOF_MISSING", review["reasons"])
        self.assertIn("SCOPED_COMPLETE_OWNER_CAPTURE_OUTCOME_PROOF_MISSING", review["reasons"])
        self.assertEqual(result["counts"]["eligible"], 0)

    def test_mixed_motion_packets_are_reviewed_before_the_other_packets(self):
        p, a, blobs = fixture()
        q, b, _ = fixture("group-mixed", "DIRECT_FAUNA_POINT_OBSERVATION_MOTION_UNRESOLVED")
        result = self.review([p, q], [a, b], blobs)
        self.assertEqual([r["review_group_id"] for r in result["packet_reviews"]],
                         ["group-mixed", "group-slow"])
        self.assertEqual(result["counts"]["unknown"], 2)

    def test_changed_source_bytes_fail_without_producing_a_label(self):
        p, a, blobs = fixture()
        blobs["data/raw/gpx/2026-08-17__legacy.gpx"] += b"tampered"
        result = self.review([p], [a], blobs)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("SOURCE_HASH_MISMATCH", result["packet_reviews"][0]["integrity_errors"])
        self.assertIsNone(result["packet_reviews"][0]["training_label"])

    def test_missing_source_cannot_be_certified_from_the_claimed_hash(self):
        p, a, blobs = fixture()
        blobs.pop("data/raw/gpx/2026-08-17__legacy.gpx")
        result = self.review([p], [a], blobs)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("SOURCE_BYTES_MISSING", result["packet_reviews"][0]["integrity_errors"])

    def test_packet_membership_must_match_the_hashed_anchors(self):
        p, a, blobs = fixture()
        p["source_event_block_sha256s"] = ["0" * 64]
        result = self.review([p], [a], blobs)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("PACKET_ANCHOR_MEMBERSHIP_MISMATCH", result["packet_reviews"][0]["integrity_errors"])

    def test_repeated_anchor_and_orphan_group_are_not_silently_deduplicated(self):
        p, a, blobs = fixture()
        orphan = dict(a, review_group_id="unknown-group")
        result = self.review([p], [a, copy.deepcopy(a), orphan], blobs)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("DUPLICATE_SOURCE_ANCHOR", result["integrity_errors"])
        self.assertIn("ORPHAN_SOURCE_ANCHOR", result["integrity_errors"])

    def test_unbound_positive_negative_or_completeness_flags_never_grant_eligibility(self):
        for label in (0, 1):
            with self.subTest(label=label):
                p, a, blobs = fixture()
                p["capture_result_ledger_complete"] = True
                a.update(training_label=label, formal_negative_eligible=True,
                         independently_certified_habu_targeted_search=True)
                result = self.review([p], [a], blobs)
                review = result["packet_reviews"][0]
                self.assertEqual(result["status"], "FAIL")
                self.assertIn("UNSUPPORTED_LABEL_OR_PROOF_CLAIM", review["integrity_errors"])
                self.assertIsNone(review["training_label"])
                self.assertFalse(review["formal_positive_eligible"])
                self.assertFalse(review["formal_negative_eligible"])

    def test_species_capture_roadkill_or_owner_words_do_not_authenticate_a_capture(self):
        for kind in ("HABU_SIGHTING", "HIMEHABU", "HABU_ROADKILL", "OTHER_PERSON_CAPTURE", "OWNER_CAPTURE"):
            with self.subTest(kind=kind):
                p, a, blobs = fixture()
                a["organism_category"] = kind
                result = self.review([p], [a], blobs)
                review = result["packet_reviews"][0]
                self.assertIsNone(review["training_label"])
                self.assertIn("SOURCE_QUALIFIED_OWNER_CAPTURE_EVENT_NOT_ESTABLISHED", review["reasons"])
                self.assertIn("CANONICAL_INDIVIDUAL_IDENTITY_NOT_ESTABLISHED", review["reasons"])

    def test_duplicate_packet_ids_and_night_disagreement_fail_closed(self):
        p, a, blobs = fixture()
        a["night"] = "2026-08-18"
        result = self.review([p, copy.deepcopy(p)], [a], blobs)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("DUPLICATE_REVIEW_GROUP", result["integrity_errors"])
        self.assertIn("PACKET_ANCHOR_NIGHT_MISMATCH", result["packet_reviews"][0]["integrity_errors"])

    def test_empty_inventory_is_blocked_and_never_a_scientific_pass(self):
        result = self.review([], [], {})
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["scientific_status"], "NOT_VALIDATED")
        self.assertEqual(result["counts"]["eligible"], 0)

    def test_boolean_anchor_count_is_not_an_authenticated_integer_count(self):
        p, a, blobs = fixture()
        p["independent_original_fauna_note_count"] = True
        result = self.review([p], [a], blobs)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("PACKET_ANCHOR_MEMBERSHIP_MISMATCH", result["packet_reviews"][0]["integrity_errors"])

    def test_unbound_full_road_search_flag_is_also_rejected(self):
        p, a, blobs = fixture()
        a["observed_entire_road_cell_as_searched"] = True
        result = self.review([p], [a], blobs)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("UNSUPPORTED_LABEL_OR_PROOF_CLAIM", result["packet_reviews"][0]["integrity_errors"])
        self.assertIsNone(result["packet_reviews"][0]["training_label"])

    def test_result_is_deterministic_and_does_not_modify_source_packets(self):
        p, a, blobs = fixture()
        before = copy.deepcopy((p, a, blobs))
        first = self.review([p], [a], blobs)
        second = self.review([p], [a], blobs)
        self.assertEqual(first, second)
        self.assertEqual((p, a, blobs), before)
        self.assertEqual(len(first["audit_sha256"]), 64)
        self.assertEqual(first["packet_reviews"][0]["source_selector_status"],
                         "NOT_REAUTHENTICATED_BY_THIS_GATE")


if __name__ == "__main__":
    unittest.main()
