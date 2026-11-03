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


    def test_xcode_27_device_hub_opens_and_selects_simulator(self):
        """Xcode 27 has DeviceHub.app, not the removed standalone Simulator.app."""
        with tempfile.TemporaryDirectory() as root:
            tmp = Path(root)
            mock_bin = tmp / "bin"
            mock_bin.mkdir()
            developer_dir = tmp / "Xcode.app/Contents/Developer"
            developer_dir.mkdir(parents=True)
            hub = tmp / "Xcode.app/Contents/Applications/DeviceHub.app"
            hub.mkdir(parents=True)
            app = (tmp / "Library/Developer/Xcode/DerivedData"
                   / "HabuFieldRecorder-LocalSmoke/Build/Products"
                   / "Debug-iphonesimulator/HabuFieldRecorder.app")
            app.mkdir(parents=True)
            open_log = tmp / "open.log"
            simctl_log = tmp / "simctl.log"

            stub(mock_bin, "uname", '[[ "$1" == "-s" ]] && echo Darwin || /usr/bin/uname "$@"')
            stub(mock_bin, "xcodebuild", '[[ "$1" == "-version" ]] && echo "Xcode mocked"; exit 0')
            stub(mock_bin, "xcodegen", "exit 0")
            stub(mock_bin, "xcode-select", f'echo "{developer_dir}"')
            stub(mock_bin, "open", r'printf "%s\n" "$*" >> "$OPEN_LOG"; exit 0')
            stub(mock_bin, "xcrun", r'''
if [[ "$1" == "simctl" && "$2" == "list" ]]; then
    printf '%s\n' '{"devices":{"com.apple.CoreSimulator.SimRuntime.iOS-27-0":[{"name":"iPhone 17","udid":"MOCK-DEVICE","state":"Booted","isAvailable":true}]}}'
else
    printf '%s\n' "$*" >> "$SIMCTL_LOG"
fi
exit 0
''')
            env = os.environ.copy()
            env.update(
                HOME=str(tmp), OPEN_LOG=str(open_log), SIMCTL_LOG=str(simctl_log),
                PATH=str(mock_bin) + os.pathsep + env["PATH"],
            )
            completed = subprocess.run(
                ["bash", str(SCRIPT)], text=True, capture_output=True, env=env
            )
            output = completed.stdout + completed.stderr
            self.assertEqual(completed.returncode, 0, output)
            self.assertIn("SIMULATOR_APP_LAUNCHED", completed.stdout)
            self.assertIn("DEVICE_HUB_OPENED", completed.stdout)
            self.assertIn("DEVICE_HUB_SELECT_REQUESTED", completed.stdout)
            commands = open_log.read_text(encoding="utf-8")
            self.assertIn(str(hub), commands)
            self.assertIn("devices://manage/select?id=MOCK-DEVICE", commands)
            self.assertNotIn("Simulator.app", commands)
            self.assertIn(
                "simctl launch MOCK-DEVICE org.habuai.fieldrecorder",
                simctl_log.read_text(encoding="utf-8"),
            )



if __name__ == "__main__":
    unittest.main()
