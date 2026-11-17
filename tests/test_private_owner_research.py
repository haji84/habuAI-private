"""Synthetic, privacy-safe tests of owner-source research receipt handoff."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from private_owner_research import intake_and_research, research_receipt, VERSION
from private_pdca_intake import IntakeError

LOG = (
    "2026/11/17 21:59\nSYNTHETIC_NOT_A_LOCATION\nエリア探索開始\n"
    "2026/11/17 22:05\n捕獲\nハブ\n"
    "2026/11/17 22:30\n目撃\nヒメハブ\n"
    "2026/11/17 23:15\n捕獲\nハブ\n2匹\n"
    "2026/11/18 00:05\n轢死\nハブ\n"
    "2026/11/18 01:20\nSYNTHETIC_NOT_A_LOCATION\nエリア探索終了\n"
)
GPX = b'<gpx creator="SYNTHETIC_NON_LOCATION"><trk><trkseg><trkpt lat="0" lon="0"/></trkseg></trk></gpx>'


class OwnerResearchBridgeTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        root = Path(self.dir.name)
        self.repo = root / "public-code"
        self.repo.mkdir()
        self.private = root / "owner-private"
        self.log = root / "owner-test.txt"
        self.gpx = root / "synthetic.gpx"
        self.log.write_text(LOG, encoding="utf-8")
        self.gpx.write_bytes(GPX)

    def read_report(self, result):
        path = self.private / "research" / (result["receipt_id"] + ".json")
        return json.loads(path.read_text(encoding="utf-8")), path

    def test_one_command_runs_existing_intake_then_indexed_research(self):
        first = intake_and_research(self.repo, self.private, log_file=self.log, gpx_file=self.gpx)
        report, path = self.read_report(first)
        self.assertEqual(report["schema_version"], VERSION)
        self.assertEqual(report["status"], "OWNER_SOURCE_DIAGNOSTIC_READY")
        self.assertEqual(first["research_nights_indexed"], 1)
        self.assertEqual(first["capture_events_indexed"], 2)
        self.assertEqual(len(report["private_event_records"]), 3)
        self.assertEqual(report["research_nights"][0]["capture_event_hours_jst"], {"22": 1, "23": 1})
        self.assertEqual(report["research_nights"][0]["habu_roadkill_events"], 1)
        self.assertEqual(report["research_nights"][0]["habu_sighting_events"], 0)
        self.assertIsNone(report["research_nights"][0]["verified_individual_count"])
        self.assertEqual(report["formal_negative_labels_created"], 0)
        self.assertEqual(report["P0_score"], "NOT_EVALUATED")
        self.assertEqual(report["research_candidate_fit"], "NOT_RUN")
        self.assertFalse(report["production_champion_activated"])
        self.assertNotIn("event_time_jst", json.dumps(first))
        self.assertNotIn("SYNTHETIC_NOT_A_LOCATION", path.read_text())
        old_bytes = path.read_bytes()
        same = intake_and_research(self.repo, self.private, log_file=self.log, gpx_file=self.gpx)
        self.assertEqual(same, first)
        self.assertEqual(path.read_bytes(), old_bytes)
        self.assertEqual(len(list((self.private / "raw" / "log").glob("*.txt"))), 1)

    def test_saved_receipt_can_be_rechecked_without_reupload(self):
        first = intake_and_research(self.repo, self.private, log_file=self.log)
        again = research_receipt(self.repo, self.private, first["receipt_id"])
        self.assertEqual(first, again)
        self.assertEqual(len(list((self.private / "research").glob("*.json"))), 1)

    def test_modified_archive_is_rejected_not_fitted(self):
        first = intake_and_research(self.repo, self.private, log_file=self.log)
        archive = next((self.private / "raw" / "log").glob("*.txt"))
        archive.write_bytes(archive.read_bytes() + b"altered")
        with self.assertRaises(IntakeError):
            research_receipt(self.repo, self.private, first["receipt_id"])
        report, _ = self.read_report(first)
        self.assertEqual(report["research_candidate_fit"], "NOT_RUN")

    def test_wrong_receipt_path_and_duplicate_keys_are_rejected(self):
        first = intake_and_research(self.repo, self.private, log_file=self.log)
        receipt = self.private / "receipts" / (first["receipt_id"] + ".json")
        original = receipt.read_bytes()
        try:
            receipt.write_bytes(original[:-2] + b', "receipt_id": "forged"}\n')
            with self.assertRaises(IntakeError):
                research_receipt(self.repo, self.private, first["receipt_id"])
        finally:
            receipt.write_bytes(original)
        row = json.loads(original)
        row["sources"][0]["private_archive"] = "/tmp/untrusted.txt"
        receipt.write_text(json.dumps(row), encoding="utf-8")
        with self.assertRaises(IntakeError):
            research_receipt(self.repo, self.private, first["receipt_id"])

    def test_gpx_only_is_unknown_not_zero_capture(self):
        result = intake_and_research(self.repo, self.private, gpx_file=self.gpx)
        report, _ = self.read_report(result)
        self.assertEqual(report["status"], "GPX_ONLY_NO_OUTCOME_LABELS")
        self.assertEqual(report["research_nights"], [])
        self.assertEqual(report["private_event_records"], [])
        self.assertEqual(report["formal_negative_labels_created"], 0)
        self.assertEqual(result["capture_events_indexed"], 0)
        self.assertFalse(result["official_model_activated"])

    def test_public_repo_root_is_rejected(self):
        with self.assertRaises(IntakeError):
            intake_and_research(self.repo, self.repo / "private", log_file=self.log)
        self.assertFalse((self.repo / "private" / "research").exists())

    def test_log_and_receipt_input_conflict_is_rejected(self):
        with self.assertRaises(IntakeError):
            intake_and_research(self.repo, self.private, log_file=self.log, receipt_id="0"*64)

    def test_invalid_receipt_id_fails_before_file_read(self):
        self.private.mkdir(mode=0o700)
        with self.assertRaises(IntakeError):
            research_receipt(self.repo, self.private, "../fake")


if __name__ == "__main__":
    unittest.main()
