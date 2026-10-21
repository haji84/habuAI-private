"""End-to-end immutable P0 artifact -> actual-evidence PDCA boundary regressions.

These tests deliberately exercise the generic, NON-AUTHORIZED Freeze path. Matching
captures are diagnostics, never claims of a live production P0 or model skill.
"""
import csv
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

import freeze_prediction
import pdca_pipeline


NIGHT = "2026-09-30"
ISSUED = datetime.fromisoformat("2026-09-30T20:00:00+09:00")


class P0ToPDCAIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / "candidate.json"
        source.write_text(json.dumps({
            "cutoff_time": ISSUED.isoformat(),
            "targets_100m_10min": [{
                "target_id": "T1",
                "latitude": 28.15,
                "longitude": 129.30,
                "predicted_time_jst": "2026-09-30T21:00:00+09:00",
                "radius_m": 100,
                "time_tolerance_min": 10,
            }],
        }), encoding="utf-8")
        self.frozen = freeze_prediction.freeze(self.root, source, NIGHT, "P0", now=ISSUED)
        self.sidecar = self.frozen.parent / "sha256.txt"

    def integrity(self):
        loaded = pdca_pipeline.load_predictions(self.root, NIGHT)
        return pdca_pipeline.verify_predictions(loaded, root=self.root, night=NIGHT)

    def test_real_freeze_bytes_and_sha_sidecar_agree(self):
        status, rows = self.integrity()
        self.assertEqual(status, "PASS")
        self.assertEqual(rows[0]["sidecar_status"], "MATCH")
        self.assertEqual(rows[0]["prediction_version"], "P0")

    def test_sidecar_corruption_is_fail_not_a_missing_provenance_warning(self):
        self.sidecar.write_text("0" * 64 + "  prediction.json\n", encoding="ascii")
        status, rows = self.integrity()
        self.assertEqual(status, "FAIL")
        self.assertEqual(rows[0]["sidecar_status"], "MISMATCH")
        self.assertIn("sidecar", rows[0]["reason"])

    def test_format_only_prediction_mutation_is_detected(self):
        record = json.loads(self.frozen.read_text(encoding="utf-8"))
        self.frozen.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        status, rows = self.integrity()
        self.assertEqual(status, "FAIL")
        self.assertEqual(rows[0]["sidecar_status"], "NONCANONICAL_BYTES")

    def test_missing_sidecar_stays_diagnostic_not_official(self):
        self.sidecar.unlink()
        status, rows = self.integrity()
        self.assertEqual(status, "PARTIAL")
        self.assertEqual(rows[0]["sidecar_status"], "MISSING")

    def test_symlinked_sidecar_is_rejected(self):
        original = self.sidecar.read_bytes()
        external = self.root / "untrusted-sidecar.txt"
        external.write_bytes(original)
        self.sidecar.unlink()
        self.sidecar.symlink_to(external)
        status, rows = self.integrity()
        self.assertEqual(status, "FAIL")
        self.assertEqual(rows[0]["sidecar_status"], "INVALID")

    def test_frozen_p0_to_gpx_capture_pdca_is_diagnostic_not_official(self):
        gpx = self.root / "data/raw/gpx/night.gpx"
        gpx.parent.mkdir(parents=True)
        gpx.write_text(
            '<?xml version="1.0"?>'
            '<gpx version="1.1"><trk><trkseg>'
            '<trkpt lat="28.15" lon="129.30">'
            '<time>2026-09-30T12:03:00Z</time>'
            '</trkpt></trkseg></trk></gpx>',
            encoding="utf-8",
        )
        captures = self.root / "data/raw/capture_db/captures.csv"
        captures.parent.mkdir(parents=True)
        with captures.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=[
                "event", "datetime_jst", "latitude", "longitude", "event_id", "event_count",
            ])
            writer.writeheader()
            writer.writerow({
                "event": "capture", "datetime_jst": "2026-09-30T21:03:00+09:00",
                "latitude": "28.15", "longitude": "129.30",
                "event_id": "C1", "event_count": "1",
            })
        result = pdca_pipeline.run_pipeline(self.root, NIGHT)
        verify = next(s for s in result["stages"] if s["name"] == "verify_prediction_integrity")
        self.assertEqual(verify["status"], "PASS")
        self.assertEqual(result["p0_score"]["matched_targets"], 1)
        self.assertEqual(result["p0_score"]["formal_100m_10min_status"], "SCORED")
        self.assertFalse(result["p0_score"]["strict_official_score_eligible"])
        p0 = next(s for s in result["stages"] if s["name"] == "score_p0")
        self.assertEqual(p0["status"], "NOT_VALIDATED")
        self.assertEqual(result["overall_status"], "PARTIAL")
        # Rechecking must not rewrite the prediction or infer Champion promotion.
        self.assertEqual(self.integrity()[0], "PASS")


if __name__ == "__main__":
    unittest.main()
