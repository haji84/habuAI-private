"""Native filesystem boundary tests; importing these does not require fcntl."""
from contextlib import contextmanager
import builtins
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


# Exact native LF function from 45c183b, before the preflight implementation.
OLD_LOCAL_PATH_SOURCE = r'''def local_path(root: Path, relative: str = '') -> Path:
    root = Path(root)
    windows = PureWindowsPath(relative)
    if windows.drive or windows.is_absolute() or '..' in windows.parts:
        raise ValueError('Unsafe relative path')
    # Reject ambiguous Windows names before resolution can hide their spelling.
    if any(part.endswith(('.', ' ')) or ':' in part or re.search(r'~[0-9]+(?:\.|$)', part)
           for part in windows.parts):
        raise ValueError('Ambiguous portable path component')
    path = safe_path(root, relative) if relative else root
    absolute = path.absolute()
    for current in reversed((absolute, *absolute.parents)):
        try:
            attributes = current.lstat()
        except FileNotFoundError:
            continue
        if (current.is_symlink() or getattr(current, 'is_junction', lambda: False)() or
                getattr(attributes, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)):
            raise ValueError('Reparse inventory path is forbidden')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Inventory path resolves outside root')
    return path
'''


def old_local_path(source=OLD_LOCAL_PATH_SOURCE):
    raw = source.encode('utf-8')
    if (len(raw), hashlib.sha256(raw).hexdigest()) != (
            1179, 'bf6bcdcd36fb76ea0ff2268ac68aca53293c2f8b93ad3eaae317576814ac9da1'):
        raise ValueError('OLD_LOCAL_PATH_ORACLE_CHANGED')
    namespace = dict(vars(inventory))
    exec(compile(source, '<frozen-local-path-45c183b>', 'exec'), namespace)
    return namespace['local_path']


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

    def assert_static_link_preflight(self, link, operation):
        # Lexical comparisons only: the observer must not itself resolve a link.
        descendant_metadata, resolutions, opened, scanned = [], [], [], []
        actual_lstat, actual_stat = Path.lstat, Path.stat
        actual_resolve, actual_open, actual_scan = Path.resolve, Path.open, os.scandir
        absolute_link = link.absolute()

        def descendant(path):
            path = Path(path).absolute()
            return path != absolute_link and path.is_relative_to(absolute_link)

        def tracked_lstat(path, *args, **kwargs):
            if descendant(path):
                descendant_metadata.append(('lstat', str(path)))
            return actual_lstat(path, *args, **kwargs)

        def tracked_stat(path, *args, **kwargs):
            if descendant(path):
                descendant_metadata.append(('stat', str(path), kwargs.get('follow_symlinks', True)))
            return actual_stat(path, *args, **kwargs)

        def tracked_resolve(path, *args, **kwargs):
            if Path(path).absolute() == absolute_link or descendant(path):
                resolutions.append(str(path))
            return actual_resolve(path, *args, **kwargs)

        def tracked_open(path, *args, **kwargs):
            opened.append(str(path))
            return actual_open(path, *args, **kwargs)

        def tracked_scan(path, *args, **kwargs):
            scanned.append(str(path))
            return actual_scan(path, *args, **kwargs)

        with patch.object(Path, 'lstat', tracked_lstat), patch.object(Path, 'stat', tracked_stat), \
                patch.object(Path, 'resolve', tracked_resolve), patch.object(Path, 'open', tracked_open), \
                patch.object(os, 'scandir', tracked_scan):
            with self.assertRaises(ValueError):
                operation()
        self.assertEqual(descendant_metadata, [], 'static link descendants must receive no metadata calls')
        self.assertEqual(resolutions, [], 'reject before normalization/resolution')
        self.assertEqual(opened, [])
        self.assertEqual(scanned, [])

    def test_frozen_old_helper_is_distinct_and_integrity_checked(self):
        old = old_local_path()
        self.assertIsNot(old, inventory.local_path)
        self.assertEqual(old.__code__.co_filename, '<frozen-local-path-45c183b>')
        with self.assertRaisesRegex(ValueError, 'OLD_LOCAL_PATH_ORACLE_CHANGED'):
            old_local_path(OLD_LOCAL_PATH_SOURCE.replace('return path', 'return root'))

    def test_ordinary_paths_and_native_errors_match_frozen_old_helper(self):
        old = old_local_path()
        self.write('existing/leaf.txt', b'immutable\r\n')
        self.write('ordinary-file', b'not a directory')
        (self.work / 'prefix').mkdir()
        (self.work / 'ordinary-file').write_bytes(b'not a directory')

        def outcome(function, root, relative):
            try:
                value = function(root, relative)
                return ('RETURN', type(value), value, str(value))
            except Exception as error:
                return ('RAISE', type(error), error.args, getattr(error, 'errno', None),
                        getattr(error, 'winerror', None), getattr(error, 'filename', None))

        previous = Path.cwd()
        os.chdir(self.work)
        try:
            roots = (self.root, Path('workspace'), self.root / 'existing/..',
                     Path('workspace/existing/..'), self.work / 'missing/../workspace',
                     Path('missing/../workspace'), self.work / 'ordinary-file/../workspace',
                     self.work / 'missing', self.work / 'ordinary-file', Path('.'), Path(''),
                     Path('prefix/..'), Path('prefix/../workspace'))
            cases = [(root, relative) for root in roots for relative in
                     ('', 'existing/leaf.txt', 'missing/leaf.txt', 'ordinary-file/child')]
            cases.extend((self.root, relative) for relative in
                         ('.', './', '../outside', '..\\outside', '/outside', 'C:\\outside',
                          'data/ORIGINAL./leaf', 'data/x~1/leaf', 'data/file:stream',
                          '\\workspace\\missing', str(self.root / 'existing/leaf.txt')[2:]))
            self.assertEqual(len(cases), 63)
            for root, relative in cases:
                with self.subTest(root=str(root), relative=relative):
                    self.assertEqual(outcome(inventory.local_path, root, relative), outcome(old, root, relative))
        finally:
            os.chdir(previous)

    @unittest.skipUnless(sys.platform == 'win32', 'Actual Windows junction metadata ordering')
    def test_nested_junction_rejects_before_descendant_metadata(self):
        with self.junction(self.root / 'data/escape') as link:
            self.assert_static_link_preflight(link, lambda: inventory.local_path(self.root, 'data/escape/sentinel.txt'))

    @unittest.skipUnless(sys.platform == 'win32', 'Actual Windows junction metadata ordering')
    def test_root_junction_rejects_before_descendant_metadata(self):
        with self.junction(self.work / 'alias') as link:
            self.assert_static_link_preflight(link, lambda: inventory.local_path(link, 'sentinel.txt'))

    @unittest.skipUnless(sys.platform == 'win32', 'Actual Windows junction metadata ordering')
    def test_root_ancestor_junction_rejects_before_descendant_metadata(self):
        (self.external / 'child').mkdir()
        with self.junction(self.work / 'alias') as link:
            self.assert_static_link_preflight(link, lambda: inventory.local_path(link / 'child', 'sentinel.txt'))

    @unittest.skipUnless(sys.platform == 'win32', 'Actual Windows junction metadata ordering')
    def test_contained_junction_rejects_before_descendant_metadata(self):
        inside = self.root / 'inside'
        inside.mkdir()
        with self.junction(self.root / 'data', inside) as link:
            self.assert_static_link_preflight(link, lambda: inventory.local_path(self.root, 'data/source.txt'))

    @unittest.skipUnless(sys.platform == 'win32', 'Actual Windows junction metadata ordering')
    def test_root_dotdot_cannot_hide_junction_before_metadata(self):
        with self.junction(self.work / 'alias') as link:
            self.assert_static_link_preflight(link, lambda: inventory.local_path(link / '../workspace', 'data/source.txt'))

    @unittest.skipUnless(sys.platform == 'win32', 'Actual Windows junction metadata ordering')
    def test_copy_junctions_reject_before_descendant_metadata_or_copy(self):
        snapshot = self.work / 'snapshot'
        snapshot.mkdir()
        self.write('data/source.txt', b'source')
        inputs = inventory.inventory(self.root)
        with self.junction(snapshot / 'data') as link:
            self.assert_static_link_preflight(link, lambda: inventory.copy_inputs(self.root, snapshot, inputs))
        with self.junction(self.root / 'other') as link:
            bad_inputs = {'other/sentinel.txt': {'sha256': hashlib.sha256(self.sentinel.read_bytes()).hexdigest()}}
            self.assert_static_link_preflight(link, lambda: inventory.copy_inputs(self.root, snapshot, bad_inputs))

    @unittest.skipUnless(sys.platform == 'win32', 'Actual Windows rooted-join metadata ordering')
    def test_rooted_join_still_preflights_the_original_root(self):
        (self.external / 'child').mkdir()
        with self.junction(self.work / 'alias') as link:
            rooted = str(self.external / 'child/source.txt')[2:]
            self.assertFalse(Path(rooted).is_absolute())
            self.assert_static_link_preflight(link, lambda: inventory.local_path(link / 'child', rooted))

    @unittest.skipUnless(sys.platform == 'win32', 'Actual Windows shared reader metadata ordering')
    def test_shared_g0_reader_rejects_junction_without_metadata_or_byte_charge(self):
        from g0_forecast_contract import G0ArtifactReader
        from prospective_inputs import ProspectiveReadContext

        raw = self.sentinel.read_bytes()
        context = ProspectiveReadContext(30.0, 1024)
        reader = G0ArtifactReader(self.root, context)
        deadline = context.deadline
        ref = {'path': 'features/sentinel.txt', 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}
        with self.junction(self.root / 'features') as link:
            self.assert_static_link_preflight(link, lambda: reader.read(ref, parse=False))
        self.assertEqual(context.bytes_read, 0)
        self.assertEqual(context.max_bytes, 1024)
        self.assertEqual(context.deadline, deadline)
        self.assertEqual(reader.refs, {})

    def test_ordinary_metadata_errors_propagate_by_identity(self):
        actual = Path.lstat
        for error in (PermissionError(13, 'fixture denied', str(self.root)),
                      NotADirectoryError(20, 'fixture prefix', str(self.root)),
                      OSError(5, 'fixture I/O', str(self.root)), TimeoutError('caller timeout')):
            def raising(path, *args, **kwargs):
                if path == self.root:
                    raise error
                return actual(path, *args, **kwargs)

            for helper in (old_local_path(), inventory.local_path):
                with self.subTest(error=type(error).__name__, helper=helper.__code__.co_filename):
                    with patch.object(Path, 'lstat', raising):
                        try:
                            helper(self.root, 'source.txt')
                        except BaseException as received:
                            self.assertIs(received, error)
                        else:
                            self.fail('ordinary caller error was swallowed')

    def test_prospective_caller_checks_preserve_error_identity_and_context(self):
        import prospective_inputs as pi

        for helper in (old_local_path(), inventory.local_path):
            for boundary in (1, 2):
                for error in (TimeoutError('caller elapsed'), pi.InputCapacityError('caller capacity')):
                    with self.subTest(helper=helper.__code__.co_filename, boundary=boundary, error=type(error).__name__):
                        context = pi.ProspectiveReadContext(30.0, 1024)
                        before = (context.deadline, context.max_bytes, context.bytes_read)
                        checks = []

                        def check():
                            context.check()
                            checks.append(len(checks) + 1)
                            if len(checks) == boundary:
                                raise error

                        with patch.object(pi, 'guarded_local_path', helper):
                            try:
                                pi._local_path(self.root, 'features/source.json', check)
                            except BaseException as received:
                                self.assertIs(received, error)
                            else:
                                self.fail('caller check was swallowed')
                        self.assertEqual(len(checks), boundary)
                        self.assertEqual((context.deadline, context.max_bytes, context.bytes_read), before)

    def test_whole_ordinary_inventory_copy_and_payload_order_match_old_helper(self):
        self.write('data/raw/source.bin', b'\x00\xffsource\r\n')
        self.write('features/source.json', b'{"feature":1}\n')
        self.write('src/nested/model.py', b'MODEL = 1\n')
        self.write('AGENTS.md', b'fixture rules\n')
        results = []
        current = inventory.local_path
        actual_hash, actual_path_open, actual_open = inventory.file_hash, Path.open, builtins.open
        for number, helper in enumerate((old_local_path(), current)):
            snapshot = self.work / f'snapshot-{number}'
            snapshot.mkdir()
            events = []

            def label(path):
                path = Path(path)
                for name, base in (('source', self.root), ('snapshot', snapshot)):
                    if path.is_relative_to(base):
                        return name + '/' + path.relative_to(base).as_posix()
                raise AssertionError('unexpected payload outside controlled roots: ' + str(path))

            def tracked_hash(path):
                result = actual_hash(path)
                events.append(('hash', label(path), result))
                return result

            def tracked_path_open(path, *args, **kwargs):
                events.append(('Path.open', label(path), args, kwargs))
                return actual_path_open(path, *args, **kwargs)

            def tracked_open(path, *args, **kwargs):
                events.append(('open', label(path), args, kwargs))
                return actual_open(path, *args, **kwargs)

            with patch.object(inventory, 'local_path', helper), patch.object(inventory, 'file_hash', tracked_hash), \
                    patch.object(Path, 'open', tracked_path_open), patch.object(builtins, 'open', tracked_open):
                inputs = inventory.inventory(self.root)
                inventory.copy_inputs(self.root, snapshot, inputs)
                matches = inventory.snapshot_matches(snapshot, inputs)
                code_hash = inventory.runtime_code_hash(self.root)
            copies = {relative: (snapshot / relative).read_bytes() for relative in inputs}
            (snapshot / 'reports').mkdir()
            (snapshot / 'reports/result.json').write_bytes(b'{"result":"fixture"}\n')
            (snapshot / 'predictions/replay').mkdir(parents=True)
            (snapshot / 'predictions/replay/result.json').write_bytes(b'{"replay":"fixture"}\n')
            with patch.object(inventory, 'local_path', helper):
                generated = inventory.generated_artifacts(snapshot, inputs)
                replay_matches = inventory.snapshot_matches(snapshot, inputs)
            results.append((inputs, copies, matches, replay_matches, code_hash, generated, events))
        self.assertEqual(results[0], results[1])
        self.assertTrue(results[1][2])
        self.assertTrue(results[1][3])
        self.assertEqual(len(results[1][0]), 4)
        self.assertEqual(set(results[1][5]), {'snapshot/reports/result.json', 'snapshot/predictions/replay/result.json'})

    def test_shared_g0_ordinary_full_read_rescan_and_tamper_match_old_helper(self):
        from g0_forecast_contract import G0ArtifactReader
        import prospective_inputs as pi

        path = 'features/source.json'
        raw = b'{"feature":1}'
        ref = {'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}
        results = []
        for helper in (old_local_path(), inventory.local_path):
            source = self.write(path, raw)
            context = pi.ProspectiveReadContext(30.0, 1024)
            deadline = context.deadline
            reader = G0ArtifactReader(self.root, context)
            opened = []
            actual = Path.open

            def tracked(path, *args, **kwargs):
                opened.append((path.relative_to(self.root).as_posix(), args, kwargs))
                return actual(path, *args, **kwargs)

            with patch.object(pi, 'guarded_local_path', helper), patch.object(Path, 'open', tracked):
                value = reader.read(ref)
                reader.rescan()
            self.assertEqual(context.bytes_read, 2 * len(raw))
            self.assertEqual(context.deadline, deadline)
            results.append((value, dict(reader.refs), context.bytes_read, context.max_bytes, list(opened)))
            source.write_bytes(b'{"feature":2}')
            with patch.object(pi, 'guarded_local_path', helper):
                with self.assertRaisesRegex(ValueError, 'Source size/hash changed or mismatched'):
                    reader.rescan()
            self.assertEqual(context.bytes_read, 3 * len(raw))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1][0], {'feature': 1})
        self.assertEqual(results[1][1], {path: ref})

    @unittest.skipIf(sys.platform == 'win32', 'Actual POSIX symlink metadata ordering')
    def test_posix_symlinks_keep_errors_and_reject_before_descendant_metadata(self):
        link = self.work / 'alias'
        link.symlink_to(self.external, target_is_directory=True)
        self.assert_static_link_preflight(link, lambda: inventory.local_path(link / 'child', 'source.txt'))
        self.assert_static_link_preflight(link, lambda: inventory.local_path(link / '../workspace', 'source.txt'))
        with self.assertRaisesRegex(ValueError, '^Symlink root is forbidden$'):
            inventory.local_path(link, 'source.txt')
        with self.assertRaisesRegex(ValueError, '^Reparse inventory path is forbidden$'):
            inventory.local_path(link)
        nested = self.root / 'alias'
        nested.symlink_to(self.external, target_is_directory=True)
        self.assert_static_link_preflight(nested, lambda: inventory.local_path(self.root, 'alias/source.txt'))
        with self.assertRaisesRegex(ValueError, '^Symlink path is forbidden: alias/source.txt$'):
            inventory.local_path(self.root, 'alias/source.txt')
        broken = self.root / 'broken'
        broken.symlink_to(self.work / 'missing', target_is_directory=True)
        self.assert_static_link_preflight(broken, lambda: inventory.local_path(self.root, 'broken/source.txt'))

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

    def test_ambiguous_portable_components_reject_before_resolution_or_metadata(self):
        relatives = (
            "evidence/ORIGINAL./manifest.json", "evidence/ORIGINAL /manifest.json",
            "evidence/ORIGINAL. /manifest.json", "evidence/source.json.",
            "evidence/source.json ", "evidence\\ORIGINAL.\\manifest.json",
            "evidence\\ORIGINAL \\manifest.json", "evidence/source.json:stream",
            "evidence/source:stream/manifest.json", "evidence/ORIGIN~1/manifest.json",
            "evidence/ORIGIN~12/manifest.json", "evidence/source~1.json",
            "evidence\\ORIGIN~1\\manifest.json",
        )
        original_lstat = Path.lstat
        for relative in relatives:
            with self.subTest(relative=relative):
                with patch.object(inventory, "safe_path", wraps=inventory.safe_path) as resolved, patch.object(
                        Path, "lstat", autospec=True, side_effect=original_lstat) as metadata:
                    error = None
                    try:
                        inventory.local_path(self.root, relative)
                    except (ValueError, OSError) as exc:
                        error = exc
                    self.assertIsInstance(error, ValueError, "ambiguous components must be rejected lexically")
                    resolved.assert_not_called()
                    metadata.assert_not_called()

    @unittest.skipUnless(sys.platform == "win32", "Actual Windows trailing-name alias regression")
    def test_native_trailing_component_aliases_cannot_reach_the_real_file(self):
        canonical = self.write("evidence/ORIGINAL/manifest.json", b"temporary native alias demonstration\r\n")
        relative = "evidence/ORIGINAL./manifest.json"
        alias = self.root / relative
        # Demonstrate Win32's actual alias on benign temporary bytes.
        self.assertTrue(alias.samefile(canonical))
        self.assertEqual(alias.read_bytes(), b"temporary native alias demonstration\r\n")
        with self.assertRaises(ValueError):
            inventory.local_path(self.root, relative)
        self.assertEqual(canonical.read_bytes(), b"temporary native alias demonstration\r\n")

    def test_unambiguous_unicode_internal_spaces_dots_and_tildes_preserve_bytes(self):
        relatives = ("evidence/日本語 資料/source .json", "data/a.b/tilde~name.txt",
                     "data/x~1name/source.json", "data/~資料/source.json")
        for relative in relatives:
            source = self.write(relative, b"\x00\xffunchanged\r\n")
            self.assertEqual(inventory.local_path(self.root, relative), source)
        inputs = inventory.inventory(self.root)
        self.assertEqual(set(inputs), set(relatives))
        self.assertTrue(all(value == {"sha256": hashlib.sha256(b"\x00\xffunchanged\r\n").hexdigest(),
                                     "size_bytes": 13} for value in inputs.values()))
        snapshot = self.work / "portable snapshot"
        snapshot.mkdir()
        inventory.copy_inputs(self.root, snapshot, inputs)
        self.assertTrue(inventory.snapshot_matches(snapshot, inputs))
        for relative in relatives:
            self.assertEqual((snapshot / relative).read_bytes(), b"\x00\xffunchanged\r\n")

    def test_shared_g0_reader_rejects_native_alias_without_reading_or_charging_bytes(self):
        from g0_forecast_contract import G0ArtifactReader
        from prospective_inputs import ProspectiveReadContext

        raw = b'{"source":"temporary"}'
        self.write("evidence/ORIGINAL/manifest.json", raw)
        for relative in ("evidence/ORIGINAL./manifest.json", "evidence/ORIGINAL /manifest.json",
                         "evidence/ORIGIN~1/manifest.json"):
            with self.subTest(relative=relative):
                context = ProspectiveReadContext(30.0, 1024)
                reader = G0ArtifactReader(self.root, context)
                ref = {"path": relative, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
                with patch.object(Path, "open", autospec=True, side_effect=Path.open) as opened:
                    with self.assertRaises(ValueError):
                        reader.read(ref, parse=False)
                    opened.assert_not_called()
                self.assertEqual(context.bytes_read, 0)
                self.assertEqual(reader.refs, {})

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
