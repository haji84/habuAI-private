import hashlib
import json
import copy
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from private_pdca_runner import run_private, PrivateRunError
from private_pdca_intake import intake
import private_pdca_intake as intake_module
import private_pdca_runner as runner_module


class RunnerTests(unittest.TestCase):
    def test_bounded_receipt_decoder_rejects_excessive_integer_and_nesting(self):
        for raw in (b'{"n":'+b'9'*5000+b'}', b'['*65+b'0'+b']'*65):
            with self.subTest(prefix=raw[:8]):
                self.rec.write_bytes(raw)
                with patch.object(runner_module.subprocess, 'run', side_effect=AssertionError('engine forbidden')):
                    with self.assertRaises(PrivateRunError):
                        run_private(self.code, self.workspace, self.store, self.rec, '2000-01-01')

    def test_remaining_child_wait_uses_the_same_whole_entry_clock(self):
        actual = Path.open
        def opening(path, *args, **kwargs):
            stream = actual(path, *args, **kwargs)
            if path == self.rec:
                time.sleep(.02)
            return stream
        marker = BaseException('SYNTHETIC_ENGINE_BOUNDARY_ONLY')
        waits = []
        def no_engine(*args, **kwargs):
            waits.append(kwargs['timeout'])
            raise marker
        with patch.object(Path, 'open', opening), patch.object(runner_module.subprocess, 'run', no_engine):
            with self.assertRaises(BaseException) as caught:
                run_private(self.code, self.workspace, self.store, self.rec, '2000-01-01', timeout_seconds=1)
        self.assertIs(caught.exception, marker)
        self.assertEqual(len(waits), 1)
        self.assertGreater(waits[0], 0)
        self.assertLess(waits[0], .99)

    def test_runner_budget_counts_receipt_source_copy_and_readback_before_engine(self):
        budgets, actual = [], runner_module._ReadBudget
        def budget(*args, **kwargs):
            item = actual(*args, **kwargs)
            budgets.append(item)
            return item
        marker = KeyboardInterrupt('SYNTHETIC_ENGINE_BOUNDARY_ONLY')
        with patch.object(runner_module, '_ReadBudget', budget), patch.object(runner_module.subprocess, 'run', side_effect=marker):
            with self.assertRaises(KeyboardInterrupt) as caught:
                run_private(self.code, self.workspace, self.store, self.rec, '2000-01-01')
        self.assertIs(caught.exception, marker)
        self.assertEqual(budgets[0].bytes_read, self.rec.stat().st_size+4*self.source.stat().st_size)

    def test_oversized_existing_inbox_is_rejected_without_engine(self):
        digest = self.manifest['sources'][0]['sha256']
        target = self.workspace/'incoming'/'private_pdca'/(digest+'.txt')
        target.parent.mkdir(parents=True)
        target.write_bytes(self.source.read_bytes()+b' ')
        with patch.object(runner_module.subprocess, 'run', side_effect=AssertionError('engine forbidden')):
            with self.assertRaises(PrivateRunError):
                run_private(self.code, self.workspace, self.store, self.rec, '2000-01-01')

    def test_invalid_whole_entry_timeout_rejected_before_any_receipt_open(self):
        for seconds in (True, False, 0, -1, float('inf'), float('nan'), 331, '1'):
            with self.subTest(timeout=seconds), patch.object(runner_module.subprocess, 'run', side_effect=AssertionError('engine forbidden')):
                with self.assertRaises(PrivateRunError):
                    run_private(self.code, self.workspace, self.store, self.rec, '2000-01-01', timeout_seconds=seconds)

    def test_receipt_consumer_rejects_oversize_before_open_or_engine(self):
        self.rec.write_bytes(b' '*65)
        actual = Path.open
        opens = []
        def opening(path, *args, **kwargs):
            if path == self.rec:
                opens.append(True)
            return actual(path, *args, **kwargs)
        with patch.object(runner_module, 'MAX_RECEIPT_BYTES', 64, create=True), patch.object(Path, 'open', opening):
            with patch.object(runner_module.subprocess, 'run', side_effect=AssertionError('engine must remain unopened')):
                with self.assertRaises(PrivateRunError):
                    run_private(self.code, self.workspace, self.store, self.rec, '2000-01-01')
        self.assertEqual(opens, [])

    def test_whole_runner_deadline_includes_receipt_preflight(self):
        actual = Path.open
        def opening(path, *args, **kwargs):
            stream = actual(path, *args, **kwargs)
            if path == self.rec:
                time.sleep(.015)
            return stream
        with patch.object(Path, 'open', opening), patch.object(runner_module.subprocess, 'run', side_effect=AssertionError('expired before engine')):
            with self.assertRaises(PrivateRunError):
                run_private(self.code, self.workspace, self.store, self.rec, '2000-01-01', timeout_seconds=.005)

    def replaced_temp_control(self, selected_parent, *, primary=None):
        native_link = os.link
        replacements = []
        marker = b"SYNTHETIC_UNOWNED_REPLACEMENT_DO_NOT_DELETE"
        def link_then_replace(source, target):
            source, target = Path(source), Path(target)
            self.assertTrue(source.is_relative_to(self.base))
            self.assertTrue(target.is_relative_to(self.base))
            native_link(source, target)
            if target.parent.name == selected_parent:
                source.unlink()
                source.write_bytes(marker)
                replacements.append(source)
                if primary is not None:
                    raise primary
        caught = None
        try:
            with patch.object(os, "link", link_then_replace):
                run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        except BaseException as exc:
            caught = exc
        self.assertEqual(len(replacements), 1)
        self.assertTrue(replacements[0].is_file(), "Cleanup deleted an unowned regular replacement")
        self.assertEqual(replacements[0].read_bytes(), marker)
        digest = self.manifest["sources"][0]["sha256"]
        self.assertEqual((self.workspace / "incoming" / "private_pdca" / (digest + ".txt")).read_bytes(), self.source.read_bytes())
        if primary is not None:
            self.assertIs(caught, primary)
            self.assertTrue(any("TEMP_CLEANUP_RESIDUAL" in x for x in caught.__notes__))
        else:
            self.assertIsInstance(caught, PrivateRunError)
            self.assertIn("TEMP_CLEANUP_RESIDUAL", str(caught))

    def test_inbox_cleanup_preserves_replaced_regular_temp(self):
        self.replaced_temp_control("private_pdca")

    def test_result_cleanup_preserves_replaced_regular_temp(self):
        self.replaced_temp_control("private_pdca_runs")

    def test_inbox_cleanup_preserves_primary_and_explicit_residual(self):
        self.replaced_temp_control("private_pdca", primary=RuntimeError("SYNTHETIC_PRIMARY"))

    def test_result_cleanup_preserves_primary_and_explicit_residual(self):
        self.replaced_temp_control("private_pdca_runs", primary=RuntimeError("SYNTHETIC_PRIMARY"))

    def test_owned_inbox_and_result_temps_are_removed_normally(self):
        result = run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        digest = self.manifest["sources"][0]["sha256"]
        self.assertEqual([p.name for p in (self.workspace / "incoming" / "private_pdca").iterdir()], [digest + ".txt"])
        self.assertEqual([p.name for p in (self.store / "private_pdca_runs").iterdir()], [result["run_receipt"] + ".json"])

    def assert_bad_receipt(self, manifest):
        self.rec.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")

    def test_receipt_id_must_bind_actual_source_rows(self):
        altered = copy.deepcopy(self.manifest)
        other = self.store / "same-bytes-new-source.txt"
        other.write_bytes(self.source.read_bytes())
        altered["sources"][0]["private_archive"] = str(other)
        self.assert_bad_receipt(altered)

    def test_receipt_schema_is_required(self):
        altered = copy.deepcopy(self.manifest)
        altered["schema"] = "unrecognized"
        self.assert_bad_receipt(altered)

    def test_extra_manifest_and_row_fields_are_rejected(self):
        for level in ("manifest", "row"):
            with self.subTest(level=level):
                altered = copy.deepcopy(self.manifest)
                target = altered if level == "manifest" else altered["sources"][0]
                target["unexpected"] = True
                # Independent legacy canonical-ID definition; not a product helper.
                altered["receipt_id"] = hashlib.sha256(json.dumps(
                    altered["sources"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                self.assert_bad_receipt(altered)

    def test_bool_and_zero_source_sizes_are_not_valid_receipt_rows(self):
        for data, bad_size in ((b"x", True), (b"", 0)):
            with self.subTest(size=bad_size):
                self.source.write_bytes(data)
                altered = copy.deepcopy(self.manifest)
                altered["sources"][0].update(sha256=hashlib.sha256(data).hexdigest(), size_bytes=bad_size)
                altered["receipt_id"] = hashlib.sha256(json.dumps(
                    altered["sources"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                self.assert_bad_receipt(altered)

    def test_non_dict_or_empty_or_duplicate_rows_raise_typed_rejection(self):
        for rows in ([], [None], self.manifest["sources"] * 2):
            with self.subTest(rows=rows):
                altered = copy.deepcopy(self.manifest)
                altered["sources"] = rows
                self.assert_bad_receipt(altered)

    def test_legacy_intake_id_and_bytes_remain_compatible(self):
        legacy_id = hashlib.sha256(json.dumps(self.manifest["sources"],
            ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        self.assertEqual(self.manifest["receipt_id"], legacy_id)
        receipt_before, source_before = self.rec.read_bytes(), self.source.read_bytes()
        result = run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        self.assertEqual(result["overall_status"], "BLOCKED")
        self.assertEqual(self.rec.read_bytes(), receipt_before)
        self.assertEqual(self.source.read_bytes(), source_before)

    def test_invalid_receipt_types_and_size_bounds_are_rejected(self):
        for field, value in (("size_bytes", "1"), ("size_bytes", 200*1024*1024+1),
                             ("private_archive", True), ("sha256", True), ("type", "other")):
            with self.subTest(field=field, value=value):
                altered = copy.deepcopy(self.manifest)
                altered["sources"][0][field] = value
                altered["receipt_id"] = hashlib.sha256(json.dumps(
                    altered["sources"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                self.assert_bad_receipt(altered)

    def test_two_real_intake_rows_roundtrip_without_rewriting_receipt(self):
        gpx = self.base / "synthetic.gpx"
        gpx.write_text('<gpx creator="SYNTHETIC_TEST_ONLY"/>', encoding="utf-8")
        result = intake(self.code, self.store, log_file=self.source, gpx_file=gpx)
        receipt = self.store / "receipts" / (result["receipt_id"] + ".json")
        before = receipt.read_bytes()
        run = run_private(self.code, self.workspace, self.store, receipt, "2000-01-01")
        self.assertEqual(run["overall_status"], "BLOCKED")
        self.assertEqual(receipt.read_bytes(), before)

    def result_alias_rejected(self, *, junction=False):
        outside = self.code / "forbidden-test-output"
        outside.mkdir()
        link = self.store / "private_pdca_runs"
        if junction:
            if os.name != "nt":
                self.skipTest("Actual Windows junction control requires Windows")
            proc = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside)],
                                  capture_output=True, check=False)
            if proc.returncode:
                self.skipTest("Junction unavailable without elevation: " + str(proc.returncode))
        else:
            try:
                link.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest("Actual symlink unavailable without elevation: " + str(exc))
        def remove_alias():
            try:
                os.rmdir(link) if junction else link.unlink()
            except FileNotFoundError:
                pass
        self.addCleanup(remove_alias)
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.workspace / "incoming").exists())

    def test_result_parent_symlink_cannot_escape_private_store(self):
        self.result_alias_rejected()

    def test_result_parent_junction_cannot_escape_private_store(self):
        self.result_alias_rejected(junction=True)

    def test_existing_result_leaf_symlink_is_not_reused(self):
        result = run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        dest = self.store / "private_pdca_runs" / (result["run_receipt"] + ".json")
        outside = self.code / "synthetic-run-receipt.json"
        dest.rename(outside)
        before = outside.read_bytes()
        try:
            dest.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("Actual symlink unavailable without elevation: " + str(exc))
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        self.assertEqual(outside.read_bytes(), before)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.code, self.store, self.workspace = (base / v for v in ("code", "store", "work"))
        for p in (self.code, self.store, self.workspace):
            p.mkdir(mode=0o700)
        (self.code / "scripts").mkdir()
        (self.code / "scripts" / "run_pdca.py").write_text(
            'import json\nprint(json.dumps({"overall_status":"BLOCKED"}))\nraise SystemExit(2)\n')
        # Genuine intake receipt over explicit synthetic bytes, never private source.
        original = base / "synthetic-log.txt"
        original.write_text("2000/01/01 19:55\n捕獲\nハブ捕獲~90幼体\n", encoding="utf-8")
        received = intake(self.code, self.store, log_file=original)
        self.rec = self.store / "receipts" / (received["receipt_id"] + ".json")
        self.manifest = json.loads(self.rec.read_text(encoding="utf-8"))
        self.source = Path(self.manifest["sources"][0]["private_archive"])
        self.base = base

    def test_repeated_run_same_sources_no_double_count(self):
        x = run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        y = run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        self.assertEqual(x, y)
        self.assertEqual(x["overall_status"], "BLOCKED")
        self.assertEqual(len(list((self.store/"private_pdca_runs").glob("*.json"))), 1)

    def test_modified_original_rejected(self):
        self.source.write_text("tampered")
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")

    def test_private_path_cannot_be_public_repo(self):
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.code, self.store, self.rec, "2000-01-01")

    def test_bad_night_rejected(self):
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.workspace, self.store, self.rec, "2026-10-26;rm")

    def test_symlink_to_external_raw_rejected(self):
        outside = self.workspace / "outside.txt"
        outside.write_bytes(self.source.read_bytes())
        self.source.unlink()
        try:
            self.source.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("Actual symlink unavailable without elevation: " + str(exc))
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")

    def test_engine_success_does_not_grant_scientific_certification(self):
        (self.code / "scripts" / "run_pdca.py").write_text(
            'import json\nprint(json.dumps({"overall_status":"PASS"}))\n')
        result = run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        self.assertEqual(result["model_validation"], "NOT_CERTIFIED")
        self.assertEqual(result["p0"], "NOT_CERTIFIED")


if __name__ == "__main__":
    unittest.main()
