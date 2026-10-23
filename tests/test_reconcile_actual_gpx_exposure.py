"""Real September 28 GPX/source contradiction cannot be silently trained."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reconcile_actual_gpx_exposure as recon


class RealSourceReconciliationTests(unittest.TestCase):
    def test_real_archive_events_and_monthly_conflict_are_quarantined(self):
        report = recon.reconcile(ROOT, "2026-09-28")
        self.assertEqual(report["status"], "TRAINING_BLOCKED")
        self.assertEqual(report["individual_capture_count_source"], 6)
        self.assertEqual(report["individual_capture_count_frozen_baseline"], 5)
        self.assertEqual(report["event_count"], 5)
        self.assertEqual(report["event_individual_total"], 6)
        self.assertEqual(report["gpx"]["point_count"], 22990)
        self.assertEqual(report["gpx"]["source_sha256"],
                         "2e9fde7aa459fc100abf8014d95635e697a638679cc9df731f4e0f6a80fb62f3")
        self.assertGreater(report["gpx"]["eligible_sample_points"], 0)
        self.assertGreater(report["gpx"]["sampled_100m_10min_units"], 0)
        self.assertEqual(report["observed_negative_count"], 0)
        self.assertEqual(report["formal_model_training_rows"], 0)
        self.assertFalse(report["P0_scored"])
        self.assertFalse(report["stage1_top10_recall_scored"])
        self.assertFalse(report["formal_100m_10min_scored"])
        self.assertTrue(report["unknown_not_negative"])
        self.assertTrue(report["gpX_passage_evidence_only"])
        blockers = {x["code"] for x in report["blockers"]}
        self.assertIn("FROZEN_BASELINE_CAPTURE_COUNT_CONFLICT", blockers)
        self.assertIn("SEARCH_EXPOSURE_AND_COMPLETE_OUTCOME_ATTESTATION_MISSING", blockers)

    def test_manifest_sha_and_line_archive_cannot_be_forged(self):
        parts = ROOT / "data/raw/gpx_archives/2026-09-28-探索.gpx.lines"
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder)
            manifest = json.loads((parts/"manifest.json").read_text())
            manifest["raw_sha256"] = "f"*64
            (archive/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
            for p in parts.glob("part_*.txt"):
                (archive/p.name).write_bytes(p.read_bytes())
            with self.assertRaises(recon.ReconciliationError):
                recon.reconstruct_archive(archive)

    def test_baseline_disagreement_blocks_more_labels_not_less(self):
        report = recon.reconcile(ROOT, "2026-09-28")
        # Both legitimate capture observations and earlier 947 reported negative
        # units must remain diagnostic, not independently validated labels.
        self.assertNotIn("training_rows", report)
        self.assertFalse(report["known_historical_exposure_csv_labels_promoted"])

    def test_point_day_boundary(self):
        self.assertEqual(recon.night_for(recon.timestamp("2026-09-29T06:59:59+09:00")),
                         "2026-09-28")
        self.assertEqual(recon.night_for(recon.timestamp("2026-09-29T07:00:00+09:00")),
                         "2026-09-29")

    def test_no_automatic_positive_eligibility_even_if_count_equal(self):
        original = recon.load_capture_ledger
        def fake(root, night):
            events, ledger = original(root, night)
            ledger["individual_count"] = 5
            return events, ledger
        with patch.object(recon, "load_capture_ledger", side_effect=fake):
            report = recon.reconcile(ROOT, "2026-09-28")
        self.assertEqual(report["formal_model_training_rows"], 0)
        self.assertEqual(report["observed_negative_count"], 0)
        codes = {x["code"] for x in report["blockers"]}
        self.assertNotIn("FROZEN_BASELINE_CAPTURE_COUNT_CONFLICT", codes)
        self.assertIn("EX_ANTE_FORECAST_UNIVERSE_AND_FEATURE_AVAILABILITY_MISSING", codes)


if __name__ == "__main__":
    unittest.main()
