"""Exercise CI target selection with command stubs; never starts a Simulator."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "mobile/ios/ci-synthetic-gps-smoke.sh"


class CISimulatorTargetTests(unittest.TestCase):
    def run_target(self, requested):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            binary = root / "bin"
            binary.mkdir()
            trace = root / "build-args"
            fixture = root / "devices.json"
            fixture.write_text(json.dumps({"devices": {"runtime.iOS.test": [
                {"name": "Private regression simulator", "udid": "SIM-OWNED-TEST", "state": "Booted"},
                {"name": "iPhone unrelated", "udid": "SIM-UNRELATED", "state": "Shutdown"},
            ]}}))
            scripts = {
                "uname": "echo Darwin",
                "xcodegen": "exit 0",
                "xcodebuild": 'printf "%s\\n" "$@" > "$MOCK_BUILD_ARGS"; exit 65',
                "xcrun": '''if [[ "$1" == simctl && "$2" == list ]]; then cat "$MOCK_DEVICES";
elif [[ "$1" == xcresulttool ]]; then echo '{}';
fi
exit 0''',
            }
            for name, body in scripts.items():
                p = binary / name
                p.write_text("#!/usr/bin/env bash\n" + body + "\n")
                p.chmod(0o755)
            env = os.environ.copy()
            env.update(PATH=str(binary) + os.pathsep + env["PATH"], TMPDIR=str(root) + "/",
                       MOCK_BUILD_ARGS=str(trace), MOCK_DEVICES=str(fixture))
            if requested is None:
                env.pop("HABU_SIMULATOR_DEVICE_ID", None)
            else:
                env["HABU_SIMULATOR_DEVICE_ID"] = requested
            result = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True,
                                    text=True, timeout=25)
            return result, trace.read_text() if trace.exists() else ""

    def test_requested_custom_named_simulator_is_the_only_build_target(self):
        result, args = self.run_target("SIM-OWNED-TEST")
        self.assertIn("platform=iOS Simulator,id=SIM-OWNED-TEST", args)
        self.assertNotIn("SIM-UNRELATED", args)
        self.assertNotEqual(result.returncode, 0, "Injected build failure must remain a failure")

    def test_missing_requested_simulator_never_falls_back_to_another_device(self):
        result, args = self.run_target("SIM-NOT-PRESENT")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(args, "")

    def test_empty_requested_simulator_never_falls_back_to_another_device(self):
        result, args = self.run_target("")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(args, "")

    def test_unset_override_keeps_default_iphone_selection(self):
        result, args = self.run_target(None)
        self.assertIn("platform=iOS Simulator,id=SIM-UNRELATED", args)
        self.assertNotIn("SIM-OWNED-TEST", args)
        self.assertNotEqual(result.returncode, 0, "Injected build failure must remain a failure")
