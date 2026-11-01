"""Regression test for Mac Simulator launch when its GUI app is not registered.

This mocked test runs on Linux and never uses location data, Apple credentials,
a real iPhone, or an installed Xcode/Simulator.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "mobile/ios/run-mac-simulator.sh"


def stub(directory: Path, name: str, body: str) -> None:
    p = directory / name
    p.write_text("#!/usr/bin/env bash\n" + body + "\n", encoding="utf-8")
    p.chmod(0o755)


class MacSimulatorLauncherTests(unittest.TestCase):
    def test_shell_syntax(self):
        completed = subprocess.run(
            ["bash", "-n", str(SCRIPT)], text=True, capture_output=True
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_gui_missing_does_not_block_install_or_launch(self):
        with tempfile.TemporaryDirectory() as root:
            tmp = Path(root)
            mock_bin = tmp / "bin"
            mock_bin.mkdir()
            log = tmp / "mock.log"
            app = (tmp / "Library/Developer/Xcode/DerivedData"
                   / "HabuFieldRecorder-LocalSmoke/Build/Products"
                   / "Debug-iphonesimulator/HabuFieldRecorder.app")
            app.mkdir(parents=True)
            stub(mock_bin, "uname", '[[ "$1" == "-s" ]] && echo Darwin || /usr/bin/uname "$@"')
            stub(mock_bin, "xcodebuild", '[[ "$1" == "-version" ]] && echo "Xcode mocked"; exit 0')
            stub(mock_bin, "xcodegen", "exit 0")
            stub(mock_bin, "xcode-select",
                 '[[ "$1" == "-p" ]] && echo "/nonexistent/Xcode/Contents/Developer"; exit 0')
            stub(mock_bin, "open", "exit 1")
            stub(mock_bin, "xcrun", r'''
if [[ "$1" == "simctl" && "$2" == "list" ]]; then
    printf '%s\n' '{"devices":{"com.apple.CoreSimulator.SimRuntime.iOS-27-0":[{"name":"iPhone 17","udid":"MOCK-DEVICE","state":"Booted","isAvailable":true}]}}'
else
    printf '%s\n' "$*" >> "$MOCK_LOG"
fi
exit 0
''')
            env = os.environ.copy()
            env.update(
                HOME=str(tmp), MOCK_LOG=str(log),
                PATH=str(mock_bin) + os.pathsep + env["PATH"],
            )
            completed = subprocess.run(
                ["bash", str(SCRIPT)], text=True, capture_output=True, env=env
            )
            output = completed.stdout + completed.stderr
            self.assertEqual(completed.returncode, 0, output)
            self.assertIn("SIMULATOR_APP_LAUNCHED", completed.stdout)
            self.assertIn("WARNING: Simulator画面アプリを発見できません", output)
            self.assertNotIn("unbound variable", output)
            actions = log.read_text(encoding="utf-8")
            self.assertIn("simctl install MOCK-DEVICE", actions)
            self.assertIn("simctl launch MOCK-DEVICE org.habuai.fieldrecorder", actions)
            self.assertLess(actions.index("simctl install"), actions.index("simctl launch"))


if __name__ == "__main__":
    unittest.main()
