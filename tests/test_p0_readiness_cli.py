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


if __name__ == "__main__":
    unittest.main()
