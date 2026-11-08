"""Static path rejection must happen before the source-freeze walker descends."""
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import codex_cycle_contract as contract


class CyclePrewalkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="g0-prewalk-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.root = self.work / "workspace"
        for folder in ("src", "scripts", "schemas"):
            (self.root / folder).mkdir(parents=True)
        self.outside = self.work / "outside"
        self.outside.mkdir()
        self.sentinel = self.outside / "not-a-source.py"
        self.sentinel.write_bytes(b"OUTSIDE_SOURCE_MUST_NOT_BE_READ\n")

    @contextmanager
    def alias(self, link, target):
        if sys.platform == "win32":
            environment = dict(os.environ, G0_TEST_LINK=str(link), G0_TEST_TARGET=str(target))
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                "New-Item -ItemType Junction -Path $env:G0_TEST_LINK -Target $env:G0_TEST_TARGET -ErrorAction Stop | Out-Null"],
                env=environment, check=True, capture_output=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.assertTrue(link.is_junction())
        else:
            link.symlink_to(target, target_is_directory=True)
        try:
            yield link
        finally:
            self.assertTrue(link.absolute().is_relative_to(self.work.absolute()))
            self.assertTrue(link.resolve().is_relative_to(self.work.resolve()))
            if sys.platform == "win32":
                os.rmdir(link)
            else:
                link.unlink()
            self.assertEqual(self.sentinel.read_bytes(), b"OUTSIDE_SOURCE_MUST_NOT_BE_READ\n")

    def assert_no_external_walk(self, root):
        scans = []
        original = os.scandir
        def observed(path):
            if Path(path).resolve().is_relative_to(self.outside.resolve()):
                scans.append(str(path))
            return original(path)
        error = None
        with patch("os.scandir", side_effect=observed):
            try:
                contract.code_paths(root)
            except ValueError as exc:
                error = exc
        self.assertEqual(scans, [], "Source freeze must reject before enumerating the external target")
        self.assertIsNotNone(error, "Unsafe source tree must be rejected")

    def test_nested_source_alias_is_rejected_before_descent(self):
        with self.alias(self.root / "src/alias", self.outside):
            self.assert_no_external_walk(self.root)

    def test_schema_alias_is_rejected_before_descent(self):
        with self.alias(self.root / "schemas/alias", self.outside):
            self.assert_no_external_walk(self.root)

    def test_root_ancestor_alias_is_rejected_before_descent_or_reference_read(self):
        (self.outside / "workspace").mkdir()
        for folder in ("src", "scripts", "schemas"):
            (self.outside / "workspace" / folder).mkdir()
        with self.alias(self.work / "alias", self.outside) as alias:
            self.assert_no_external_walk(alias / "workspace")
            with self.assertRaises(ValueError):
                contract._local_path(alias / "workspace", "src")

    def test_regular_source_closure_and_limits_are_preserved(self):
        for relative in ("src/a.py", "src/nested/b.py", "scripts/c.py", "schemas/d.json", "src/ignored.txt"):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"{}\n")
        self.assertEqual(contract.code_paths(self.root), sorted([
            "src/a.py", "src/nested/b.py", "scripts/c.py", "schemas/d.json",
            "requirements-analysis.txt", "requirements-osm.txt"]))


if __name__ == "__main__":
    unittest.main()
