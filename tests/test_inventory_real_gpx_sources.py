"""Real GPX inventory cannot turn legacy tracks into zero-capture observations."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import inventory_real_gpx_sources as inv


class TrackInventoryTests(unittest.TestCase):
    def test_original_repo_has_many_real_tracks_but_no_new_training_labels(self):
        report = inv.build_inventory(ROOT)
        self.assertEqual(report["status"], "TRAINING_INPUTS_INCOMPLETE")
        self.assertGreaterEqual(report["raw_gpx_files"], 13)
        self.assertGreaterEqual(report["archive_manifests"], 1)
        self.assertEqual(report["formal_model_learning_rows"], 0)
        self.assertFalse(report["official_original_p0_scored"])
        self.assertFalse(any(x["negative_label_eligible"] for x in report["raw_gpx"]))
        self.assertFalse(any(x["negative_label_eligible"] for x in report["archives"]))
        self.assertEqual(len(report["raw_gpx"]), report["raw_gpx_files"])

    def test_one_gpx_is_not_proof_of_a_capture_free_night(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            gpx=root/"data/raw/gpx/2026-08-11__legacy.gpx"
            gpx.parent.mkdir(parents=True)
            gpx.write_text(
                '<?xml version="1.0" ?><gpx version="1.1"><trk><trkseg>'
                '<trkpt lat="28.18" lon="129.34"><time>2026-08-11T12:00:00Z</time></trkpt>'
                '<trkpt lat="28.18" lon="129.35"><time>2026-08-11T12:01:00Z</time></trkpt>'
                '</trkseg></trk></gpx>',
                encoding="utf-8")
            report=inv.build_inventory(root)
            self.assertEqual(report["raw_gpx_files"], 1)
            track=report["raw_gpx"][0]
            self.assertTrue(track["gpx_track_valid"])
            self.assertEqual(track["operational_night_point_counts"], {"2026-08-11": 2})
            self.assertFalse(track["negative_label_eligible"])
            self.assertIsNone(track["observed_zero_captures"])
            self.assertFalse(track["paired_event_and_individual_ledgers"])

    def test_wrong_clock_is_quarantined(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"clock.gpx"
            p.write_text(
                '<gpx><trk><trkseg>'
                '<trkpt lat="28.18" lon="129.34"><time>2026-08-11T12:01:00Z</time></trkpt>'
                '<trkpt lat="28.18" lon="129.35"><time>2026-08-11T12:00:00Z</time></trkpt>'
                '</trkseg></trk></gpx>', encoding="utf-8")
            report=inv.audit_real_gpx(p)
            self.assertEqual(report["backward_time_jumps"], 1)
            self.assertFalse(report["gpx_track_valid"])
            self.assertEqual(report["scientific_label_status"], "TRACK_CLOCK_QC_FAILED")


if __name__ == "__main__":
    unittest.main()
