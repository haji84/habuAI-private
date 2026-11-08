import importlib.util
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "private_pdca_intake", Path(__file__).resolve().parents[1] / "scripts" / "private_pdca_intake.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PrivateIntakeTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='posix','Actual POSIX post-dup construction failure; mandatory on Ubuntu')
    def test_creation_dup_fstat_failure_closes_once_and_preserves_first(self):
        class FalseyError(OSError):
            def __bool__(self):return False
        for kind in (FalseyError,KeyboardInterrupt):
            for close_fault in (False,True):
                with self.subTest(first=kind.__name__,close_fault=close_fault),tempfile.TemporaryDirectory() as tmp:
                    first=kind('SYNTHETIC_POST_DUP_FSTAT_FIRST')
                    secondary=FalseyError('SYNTHETIC_CLOSE_AFTER_REAL_RELEASE')
                    fstat,dup,close=os.fstat,os.dup,os.close
                    owned=[];closes=[];failed_owner=None
                    def duplicated(fd):
                        value=dup(fd);owned.append(value);return value
                    def inspected(fd):
                        if fd in owned:raise first
                        return fstat(fd)
                    def released(fd):
                        close(fd)
                        if fd in owned:
                            closes.append(fd)
                            if close_fault:raise secondary
                    with mod.NamedTemporaryFile(dir=tmp,delete=False) as stream:
                        try:
                            with patch.object(os,'dup',duplicated),patch.object(os,'fstat',inspected),patch.object(os,'close',released):
                                try:mod._temp_owner(stream)
                                except BaseException as caught:
                                    self.assertIs(caught,first)
                                    # Retain the real constructor traceback: __del__ cannot be cleanup proof.
                                    frame=caught.__traceback__
                                    while frame is not None:
                                        candidate=frame.tb_frame.f_locals.get('self')
                                        if type(candidate) is mod._TempOwner:failed_owner=candidate
                                        frame=frame.tb_next
                                else:self.fail('post-dup fstat failure not propagated')
                            self.assertEqual(closes,owned)
                            self.assertEqual(len(owned),1)
                            self.assertIsNotNone(failed_owner)
                            self.assertTrue(failed_owner._closed)
                            self.assertIsNone(failed_owner._fd)
                            with self.assertRaises(OSError):fstat(owned[0])
                            failed_owner.close()
                            self.assertEqual(closes,owned)
                            self.assertEqual(any('CONSTRUCTION_CLOSE_RESIDUAL' in n for n in getattr(first,'__notes__',[])),close_fault)
                        finally:
                            # Test-owned teardown only, after the behavioral assertions above.
                            if failed_owner is not None:failed_owner.close()

    def test_closed_stat_pair_is_not_a_temp_generation_owner(self):
        self.private.mkdir()
        path=self.private/'SYNTHETIC_OWNER_PROOF_REQUIRED'
        path.write_bytes(b'SYNTHETIC_ONLY')
        with path.open('rb') as stream:
            info=os.fstat(stream.fileno())
            pair=(info.st_dev,info.st_ino)
        with self.assertRaisesRegex(mod.IntakeError,'TEMP_CLEANUP_RESIDUAL'):
            mod.cleanup_owned_temp(self.private,path,pair,None)
        self.assertEqual(path.read_bytes(),b'SYNTHETIC_ONLY')

    @unittest.skipUnless(os.name=='posix','Real POSIX unlinked-open generation ownership; mandatory on Ubuntu')
    def test_capture_creation_descriptor_pins_generation_until_cleanup(self):
        actual_owner=mod._temp_owner;observed=[];marker=RuntimeError('SYNTHETIC_PARSE_FIRST')
        def owner(stream):
            result=actual_owner(stream);observed.append((Path(stream.name),result,result._fd))
            return result
        def replacing(*args,**kwargs):
            staged,token,fd=observed[0]
            held=os.fstat(fd)
            self.assertEqual((held.st_dev,held.st_ino),token.identity)
            staged.unlink()
            self.assertEqual(os.fstat(fd).st_nlink,0)
            staged.write_bytes(b'SYNTHETIC_UNOWNED_CAPTURE')
            replacement=staged.stat()
            self.assertNotEqual((replacement.st_dev,replacement.st_ino),token.identity)
            raise marker
        with patch.object(mod,'_temp_owner',owner),patch.object(mod,'summarize_log',replacing):
            with self.assertRaises(RuntimeError) as caught:mod.intake(self.repo,self.private,log_file=self.log)
        self.assertIs(caught.exception,marker)
        self.assertEqual(observed[0][0].read_bytes(),b'SYNTHETIC_UNOWNED_CAPTURE')
        self.assertTrue(any('TEMP_CLEANUP_RESIDUAL' in n for n in marker.__notes__))
        for path,token,fd in observed:
            with self.assertRaises(OSError):os.fstat(fd)

    @unittest.skipUnless(os.name=='posix','Real creation dup/close FIRST controls; mandatory on Ubuntu')
    def test_owned_descriptor_close_fault_preserves_first_and_releases_fd(self):
        class FalseyError(OSError):
            def __bool__(self):return False
        for with_primary in (False,True):
            with self.subTest(primary=with_primary),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                with mod.NamedTemporaryFile(dir=root,delete=False) as stream:
                    path=Path(stream.name);token=mod._temp_owner(stream);fd=token._fd
                primary=FalseyError('SYNTHETIC_PRIMARY');close_error=FalseyError('SYNTHETIC_REAL_CLOSE_THEN_ERROR')
                native=os.close
                def close(value):
                    native(value)
                    if value==fd:raise close_error
                with patch.object(os,'close',close):
                    if with_primary:
                        with self.assertRaises(FalseyError) as caught:
                            try:raise primary
                            finally:mod.cleanup_owned_temp(root,path,token,sys.exception())
                        self.assertIs(caught.exception,primary)
                    else:
                        with self.assertRaises(FalseyError) as caught:mod.cleanup_owned_temp(root,path,token,None)
                        self.assertIs(caught.exception,close_error)
                with self.assertRaises(OSError):os.fstat(fd)
                self.assertFalse(path.exists())
                self.assertTrue(any('TEMP_CLEANUP_RESIDUAL' in n for n in caught.exception.__notes__))

    def test_unbound_xml_namespace_prefix_is_still_rejected(self):
        self.gpx.write_bytes(b'<gpx><missing:trkpt/></gpx>')
        with self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.private, gpx_file=self.gpx)
        self.assertFalse((self.private/'raw'/'gpx').exists())

    def test_namespaced_xml_point_limit_is_not_bypassed(self):
        self.gpx.write_bytes(b'<gpx xmlns="urn:SYNTHETIC"><trkpt/><trkpt/></gpx>')
        with patch.object(mod, 'MAX_XML_POINTS', 1), self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.private, gpx_file=self.gpx)

    def test_failed_plus_one_read_is_charged_before_growth_rejection(self):
        actual_open, actual_budget = Path.open, mod._ReadBudget
        budgets, requests = [], []
        size = self.gpx.stat().st_size
        class GrowingStream:
            def __init__(wrapped, stream):
                wrapped.stream = stream
            def __enter__(wrapped):
                return wrapped
            def __exit__(wrapped, *args):
                return wrapped.stream.__exit__(*args)
            def fileno(wrapped):
                return wrapped.stream.fileno()
            def read(wrapped, amount):
                requests.append(amount)
                if len(requests) == 1:
                    with actual_open(self.gpx, 'ab') as grow:
                        grow.write(b' ')
                return wrapped.stream.read(amount)
        def opening(path, *args, **kwargs):
            stream = actual_open(path, *args, **kwargs)
            return GrowingStream(stream) if path == self.gpx and args == ('rb',) else stream
        def budget(*args, **kwargs):
            item = actual_budget(*args, **kwargs)
            budgets.append(item)
            return item
        with patch.object(mod, '_ReadBudget', budget), patch.object(Path, 'open', opening):
            with self.assertRaises(mod.IntakeError):
                mod.intake(self.repo, self.private, gpx_file=self.gpx)
        self.assertEqual(requests, [size+1])
        self.assertEqual(budgets[0].bytes_read, size+1)
        self.assertFalse((self.private/'raw').exists())

    def test_failed_global_plus_one_includes_previous_capture_reads(self):
        actual_budget, budgets = mod._ReadBudget, []
        size = self.log.stat().st_size
        def budget(*args, **kwargs):
            item = actual_budget(*args, **kwargs)
            budgets.append(item)
            return item
        with patch.object(mod, '_ReadBudget', budget), patch.object(mod, 'MAX_READ_BYTES', size+3):
            with self.assertRaises(mod.IntakeError):
                mod.intake(self.repo, self.private, log_file=self.log)
        self.assertEqual(budgets[0].bytes_read, size+4)
        self.assertEqual(list(self.private.glob('.capture-*')), [])

    def test_parse_and_second_source_share_the_original_deadline(self):
        actual = mod.summarize_log
        def delayed(*args, **kwargs):
            result = actual(*args, **kwargs)
            time.sleep(.025)
            return result
        actual_open, gpx_opens = Path.open, []
        def opening(path, *args, **kwargs):
            if path == self.gpx:
                gpx_opens.append(True)
            return actual_open(path, *args, **kwargs)
        with patch.object(mod, 'MAX_INTAKE_SECONDS', .02), patch.object(mod, 'summarize_log', delayed), patch.object(Path, 'open', opening):
            with self.assertRaises(mod.IntakeError):
                mod.intake(self.repo, self.private, log_file=self.log, gpx_file=self.gpx)
        self.assertEqual(gpx_opens, [])
        self.assertEqual(list(self.private.glob('receipts/*.json')), [])

    def test_capture_cleanup_preserves_replacement_and_primary(self):
        marker = RuntimeError('SYNTHETIC_PARSE_FIRST')
        replacements = []
        def replacing(*args, **kwargs):
            staged, = self.private.glob('.capture-*')
            staged.unlink()
            staged.write_bytes(b'SYNTHETIC_UNOWNED_CAPTURE')
            replacements.append(staged)
            raise marker
        with patch.object(mod, 'summarize_log', replacing):
            with self.assertRaises(RuntimeError) as caught:
                mod.intake(self.repo, self.private, log_file=self.log)
        self.assertIs(caught.exception, marker)
        self.assertEqual(replacements[0].read_bytes(), b'SYNTHETIC_UNOWNED_CAPTURE')
        self.assertTrue(any('TEMP_CLEANUP_RESIDUAL' in note for note in marker.__notes__))

    def test_capture_cleanup_without_primary_preserves_unowned_replacement(self):
        actual = mod.summarize_log
        replacements = []
        def replacing(*args, **kwargs):
            result = actual(*args, **kwargs)
            staged, = self.private.glob('.capture-*')
            raw = staged.read_bytes()
            staged.unlink()
            staged.write_bytes(raw)
            replacements.append(staged)
            return result
        with patch.object(mod, 'summarize_log', replacing):
            with self.assertRaises(mod.IntakeError) as caught:
                mod.intake(self.repo, self.private, log_file=self.log)
        self.assertIn('TEMP_CLEANUP_RESIDUAL', str(caught.exception))
        self.assertEqual(replacements[0].read_bytes(), self.log.read_bytes())

    def test_copy_and_receipt_fsync_expiry_prevent_next_publication(self):
        native_fsync = os.fsync
        for phase in (2, 3):
            with self.subTest(fsync=phase), tempfile.TemporaryDirectory() as directory:
                private = Path(directory)/'private'
                calls = []
                def fsync(fd):
                    native_fsync(fd)
                    calls.append(fd)
                    if len(calls) == phase:
                        time.sleep(.03)
                with patch.object(mod, 'MAX_INTAKE_SECONDS', .025), patch.object(os, 'fsync', fsync):
                    with self.assertRaises(mod.IntakeError):
                        mod.intake(self.repo, private, log_file=self.log)
                self.assertEqual(list(private.glob('receipts/*.json')), [])
                self.assertEqual(list(private.rglob('.pending-*')), [])
                self.assertEqual(list(private.glob('.capture-*')), [])

    def test_existing_receipt_readback_consumes_remaining_global_budget(self):
        result = mod.intake(self.repo, self.private, log_file=self.log)
        receipt = self.private/'receipts'/(result['receipt_id']+'.json')
        before = receipt.read_bytes()
        # Reuse reads original + parse-stage + existing archive, then actual receipt.
        cap = self.log.stat().st_size*3+len(before)-1
        with patch.object(mod, 'MAX_READ_BYTES', cap), self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.private, log_file=self.log)
        self.assertEqual(receipt.read_bytes(), before)

    def test_existing_archive_readback_is_counted_and_size_conflict_rejected(self):
        result = mod.intake(self.repo, self.private, log_file=self.log)
        row = json.loads((self.private/'receipts'/(result['receipt_id']+'.json')).read_bytes())['sources'][0]
        archive = Path(row['private_archive'])
        archive.write_bytes(archive.read_bytes()+b' ')
        with self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.private, log_file=self.log)

    def test_log_byte_record_and_night_limits_reject_before_archive(self):
        cases = [('MAX_LOG_BYTES', 16, '2000/01/01 19:00\n目撃\nハブ\n'),
                 ('MAX_LOG_RECORDS', 1, '2000/01/01 19:00\n目撃\nハブ\n2000/01/01 20:00\n目撃\nハブ\n'),
                 ('MAX_LOG_NIGHTS', 1, '2000/01/01 19:00\n目撃\nハブ\n2000/01/02 20:00\n目撃\nハブ\n')]
        for name, limit, text in cases:
            with self.subTest(limit=name):
                self.log.write_text(text, encoding='utf-8')
                with patch.object(mod, name, limit, create=True), self.assertRaises(mod.IntakeError):
                    mod.intake(self.repo, self.private, log_file=self.log)
                self.assertFalse((self.private/'raw'/'log').exists())

    def test_xml_structure_limits_and_encoded_dtd_reject_before_archive(self):
        for name, limit, xml in [('MAX_XML_POINTS', 1, '<gpx><trkpt/><trkpt/></gpx>'),
                                 ('MAX_XML_ELEMENTS', 2, '<gpx><trk><trkseg/></trk></gpx>'),
                                 ('MAX_XML_DEPTH', 2, '<gpx><trk><trkseg/></trk></gpx>')]:
            with self.subTest(limit=name):
                self.gpx.write_bytes(xml.encode())
                with patch.object(mod, name, limit, create=True), self.assertRaises(mod.IntakeError):
                    mod.intake(self.repo, self.private, gpx_file=self.gpx)
                self.assertFalse((self.private/'raw'/'gpx').exists())
        xml = '<!DOCTYPE gpx [<!ENTITY a "SYNTHETIC_ONLY">]><gpx>&a;</gpx>'
        for encoding in ('utf-8', 'utf-8-sig', 'utf-16', 'utf-16-be'):
            with self.subTest(encoding=encoding):
                self.gpx.write_bytes(xml.encode(encoding))
                with patch.object(mod, 'READ_CHUNK_BYTES', 3, create=True), self.assertRaises(mod.IntakeError):
                    mod.intake(self.repo, self.private, gpx_file=self.gpx)

    def test_growing_original_is_not_archived(self):
        actual = Path.open
        opened = []
        def opening(path, *args, **kwargs):
            if path == self.gpx and args and args[0] == 'rb' and not opened:
                with actual(path, 'ab') as stream:
                    stream.write(b' ')
                opened.append(True)
            return actual(path, *args, **kwargs)
        with patch.object(Path, 'open', opening), self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.private, gpx_file=self.gpx)
        self.assertFalse((self.private/'raw'/'gpx').exists())

    def test_deadline_covers_source_open_and_prevents_publication(self):
        actual = Path.open
        def opening(path, *args, **kwargs):
            stream = actual(path, *args, **kwargs)
            if path == self.log:
                time.sleep(.015)
            return stream
        with patch.object(mod, 'MAX_INTAKE_SECONDS', .005, create=True), patch.object(Path, 'open', opening):
            with self.assertRaises(mod.IntakeError):
                mod.intake(self.repo, self.private, log_file=self.log)
        self.assertFalse((self.private/'receipts').exists())

    def test_receipt_producer_cap_rejects_without_receipt(self):
        with patch.object(mod, 'MAX_RECEIPT_BYTES', 64, create=True), self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.private, log_file=self.log)
        self.assertEqual(list(self.private.glob('receipts/*.json')), [])

    def test_cumulative_read_cap_includes_stage_parse_and_archive_verification(self):
        source_size = self.log.stat().st_size
        with patch.object(mod, 'MAX_READ_BYTES', source_size*2, create=True), self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.private, log_file=self.log)
        self.assertEqual(list(self.private.glob('receipts/*.json')), [])

    def test_oversize_is_rejected_before_hashing_or_opening_source(self):
        self.log.write_bytes(b'x'*33)
        actual = Path.open
        opened = []
        def opening(path, *args, **kwargs):
            if path == self.log:
                opened.append(args[0] if args else kwargs.get('mode', 'r'))
            return actual(path, *args, **kwargs)
        with patch.object(mod, 'MAX_RAW_BYTES', 32), patch.object(Path, 'open', opening):
            with self.assertRaises(mod.IntakeError):
                mod.intake(self.repo, self.private, log_file=self.log)
        self.snapshot_evidence = dict(cap=32, source_bytes=33, source_opens=opened, engine_calls=0)
        self.assertEqual(opened, [], 'Declared oversize was hashed/read before rejection')

    def test_archive_and_diagnostic_share_bytes_during_source_a_b_a_reopen(self):
        a = '2000/01/01 19:00\n目撃\nハブ\n'.encode('utf-8')
        b = '2000/01/01 19:00\n捕獲\nハブ\n'.encode('utf-8')
        self.assertEqual(len(a), len(b))
        self.log.write_bytes(a)
        actual = Path.open
        swaps = []
        def opening(path, *args, **kwargs):
            mode = args[0] if args else kwargs.get('mode', 'r')
            if path == self.log and mode == 'r':
                with actual(path, 'wb') as stream:
                    stream.write(b)
                swaps.append('B-before-original-text-parse')
            elif path == self.log and mode == 'rb' and swaps == ['B-before-original-text-parse']:
                with actual(path, 'wb') as stream:
                    stream.write(a)
                swaps.append('A-before-original-copy')
            return actual(path, *args, **kwargs)
        with patch.object(Path, 'open', opening):
            result = mod.intake(self.repo, self.private, log_file=self.log)
        receipt = json.loads((self.private/'receipts'/(result['receipt_id']+'.json')).read_bytes())
        row = receipt['sources'][0]
        archived = Path(row['private_archive']).read_bytes()
        self.assertEqual(archived, a)
        self.assertEqual(row['sha256'], hashlib.sha256(archived).hexdigest())
        nights = receipt['log_diagnostic']['nights']['2000-01-01']
        self.snapshot_evidence = dict(source_a_sha256=hashlib.sha256(a).hexdigest(),
            source_b_sha256=hashlib.sha256(b).hexdigest(), archived_sha256=row['sha256'],
            swaps=swaps, archive_capture_events=0, receipt_capture_events=nights['owner_habu_capture_events'],
            engine_calls=0)
        self.assertEqual(nights['owner_habu_capture_events'], 0,
                         'Archived sighting A was bound to capture diagnostic from mutable B')
        self.assertEqual(nights['habu_sighting_events'], 1)

    def replaced_temp_control(self, selected_parent, *, primary=None):
        native_link = os.link
        replacements = []
        marker = b"SYNTHETIC_UNOWNED_REPLACEMENT_DO_NOT_DELETE"
        def link_then_replace(source, target):
            source, target = Path(source), Path(target)
            self.assertTrue(source.is_relative_to(self.root))
            self.assertTrue(target.is_relative_to(self.root))
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
                mod.intake(self.repo, self.private, log_file=self.log)
        except BaseException as exc:
            caught = exc
        self.assertEqual(len(replacements), 1)
        self.assertTrue(replacements[0].is_file(), "Cleanup deleted an unowned regular replacement")
        self.assertEqual(replacements[0].read_bytes(), marker)
        digest = hashlib.sha256(self.log.read_bytes()).hexdigest()
        self.assertEqual((self.private / "raw" / "log" / (digest + ".txt")).read_bytes(), self.log.read_bytes())
        if primary is not None:
            self.assertIs(caught, primary)
            self.assertTrue(any("TEMP_CLEANUP_RESIDUAL" in x for x in caught.__notes__))
        else:
            self.assertIsInstance(caught, mod.IntakeError)
            self.assertIn("TEMP_CLEANUP_RESIDUAL", str(caught))

    def test_archive_cleanup_preserves_replaced_regular_temp(self):
        self.replaced_temp_control("log")

    def test_receipt_cleanup_preserves_replaced_regular_temp(self):
        self.replaced_temp_control("receipts")

    def test_archive_cleanup_preserves_primary_and_explicit_residual(self):
        self.replaced_temp_control("log", primary=RuntimeError("SYNTHETIC_PRIMARY"))

    def test_receipt_cleanup_preserves_primary_and_explicit_residual(self):
        self.replaced_temp_control("receipts", primary=RuntimeError("SYNTHETIC_PRIMARY"))

    def test_owned_archive_and_receipt_temps_are_removed_normally(self):
        result = mod.intake(self.repo, self.private, log_file=self.log)
        digest = hashlib.sha256(self.log.read_bytes()).hexdigest()
        self.assertEqual([p.name for p in (self.private / "raw" / "log").iterdir()], [digest + ".txt"])
        self.assertEqual([p.name for p in (self.private / "receipts").iterdir()], [result["receipt_id"] + ".json"])

    def directory_alias(self, link, target, *, junction=False):
        self.assertTrue(link.is_relative_to(self.root))
        self.assertTrue(target.is_relative_to(self.root))
        if junction:
            if os.name != "nt":
                self.skipTest("Actual Windows junction control requires Windows")
            result = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
                                    capture_output=True, check=False)
            if result.returncode:
                self.skipTest("Junction unavailable without elevation: " + str(result.returncode))
        else:
            try:
                link.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest("Actual symlink unavailable without elevation: " + str(exc))
        def remove_alias():
            try:
                os.rmdir(link) if junction else link.unlink()
            except FileNotFoundError:
                pass
        self.addCleanup(remove_alias)

    def parent_alias_rejected(self, child, *, junction=False):
        self.private.mkdir(mode=0o700)
        outside = self.repo / "forbidden-test-output"
        outside.mkdir()
        self.directory_alias(self.private / child, outside, junction=junction)
        with self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.private, log_file=self.log)
        self.assertEqual(list(outside.iterdir()), [])

    def test_raw_parent_symlink_cannot_escape_private_root(self):
        self.parent_alias_rejected("raw")

    def test_receipts_parent_symlink_cannot_escape_private_root(self):
        self.parent_alias_rejected("receipts")

    def test_raw_parent_junction_cannot_escape_private_root(self):
        self.parent_alias_rejected("raw", junction=True)

    def test_receipts_parent_junction_cannot_escape_private_root(self):
        self.parent_alias_rejected("receipts", junction=True)

    def test_receipt_leaf_symlink_is_not_reused(self):
        result = mod.intake(self.repo, self.private, log_file=self.log)
        receipt = self.private / "receipts" / (result["receipt_id"] + ".json")
        outside = self.repo / "synthetic-receipt.json"
        receipt.rename(outside)
        before = outside.read_bytes()
        try:
            receipt.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("Actual symlink unavailable without elevation: " + str(exc))
        with self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.private, log_file=self.log)
        self.assertEqual(outside.read_bytes(), before)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.private = self.root / "private"
        self.log = self.root / "log.txt"
        # Explicitly synthetic, non-identifying test input; not an owner log/route.
        self.log.write_text(
            "2000/01/01 19:36\nSYNTHETIC_NONLOCATION_ONLY\nエリア探索開始\n"
            "2000/01/01 19:55\n捕獲\nハブ捕獲~90幼体\n"
            "2000/01/02 0:12\n目撃\n1匹\nヒメハブ\n"
            "2000/01/02 0:15\n轢死\n1匹\nハブ\n"
            "2000/01/02 1:27\nSYNTHETIC_NONLOCATION_ONLY\nエリア探索終了\n",
            encoding="utf-8",
        )
        self.gpx = self.root / "route.gpx"
        self.gpx.write_text('<gpx creator="SYNTHETIC_TEST_ONLY"><trk><trkseg>'
                            '<trkpt lat="0" lon="0"/></trkseg></trk></gpx>')

    def test_07_rollover_and_species_separation(self):
        a = mod.summarize_log(self.log.read_text(encoding="utf-8"))
        self.assertEqual(list(a["nights"]), ["2000-01-01"])
        n = a["nights"]["2000-01-01"]
        self.assertEqual(n["owner_habu_capture_events"], 1)
        self.assertEqual(n["habu_sighting_events"], 0)
        self.assertEqual(n["habu_roadkill_events"], 1)
        self.assertEqual(n["start_events"], 1)
        self.assertEqual(n["end_events"], 1)

    def test_private_immutable_deduplicated_intake(self):
        a = mod.intake(self.repo, self.private, log_file=self.log, gpx_file=self.gpx)
        b = mod.intake(self.repo, self.private, log_file=self.log, gpx_file=self.gpx)
        self.assertEqual(a, b)
        self.assertEqual(len(list((self.private / "raw" / "gpx").glob("*.gpx"))), 1)
        self.assertNotIn("SYNTHETIC_NONLOCATION_ONLY", json.dumps(a))
        src_hash = hashlib.sha256(self.gpx.read_bytes()).hexdigest()
        self.assertEqual(
            (self.private / "raw" / "gpx" / f"{src_hash}.gpx").read_bytes(),
            self.gpx.read_bytes(),
        )
        receipt = json.loads(next((self.private / "receipts").glob("*.json")).read_text())
        self.assertEqual(receipt["pdca"], "NOT_RUN")

    def test_public_repo_and_symlinks_refused(self):
        with self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.repo / "private", gpx_file=self.gpx)
        self.private.mkdir()
        link = self.root / "link.gpx"
        try:
            link.symlink_to(self.gpx)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("Actual symlink unavailable without elevation: " + str(exc))
        with self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.private, gpx_file=link)

    def test_corrupt_gpx_rejected_without_archive(self):
        self.gpx.write_text("<gpx><trk>")
        with self.assertRaises(mod.IntakeError):
            mod.intake(self.repo, self.private, gpx_file=self.gpx)
        self.assertFalse((self.private / "raw" / "gpx").exists())

    def test_bad_timestamp_rejected(self):
        with self.assertRaises(mod.IntakeError):
            mod.summarize_log("2026/02/30 21:00\n捕獲\nハブ捕獲~90幼体")


if __name__ == "__main__":
    unittest.main()
