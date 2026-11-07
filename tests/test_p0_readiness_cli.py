"""Read-only readiness must not depend on the POSIX execution runtime."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class P0ReadinessCLIRegressionTests(unittest.TestCase):
    def test_unavailable_posix_runtime_still_returns_actual_blocked_preflight(self):
        with tempfile.TemporaryDirectory() as folder:
            # A real child process sees fcntl as unavailable on every platform.
            # No fake lock implementation or production registry is installed.
            result = subprocess.run(
                [sys.executable, "-X", "utf8", "-c",
                 "import runpy,sys; sys.modules['fcntl']=None; "
                 "sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')",
                 str(ROOT / "scripts/check_p0_readiness.py"),
                 "--root", folder, "--night", "2099-11-02",
                 "--planned-start", "2099-11-02T19:00:00+09:00"],
                capture_output=True, text=True, encoding="utf-8", timeout=30,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertIs(report["read_only"], True)
            self.assertIs(report["official_original_p0_issued"], False)
            codes = {b["code"] for b in report["blockers"]}
            self.assertIn("PRODUCTION_ISSUANCE_AUTHORITY_BLOCKED", codes)
            self.assertIn("EX_ANTE_INPUT_BUNDLE_NOT_ATTESTED", codes)
            self.assertIn("FORMAL_PREDICTION_OUTPUT_NOT_ATTESTED", codes)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_issuer_cli_reaches_canonical_preflight_without_posix_or_a_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            issuer = str(ROOT / "scripts/issue_prediction.py")
            command = [sys.executable, "-X", "utf8", "-c",
                "import runpy,sys; sys.modules['fcntl']=None; "
                "sys.modules['champion_registry']=None; sys.modules['freeze_prediction']=None; "
                "sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')", issuer,
                "--root", folder, "--night", "2099-11-02",
                "--planned-start", "2099-11-02T19:00:00+09:00"]
            for optional in ([], ["--snapshot", str(Path(folder) / "unopened.json"),
                                   "--snapshot-sha256", "0" * 64, "--version", "P0"]):
                with self.subTest(legacy_arguments=bool(optional)):
                    result = subprocess.run(command + optional, capture_output=True, text=True,
                                            encoding="utf-8", timeout=30)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    report = json.loads(result.stdout)
                    self.assertEqual(report["status"], "BLOCKED")
                    self.assertEqual(report["decision"], "PROVISIONAL_NOT_FREEZABLE")
                    self.assertIs(report["official_original_p0_issued"], False)
                    self.assertIs(report["read_only"], True)
                    codes = {b["code"] for b in report["blockers"]}
                    self.assertIn("PRODUCTION_ISSUANCE_AUTHORITY_BLOCKED", codes)
                    self.assertNotIn("PRE_EXPLORATION_START_UNKNOWN", codes)
                    self.assertNotIn("unopened.json", result.stdout + result.stderr)
                    self.assertEqual(list(Path(folder).iterdir()), [])

    def test_both_clis_reject_an_offset_that_python_would_normalize(self):
        for script in ("check_p0_readiness.py", "issue_prediction.py"):
            with self.subTest(script=script):
                result = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts" / script),
                    "--night", "2099-11-02", "--planned-start", "2099-11-02T19:00:00+08:60"],
                    capture_output=True, text=True, encoding="utf-8", timeout=30)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn("--planned-start", result.stderr)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
