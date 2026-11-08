"""Bounded byte transport is trajectory evidence, never outcome qualification."""
import base64
import hashlib
import importlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import evidence_audit as audit
from master_contracts import canonical_bytes

NIGHT = '2026-10-22'
NOW = '2026-10-25T20:00:00+09:00'
ANCHOR = 'data/raw/attachment_archives/gpx'
GPX = (b'<gpx><trk><trkseg><trkpt lat="28.15" lon="129.3">'
       b'<time>2026-10-22T12:00:00Z</time></trkpt>'
       b'<trkpt lat="28.15" lon="129.3"><time>2026-10-22T12:00:10Z</time>'
       b'</trkpt></trkseg></trk></gpx>')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pack(root, raw=GPX, *, compressed=None, part_chars=64):
    compressed = lzma.compress(raw, preset=0) if compressed is None else compressed
    encoded = base64.b64encode(compressed)
    directory = root / ANCHOR / sha(raw)
    directory.mkdir(parents=True, exist_ok=True)
    chunks = [encoded[i:i + part_chars] for i in range(0, len(encoded), part_chars)]
    for i, chunk in enumerate(chunks):
        (directory / f'part_{i:03d}.b64').write_bytes(chunk)
    manifest = dict(schema_version='habu-text-safe-byte-archive-v1',
                    original_filename='測定 GPX.gpx', kind='gpx', source='synthetic test',
                    source_ref=None, raw_size_bytes=len(raw), raw_sha256=sha(raw),
                    compression='xz', compressed_size_bytes=len(compressed),
                    compressed_sha256=sha(compressed), transfer_encoding='base64',
                    encoded_chars=len(encoded), part_chars=part_chars,
                    part_count=len(chunks), part_glob='part_*.b64')
    path = directory / 'manifest.json'
    path.write_bytes(canonical_bytes(manifest))
    return path.relative_to(root).as_posix(), manifest


class RecordedAudit(audit.Audit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order = []

    def read(self, path, *, max_bytes=None):
        self.order.append(path)
        return super().read(path, max_bytes=max_bytes)


class GpxAttachmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def helper(self):
        self.assertIsNotNone(importlib.util.find_spec('gpx_attachment_archive'),
                             'new guarded transport module is required')
        return importlib.import_module('gpx_attachment_archive')

    def consume(self, maximum=100 * 1024 * 1024):
        state = {'produced': 0}

        def charge(n):
            self.assertIs(type(n), int)
            self.assertGreaterEqual(n, 0)
            state['produced'] += n
            if state['produced'] > maximum:
                raise audit.AuditBudgetExceeded('DECODED_LIMIT')
            return maximum - state['produced']
        return charge, state

    def read_transport(self, path, *, a=None, charge=None, check=None):
        a = a or RecordedAudit(self.root, NOW)
        charge = charge or self.consume()[0]
        return self.helper().read_gpx_attachment_archive(
            self.root, path, read=a.read, check=check or a.tick,
            consume_decoded_bytes=charge)

    def test_verified_transport_retains_physical_and_raw_identities(self):
        path, manifest = pack(self.root)
        a = RecordedAudit(self.root, NOW)
        charge, state = self.consume()
        raw, crosswalk = self.read_transport(path, a=a, charge=charge)
        self.assertEqual(raw, GPX)
        self.assertEqual(state['produced'], len(GPX))
        self.assertEqual(crosswalk['manifest_ref'], dict(path=path,
                         sha256=sha((self.root / path).read_bytes()),
                         size_bytes=len((self.root / path).read_bytes())))
        self.assertEqual(crosswalk['reconstructed'], dict(sha256=sha(GPX), size_bytes=len(GPX)))
        self.assertEqual(crosswalk['compressed']['sha256'], manifest['compressed_sha256'])
        self.assertEqual(a.reads, 1 + manifest['part_count'])
        self.assertEqual(a.read_bytes, sum((self.root / p).stat().st_size for p in a.order))
        self.assertEqual(set(a.consumed), {path} | {p['path'] for p in crosswalk['parts']})

    def test_no_archive_seven_whole_results_and_actual_reads_match_immutable_original(self):
        capsule = ROOT / 'tests/fixtures/evidence_audit_9c06_original.py.txt'
        self.assertTrue(capsule.is_file(), 'hermetic original-reader capsule is required')
        raw = capsule.read_text(encoding='utf-8').encode('utf-8')
        self.assertEqual(len(raw), 42426)
        self.assertEqual(sha(raw), '4d8de850a18a79899f17baf33cbd8ab7d6caeb606550771d3a692cdfba97ccf3')
        original_module = types.ModuleType('gpx_intake_original_evidence_audit_9c06')
        original_module.__file__ = str(capsule)
        exec(compile(raw, str(capsule), 'exec'), original_module.__dict__)
        self.assertIsNot(original_module.audit_evidence, audit.audit_evidence)
        fixtures = importlib.import_module('test_evidence_audit')

        def run(module, root):
            instances = []
            actual_class = module.Audit
            class Record(actual_class):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.order = []
                    instances.append(self)
                def read(self, path, *, max_bytes=None):
                    self.order.append(path)
                    return super().read(path, max_bytes=max_bytes)
            opens = []
            actual_open = Path.open
            def opened(path, *args, **kwargs):
                opens.append(path.relative_to(root).as_posix())
                return actual_open(path, *args, **kwargs)
            with patch.object(module, 'Audit', Record), patch.object(Path, 'open', opened):
                result = module.audit_evidence(root, '2026-09-28', verified_at=NOW)
            instance = instances[0]
            return dict(result=result, reads=instance.reads, bytes=instance.read_bytes,
                        points=instance.points, read_order=instance.order, open_order=opens)

        for name in ('empty', 'unqualified', 'qualified_search', 'qualified_passage',
                     'raw_conflict', 'line_archive', 'bad_line_archive'):
            with self.subTest(case=name):
                root = self.root / name
                root.mkdir()
                if name in ('unqualified', 'qualified_search', 'qualified_passage', 'raw_conflict'):
                    _, capture = fixtures.fixture(root, name.startswith('qualified'),
                        search_role='PASSAGE' if name == 'qualified_passage' else 'SEARCH')
                    if name.startswith('qualified'):
                        fixtures.complete_coverage(root, capture)
                    if name == 'raw_conflict':
                        fixtures.write(root, 'data/raw/habu_logs/log.json', dict(
                            operational_date='2026-09-28',
                            capture_summary=dict(individuals=3, capture_events=1),
                            events=[dict(type='capture', time_local='2026-09-28T21:20:00+09:00',
                                         individual_count=3)]))
                if name.endswith('line_archive'):
                    gpx = (b'<gpx><trk><trkseg><trkpt lat="28.15" lon="129.3">'
                           b'<time>2026-09-28T12:00:00Z</time></trkpt></trkseg></trk></gpx>')
                    base = 'data/raw/gpx_archives/test.lines/'
                    fixtures.write(root, base + 'part_000.txt', gpx)
                    fixtures.write(root, base + 'manifest.json', dict(part_count=1,
                        part_glob='part_*.txt', encoding='utf-8', raw_size_bytes=len(gpx),
                        raw_sha256='0' * 64 if name.startswith('bad') else sha(gpx), trackpoint_count=1))
                before = run(original_module, root)
                after = run(audit, root)
                # Includes every result field, input hash, typed value, list order,
                # physical read charge and actual open. No exclusions or new-code goldens.
                self.assertEqual(canonical_bytes(before), canonical_bytes(after))

    def test_audit_consumes_archive_but_never_qualifies_search_or_outcomes(self):
        path, manifest = pack(self.root)
        result = audit.audit_evidence(self.root, NIGHT, verified_at=NOW)
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(len(result['trajectory_audit']), 1)
        self.assertEqual(result['trajectory_audit'][0]['point_count'], 2)
        source = next(s for s in result['source_manifest'] if s['path'] == path)
        self.assertNotEqual(source['sha256'], manifest['raw_sha256'])
        self.assertEqual(source['reconstructed_sha256'], manifest['raw_sha256'])
        self.assertEqual(source['use_roles'], ['diagnostic_only'])
        self.assertIsNone(source['historical_available_at'])
        self.assertEqual(source['availability_basis'], 'VERIFIED_PRESENT_NOW')
        self.assertEqual(source['attachment_archive']['integrity'], 'BYTE_EXACT_VERIFIED')
        self.assertTrue(result['observation_units'])
        self.assertTrue(all(u['label'] is None for u in result['observation_units']))
        self.assertEqual(result['outcome_ledger']['denominator_coverage'], 'NOT_ESTABLISHED')

    def test_manifest_contradiction_rejects_before_any_part_read(self):
        path, m = pack(self.root)
        m['part_count'] = True
        (self.root / path).write_bytes(canonical_bytes(m))
        a = RecordedAudit(self.root, NOW)
        with self.assertRaises(ValueError):
            self.read_transport(path, a=a)
        self.assertEqual(a.order, [path])

    def test_failed_raw_hash_still_charges_returned_decoded_bytes(self):
        path, m = pack(self.root)
        # The directory and manifest agree, but actual decoded raw does not.
        wrong = '0' * 64
        original = self.root / path
        destination = self.root / ANCHOR / wrong
        original.parent.rename(destination)
        path = (destination / 'manifest.json').relative_to(self.root).as_posix()
        m['raw_sha256'] = wrong
        (self.root / path).write_bytes(canonical_bytes(m))
        charge, state = self.consume(len(GPX) + 1)
        with self.assertRaises(ValueError):
            self.read_transport(path, charge=charge)
        self.assertEqual(state['produced'], len(GPX))
        with self.assertRaises(audit.AuditBudgetExceeded):
            self.read_transport(path, charge=charge)
        self.assertGreater(state['produced'], len(GPX))

    def test_membership_inserted_by_unrelated_late_stage_invalidates_whole_audit(self):
        path, _ = pack(self.root)
        original = audit._osm

        def insert(a):
            (self.root / path).parent.joinpath('part_999.b64').write_bytes(b'AAAA')
            return original(a)
        with patch.object(audit, '_osm', insert):
            result = audit.audit_evidence(self.root, NIGHT, verified_at=NOW)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['observation_units'], [])
        self.assertEqual(result['trajectory_audit'], [])

    def test_manifest_fields_types_hashes_and_declared_lengths_are_strict(self):
        path, original = pack(self.root)
        changes = [('extra', 1), ('kind', 'pdca_artifact'), ('compression', 'zip'),
                   ('transfer_encoding', 'base64url'), ('part_glob', '../*.b64'),
                   ('schema_version', 'other'), ('raw_sha256', 'A' * 64),
                   ('compressed_sha256', 1), ('source_ref', []), ('source', ''),
                   ('original_filename', 'a\0b'), ('encoded_chars', 1),
                   ('part_count', 4001), ('part_chars', 63)]
        changes += [(key, value) for key in ('raw_size_bytes', 'compressed_size_bytes',
                    'part_chars', 'encoded_chars', 'part_count') for value in (True, 0, -1, 1.0)]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                m = dict(original);m[key] = value
                (self.root / path).write_bytes(canonical_bytes(m))
                a = RecordedAudit(self.root, NOW)
                with self.assertRaises(ValueError):
                    self.read_transport(path, a=a)
                self.assertEqual(a.order, [path])

    def test_duplicate_json_keys_and_nonfinite_constants_reject_before_parts(self):
        path, m = pack(self.root)
        body = canonical_bytes(m)
        for raw in (b'{"kind":"gpx",' + body[1:], body.replace(b'"source_ref":null', b'"source_ref":NaN')):
            (self.root / path).write_bytes(raw)
            a = RecordedAudit(self.root, NOW)
            with self.assertRaises(ValueError):
                self.read_transport(path, a=a)
            self.assertEqual(a.order, [path])

    def test_escaped_surrogate_metadata_rejects_before_part_reads(self):
        path, m = pack(self.root)
        m['source'] = '\ud800'
        (self.root / path).write_bytes(json.dumps(m, ensure_ascii=True).encode('utf-8'))
        a = RecordedAudit(self.root, NOW)
        with self.assertRaises(self.helper().GpxAttachmentError):
            self.read_transport(path, a=a)
        self.assertEqual(a.order, [path])

    def test_overlong_json_integer_is_dedicated_format_error_before_parts(self):
        path, m = pack(self.root)
        raw = canonical_bytes(m).replace(
            ('"compressed_size_bytes":' + str(m['compressed_size_bytes'])).encode(),
            b'"compressed_size_bytes":' + b'9' * 5000)
        (self.root / path).write_bytes(raw)
        a = RecordedAudit(self.root, NOW)
        error = None
        try:
            self.read_transport(path, a=a)
        except ValueError as caught:
            error = caught
        self.assertIsInstance(error, self.helper().GpxAttachmentError)
        self.assertEqual(a.order, [path])

    def test_unsafe_paths_reject_before_metadata_or_payload(self):
        h = self.helper()
        for path in ('../manifest.json', '/manifest.json', 'reports/manifest.json',
                     ANCHOR + '/x/manifest.json', ANCHOR + '/' + '0' * 64 + '/manifest.json.',
                     ANCHOR + '/' + '0' * 64 + '/part_000.b64'):
            a = RecordedAudit(self.root, NOW)
            with self.subTest(path=path), patch.object(h, 'local_path', side_effect=AssertionError('metadata')):
                with self.assertRaises(h.GpxAttachmentError):
                    self.read_transport(path, a=a)
            self.assertEqual(a.order, [])

    def test_unexpected_member_rejects_before_manifest_payload(self):
        path, _ = pack(self.root)
        unexpected = (self.root / path).parent / 'notes.txt'
        unexpected.write_bytes(b'no hidden source')
        a = RecordedAudit(self.root, NOW)
        with self.assertRaises(ValueError):
            self.read_transport(path, a=a)
        self.assertEqual(a.order, [])

    def test_missing_or_extra_indexed_part_rejects_before_part_payload(self):
        path, _ = pack(self.root)
        extra = (self.root / path).parent / 'part_999.b64'
        extra.write_bytes(b'AAAA')
        a = RecordedAudit(self.root, NOW)
        with self.assertRaises(ValueError):
            self.read_transport(path, a=a)
        self.assertEqual(a.order, [path])
        extra.unlink()
        (self.root / path).parent.joinpath('part_000.b64').unlink()
        a = RecordedAudit(self.root, NOW)
        with self.assertRaises(ValueError):
            self.read_transport(path, a=a)
        self.assertEqual(a.order, [path])

    def test_wrong_part_length_or_invalid_base64_never_reaches_xml(self):
        path, _ = pack(self.root)
        part = (self.root / path).parent / 'part_000.b64'
        original = part.read_bytes()
        for changed in (original + b'A', original[:-1], b'!' + original[1:]):
            part.write_bytes(changed)
            with self.assertRaises(ValueError):
                self.read_transport(path)

    def test_premature_base64_padding_rejects_even_when_all_payload_hashes_match(self):
        raw = GPX
        compressed = lzma.compress(raw, preset=0)
        while len(compressed) % 3 == 0:
            raw += b' '
            compressed = lzma.compress(raw, preset=0)
        remainder = len(compressed) % 3
        parts = [base64.b64encode(compressed[:remainder])]
        parts += [base64.b64encode(compressed[i:i + 3])
                  for i in range(remainder, len(compressed), 3)]
        with self.assertRaises(ValueError):
            base64.b64decode(b''.join(parts), validate=True)
        path, m = pack(self.root, raw, compressed=compressed, part_chars=4)
        self.assertEqual(len(parts), m['part_count'])
        for i, chunk in enumerate(parts):
            (self.root / path).parent.joinpath(f'part_{i:03d}.b64').write_bytes(chunk)
        a = RecordedAudit(self.root, NOW)
        with self.assertRaises(self.helper().GpxAttachmentError):
            self.read_transport(path, a=a)
        self.assertEqual(len(a.order), 2)

    def test_trailing_and_concatenated_xz_are_not_silently_accepted(self):
        for suffix in (b'junk', lzma.compress(b'second stream', preset=0)):
            with self.subTest(suffix=suffix[:8]), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                path, _ = pack(root, compressed=lzma.compress(GPX, preset=0) + suffix)
                a = RecordedAudit(root, NOW)
                with self.assertRaises(self.helper().GpxAttachmentError):
                    self.helper().read_gpx_attachment_archive(root, path, read=a.read,
                        check=a.tick, consume_decoded_bytes=self.consume()[0])

    def test_bounded_output_overrun_charges_one_detected_excess_byte(self):
        path, m = pack(self.root)
        m['raw_size_bytes'] = 10
        (self.root / path).write_bytes(canonical_bytes(m))
        charge, state = self.consume()
        with self.assertRaises(ValueError):
            self.read_transport(path, charge=charge)
        self.assertEqual(state['produced'], 11)

    def test_actual_xz_memory_limit_is_runtime_blocked(self):
        path, _ = pack(self.root)
        with patch.object(self.helper(), 'XZ_MEMORY_LIMIT', 4096):
            result = audit.audit_evidence(self.root, NIGHT, verified_at=NOW)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['observation_units'], [])
        self.assertEqual(result['input_requirements'][-1]['kind'], 'RUNTIME_BLOCKED')

    def test_multiple_rejected_archives_share_one_audit_decoded_capacity(self):
        for character in ('0', '1'):
            path, m = pack(self.root)
            wrong = character * 64
            source = self.root / path
            destination = self.root / ANCHOR / wrong
            source.parent.rename(destination)
            m['raw_sha256'] = wrong
            destination.joinpath('manifest.json').write_bytes(canonical_bytes(m))
        with patch.object(self.helper(), 'MAX_DECODED_BYTES', len(GPX) + 1):
            result = audit.audit_evidence(self.root, NIGHT, verified_at=NOW)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['observation_units'], [])
        self.assertEqual(result['input_requirements'][-1]['kind'], 'RUNTIME_BLOCKED')

    def test_discovery_and_parsed_point_caps_are_runtime_blocked(self):
        pack(self.root)
        with patch.object(self.helper(), 'MAX_DISCOVERY_ENTRIES', 1):
            result = audit.audit_evidence(self.root, NIGHT, verified_at=NOW)
        self.assertEqual(result['status'], 'BLOCKED')
        with patch.object(audit, 'MAX_POINTS', 1):
            result = audit.audit_evidence(self.root, NIGHT, verified_at=NOW)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['trajectory_audit'], [])

    def test_read_and_total_byte_caps_use_same_actual_reader(self):
        pack(self.root)
        for name, value in (('MAX_READS', 1), ('MAX_READ_BYTES', 20)):
            with self.subTest(name=name), patch.object(audit, name, value):
                result = audit.audit_evidence(self.root, NIGHT, verified_at=NOW)
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertEqual(result['observation_units'], [])

    def test_caller_check_and_reader_and_charge_exceptions_preserve_identity(self):
        path, _ = pack(self.root)
        for error in (ValueError('caller'), OSError('caller'), TypeError('caller'),
                      TimeoutError('caller'), MemoryError('caller')):
            for operation in ('check', 'read', 'charge'):
                with self.subTest(error=type(error).__name__, operation=operation):
                    a = RecordedAudit(self.root, NOW)
                    def fail(*args, **kwargs):
                        raise error
                    try:
                        self.helper().read_gpx_attachment_archive(self.root, path,
                            read=fail if operation == 'read' else a.read,
                            check=fail if operation == 'check' else a.tick,
                            consume_decoded_bytes=fail if operation == 'charge' else self.consume()[0])
                    except BaseException as caught:
                        self.assertIs(caught, error)
                    else:
                        self.fail('caller exception was swallowed')

    def test_same_raw_aliases_do_not_double_points_or_effort(self):
        path, _ = pack(self.root)
        direct = self.root / 'data/raw/gpx/direct.gpx'
        direct.parent.mkdir(parents=True)
        direct.write_bytes(GPX)
        result = audit.audit_evidence(self.root, NIGHT, verified_at=NOW)
        self.assertEqual(len(result['trajectory_audit']), 1)
        self.assertEqual(result['sampled_coverage'], {NIGHT: 2})
        self.assertTrue(any(c['check'] == 'duplicate_gpx' for c in result['checks']))
        self.assertTrue(any(s['path'] == path and 'attachment_archive' in s for s in result['source_manifest']))

    def test_full_audit_rereads_each_member_and_counts_actual_bytes(self):
        path, m = pack(self.root)
        instances = []
        class Captured(RecordedAudit):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs);instances.append(self)
        with patch.object(audit, 'Audit', Captured):
            result = audit.audit_evidence(self.root, NIGHT, verified_at=NOW)
        a = instances[0]
        count = 1 + m['part_count']
        self.assertEqual(a.reads, 2 * count)
        self.assertEqual(a.order[:count], a.order[count:])
        self.assertEqual(a.read_bytes, sum((self.root / p).stat().st_size for p in a.order))
        self.assertEqual(result['input_hashes'], a.consumed)

    def test_late_payload_change_clears_all_trajectory_output(self):
        path, _ = pack(self.root)
        original = audit._osm
        def mutate(a):
            part = (self.root / path).parent / 'part_000.b64'
            old = part.read_bytes();part.write_bytes(b'A' + old[1:])
            return original(a)
        with patch.object(audit, '_osm', mutate):
            result = audit.audit_evidence(self.root, NIGHT, verified_at=NOW)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['trajectory_audit'], [])
        self.assertEqual(result['observation_units'], [])

    def test_shared_expiry_after_parsing_prevents_final_result(self):
        pack(self.root)
        original = audit._osm
        def expire(a):
            result = original(a)
            a.deadline = 0
            return result
        with patch.object(audit, '_osm', expire):
            result = audit.audit_evidence(self.root, NIGHT, verified_at=NOW)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['trajectory_audit'], [])
        self.assertEqual(result['observation_units'], [])

    def test_membership_change_after_actual_gpx_parse_prevents_returned_rows(self):
        path, _ = pack(self.root)
        original = audit._gpx
        def mutate(*args, **kwargs):
            result = original(*args, **kwargs)
            (self.root / path).parent.joinpath('part_999.b64').write_bytes(b'AAAA')
            return result
        with patch.object(audit, '_gpx', mutate):
            result = audit.audit_evidence(self.root, NIGHT, verified_at=NOW)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['trajectory_audit'], [])
        self.assertEqual(result['observation_units'], [])

    def test_membership_insertion_during_final_reads_is_detected(self):
        path, _ = pack(self.root)
        root = self.root
        class Mutate(RecordedAudit):
            def read(self, relative, *, max_bytes=None):
                raw = super().read(relative, max_bytes=max_bytes)
                if relative == path and self.order.count(relative) == 2:
                    (root / path).parent.joinpath('part_999.b64').write_bytes(b'AAAA')
                return raw
        with patch.object(audit, 'Audit', Mutate):
            result = audit.audit_evidence(self.root, NIGHT, verified_at=NOW)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['observation_units'], [])

    def test_new_archive_inserted_after_absent_discovery_is_detected(self):
        original = audit._osm
        def insert(a):
            pack(self.root)
            return original(a)
        with patch.object(audit, '_osm', insert):
            result = audit.audit_evidence(self.root, NIGHT, verified_at=NOW)
        self.assertEqual(result['status'], 'FAIL')

    def test_generated_report_archive_is_never_discovered(self):
        directory = self.root / 'data/raw/attachment_archives/pdca_artifact/x'
        directory.mkdir(parents=True)
        directory.joinpath('manifest.json').write_bytes(b'not a GPX manifest')
        result = audit.audit_evidence(self.root, NIGHT, verified_at=NOW)
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['input_hashes'], {})
        self.assertEqual(result['trajectory_audit'], [])

    @unittest.skipUnless(sys.platform == 'win32', 'actual Windows junction')
    def test_windows_junction_rejects_before_external_scan_or_open(self):
        self.helper()
        with tempfile.TemporaryDirectory() as d:
            external = Path(d)
            pack(external)
            link = self.root / ANCHOR
            link.parent.mkdir(parents=True)
            target = external / ANCHOR
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            a = RecordedAudit(self.root, NOW)
            original_scan = os.scandir
            external_scans = []
            def scan(path):
                if Path(path).resolve().is_relative_to(external):
                    external_scans.append(str(path))
                return original_scan(path)
            try:
                with patch.object(os, 'scandir', scan), self.assertRaises(ValueError):
                    self.helper().discover_gpx_attachment_archives(self.root, check=a.tick)
                self.assertEqual(external_scans, [])
                self.assertEqual(a.order, [])
            finally:
                os.rmdir(link)

    @unittest.skipIf(sys.platform == 'win32', 'actual POSIX symlink; native junction above')
    def test_posix_source_symlink_rejects_before_external_reads(self):
        self.helper()
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            link = self.root / ANCHOR
            link.parent.mkdir(parents=True)
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(ValueError):
                self.helper().discover_gpx_attachment_archives(self.root, check=lambda: None)


if __name__ == '__main__':
    unittest.main()
