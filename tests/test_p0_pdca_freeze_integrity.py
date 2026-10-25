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

import pdca_pipeline


NIGHT = "2026-09-30"
ISSUED = datetime.fromisoformat("2026-09-30T20:00:00+09:00")


class PredictionSidecarPathTests(unittest.TestCase):
    """Verify existing disk bytes without depending on the Linux Freeze writer."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.record = {
            "prediction_class": "ORIGINAL",
            "prediction_version": "P0",
            "operational_night": NIGHT,
            "cutoff_time": "2026-09-30T20:00:00+09:00",
            "payload_sha256": "1371f25b0429307ebd7fe9cc039c469b8c3b6369fa96b9a5b2593d235a8dea3f",
        }
        self.frozen = self.root / f"predictions/original/{NIGHT}/P0/prediction.json"
        self.frozen.parent.mkdir(parents=True)
        self.frozen.write_bytes(
            json.dumps(self.record, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        )
        self.sidecar = self.frozen.with_name("sha256.txt")
        self.sidecar.write_bytes((self.record["payload_sha256"] + "  prediction.json\n").encode("ascii"))

    def assert_path_integrity(self, status, sidecar_status, *, night=NIGHT):
        for separator in ("/", "\\"):
            with self.subTest(separator=separator):
                loaded = pdca_pipeline.load_predictions(self.root, NIGHT)
                loaded[0]["_path"] = f"predictions/original/{night}/P0/prediction.json".replace("/", separator)
                actual_status, rows = pdca_pipeline.verify_predictions(loaded, root=self.root, night=night)
                self.assertEqual(actual_status, status)
                self.assertEqual(rows[0]["sidecar_status"], sidecar_status)

    def test_valid_sidecar_is_checked_for_both_path_separators(self):
        self.assert_path_integrity("PASS", "MATCH")

    def test_missing_sidecar_is_partial_for_both_path_separators(self):
        self.sidecar.unlink()
        self.assert_path_integrity("PARTIAL", "MISSING")

    def test_corrupt_sidecar_fails_for_both_path_separators(self):
        self.sidecar.write_bytes(b"corrupt\n")
        self.assert_path_integrity("FAIL", "MISMATCH")

    def test_noncanonical_record_bytes_fail_for_both_path_separators(self):
        self.frozen.write_bytes(json.dumps(self.record, indent=2).encode("utf-8") + b"\n")
        self.assert_path_integrity("FAIL", "NONCANONICAL_BYTES")

    def test_loader_native_path_cannot_skip_corrupt_sidecar(self):
        self.sidecar.write_bytes(b"corrupt\n")
        loaded = pdca_pipeline.load_predictions(self.root, NIGHT)
        status, rows = pdca_pipeline.verify_predictions(loaded, root=self.root, night=NIGHT)
        self.assertEqual(status, "FAIL")
        self.assertEqual(rows[0]["sidecar_status"], "MISMATCH")

    def test_canonical_night_traversal_is_rejected_for_both_path_separators(self):
        self.assert_path_integrity("FAIL", "INVALID", night=f"{NIGHT}/../{NIGHT}")

    def test_symlinked_sidecar_is_rejected_for_both_path_separators(self):
        external = self.root / "untrusted-sidecar.txt"
        external.write_bytes(self.sidecar.read_bytes())
        self.sidecar.unlink()
        self.sidecar.symlink_to(external)
        self.assert_path_integrity("FAIL", "INVALID")

    def test_symlinked_record_is_rejected_for_both_path_separators(self):
        external = self.root / "untrusted-prediction.json"
        external.write_bytes(self.frozen.read_bytes())
        self.frozen.unlink()
        self.frozen.symlink_to(external)
        self.assert_path_integrity("FAIL", "INVALID")


class P0ToPDCAIntegrityTests(unittest.TestCase):
    def setUp(self):
        import freeze_prediction

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

    def test_pdca_aborts_before_reading_observations_on_corrupt_frozen_p0(self):
        self.sidecar.write_text("corrupt\n", encoding="ascii")
        result = pdca_pipeline.run_pipeline(self.root, NIGHT)
        self.assertEqual(result["overall_status"], "FAIL")
        self.assertNotIn("p0_score", result)
        self.assertEqual(result["integrity"][0]["sidecar_status"], "MISMATCH")

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
