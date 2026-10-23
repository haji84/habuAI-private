"""Regression guard for April 17/19 legacy Habu capture source conflict."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/reconstructions/habu_captures/2026-04-17-19-audit.json"
BASELINE = ROOT / "dashboard/baseline_2026.json"


class April1719AuditTests(unittest.TestCase):
    def test_no_unverified_promotion_or_fabricated_gpx(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "CONFLICT_REQUIRES_ORIGINAL_SOURCE")
        ids = {r["legacy_id"] for r in data["legacy_records"]}
        self.assertEqual(ids, {54, 55, 56, 57})
        for key, value in data["eligibility"].items():
            if key != "may_document_owner_report_at_coarse_area":
                self.assertFalse(value, key)
        self.assertFalse(data["source_independence"]["april_gpx_verified"])
        self.assertFalse(data["source_independence"]["original_event_ids_verified"])
        self.assertFalse(data["source_independence"]["precise_spatial_evidence_verified"])
        for record in data["legacy_records"]:
            self.assertNotIn("lat", record)
            self.assertNotIn("lon", record)
            self.assertNotIn("gpx_point_id", record)

    def test_owner_reports_distinguished_from_derived_db(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        reports = {r["operational_night"]: r for r in data["owner_conversation_summaries"]}
        self.assertEqual(reports["2026-04-17"]["reported_capture_count_at_post"], 0)
        self.assertEqual(reports["2026-04-19"]["reported_capture_count"], 2)
        self.assertEqual([x["reported_time"] for x in reports["2026-04-19"]["reported_events"]], ["21:40", "22:20"])
        self.assertTrue(all(not r["verbatim_post_bytes_available"] for r in reports.values()))
        self.assertFalse(data["later_owner_memory"]["specific_night_assignment_known"])
        self.assertEqual(data["arithmetic"]["unresolved_difference_to_april_total"], 2)

    def test_existing_dashboard_unchanged_pending_review(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        self.assertEqual(baseline["total"], 241)
        self.assertEqual(baseline["months"][0]["n"], 11)
        self.assertEqual(data["arithmetic"]["displayed_april_total_provisional"], 11)
        april = {n["night"]: n["count"] for n in baseline["nights"] if n["month"] == "2026-04"}
        self.assertEqual((april["2026-04-17"], april["2026-04-19"], april["2026-04-29"]), (2, 2, 3))


if __name__ == "__main__":
    unittest.main()
