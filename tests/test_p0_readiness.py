"""Evidence-aware P0 preflight must never issue or backdate ORIGINAL forecasts."""
import importlib.util
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "habu_p0_preflight", ROOT / "scripts" / "check_p0_readiness.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
JST = ZoneInfo("Asia/Tokyo")


class P0ReadinessTests(unittest.TestCase):
    def test_production_issuance_is_blocked_without_authority(self):
        with tempfile.TemporaryDirectory() as folder:
            now = datetime(2026, 10, 23, 17, 0, tzinfo=JST)
            start = datetime(2026, 10, 23, 19, 0, tzinfo=JST)
            report = module.inspect(Path(folder), "2026-10-23",
                                    now=now, planned_start=start)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertFalse(report["official_original_p0_issued"])
            self.assertTrue(report["read_only"])
            self.assertIn("PRODUCTION_ISSUANCE_AUTHORITY_BLOCKED",
                          {b["code"] for b in report["blockers"]})
            self.assertFalse((Path(folder) / "predictions").exists())

    def test_past_night_and_after_start_cannot_be_retroactive_original(self):
        with tempfile.TemporaryDirectory() as folder:
            report = module.inspect(
                Path(folder), "2026-10-22",
                now=datetime(2026, 10, 23, 8, 0, tzinfo=JST),
                planned_start=datetime(2026, 10, 22, 20, 0, tzinfo=JST),
            )
            errors = {b["code"] for b in report["blockers"]}
            self.assertIn("HISTORICAL_NIGHT", errors)
            self.assertIn("START_NOT_FUTURE", errors)
            self.assertFalse(report["official_stage_gate_scored"])

    def test_existing_original_is_never_modified(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "predictions/original/2026-10-23/P0/prediction.json"
            path.parent.mkdir(parents=True)
            path.write_text('{"fake": true}', encoding="utf-8")
            before = path.read_bytes()
            report = module.inspect(
                Path(folder), "2026-10-23",
                now=datetime(2026, 10, 23, 17, 0, tzinfo=JST),
                planned_start=datetime(2026, 10, 23, 20, 0, tzinfo=JST),
            )
            self.assertTrue(report["existing_p0_directory"])
            self.assertIn("ORIGINAL_P0_ALREADY_EXISTS",
                          {b["code"] for b in report["blockers"]})
            self.assertEqual(path.read_bytes(), before)

    def test_0700_boundary_and_timezone_aware(self):
        self.assertEqual(module.operational_night(
            datetime(2026, 10, 23, 6, 59, tzinfo=JST)), "2026-10-22")
        self.assertEqual(module.operational_night(
            datetime(2026, 10, 23, 7, 0, tzinfo=JST)), "2026-10-23")
        with self.assertRaises(ValueError):
            module.operational_night(datetime(2026, 10, 23, 0, 0))
        with self.assertRaises(ValueError):
            module.inspect(Path("."), "2026-10-23",
                           now=datetime(2026, 10, 23, 9, 0))

    def test_start_requires_same_operational_night(self):
        with tempfile.TemporaryDirectory() as folder:
            report = module.inspect(
                Path(folder), "2026-10-23",
                now=datetime(2026, 10, 23, 18, 0, tzinfo=JST),
                planned_start=datetime(2026, 10, 24, 7, 0, tzinfo=JST))
            self.assertIn("START_NIGHT_MISMATCH",
                          {b["code"] for b in report["blockers"]})


if __name__ == "__main__":
    unittest.main()
