"""Signing diagnostics must not leak sensitive Xcode build logs.

All fixtures synthetic. Never use real Apple identifiers or private profiles.
"""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLASSIFIER = ROOT / "mobile/ios/signing_failure_classifier.py"
SPEC = importlib.util.spec_from_file_location("signing_failure_classifier", CLASSIFIER)
assert SPEC is not None and SPEC.loader is not None
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class SigningFailureClassifierTests(unittest.TestCase):
    def test_xcode_classifications(self):
        fixtures = {
            "error: There are no accounts registered with Xcode. Add an account.": "ACCOUNT_NOT_CONFIGURED",
            "error: No Account for Team XXXXXXXXXX": "ACCOUNT_NOT_CONFIGURED",
            "error: Your program license agreement has been updated": "AGREEMENT_REQUIRED",
            "error: Failed to register bundle identifier org.example.test": "BUNDLE_ID_UNAVAILABLE",
            "error: Bundle identifier org.example.test is not available": "BUNDLE_ID_UNAVAILABLE",
            "error: No signing certificate 'iOS Development' found": "CERTIFICATE_NOT_USABLE",
            "error: No profiles for 'org.example.test' were found": "PROVISIONING_PROFILE_MISSING",
            "error: Provisioning profile does not include the device": "DEVICE_NOT_REGISTERED",
            "error: Personal Team does not support this capability": "CAPABILITY_NOT_ALLOWED",
            "error: Could not connect to Apple Developer Portal": "DEVELOPER_SERVICE_UNAVAILABLE",
            "View.swift:12:15: error: cannot find 'missingSymbol' in scope": "COMPILATION_ERROR",
            "error: Swift compiler exited for unclassified reason": "BUILD_FAILURE_UNCLASSIFIED",
        }
        for sample, expected in fixtures.items():
            with self.subTest(expected=expected, sample=sample):
                self.assertEqual(mod.classify(sample), expected)

    def test_ordinary_signing_word_is_not_proof_of_signing_failure(self):
        log = "note: signing settings were checked\nerror: unusual test failure"
        self.assertEqual(mod.classify(log), "BUILD_FAILURE_UNCLASSIFIED")

    def test_cli_never_discloses_private_log_contents(self):
        private_text = (
            "/Users/private-user/Library/Developer/Xcode/file\n"
            "developer@example.invalid\n"
            'error: No profiles for "org.example.habu" were found\n'
            "Private signing serial: SECRET-123\n"
        )
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "build.log"
            file.write_text(private_text, encoding="utf-8")
            output = subprocess.run(
                [sys.executable, str(CLASSIFIER), str(file)],
                capture_output=True, text=True, check=True,
            )
            self.assertEqual(output.stdout.strip(), "PROVISIONING_PROFILE_MISSING")
            self.assertEqual(output.stderr, "")
            for secret in ("private-user", "developer@example.invalid",
                           "org.example.habu", "SECRET-123", str(file)):
                self.assertNotIn(secret, output.stdout + output.stderr)


if __name__ == "__main__":
    unittest.main()
