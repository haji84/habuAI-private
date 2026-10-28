"""Read-only future-night acceptance never promotes synthetic or unauthenticated evidence."""
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

import pdca_pipeline
from master_contracts import canonical_bytes

spec = importlib.util.spec_from_file_location(
    "next_night_e2e", ROOT / "scripts" / "audit_next_real_night_e2e.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
JST = ZoneInfo("Asia/Tokyo")
NIGHT = "2026-11-02"
START = datetime(2026, 11, 2, 19, 0, tzinfo=JST)
NOW = datetime(2026, 11, 2, 17, 0, tzinfo=JST)


class RealNightE2EAcceptanceTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)

    def check(self, phase="after", start=START, now=NOW):
        return gate.inspect(self.root, NIGHT, actual_start=start, phase=phase, now=now)

    def codes(self, result):
        return {v["code"] for v in result["blockers"]}

    def write_p0(self, *, created="2026-11-02T18:00:00+09:00",
                 frozen="2026-11-02T18:01:00+09:00", corrupt=False):
        payload = {
            "prediction_class": "ORIGINAL",
            "operational_night": NIGHT,
            "prediction_version": "P0",
            "created_at": created,
            "cutoff_time": "2026-11-02T17:59:00+09:00",
            "frozen_at": frozen,
            "targets_100m_10min": [{
                "target_id": "mock-only",
                "latitude": 28.15,
                "longitude": 129.3,
                "predicted_time_jst": "2026-11-02T20:00:00+09:00",
            }],
        }
        payload["payload_sha256"] = pdca_pipeline.canonical_prediction_hash(payload)
        path = self.root / f"predictions/original/{NIGHT}/P0/prediction.json"
        path.parent.mkdir(parents=True)
        path.write_bytes(canonical_bytes(payload) + b"\n")
        sidecar = path.with_name("sha256.txt")
        sidecar.write_bytes(((("0" * 64) if corrupt else payload["payload_sha256"])
                             + "  prediction.json\n").encode("ascii"))
        return path

    def test_missing_original_remains_blocked_without_writes(self):
        before = sorted(self.root.rglob("*"))
        result = self.check()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("P0_MISSING_OR_DUPLICATE", self.codes(result))
        self.assertIn("PDCA_REPORT_MISSING", self.codes(result))
        self.assertEqual(sorted(self.root.rglob("*")), before)

    def test_before_reuses_existing_strict_preflight(self):
        result = self.check("before")
        self.assertFalse(result["official_e2e_complete"])
        self.assertTrue(result["read_only"])
        self.assertIn("PRODUCTION_ISSUANCE_AUTHORITY_BLOCKED", self.codes(result))
        self.assertFalse((self.root / "predictions").exists())

    def test_valid_synthetic_freeze_is_not_production_authority(self):
        original = self.write_p0()
        before = original.read_bytes()
        result = self.check()
        self.assertEqual(result["evidence"]["p0_freeze_integrity"], "PASS")
        self.assertEqual(result["evidence"]["p0_sidecar"], "MATCH")
        self.assertIn("TRUSTED_REAL_E2E_UNATTESTED", self.codes(result))
        self.assertNotIn("P0_NOT_PROSPECTIVE", self.codes(result))
        self.assertFalse(result["official_e2e_complete"])
        self.assertEqual(original.read_bytes(), before)

    def test_late_freeze_is_rejected(self):
        self.write_p0(frozen="2026-11-02T19:00:00+09:00")
        self.assertIn("P0_NOT_PROSPECTIVE", self.codes(self.check()))

    def test_bad_sidecar_never_counts_as_p0(self):
        self.write_p0(corrupt=True)
        result = self.check()
        self.assertIn("P0_FREEZE_INVALID", self.codes(result))
        self.assertEqual(result["evidence"]["p0_sidecar"], "MISMATCH")

    def test_recovered_prediction_does_not_replace_original(self):
        path = self.root / f"predictions/recovered_original/{NIGHT}/P0/prediction.json"
        path.parent.mkdir(parents=True)
        path.write_text('{"prediction_version":"P0"}', encoding="utf-8")
        self.assertIn("P0_MISSING_OR_DUPLICATE", self.codes(self.check()))

    def test_fake_all_pass_pdca_report_does_not_certify_real_e2e(self):
        self.write_p0()
        path = self.root / f"reports/pdca/{NIGHT}/pdca_result.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({
            "operational_night": NIGHT, "overall_status": "PASS",
            "completed": True,
            "run_id": "f" * 64,
            "stages": [{"name": n, "status": "PASS"} for n in gate.STAGE_NAMES],
            "operational_result": {"p0_score": {"strict_official_score_eligible": True}},
        }), encoding="utf-8")
        result = self.check()
        self.assertIn("PDCA_MANIFEST_NOT_BOUND", self.codes(result))
        self.assertIn("TRUSTED_REAL_E2E_UNATTESTED", self.codes(result))
        self.assertFalse(result["official_e2e_complete"])

    def test_0700_boundary_and_wrong_night(self):
        at = datetime(2026, 11, 3, 6, 59, tzinfo=JST)
        self.assertEqual(gate.night_for(at), NIGHT)
        self.assertEqual(gate.night_for(datetime(2026, 11, 3, 7, 0, tzinfo=JST)),
                         "2026-11-03")
        self.assertIn("START_NIGHT_MISMATCH", self.codes(self.check(start=datetime(
            2026, 11, 3, 7, 0, tzinfo=JST))))

    def test_naive_time_and_invalid_phase_rejected(self):
        with self.assertRaises(ValueError):
            gate.aware("2026-11-02T18:00:00")
        with self.assertRaises(ValueError):
            self.check(start=datetime(2026, 11, 2, 19, 0))
        with self.assertRaises(ValueError):
            self.check(phase="issue")

    def test_symlink_to_external_original_never_accepted(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "original"
            target.mkdir()
            p = self.root / "predictions"
            p.mkdir()
            (p / "original").symlink_to(target, target_is_directory=True)
            result = self.check()
            self.assertIn("P0_READ_INVALID", self.codes(result))


if __name__ == "__main__":
    unittest.main()
