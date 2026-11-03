"""Mock-only checks for owner-triggered wireless installation.

Never connects to a real phone, uses Apple credentials, or ships artifacts.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "mobile/ios/install-owned-iphone-wireless.sh"


def executable(directory: Path, name: str, body: str):
    path = directory / name
    path.write_text("#!/usr/bin/env bash\n" + body + "\n", encoding="utf-8")
    path.chmod(0o755)


class OwnedIPhoneInstallerTests(unittest.TestCase):
    def test_script_syntax(self):
        result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def run_mock(self, devices: dict, certificate: bool = True, failure_log: str = ""):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            binaries = base / "bin"
            binaries.mkdir()
            trace = base / "trace"
            fixture = base / "devices.json"
            import json
            fixture.write_text(json.dumps({"result": {"devices": devices}}), encoding="utf-8")
            executable(binaries, "uname", '[[ "$1" == "-s" ]] && echo Darwin || /usr/bin/uname "$@"')
            executable(binaries, "xcodegen", "exit 0")
            executable(binaries, "security", (
                'echo \'  1) DEADBEEF "Apple Development: Unit Test (ABCDEFGHIJ)"\''
                if certificate else 'echo "0 valid identities found"'
            ))
            executable(binaries, "xcrun", r'''
if [[ "$1" == "devicectl" && "$2" == "list" && "$3" == "devices" ]]; then
  cp "$DEVICE_FIXTURE" "$5"
elif [[ "$1" == "devicectl" && "$2" == "device" && "$3" == "install" ]]; then
  echo "device-install" >> "$MOCK_TRACE"
elif [[ "$1" == "devicectl" && "$2" == "device" && "$3" == "process" && "$4" == "launch" ]]; then
  echo "device-launch" >> "$MOCK_TRACE"
else
  exit 2
fi
''')
            executable(binaries, "xcodebuild", r'''
if [[ "$1" == "-version" ]]; then echo "Xcode 27.0"; exit 0; fi
if [[ -n "${MOCK_XCODE_FAILURE:-}" ]]; then
  printf '%s\n' "$MOCK_XCODE_FAILURE" >&2
  exit 65
fi
previous=""
for arg in "$@"; do
  if [[ "$previous" == "-derivedDataPath" ]]; then
    mkdir -p "$arg/Build/Products/Debug-iphoneos/HabuFieldRecorder.app"
  fi
  previous="$arg"
done
echo "build" >> "$MOCK_TRACE"
''')
            env = os.environ.copy()
            env.pop("HABU_DEVELOPMENT_TEAM", None)
            env.update({
                "PATH": str(binaries) + os.pathsep + env["PATH"],
                "DEVICE_FIXTURE": str(fixture),
                "MOCK_TRACE": str(trace),
                "TMPDIR": str(base) + "/",
                "MOCK_XCODE_FAILURE": failure_log,
            })
            result = subprocess.run(
                ["bash", str(SCRIPT)], capture_output=True, text=True, env=env,
                timeout=30,
            )
            return result, trace.read_text(encoding="utf-8") if trace.exists() else ""

    def test_connected_iphone13pro_signs_installs_and_launches(self):
        device = {
            "identifier": "MOCK-LOCAL-DEVICE-IDENTIFIER",
            "hardwareProperties": {"productType": "iPhone14,2"},
            "connectionProperties": {
                "pairingState": "paired", "tunnelState": "connected",
                "transportType": "localNetwork",
            },
        }
        result, commands = self.run_mock([device])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OWNED_IPHONE_INSTALL_PASS", result.stdout)
        self.assertIn("OWNED_IPHONE_LAUNCHED", result.stdout)
        self.assertNotIn("MOCK-LOCAL-DEVICE-IDENTIFIER", result.stdout)
        self.assertNotIn("ABCDEFGHIJ", result.stdout)
        self.assertEqual(commands.splitlines(), ["build", "device-install", "device-launch"])

    def test_unpaired_or_wrong_model_prevents_install(self):
        wrong = {
            "identifier": "MOCK-OTHER-IPHONE",
            "hardwareProperties": {"productType": "iPhone14,3"},
            "connectionProperties": {
                "pairingState": "paired", "tunnelState": "connected",
            },
        }
        result, commands = self.run_mock([wrong])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("STOP:", result.stderr)
        self.assertNotIn("device-install", commands)

    def test_missing_signing_team_prevents_install(self):
        device = {
            "identifier": "MOCK-LOCAL-DEVICE-IDENTIFIER",
            "hardwareProperties": {"productType": "iPhone14,2"},
            "connectionProperties": {
                "pairingState": "paired", "tunnelState": "connected",
            },
        }
        result, commands = self.run_mock([device], certificate=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("署名Teamを1つに特定できません", result.stderr)
        self.assertNotIn("build", commands)
        self.assertNotIn("device-install", commands)


    def test_build_failure_is_classified_without_private_text(self):
        device = {
            "identifier": "MOCK-LOCAL-DEVICE-IDENTIFIER",
            "hardwareProperties": {"productType": "iPhone14,2"},
            "connectionProperties": {
                "pairingState": "paired", "tunnelState": "connected",
            },
        }
        result, commands = self.run_mock(
            [device],
            failure_log=(
                'error: No profiles for "org.example.habu" were found; '
                "developer@example.invalid SECRET-PRIVATE"
            ),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PROVISIONING_PROFILE_MISSING", result.stderr)
        for secret in ("org.example.habu", "developer@example.invalid", "SECRET-PRIVATE"):
            self.assertNotIn(secret, result.stderr + result.stdout)
        self.assertNotIn("device-install", commands)

    def test_non_signing_failure_does_not_claim_signing(self):
        device = {
            "identifier": "MOCK-LOCAL-DEVICE-IDENTIFIER",
            "hardwareProperties": {"productType": "iPhone14,2"},
            "connectionProperties": {
                "pairingState": "paired", "tunnelState": "connected",
            },
        }
        result, commands = self.run_mock(
            [device], failure_log="note: Signing settings checked\nerror: unrelated"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BUILD_FAILURE_UNCLASSIFIED", result.stderr)
        self.assertNotIn("SIGNING_FAILED", result.stderr)
        self.assertNotIn("device-install", commands)

    def test_account_vs_team_mismatch_diagnostics(self):
        device = {
            "identifier": "MOCK-LOCAL-DEVICE-IDENTIFIER",
            "hardwareProperties": {"productType": "iPhone14,2"},
            "connectionProperties": {
                "pairingState": "paired", "tunnelState": "connected",
            },
        }
        samples = {
            "error: There are no accounts registered with Xcode": "XCODE_NO_ACCOUNTS",
            "error: No Account for Team XXXXXXXXXX": "TEAM_ACCOUNT_MISMATCH",
        }
        for failure, code in samples.items():
            with self.subTest(code=code):
                result, commands = self.run_mock([device], failure_log=failure)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(code, result.stderr)
                self.assertNotIn("device-install", commands)
                self.assertNotIn("XXXXXXXXXX", result.stderr)


if __name__ == "__main__":
    unittest.main()
