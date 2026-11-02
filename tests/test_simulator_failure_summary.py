"""Public CI diagnostics may emit fixed categories, never raw test payloads."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "mobile/ios/simulator_failure_summary.py"


class SimulatorFailureSummaryTests(unittest.TestCase):
    def run_report(self, payload):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "report.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run([sys.executable, str(SCRIPT), str(p)],
                                  capture_output=True, text=True)

    def test_classifies_stale_target_without_printing_values(self):
        result = self.run_report({"passedTests": 8, "failedTests": 1,
            "testFailures": [{"failureText":
                "新しい探索の検証・書き出し先が以前の記録のまま secret@example.invalid 35.12345",
                "testName": "testNewSearchSelectsNewRecordAndClearsPreviousEvidenceAndExport()"}]})
        self.assertEqual(result.returncode, 0)
        self.assertIn("WRONG_SESSION_TARGET", result.stdout)
        self.assertNotIn("secret@", result.stdout)
        self.assertNotIn("35.12345", result.stdout)

    def test_reports_share_control_failure(self):
        result = self.run_report({"testFailures": [{"failureText": "GPX作成後の共有UIがない"}]})
        self.assertEqual(result.returncode, 0)
        self.assertIn("SHARE_CONTROL_NOT_FOUND", result.stdout)

    def test_unknown_payload_is_not_echoed(self):
        result = self.run_report({"testFailures": [{"failureText": "PRIVATE-DEVICE-ID",
                                                   "testName": "PRIVATE-ACCOUNT"}]})
        self.assertEqual(result.returncode, 0)
        self.assertIn("UNCLASSIFIED_ASSERTION", result.stdout)
        self.assertNotIn("PRIVATE", result.stdout + result.stderr)

    def test_unreadable_report_is_fixed_category(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "/missing/private/path.json"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "SIMULATOR_REPORT_UNAVAILABLE")
        self.assertEqual(result.stderr, "")

    def test_empty_report_still_emits_a_fixed_diagnostic(self):
        result = self.run_report({})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "SIMULATOR_REPORT_NO_FAILURE_DETAILS")
