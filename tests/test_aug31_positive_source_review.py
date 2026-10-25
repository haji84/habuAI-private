"""Native source occurrences, not permanent animals or production authority."""
from copy import deepcopy
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
import evidence_audit as audit
from master_contracts import canonical_bytes, digest
from master_inventory import local_path

NATIVE = 'evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt'
CAPTURE = 'data/processed/capture_events/2026/2026-08-31.csv'
INDIVIDUALS = 'data/processed/individuals/2026/2026-08-31.csv'
REVIEW = 'evidence/source_reviews/2026-08-31-positive-source-review.json'
PROFILE = 'aug31-owner-capture-occurrence-crosswalk-v1'
NOW = '2026-10-25T16:00:00+00:00'
SOURCE_PATHS = {
    'native_log': NATIVE,
    'native_byte_proof': 'evidence/recovered_sources/2026-08-native-original-library-byte-proof.json',
    'gpx': 'data/raw/gpx/2026-08-31__legacy.gpx',
    'owner_count_record': 'data/reconstructions/habu_captures/2026-08-count-correction-owner-confirmed-47.json',
    'captures': CAPTURE, 'individuals': INDIVIDUALS,
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def native(path):
    return subprocess.check_output(['git', 'show', 'HEAD:' + path], cwd=ROOT)


def write(root, path, raw):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)


def csv_bytes(fields, rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writeheader();writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def derived_tables(raw):
    lines = raw.decode('utf-8').splitlines()
    events = [];individuals = []
    for start, clock, place in [(10110, '2026-08-31T21:43:00+09:00', ''),
                                 (10492, '2026-09-01T01:17:00+09:00', lines[10497])]:
        body = lines[start - 1:]
        numbers = [v for v in body[:10] if __import__('re').fullmatch(r'\d+\.\d+', v)]
        key = 'AUG31SRC-L' + str(start)
        events.append(dict(event_id=key, operational_date='2026-08-31', event_time_local=clock,
            event_place=place, event_type='capture', event_count=1, latitude=numbers[0],
            longitude=numbers[1], surface=body[5], source_note=body[2]))
        individuals.append(dict(individual_id=key + '-OCC01', event_id=key, individual_index=1,
            operational_date='2026-08-31', event_time_local=clock, event_place=place,
            size_note='100~120', sex='オス', behavior=body[3], microhabitat=body[4]))
    return (csv_bytes(['event_id','operational_date','event_time_local','event_place','event_type',
                       'event_count','latitude','longitude','surface','source_note'], events),
            csv_bytes(['individual_id','event_id','individual_index','operational_date','event_time_local',
                       'event_place','size_note','sex','behavior','microhabitat'], individuals))


def snapshot(root):
    for role, path in SOURCE_PATHS.items():
        if role not in {'captures', 'individuals'}:
            write(root, path, native(path))
    captures, individuals = derived_tables((root / NATIVE).read_bytes())
    for path, expected in ((CAPTURE, captures), (INDIVIDUALS, individuals)):
        tracked = subprocess.run(['git', 'cat-file', '-e', 'HEAD:' + path], cwd=ROOT,
                                 capture_output=True).returncode == 0
        # Explicit pre-commit fallback; committed runs always read native Git blobs.
        raw = native(path) if tracked else (ROOT / path).read_bytes()
        if raw != expected:raise AssertionError('Derived CSV differs from exact original-source projection')
        write(root, path, raw)


def reference(root, path):
    raw = (root / path).read_bytes()
    return dict(path=path, sha256=sha(raw), size_bytes=len(raw))


def provisional_review(root, now=NOW, proof=None):
    """Private test review only; never writes a repository registration."""
    import aug31_positive_source_review as module
    refs = {k: reference(root, v) for k, v in SOURCE_PATHS.items()}
    if proof is None:
        a = audit.Audit(root, now)
        def point():
            a.points += 1;a.tick()
        proof = module.reproduce_sources(refs, read_ref=a.ref, tick=a.tick, consume_point=point)
    return dict(schema_version='1.0', verification_profile=PROFILE,
        source_sha256=refs['captures']['sha256'], use_roles=['outcome_label'],
        reviewed_at=now, cohort_exposure='RESEARCH_EXPOSED', scope=module.SCOPE,
        independent_device_authentication='NOT_ESTABLISHED',
        permanent_biological_identity='NOT_ESTABLISHED', coordinate_method=module.COORDINATE_METHOD,
        recovery_class=module.RECOVERY_CLASS, source_refs=refs, proof=deepcopy(proof),
        proof_sha256=digest(proof), **{key: False for key in module.FORBIDDEN_AUTHORITY})


class Aug31SourceReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);snapshot(root)
            cls.valid_review = provisional_review(root)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        snapshot(self.root)

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('aug31_positive_source_review'),
                             'The bounded Aug31 verifier is not implemented')
        return __import__('aug31_positive_source_review')

    def verify(self, review=None, a=None, read_ref=None, tick=None):
        a = a or audit.Audit(self.root, NOW)
        def point():
            a.points += 1;a.tick()
        return self.module().verify_review(deepcopy(self.valid_review) if review is None else review,
            read_ref=a.ref if read_ref is None else read_ref, tick=a.tick if tick is None else tick,
            consume_point=point, now=NOW)

    def policy(self, review=None):
        write(self.root, REVIEW, canonical_bytes(self.valid_review if review is None else review))
        entry = dict(reference(self.root, CAPTURE), review_ref=reference(self.root, REVIEW))
        write(self.root, 'policies/observation_evidence.json', canonical_bytes(dict(
            schema_version='1.0', sources=[entry], sessions=[], outcome_coverage=[])))
        return entry

    def assert_unqualified(self, result):
        self.assertIn(result['status'], ('FAIL', 'BLOCKED'))
        self.assertEqual(result['observation_units'], [])
        self.assertEqual(result['outcome_ledger']['events'], [])

    def declare(self, reviews):
        entries = []
        for index, review in enumerate(reviews):
            path = (REVIEW if review.get('verification_profile') == PROFILE
                    else REVIEW.replace('.json', '-bad-%s.json' % index))
            write(self.root, path, canonical_bytes(review))
            entries.append(dict(reference(self.root, CAPTURE), review_ref=reference(self.root, path)))
        # Invalid declarations also use a disallowed review path. Neither order
        # may retain the qualification from the independently valid declaration.
        write(self.root, 'policies/observation_evidence.json', canonical_bytes(dict(
            schema_version='1.0', sources=entries, sessions=[], outcome_coverage=[])))
        a = audit.Audit(self.root, NOW);audit._declarations(a)
        return a

    def test_duplicate_new_source_declarations_never_keep_partial_qualification(self):
        good = deepcopy(self.valid_review)
        for bad_kind in ('missing', 'unknown'):
            bad = deepcopy(good)
            if bad_kind == 'missing':bad.pop('verification_profile')
            else:bad['verification_profile'] = 'unrecognized-profile'
            for reviews in ([good, bad], [bad, good]):
                with self.subTest(kind=bad_kind, good_first=reviews[0] is good):
                    a = self.declare(reviews)
                    self.assertNotIn('outcome_label', a.sources.get(CAPTURE, {}).get('use_roles', []))

    def test_duplicate_aug31_rejection_keeps_valid_sept28_declaration(self):
        import test_sept28_positive_source_review as sept
        sept.snapshot(self.root)
        sept_entry = next(entry for entry in json.loads(native('policies/observation_evidence.json'))['sources']
                          if entry['path'] == sept.CAPTURE)
        good = deepcopy(self.valid_review);bad = deepcopy(good);bad.pop('verification_profile')
        for reviews in ([good, bad], [bad, good], [good, good]):
            self.declare(reviews)
            policy_path = self.root / 'policies/observation_evidence.json'
            policy = json.loads(policy_path.read_bytes());policy['sources'].insert(1, sept_entry)
            policy_path.write_bytes(canonical_bytes(policy))
            a = audit.Audit(self.root, NOW);audit._declarations(a)
            self.assertNotIn('outcome_label', a.sources.get(CAPTURE, {}).get('use_roles', []))
            self.assertEqual(a.sources[sept.CAPTURE]['use_roles'], ['outcome_label'])
            self.assertEqual(a.points, 22990)

    def test_new_fixed_source_alias_cannot_downgrade_or_duplicate_admission(self):
        spellings = (CAPTURE.replace('capture_events', 'CAPTURE_EVENTS'),
                     CAPTURE.removesuffix('.csv') + '.CSV', CAPTURE.replace('/', '\\'),
                     CAPTURE.replace('/2026/', '/2026/./'))
        for spelling in spellings:
            bad = deepcopy(self.valid_review);bad.pop('verification_profile')
            self.policy(bad)
            policy_path = self.root/'policies/observation_evidence.json'
            policy = json.loads(policy_path.read_bytes());policy['sources'][0]['path'] = spelling
            policy_path.write_bytes(canonical_bytes(policy))
            a = audit.Audit(self.root, NOW);audit._declarations(a)
            self.assertFalse(any('outcome_label' in s['use_roles'] for s in a.sources.values()))
            good_entry = self.policy()
            bad_review_path = REVIEW.replace('.json', '-alias-bad.json')
            write(self.root, bad_review_path, canonical_bytes(bad))
            bad_entry = dict(reference(self.root, CAPTURE), path=spelling,
                             review_ref=reference(self.root, bad_review_path))
            for entries in ([good_entry, bad_entry], [bad_entry, good_entry]):
                with self.subTest(spelling=spelling, good_first=entries[0] is good_entry):
                    policy['sources'] = entries;policy_path.write_bytes(canonical_bytes(policy))
                    a = audit.Audit(self.root, NOW);audit._declarations(a)
                    self.assertFalse(any('outcome_label' in s['use_roles'] for s in a.sources.values()))

    def test_real_directory_links_reject_before_csv_review_or_gpx_payload_open(self):
        cases = [(str(Path(p).parent), False) for p in (CAPTURE, REVIEW, SOURCE_PATHS['gpx'])]
        cases.append((str(Path(CAPTURE).parent), True))
        for anchor, missing_profile in cases:
            review = deepcopy(self.valid_review)
            if missing_profile:review.pop('verification_profile')
            self.policy(review)
            with self.subTest(anchor=anchor, missing_profile=missing_profile), tempfile.TemporaryDirectory(prefix='aug31-outside-') as temporary:
                link = self.root / anchor;outside = Path(temporary) / 'payload'
                self.assertTrue(link.absolute().is_relative_to(self.root.absolute()))
                self.assertTrue(outside.absolute().is_relative_to(Path(temporary).absolute()))
                link.rename(outside)
                try:
                    if os.name == 'nt':
                        subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(outside)], check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                        self.assertTrue(link.is_junction());self.assertFalse(link.is_symlink())
                    else:link.symlink_to(outside, target_is_directory=True)
                    opened = [];native_open = Path.open
                    def observe(path, *args, **kwargs):
                        if path.is_relative_to(link) or path.is_relative_to(outside):opened.append(path)
                        return native_open(path, *args, **kwargs)
                    with patch.object(Path, 'open', observe):
                        a = audit.Audit(self.root, NOW);audit._declarations(a)
                    self.assertEqual(opened, [])
                    self.assertNotIn('outcome_label', a.sources.get(CAPTURE, {}).get('use_roles', []))
                    self.assertTrue(any(c['status'] == 'FAIL' for c in a.checks))
                finally:
                    if os.name == 'nt' and link.is_junction():os.rmdir(link)
                    elif link.is_symlink():link.unlink()
                    outside.rename(link)

    def test_actual_two_occurrences_verifier_api_exists(self):
        module = self.module()
        a = audit.Audit(self.root, NOW)
        refs = {k: reference(self.root, v) for k, v in SOURCE_PATHS.items()}
        def point():
            a.points += 1;a.tick()
        proof = module.reproduce_sources(refs, read_ref=a.ref, tick=a.tick, consume_point=point)
        self.assertEqual((proof['event_count'], proof['individual_occurrence_count']), (2, 2))
        self.assertFalse(proof['permanent_biological_identity_verified'])
        self.assertEqual(a.points, 17906)

    def test_fixed_new_csv_cannot_downgrade_to_legacy_outcome_flag(self):
        ref = reference(self.root, CAPTURE)
        row = dict(schema_version='1.0', source_sha256=ref['sha256'], use_roles=['outcome_label'],
                   reviewed_at=NOW, coordinate_method='original owner TXT coordinates')
        write(self.root, REVIEW, canonical_bytes(row))
        entry = dict(ref, review_ref=reference(self.root, REVIEW))
        write(self.root, 'policies/observation_evidence.json', canonical_bytes(dict(
            schema_version='1.0', sources=[entry], sessions=[], outcome_coverage=[])))
        a = audit.Audit(self.root, NOW)
        audit._declarations(a)
        self.assertNotIn('outcome_label', a.sources[CAPTURE]['use_roles'])
        self.assertTrue(any(c['check']=='source_declaration' and c['status']=='FAIL' for c in a.checks))

    def test_private_review_admits_only_two_current_source_occurrences(self):
        self.policy();a = audit.Audit(self.root, NOW);audit._declarations(a)
        source = a.sources[CAPTURE]
        self.assertEqual(source['use_roles'], ['outcome_label'])
        self.assertEqual(a.points, 17906)
        self.assertEqual(audit.timestamp(source['available_at']), audit.timestamp(NOW))
        self.assertTrue(any(r['code'] == 'RECEIPT' for r in a.requirements))
        result = audit.audit_evidence(self.root, '2026-08-31', verified_at=NOW)
        self.assertEqual(len(result['outcome_ledger']['events']), 2)
        self.assertEqual(sum(e['capture_count'] for e in result['outcome_ledger']['events']), 2)
        self.assertEqual(sum(u['label'] == 1 for u in result['observation_units']), 2)
        self.assertFalse(any(u['label'] == 0 for u in result['observation_units']))
        self.assertEqual(result['outcome_ledger']['denominator_coverage'], 'NOT_ESTABLISHED')
        self.assertEqual(result['scientific_validation'], 'NOT_VALIDATED')

    def test_derived_csv_without_registration_is_diagnostic_only(self):
        result = audit.audit_evidence(self.root, '2026-08-31', verified_at=NOW)
        self.assertEqual(result['outcome_ledger']['events'], [])
        self.assertFalse(any(u['label'] is not None for u in result['observation_units']))

    def test_actual_selectors_sizes_hashes_qc_and_occurrence_semantics(self):
        proof = self.valid_review['proof'];module = self.module()
        raw = (self.root / NATIVE).read_bytes()
        for row, expected in zip(proof['crosswalk'], module.EXPECTED):
            self.assertEqual(sha(raw[row['source_byte_start']:row['source_byte_end_exclusive']]), expected[5])
            self.assertEqual(row['count'], 1)
            self.assertEqual(row['individual_occurrence_id'], row['event_id'] + '-OCC01')
            self.assertEqual(row['neighboring_gap_seconds'], [1.0, 1.0])
            self.assertLessEqual(row['hdop'], 10)
        self.assertEqual(proof['gpx_qc'], dict(point_count=17906, excluded_points=0,
            segment_breaks=1, maximum_gap_seconds=50.826))
        self.assertEqual([x['source_line_start'] for x in proof['crosswalk']], [10110, 10492])
        self.assertFalse(proof['permanent_biological_identity_verified'])
        self.assertTrue(all(proof[key] is False for key in module.FORBIDDEN_AUTHORITY))

    def test_every_fixed_source_tamper_and_rehashed_ref_reject(self):
        for role, path in SOURCE_PATHS.items():
            original = (self.root / path).read_bytes()
            write(self.root, path, original + b'\n')
            with self.subTest(role=role), self.assertRaises(ValueError):self.verify()
            review = deepcopy(self.valid_review)
            review['source_refs'][role] = reference(self.root, path)
            with self.subTest(rehashed=role), self.assertRaises(ValueError):self.verify(review)
            write(self.root, path, original)

    def test_closed_reference_types_and_expected_sizes_reject_before_read(self):
        for value in (None, True, [], 1, {}, dict(path=CAPTURE, sha256='0'*64, size_bytes=413)):
            review = deepcopy(self.valid_review);review['source_refs']['captures'] = value
            paths = []
            def read(ref):paths.append(ref['path']);return (self.root/ref['path']).read_bytes()
            with self.subTest(value=value), self.assertRaises(ValueError):self.verify(review, read_ref=read)
            self.assertNotIn(CAPTURE, paths)
        for size in (True, -1, 0, 414, 2**100):
            review = deepcopy(self.valid_review);review['source_refs']['native_log']['size_bytes'] = size
            with self.subTest(size=size), self.assertRaises(ValueError):self.verify(review)

    def test_typed_rehashed_proof_numbers_cannot_equal_actual_proof(self):
        for key, value in [('count', True), ('csv_row', 2.0), ('source_line_start', 5249)]:
            review = deepcopy(self.valid_review);review['proof']['crosswalk'][0][key] = value
            review['proof_sha256'] = digest(review['proof'])
            with self.subTest(key=key), self.assertRaises(ValueError):self.verify(review)

    def test_authority_scope_availability_and_profile_are_closed(self):
        changes = [(key, True) for key in self.module().FORBIDDEN_AUTHORITY] + [
            ('independent_device_authentication', 'ESTABLISHED'),
            ('permanent_biological_identity', 'ESTABLISHED'), ('scope', 'ALL_AUGUST'),
            ('cohort_exposure', 'UNTOUCHED'), ('reviewed_at', '2026-08-31T18:00:00+09:00'),
            ('reviewed_at', '2027-01-01T00:00:00+00:00'), ('verification_profile', 'unknown'),
            ('use_roles', ['outcome_label', 'observed_exposure'])]
        for key, value in changes:
            review = deepcopy(self.valid_review);review[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):self.verify(review)

    def test_review_json_duplicates_and_nonfinite_cannot_grant_role(self):
        for addition in (b'"scope":"ALL_AUGUST",', b'"x":{"nested":1e999},'):
            raw = canonical_bytes(self.valid_review)
            write(self.root, REVIEW, b'{' + addition + raw[1:])
            entry = dict(reference(self.root, CAPTURE), review_ref=reference(self.root, REVIEW))
            write(self.root, 'policies/observation_evidence.json', canonical_bytes(dict(
                schema_version='1.0', sources=[entry], sessions=[], outcome_coverage=[])))
            a = audit.Audit(self.root, NOW);audit._declarations(a)
            self.assertNotIn('outcome_label', a.sources[CAPTURE]['use_roles'])
            self.assertTrue(any(c['status'] == 'FAIL' for c in a.checks))

    def test_internal_crosswalk_rejects_duplicates_orphans_extra_rows_and_wrong_source_fields(self):
        # Internal semantic seam only. The public verifier first checks every fixed SHA.
        base = {key: (self.root/path).read_bytes() for key, path in SOURCE_PATHS.items()}
        for kind in ('duplicate', 'orphan', 'extra', 'count', 'night', 'coordinate', 'attributes', 'index'):
            payloads = dict(base)
            role = 'individuals' if kind in ('orphan', 'index') else 'captures'
            reader = csv.DictReader(io.StringIO(payloads[role].decode('utf-8')))
            rows = list(reader)
            if kind == 'duplicate':rows[1]['event_id'] = rows[0]['event_id']
            elif kind == 'orphan':rows[0]['event_id'] = 'UNBOUND'
            elif kind == 'extra':rows.append(dict(rows[0]))
            elif kind == 'count':rows[0]['event_count'] = '2'
            elif kind == 'night':rows[0]['operational_date'] = '2026-08-19'
            elif kind == 'coordinate':rows[0]['latitude'] = rows[1]['latitude']
            elif kind == 'attributes':rows[0]['source_note'] = '反応'
            elif kind == 'index':rows[0]['individual_index'] = '2'
            payloads[role] = csv_bytes(reader.fieldnames, rows)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.module()._cross_bind(payloads, tick=lambda: None, consume_point=lambda: None)

    def test_source_rescan_detects_late_mutation(self):
        a = audit.Audit(self.root, NOW);calls = []
        def read(ref):
            raw = a.ref(ref);calls.append(ref['path'])
            if len(calls) == 6:
                write(self.root, NATIVE, (self.root/NATIVE).read_bytes() + b'\n')
            return raw
        with self.assertRaises(ValueError):self.verify(a=a, read_ref=read)
        self.assertEqual(len(calls), 6)

    def test_shared_point_read_and_deadline_budgets_are_not_reset(self):
        for resource in ('point', 'read', 'time'):
            a = audit.Audit(self.root, NOW)
            if resource == 'point':a.points = audit.MAX_POINTS
            elif resource == 'read':a.read_bytes = audit.MAX_READ_BYTES - 1
            else:a.deadline = 0
            with self.subTest(resource=resource), self.assertRaises(audit.AuditBudgetExceeded):self.verify(a=a)

    def test_caller_checks_keep_exact_exception_identity(self):
        for error in (ValueError('caller'), TimeoutError('caller'),
                      audit.AuditBudgetExceeded('caller'), MemoryError('caller')):
            for at in (1, 20, 1000):
                calls = 0
                def check():
                    nonlocal calls
                    calls += 1
                    if calls == at:raise error
                with self.subTest(kind=type(error), at=at), self.assertRaises(type(error)) as caught:
                    self.verify(tick=check)
                self.assertIs(caught.exception, error)

    def test_review_is_owned_before_reader_can_mutate_callers_object(self):
        review = deepcopy(self.valid_review);a = audit.Audit(self.root, NOW)
        def read(ref):
            review['proof']['crosswalk'][0]['count'] = 999
            return a.ref(ref)
        result = self.verify(review, a=a, read_ref=read)
        self.assertEqual(result['crosswalk'][0]['count'], 1)
        self.assertEqual(review['proof']['crosswalk'][0]['count'], 999)

    def test_owned_gpx_size_entity_and_point_count_are_not_optional(self):
        module = self.module();raw = (self.root/SOURCE_PATHS['gpx']).read_bytes()
        for value in (raw+b' ', b'<!ENTITY'+raw[8:], raw.replace(b'trkpt', b'badpt')):
            with self.subTest(size=len(value)), self.assertRaises(ValueError):
                module._points(value, lambda: None, lambda: None)

    def test_parent_late_source_mutation_clears_public_qualified_units(self):
        self.policy();original = audit._osm
        def mutate(a):
            result = original(a)
            write(self.root, NATIVE, (self.root/NATIVE).read_bytes() + b'\n')
            return result
        with patch.object(audit, '_osm', mutate):
            result = audit.audit_evidence(self.root, '2026-08-31', verified_at=NOW)
        self.assert_unqualified(result)

    def test_late_review_mutation_prevents_role_update(self):
        self.policy();a = audit.Audit(self.root, NOW);actual = a.ref
        def read(ref):
            raw = actual(ref)
            if ref['path'] == INDIVIDUALS:
                write(self.root, REVIEW, (self.root/REVIEW).read_bytes() + b' ')
            return raw
        with patch.object(a, 'ref', read):audit._declarations(a)
        self.assertNotIn('outcome_label', a.sources[CAPTURE]['use_roles'])
        self.assertTrue(any(c['status'] == 'FAIL' for c in a.checks))

    def test_parent_shared_budget_expiry_has_runtime_classification(self):
        self.policy()
        result = audit.audit_evidence(self.root, '2026-08-31', verified_at=NOW, budget_seconds=0)
        self.assert_unqualified(result)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertTrue(any(r.get('kind') == 'RUNTIME_BLOCKED' for r in result['input_requirements']))

    def test_parent_success_seal_expiry_clears_public_qualified_units(self):
        self.policy();instances = [];original = audit.Audit;native_digest = audit.digest
        class Record(original):
            def __init__(self, *args, **kwargs):super().__init__(*args, **kwargs);instances.append(self)
        def expire(value):
            result = native_digest(value)
            if isinstance(value, dict) and value.get('observation_units'):
                instances[-1].deadline = 0
            return result
        with patch.object(audit, 'Audit', Record), patch.object(audit, 'digest', expire):
            result = audit.audit_evidence(self.root, '2026-08-31', verified_at=NOW)
        self.assert_unqualified(result);self.assertEqual(result['status'], 'BLOCKED')


class ReviewKeyAdmissionTests(unittest.TestCase):
    def test_oversized_review_keys_reject_before_json_encoding_or_source_reads(self):
        import aug31_positive_source_review as module
        key = 'k' * (128 * 1024 + 1)
        original = module.json.JSONEncoder.iterencode
        for review in ({key: None}, {'proof': {key: None}}, {'proof': [{key: None}]}):
            encoded = []
            reads = []
            def encode(encoder, value, *args, **kwargs):
                encoded.append(True)
                return original(encoder, value, *args, **kwargs)
            def read(ref):
                reads.append(ref)
                raise AssertionError('Oversized review must not read a source')
            with self.subTest(nested='proof' in review):
                with patch.object(module.json.JSONEncoder, 'iterencode', encode):
                    with self.assertRaisesRegex(ValueError, 'AUG31_REVIEW_SIZE'):
                        module.verify_review(review, read_ref=read, tick=lambda: None,
                                             consume_point=lambda: None, now=NOW)
                self.assertEqual(encoded, [])
                self.assertEqual(reads, [])


if __name__ == '__main__':
    unittest.main()
