"""Native filesystem boundary tests; importing these does not require fcntl."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import master_inventory as inventory


class MasterInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="master-inventory-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.root = self.work / "workspace"
        self.root.mkdir()
        self.external = self.work / "external"
        self.external.mkdir()
        self.sentinel = self.external / "sentinel.txt"
        self.sentinel.write_bytes(b"external sentinel remains unchanged")

    def write(self, relative, raw=b"source bytes"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return path

    @contextmanager
    def junction(self, link, target=None):
        target = target or self.external
        link.parent.mkdir(parents=True, exist_ok=True)
        environment = dict(os.environ, MASTER_TEST_LINK=str(link), MASTER_TEST_TARGET=str(target))
        subprocess.run([
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "New-Item -ItemType Junction -Path $env:MASTER_TEST_LINK "
            "-Target $env:MASTER_TEST_TARGET -ErrorAction Stop | Out-Null",
        ], env=environment, check=True, capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            self.assertTrue(link.is_junction())
            self.assertFalse(link.is_symlink())
            yield link
        finally:
            self.assertTrue(link.absolute().is_relative_to(self.work))
            self.assertTrue(link.resolve().is_relative_to(self.work))
            os.rmdir(link)  # Remove the junction only, before recursive temp cleanup.
            self.assertFalse(link.exists())
            self.assertEqual(self.sentinel.read_bytes(), b"external sentinel remains unchanged")

    def assert_rejected_without_external_reads(self, operation, *args, target=None):
        target = target or self.external
        reads, scans = [], []
        actual_hash, actual_scan = inventory.file_hash, os.scandir

        def tracked_hash(path):
            if Path(path).resolve().is_relative_to(target):
                reads.append(str(path))
            return actual_hash(path)

        def tracked_scan(path):
            if Path(path).resolve().is_relative_to(target):
                scans.append(str(path))
            return actual_scan(path)

        error = None
        with patch.object(inventory, "file_hash", side_effect=tracked_hash), patch.object(inventory.os, "scandir", side_effect=tracked_scan):
            try:
                operation(*args)
            except ValueError as exc:
                error = exc
        self.assertEqual(scans, [], "external directory must not be enumerated")
        self.assertEqual(reads, [], "external file bytes must not be hashed")
        self.assertIsNotNone(error, "unsafe path must fail closed")

    def test_inventory_preserves_source_selection_and_byte_identity(self):
        accepted = ("data/raw/source.txt", "docs/source.md", "requirements-analysis.txt",
                    "AGENTS.md", "reports/legacy_chronological_walkforward.json")
        for relative in accepted:
            self.write(relative, b"immutable source\r\n")
        for relative in ("src/__pycache__/cached.pyc", "data/ignored.pyc", "unrelated/not-input.txt"):
            self.write(relative)
        actual = inventory.inventory(self.root)
        expected = {relative: {"sha256": hashlib.sha256(b"immutable source\r\n").hexdigest(), "size_bytes": 18}
                    for relative in accepted}
        self.assertEqual(actual, expected)

    def test_generated_artifacts_and_replay_reuse_keep_existing_semantics(self):
        self.write("data/raw/source.txt")
        inputs = inventory.inventory(self.root)
        self.write("predictions/replay/candidate.json", b"candidate")
        self.write("reports/generated.json", b"report")
        self.assertTrue(inventory.snapshot_matches(self.root, inputs))
        self.assertEqual(inventory.generated_artifacts(self.root, inputs), {
            "snapshot/predictions/replay/candidate.json": hashlib.sha256(b"candidate").hexdigest(),
            "snapshot/reports/generated.json": hashlib.sha256(b"report").hexdigest(),
        })

    def test_snapshot_reuse_rejects_changed_or_new_consumed_inputs(self):
        source = self.write("data/raw/source.txt")
        inputs = inventory.inventory(self.root)
        source.write_bytes(b"changed")
        self.assertFalse(inventory.snapshot_matches(self.root, inputs))
        source.write_bytes(b"source bytes")
        self.write("data/new.txt")
        self.assertFalse(inventory.snapshot_matches(self.root, inputs))

    def test_copy_preserves_exact_bytes_and_source(self):
        source = self.write("data/raw/source.txt", b"\x00\xffsource\r\n")
        inputs = inventory.inventory(self.root)
        snapshot = self.work / "snapshot"
        snapshot.mkdir()
        inventory.copy_inputs(self.root, snapshot, inputs)
        self.assertEqual((snapshot / "data/raw/source.txt").read_bytes(), b"\x00\xffsource\r\n")
        self.assertEqual(source.read_bytes(), b"\x00\xffsource\r\n")
        self.assertTrue(inventory.snapshot_matches(snapshot, inputs))

    def test_copy_rejects_source_hash_change(self):
        source = self.write("data/raw/source.txt")
        inputs = inventory.inventory(self.root)
        source.write_bytes(b"changed")
        snapshot = self.work / "snapshot"
        snapshot.mkdir()
        with self.assertRaisesRegex(ValueError, "INPUT_CHANGED"):
            inventory.copy_inputs(self.root, snapshot, inputs)

    def test_paths_reject_traversal_and_cross_platform_absolute_names(self):
        for relative in ("../external/sentinel.txt", "..\\external\\sentinel.txt", str(self.external), "C:\\outside\\source.txt"):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                inventory.local_path(self.root, relative)

    def test_iterative_walk_preserves_deep_and_wide_inventory(self):
        for number in range(64):
            self.write(f"data/wide/source-{number}.txt")
        self.write("data/" + "d/" * 40 + "source.txt")
        self.assertEqual(len(inventory.inventory(self.root)), 65)

    def test_missing_snapshot_has_no_generated_artifacts(self):
        self.assertEqual(inventory.generated_artifacts(self.work / "missing", {}), {})

    @unittest.skipUnless(sys.platform == "win32", "Windows junction regression")
    def test_inventory_refuses_source_junction_before_enumerating_or_hashing(self):
        with self.junction(self.root / "data"):
            self.assert_rejected_without_external_reads(inventory.inventory, self.root)

    @unittest.skipUnless(sys.platform == "win32", "Windows junction regression")
    def test_inventory_refuses_nested_junction_before_enumerating_or_hashing(self):
        with self.junction(self.root / "data/raw/escape"):
            self.assert_rejected_without_external_reads(inventory.inventory, self.root)

    @unittest.skipUnless(sys.platform == "win32", "Windows junction regression")
    def test_generated_artifacts_refuse_junction_before_enumerating_or_hashing(self):
        with self.junction(self.root / "reports/escape"):
            self.assert_rejected_without_external_reads(inventory.generated_artifacts, self.root, {})

    @unittest.skipUnless(sys.platform == "win32", "Windows junction regression")
    def test_root_and_root_ancestor_junctions_are_rejected(self):
        (self.external / "data").mkdir()
        (self.external / "data/source.txt").write_bytes(b"external input")
        with self.junction(self.work / "alias") as alias:
            self.assert_rejected_without_external_reads(inventory.inventory, alias)
            self.assert_rejected_without_external_reads(inventory.inventory, alias / "nested")
            self.assert_rejected_without_external_reads(inventory.runtime_code_hash, alias)

    @unittest.skipUnless(sys.platform == "win32", "Windows junction regression")
    def test_contained_junction_is_also_rejected_before_enumeration(self):
        inside = self.root / "inside"
        inside.mkdir()
        (inside / "source.txt").write_bytes(b"contained target")
        with self.junction(self.root / "data", inside):
            self.assert_rejected_without_external_reads(inventory.inventory, self.root, target=inside)

    @unittest.skipUnless(sys.platform == "win32", "Windows junction regression")
    def test_copy_refuses_junction_source_before_copy(self):
        snapshot = self.work / "snapshot"
        snapshot.mkdir()
        inputs = {"data/sentinel.txt": {"sha256": hashlib.sha256(self.sentinel.read_bytes()).hexdigest()}}
        with self.junction(self.root / "data"), patch.object(inventory.shutil, "copyfile", wraps=inventory.shutil.copyfile) as copied:
            with self.assertRaises(ValueError):
                inventory.copy_inputs(self.root, snapshot, inputs)
            copied.assert_not_called()
        self.assertFalse((snapshot / "data/sentinel.txt").exists())

    @unittest.skipUnless(sys.platform == "win32", "Windows junction regression")
    def test_copy_refuses_junction_destination_before_copy(self):
        self.write("data/source.txt")
        inputs = inventory.inventory(self.root)
        snapshot = self.work / "snapshot"
        snapshot.mkdir()
        with self.junction(snapshot / "data"), patch.object(inventory.shutil, "copyfile", wraps=inventory.shutil.copyfile) as copied:
            with self.assertRaises(ValueError):
                inventory.copy_inputs(self.root, snapshot, inputs)
            copied.assert_not_called()
        self.assertFalse((self.external / "source.txt").exists())

    @unittest.skipUnless(sys.platform == "win32", "Windows junction regression")
    def test_snapshot_reuse_refuses_junction_before_external_reads(self):
        with self.junction(self.root / "data"):
            self.assert_rejected_without_external_reads(inventory.snapshot_matches, self.root, {})

    @unittest.skipIf(sys.platform == "win32", "POSIX symlink regression; Windows junction tests above")
    def test_source_symlink_is_rejected_without_external_reads(self):
        (self.root / "data").symlink_to(self.external, target_is_directory=True)
        self.assert_rejected_without_external_reads(inventory.inventory, self.root)

    @unittest.skipIf(sys.platform == "win32", "POSIX symlink regression; Windows junction tests above")
    def test_generated_symlink_is_rejected_without_external_reads(self):
        (self.root / "generated").symlink_to(self.external, target_is_directory=True)
        self.assert_rejected_without_external_reads(inventory.generated_artifacts, self.root, {})

    @unittest.skipIf(sys.platform == "win32", "POSIX symlink regression; Windows junction tests above")
    def test_snapshot_copy_rejects_symlink_destination(self):
        self.write("data/source.txt")
        snapshot = self.work / "snapshot"
        snapshot.mkdir()
        (snapshot / "data").symlink_to(self.external, target_is_directory=True)
        with self.assertRaises(ValueError):
            inventory.copy_inputs(self.root, snapshot, inventory.inventory(self.root))

    def test_foreign_execution_root_nested_code_changes_runtime_identity(self):
        execution = self.work / "execution"
        nested = execution / "src/models/nested.py"
        nested.parent.mkdir(parents=True)
        nested.write_bytes(b"MODEL = 1\n")
        (execution / "src/main.py").write_bytes(b"TOP = 1\n")
        (execution / "scripts").mkdir()
        helper = execution / "scripts/nested/helper.py"
        helper.parent.mkdir()
        helper.write_bytes(b"HELPER = 1\n")
        self.write("data/source.txt")
        inputs = inventory.inventory(self.root)
        initial = inventory.runtime_code_hash(execution)
        nested.write_bytes(b"MODEL = 2\n")
        changed_model = inventory.runtime_code_hash(execution)
        self.assertNotEqual(initial, changed_model)
        helper.write_bytes(b"HELPER = 2\n")
        self.assertNotEqual(changed_model, inventory.runtime_code_hash(execution))
        self.assertEqual(inventory.inventory(self.root), inputs)

    @unittest.skipUnless(sys.platform == "win32", "Windows junction regression")
    def test_runtime_code_refuses_nested_junction_before_external_reads(self):
        with self.junction(self.root / "src/models"):
            self.assert_rejected_without_external_reads(inventory.runtime_code_hash, self.root)

    @unittest.skipIf(sys.platform == "win32", "Linux orchestrator integration requires fcntl")
    def test_foreign_and_derived_root_nested_code_changes_inspect_and_cached_run_identity(self):
        import master_orchestrator as master

        execution = self.work / "execution"
        nested = execution / "src/models/nested.py"
        nested.parent.mkdir(parents=True)
        (execution / "scripts").mkdir()
        for number, data_root in enumerate((self.root, self.work / "derived-evaluation-root")):
            data_root.mkdir(exist_ok=True)
            nested.write_bytes(f"MODEL = {number}\n".encode())
            with patch.object(master, "__file__", str(execution / "src/master_orchestrator.py")):
                first_identity = master.inspect_run_identity(data_root, "2026-09-30", execution_root=execution)
                first = master.run_master(data_root, "2026-09-30", 0)
                cached = master.run_master(data_root, "2026-09-30", 0)
                self.assertEqual(first["run_id"], cached["run_id"])
                nested.write_bytes(f"MODEL = {number + 10}\n".encode())
                second_identity = master.inspect_run_identity(data_root, "2026-09-30", execution_root=execution)
                second = master.run_master(data_root, "2026-09-30", 0)
            self.assertEqual(first_identity["inputs"], second_identity["inputs"])
            self.assertNotEqual(first_identity["run_id"], second_identity["run_id"])
            self.assertNotEqual(first["run_id"], second["run_id"])
        alias = self.work / "execution-link"
        alias.symlink_to(execution, target_is_directory=True)
        with patch.object(master, "__file__", str(alias / "src/master_orchestrator.py")):
            with self.assertRaises(ValueError):
                master._code_hash()


if __name__ == "__main__":
    unittest.main()
