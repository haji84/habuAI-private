"""Closed Aug24 source occurrences; no biological, denominator or TRAIN claim."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
import august_positive_source_review as family
import evidence_audit as audit
from master_contracts import canonical_bytes, digest
from test_aug31_positive_source_review import native, reference, write

STEM = '2026-08-24-batch-v1'
ADMISSION = 'evidence/source_reviews/august-2026/admissions/' + STEM + '.json'
CAPTURE = 'data/processed/capture_events/source_reviews/august-2026/' + STEM + '.csv'
INDIVIDUALS = 'data/processed/individuals/source_reviews/august-2026/' + STEM + '.csv'
REVIEW = 'evidence/source_reviews/august-2026/' + STEM + '.json'
NOW = '2026-10-25T21:40:06.240193+00:00'
IDS = ['AUG2026SRC-L6791', 'AUG2026SRC-L7201', 'AUG2026SRC-L7351']


def source_bytes(path):
    # New, not-yet-committed owned artifacts have an explicit authoring fallback.
    import subprocess
    result = subprocess.run(['git', 'show', 'HEAD:' + path], cwd=ROOT, capture_output=True)
    return result.stdout if result.returncode == 0 else (ROOT / path).read_bytes()


def fixture(root):
    desc = json.loads(source_bytes(ADMISSION))
    for key in ('primary_ref', 'native_byte_proof_ref', 'owner_context_ref',
                'gpx_ref', 'captures_ref', 'occurrences_ref'):
        path = desc[key]['path']
        write(root, path, source_bytes(path))
    write(root, ADMISSION, source_bytes(ADMISSION))
    for path, *_ in family.ADMITTED:
        write(root, path, source_bytes(path))
    return desc


def reproduce(root, context=None):
    a = context or audit.Audit(root, NOW)
    def point():
        a.points += 1
        a.tick()
    proof = family.reproduce_sources(reference(root, ADMISSION), read_ref=a.ref,
                                     tick=a.tick, consume_point=point)
    return proof, a


def provisional(root):
    proof, _ = reproduce(root)
    return dict(schema_version='1.0', verification_profile=family.PROFILE,
        source_sha256=reference(root, CAPTURE)['sha256'], use_roles=['outcome_label'],
        reviewed_at=NOW, cohort_exposure='RESEARCH_EXPOSED', scope=family.SCOPE,
        independent_device_authentication='NOT_ESTABLISHED', permanent_biological_identity='NOT_ESTABLISHED',
        coordinate_method=family.COORDINATE_METHOD, recovery_class=family.RECOVERY_CLASS,
        source_refs=family._refs(json.loads((root / ADMISSION).read_bytes())),
        descriptor_ref=reference(root, ADMISSION), proof=proof, proof_sha256=digest(proof),
        **{k: False for k in family.FORBIDDEN_AUTHORITY})


def directory_aliases():
    for base in (CAPTURE, INDIVIDUALS):
        parts = base.split('/')
        for index in range(len(parts) - 1):
            for suffix in ('.', ' '):
                modified = parts.copy(); modified[index] += suffix
                alias = '/'.join(modified)
                yield from (alias, alias.upper(), alias.replace('/', '\\'))


class Aug24BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'workspace'
        self.root.mkdir()
        self.desc = fixture(self.root)

    def test_actual_closed_three_records_share_one_real_track(self):
        proof, context = reproduce(self.root)
        self.assertEqual(proof['event_count'], 3)
        self.assertEqual(proof['individual_occurrence_count'], 3)
        self.assertEqual([r['event_id'] for r in proof['crosswalk']], IDS)
        self.assertEqual(context.points, 21246)
        self.assertEqual(proof['gpx_qc'], self.desc['expected_gpx_qc']['track'])
        for row, expected in zip(proof['crosswalk'], self.desc['expected_gpx_qc']['selected_points']):
            self.assertEqual(canonical_bytes({k: row[k] for k in expected}), canonical_bytes(expected))
        self.assertIs(proof['permanent_biological_identity_verified'], False)
        self.assertTrue(all(proof[k] is False for k in family.FORBIDDEN_AUTHORITY))

    def declare(self, entries):
        write(self.root, 'policies/observation_evidence.json', canonical_bytes(dict(
            schema_version='1.0', sources=entries, sessions=[], outcome_coverage=[])))
        context = audit.Audit(self.root, NOW)
        audit._declarations(context)
        return context

    def entry(self, review=None):
        write(self.root, REVIEW, canonical_bytes(review or provisional(self.root)))
        return dict(reference(self.root, CAPTURE), review_ref=reference(self.root, REVIEW))

    def original_entry(self):
        import test_august_positive_source_review as old
        old.fixture(self.root)
        write(self.root, old.REVIEW, native(old.REVIEW))
        return dict(reference(self.root, old.CAPTURE), review_ref=reference(self.root, old.REVIEW))

    def assert_no_family_roles(self, context):
        for path, _, _, capture, *_ in family.ADMITTED:
            self.assertNotIn('outcome_label', context.sources.get(capture, {}).get('use_roles', []))
        self.assertTrue(any(c['status'] == 'FAIL' for c in context.checks))

    def load_changed(self, desc):
        # Controlled literal-pin fault injection isolates structural checks after
        # digest admission. Production never accepts these rehashed descriptors.
        write(self.root, ADMISSION, canonical_bytes(desc))
        ref = reference(self.root, ADMISSION)
        pins = tuple((ref['path'], ref['size_bytes'], ref['sha256'], *p[3:])
                     if p[0] == ADMISSION else p for p in family.ADMITTED)
        context = audit.Audit(self.root, NOW)
        with patch.object(family, 'ADMITTED', pins), self.assertRaises(ValueError):
            family._load(ref, context.ref, context.tick)
        self.assertEqual(context.points, 0)

    def test_every_record_schema_type_night_order_and_closed_quantity(self):
        variants = []
        for index in range(3):
            for key, value in [('count', True), ('count', 2), ('operational_night', '2026-08-25'),
                               ('source_line_start', 1.0), ('coordinate_lines', [True, 7359]),
                               ('legacy_aliases', ['alias']), ('event_id', IDS[0]),
                               ('source_time_jst', '2026-08-25T12:00:00+09:00')]:
                if key == 'event_id' and index == 0:
                    value = 'fabricated'
                desc = deepcopy(self.desc); desc['records'][index][key] = value; variants.append(desc)
            desc = deepcopy(self.desc); del desc['records'][index]['surface']; variants.append(desc)
            desc = deepcopy(self.desc); desc['records'][index]['extra'] = False; variants.append(desc)
        for count in (1, 2, 4, True):
            desc = deepcopy(self.desc); desc['expected_counts']['events'] = count; variants.append(desc)
        desc = deepcopy(self.desc); desc['records'].reverse(); variants.append(desc)
        desc = deepcopy(self.desc); desc['records'][-1] = None; variants.append(desc)
        for i, desc in enumerate(variants):
            with self.subTest(case=i): self.load_changed(desc)

    def test_each_qc_row_has_exact_fields_types_cardinality_and_binding(self):
        variants = []
        for index in range(3):
            for key, value in [('gpx_sequence', True), ('distance_m', float('inf')),
                               ('event_id', 'OTHER'), ('neighboring_gap_seconds', [True, 1.0]),
                               ('hdop', 11.0), ('gpx_time_utc', 'bad')]:
                desc = deepcopy(self.desc); desc['expected_gpx_qc']['selected_points'][index][key] = value
                if value == float('inf'): value = 101.0; desc['expected_gpx_qc']['selected_points'][index][key] = value
                variants.append(desc)
            for remove in (True, False):
                desc = deepcopy(self.desc); row = desc['expected_gpx_qc']['selected_points'][index]
                if remove: del row['hdop']
                else: row['extra'] = 1
                variants.append(desc)
        desc = deepcopy(self.desc); desc['expected_gpx_qc']['selected_points'].reverse(); variants.append(desc)
        desc = deepcopy(self.desc); desc['expected_gpx_qc']['selected_points'].pop(); variants.append(desc)
        desc = deepcopy(self.desc); desc['expected_gpx_qc']['track']['point_count'] = True; variants.append(desc)
        for i, desc in enumerate(variants):
            with self.subTest(case=i): self.load_changed(desc)

    def test_default_pin_and_old_descriptor_remain_closed_and_exact(self):
        self.assertEqual(family.admission_ref()['sha256'],
                         '0582d7b6150d6dcc9cbffcd568172fdb23feab5d4b47ba3f32e0331eb693f32c')
        for key, value in [('sha256', '0' * 64), ('size_bytes', True), ('path', ADMISSION.upper())]:
            ref = reference(self.root, ADMISSION); ref[key] = value; calls = []
            with self.subTest(field=key), self.assertRaises(ValueError):
                family.reproduce_sources(ref, read_ref=lambda r: calls.append(r),
                                         tick=lambda: None, consume_point=lambda: None)
            self.assertEqual(calls, [])
        altered = deepcopy(self.desc); altered['records'][-1]['count'] = 2
        write(self.root, ADMISSION, canonical_bytes(altered))
        with self.assertRaises(ValueError): reproduce(self.root)

    def test_valid_initial_and_batch_entries_both_orders(self):
        new = self.entry(); old = self.original_entry()
        for entries in ([old, new], [new, old]):
            context = self.declare(entries)
            self.assertFalse(any(c['status'] == 'FAIL' for c in context.checks))
            self.assertEqual(context.points, 13565 + 21246)
            self.assertTrue(all(context.sources[e['path']]['use_roles'] == ['outcome_label'] for e in entries))

    def test_last_poison_or_alias_leaves_neither_family_entry_qualified(self):
        new = self.entry(); old = self.original_entry(); valid = json.loads((self.root / REVIEW).read_bytes())
        for alias in (CAPTURE, CAPTURE.upper(), CAPTURE.replace('/', '\\'),
                      CAPTURE.replace('august-2026/', 'august-2026/./')):
            bad = deepcopy(new); bad['path'] = alias
            for entries in ([old, new, bad], [bad, new, old]):
                with self.subTest(alias=alias, first=entries[0]['path']):
                    self.assert_no_family_roles(self.declare(entries))
        for key, value in [('count', True), ('csv_row', 4.0)]:
            bad = deepcopy(valid); bad['proof']['crosswalk'][-1][key] = value
            bad['proof_sha256'] = digest(bad['proof']); write(self.root, REVIEW, canonical_bytes(bad))
            poisoned = dict(reference(self.root, CAPTURE), review_ref=reference(self.root, REVIEW))
            for entries in ([old, poisoned], [poisoned, old]): self.assert_no_family_roles(self.declare(entries))

    def test_unknown_missing_downgrade_and_authority_are_not_qualification(self):
        valid = provisional(self.root)
        for key, value in [('verification_profile', None), ('verification_profile', 'legacy'),
                           ('training_authorized', True), ('permanent_biological_identity', 'ESTABLISHED')]:
            review = deepcopy(valid)
            if value is None: del review[key]
            else: review[key] = value
            self.assert_no_family_roles(self.declare([self.entry(review)]))

    def test_directory_dot_space_alias_classifier_preserves_nonfamily_paths(self):
        for spelling in directory_aliases():
            with self.subTest(path=spelling): self.assertTrue(family.is_family_path(spelling))
        for legacy in ('data/processed/capture_events/2026/2026-08-31.csv',
                       'data/processed/capture_events/2026/2026-09-28.csv',
                       'data/raw/gpx/2026-08-24__legacy.gpx'):
            self.assertFalse(family.is_family_path(legacy))

    def test_directory_dot_space_alias_invalidates_all_family_declaration_orders(self):
        new = self.entry(); old = self.original_entry()
        for spelling in directory_aliases():
            bad = dict(new, path=spelling)
            for entries in ([bad, old, new], [old, new, bad], [bad, new, old], [new, old, bad]):
                with self.subTest(path=spelling, paths=[e['path'] for e in entries]):
                    context = self.declare(entries)
                    self.assert_no_family_roles(context)
                    self.assertEqual(context.points, 0)
                    self.assertEqual(list(context.consumed), ['policies/observation_evidence.json'])

    def test_forbidden_paths_bound_to_admitted_review_cannot_escape_family_set(self):
        new = self.entry(); old = self.original_entry()
        paths = [CAPTURE.replace('august-2026/', 'AUGUST~1/'),
                 CAPTURE.replace('august-2026/', 'august-2026:stream/'),
                 'C:/' + CAPTURE, CAPTURE.replace('august-2026/', 'august-2026\x01/'),
                 CAPTURE.replace('august-2026/', 'august-2026\x7f/')]
        for path in paths:
            bad = dict(new, path=path)
            for entries in ([bad, old, new], [old, new, bad], [bad, new, old], [new, old, bad], [bad]):
                with self.subTest(path=repr(path), count=len(entries)):
                    context = self.declare(entries)
                    self.assert_no_family_roles(context)
        # The actual raw path must still reject even when its closed review
        # identity is expressed with another forbidden spelling.
        for spelling in (REVIEW.upper(), REVIEW.replace('/', '\\'),
                         REVIEW.replace('august-2026/', 'august-2026./'), REVIEW + ' '):
            bad = dict(new, path=paths[0], review_ref=dict(new['review_ref'], path=spelling))
            with self.subTest(review=spelling): self.assert_no_family_roles(self.declare([old, bad, new]))

    def test_malformed_known_family_intent_has_local_value_error_before_reads(self):
        new = self.entry(); old = self.original_entry()
        for path in (None, [], {}, 3, 'missing'):
            bad = deepcopy(new)
            if path == 'missing': del bad['path']
            else: bad['path'] = path
            context = audit.Audit(self.root, NOW)
            raw = canonical_bytes(dict(schema_version='1.0', sources=[old, bad],
                                       sessions=[], outcome_coverage=[]))
            with self.subTest(path=path), self.assertRaises(ValueError):
                family.preflight_declarations(raw, read_ref=context.ref, tick=context.tick,
                                              consume_point=lambda: None, now=NOW)
            self.assertEqual(context.reads, 0)
        for ref in (None, [], 3, {}, {'path': []}, dict(new['review_ref'], path={} )):
            bad = dict(new, review_ref=ref)
            context = audit.Audit(self.root, NOW)
            raw = canonical_bytes(dict(schema_version='1.0', sources=[old, bad],
                                       sessions=[], outcome_coverage=[]))
            with self.subTest(review_ref=ref), self.assertRaises(ValueError):
                family.preflight_declarations(raw, read_ref=context.ref, tick=context.tick,
                                              consume_point=lambda: None, now=NOW)
            self.assertEqual(context.reads, 0)

    def test_unregistered_batch_still_participates_in_global_overlap(self):
        old = self.original_entry(); desc = deepcopy(self.desc)
        initial = json.loads((self.root / family.ADMISSION_PATH).read_bytes())['records'][0]
        last = desc['records'][-1]
        for key in ('source_line_start', 'source_line_end', 'source_byte_start',
                    'source_byte_end_exclusive', 'source_slice_sha256', 'coordinate_lines', 'event_id'):
            last[key] = initial[key]
        desc['expected_gpx_qc']['selected_points'][-1]['event_id'] = last['event_id']
        write(self.root, ADMISSION, canonical_bytes(desc)); ref = reference(self.root, ADMISSION)
        pins = tuple((p[0], ref['size_bytes'], ref['sha256'], *p[3:]) if p[0] == ADMISSION else p
                     for p in family.ADMITTED)
        with patch.object(family, 'ADMITTED', pins): context = self.declare([old])
        self.assert_no_family_roles(context)
        self.assertEqual(context.points, 13565)  # rejected work is still charged

    def test_global_source_id_duplicate_is_rejected_even_with_disjoint_byte_keys(self):
        old = self.original_entry(); desc = deepcopy(self.desc)
        initial = json.loads((self.root / family.ADMISSION_PATH).read_bytes())['records'][0]
        last = desc['records'][-1]
        for key in ('source_line_start', 'source_line_end', 'coordinate_lines', 'event_id'):
            last[key] = initial[key]
        # Contradictory unregistered metadata must not evade the global ID gate
        # merely by declaring another, nonoverlapping byte interval.
        last['source_byte_start'] = initial['source_byte_end_exclusive'] + 1
        last['source_byte_end_exclusive'] = last['source_byte_start'] + 100
        desc['expected_gpx_qc']['selected_points'][-1]['event_id'] = last['event_id']
        write(self.root, ADMISSION, canonical_bytes(desc)); ref = reference(self.root, ADMISSION)
        pins = tuple((p[0], ref['size_bytes'], ref['sha256'], *p[3:]) if p[0] == ADMISSION else p
                     for p in family.ADMITTED)
        with patch.object(family, 'ADMITTED', pins): context = self.declare([old])
        self.assert_no_family_roles(context)

    def test_duplicate_admitted_descriptor_or_path_alias_fails_global_set(self):
        old = self.original_entry()
        with patch.object(family, 'ADMITTED', family.ADMITTED + (family.ADMITTED[-1],)):
            context = self.declare([old])
        self.assert_no_family_roles(context)

    def test_every_csv_and_native_source_mutation_rejects(self):
        for role in ('primary_ref', 'native_byte_proof_ref', 'owner_context_ref',
                     'gpx_ref', 'captures_ref', 'occurrences_ref'):
            path = self.root / self.desc[role]['path']; original = path.read_bytes()
            path.write_bytes(original + b' ')
            with self.subTest(role=role), self.assertRaises(ValueError): reproduce(self.root)
            path.write_bytes(original)

    def test_callback_exception_identity_and_rejected_charges(self):
        ref = reference(self.root, ADMISSION)
        for error in (OverflowError('caller'), KeyboardInterrupt('caller'), ValueError('caller'), MemoryError('caller')):
            for seam in ('tick', 'read', 'point'):
                a = audit.Audit(self.root, NOW)
                def fail(): raise error
                def reader(value):
                    raw = a.ref(value)
                    if seam == 'read': raise error
                    return raw
                def point():
                    a.points += 1; a.tick()
                    if seam == 'point': raise error
                with self.subTest(error=type(error), seam=seam), self.assertRaises(type(error)) as caught:
                    family.reproduce_sources(ref, read_ref=reader, tick=fail if seam == 'tick' else a.tick,
                                             consume_point=point)
                self.assertIs(caught.exception, error)
                if seam != 'tick': self.assertGreater(a.reads, 0)
                if seam == 'point': self.assertEqual(a.points, 1)

    def test_shared_byte_point_deadline_caps_and_pure_datetime_classification(self):
        for resource in ('bytes', 'point', 'deadline'):
            a = audit.Audit(self.root, NOW)
            if resource == 'bytes': a.read_bytes = audit.MAX_READ_BYTES - 1
            elif resource == 'point': a.points = audit.MAX_POINTS
            else: a.deadline = 0
            with self.subTest(resource=resource), self.assertRaises(audit.AuditBudgetExceeded): reproduce(self.root, a)
        valid = provisional(self.root)
        for clock in ('9999-12-31T23:59:00+00:00', '0001-01-01T00:00:00+23:00'):
            review = deepcopy(valid); review['reviewed_at'] = clock; a = audit.Audit(self.root, NOW)
            with self.subTest(clock=clock), self.assertRaises(ValueError):
                family.verify_review(review, read_ref=a.ref, tick=a.tick, consume_point=lambda: None, now=NOW)
            self.assertEqual(a.reads, 0)

    def test_owned_review_ref_lineage_after_real_reader_mutates_argument(self):
        entry = self.entry(); original = audit.Audit.ref
        def mutate(context, value):
            raw = original(context, value)
            if value['path'] == REVIEW: value['sha256'] = '0' * 64
            return raw
        with patch.object(audit.Audit, 'ref', mutate): context = self.declare([entry])
        source = context.sources[CAPTURE]
        self.assertEqual(source['use_roles'], ['outcome_label'])
        self.assertEqual(source['review_ref']['sha256'], entry['review_ref']['sha256'])
        self.assertEqual(context.consumed[REVIEW], entry['review_ref']['sha256'])

    def test_all_public_family_seams_lend_owned_source_refs_to_reader(self):
        new = self.entry(); old = self.original_entry()
        for entry in (old, new):
            review = json.loads((self.root / entry['review_ref']['path']).read_bytes())
            for method in ('reproduce_sources', 'verify_review', 'preflight_declarations'):
                context = audit.Audit(self.root, NOW); passed = []
                def reader(ref):
                    raw = context.ref(ref)  # genuine path/size/hash verification
                    passed.append(dict(ref))
                    ref['sha256'] = '0' * 64  # only the lent dictionary is changed
                    return raw
                def point(): context.points += 1; context.tick()
                kwargs = dict(read_ref=reader, tick=context.tick, consume_point=point)
                with self.subTest(source=entry['path'], method=method):
                    if method == 'reproduce_sources':
                        proof = family.reproduce_sources(review['descriptor_ref'], **kwargs)
                    elif method == 'verify_review':
                        proof = family.verify_review(review, now=NOW, **kwargs)
                    else:
                        policy = canonical_bytes(dict(schema_version='1.0', sources=[entry],
                                                      sessions=[], outcome_coverage=[]))
                        staged = family.preflight_declarations(policy, now=NOW, **kwargs)
                        self.assertEqual(staged[0]['entry'], entry)
                        proof = staged[0]['review']['proof']
                    self.assertEqual(canonical_bytes(proof), canonical_bytes(review['proof']))
                    self.assertTrue(passed)
                    self.assertTrue(all(ref['sha256'] != '0' * 64 for ref in passed))
                    self.assertEqual(context.points, 21246 if entry['path'] == CAPTURE else 13565)

    def test_late_payload_and_review_mutations_cannot_publish_partial_roles(self):
        entry = self.entry(); original = audit.Audit.ref
        for target in (CAPTURE, ADMISSION, REVIEW):
            original_bytes = (self.root / target).read_bytes(); calls = []
            def mutate(context, value):
                raw = original(context, value); calls.append(value['path'])
                if value['path'] == self.desc['gpx_ref']['path'] and calls.count(value['path']) == 1:
                    write(self.root, target, original_bytes + b' ')
                return raw
            with self.subTest(target=target), patch.object(audit.Audit, 'ref', mutate):
                self.assert_no_family_roles(self.declare([entry]))
            write(self.root, target, original_bytes)

    def test_private_batch_audit_has_three_positives_without_denominator_or_repository_review_changes(self):
        repository_review = (ROOT / REVIEW).read_bytes() if (ROOT / REVIEW).exists() else None
        self.declare([self.entry()])
        result = audit.audit_evidence(self.root, '2026-08-24', verified_at=NOW)
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual([e['event_id'] for e in result['outcome_ledger']['events']], IDS)
        self.assertEqual(sum(u['label'] == 1 for u in result['observation_units']), 3)
        self.assertFalse(any(u['label'] == 0 for u in result['observation_units']))
        self.assertEqual(result['outcome_ledger']['denominator_coverage'], 'NOT_ESTABLISHED')
        self.assertEqual(result['scientific_validation'], 'NOT_VALIDATED')
        self.assertEqual((ROOT / REVIEW).read_bytes() if (ROOT / REVIEW).exists() else None,
                         repository_review)

    def test_public_batch_final_rescan_and_success_seal_fail_closed(self):
        self.declare([self.entry()]); original = audit._osm
        def change(context):
            result = original(context)
            write(self.root, CAPTURE, (self.root / CAPTURE).read_bytes() + b' ')
            return result
        with patch.object(audit, '_osm', change):
            result = audit.audit_evidence(self.root, '2026-08-24', verified_at=NOW)
        self.assertEqual(result['observation_units'], [])
        self.assertEqual(result['outcome_ledger']['events'], [])
        fixture(self.root); self.declare([self.entry()]); instances = []; base = audit.Audit; actual = audit.digest
        class Observed(base):
            def __init__(context, *args, **kwargs):
                super().__init__(*args, **kwargs); instances.append(context)
        def expire(value):
            output = actual(value)
            if isinstance(value, dict) and value.get('observation_units'): instances[-1].deadline = 0
            return output
        with patch.object(audit, 'Audit', Observed), patch.object(audit, 'digest', expire):
            result = audit.audit_evidence(self.root, '2026-08-24', verified_at=NOW)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['observation_units'], [])
        self.assertEqual(result['outcome_ledger']['events'], [])

    def test_genuine_directory_reparse_guards_before_external_payload_open(self):
        import subprocess
        ref = reference(self.root, ADMISSION)
        self.entry()
        review_ref = reference(self.root, REVIEW)
        for target in (CAPTURE, INDIVIDUALS, ADMISSION, REVIEW, None):
            parent = (self.root / target).parent if target else self.root
            outside = Path(self.temp.name) / 'outside'
            self.assertTrue(parent.resolve().is_relative_to(self.root.resolve()))
            preserved = {p.relative_to(parent).as_posix(): p.read_bytes()
                         for p in parent.rglob('*') if p.is_file()}
            parent.rename(outside); opened = []; actual = Path.open
            try:
                if os.name == 'nt':
                    subprocess.run(['cmd', '/c', 'mklink', '/J', str(parent), str(outside)],
                                   check=True, capture_output=True)
                    self.assertTrue(parent.is_junction()); self.assertFalse(parent.is_symlink())
                else:
                    parent.symlink_to(outside, target_is_directory=True); self.assertTrue(parent.is_symlink())
                def op(path, *args, **kwargs):
                    if path.is_relative_to(parent): opened.append(str(path))
                    return actual(path, *args, **kwargs)
                a = audit.Audit(self.root, NOW)
                with patch.object(Path, 'open', op), self.assertRaises((ValueError, OSError)):
                    if target == REVIEW: a.ref(review_ref)
                    else: family.reproduce_sources(ref, read_ref=a.ref, tick=a.tick, consume_point=lambda: None)
                self.assertEqual(opened, [])
            finally:
                if os.name == 'nt': os.rmdir(parent)  # remove only this verified junction
                else: parent.unlink()
                outside.rename(parent)
            self.assertEqual({p.relative_to(parent).as_posix(): p.read_bytes()
                              for p in parent.rglob('*') if p.is_file()}, preserved)

    def test_hermetic_old_program_full_direct_n1_results_reads_opens_match(self):
        import test_august_positive_source_review as old
        old.fixture(self.root)
        old_review = json.loads(native(old.REVIEW)); capsule = (
            ROOT / 'tests/fixtures/august_positive_source_review_48d_original.py.txt').read_text(encoding='utf-8').encode()
        self.assertEqual(len(capsule), 12084)
        self.assertEqual(hashlib.sha256(capsule).hexdigest(),
                         '7501ce6ad1e32de9d886c61503096e7bc1f90d6631197f0625bda45a49620e9a')
        frozen = types.ModuleType('frozen_august_family_48d')
        exec(compile(capsule, '<frozen-48d-original>', 'exec'), frozen.__dict__)
        def observe(module, method):
            reads = []; opens = []; interleaving = []; actual = Path.open
            class Observed(audit.Audit):
                def read(context, path, *, max_bytes=None):
                    interleaving.append(['read', path, max_bytes]); raw = super().read(path, max_bytes=max_bytes)
                    row = [path, max_bytes, len(raw), hashlib.sha256(raw).hexdigest()]
                    reads.append(row); interleaving.append(['returned', *row]); return raw
            a = Observed(self.root, NOW)
            def op(path, *args, **kwargs):
                row = [path.relative_to(self.root).as_posix(), args[0] if args else kwargs.get('mode', 'r')]
                opens.append(row); interleaving.append(['open', *row]); return actual(path, *args, **kwargs)
            def point(): a.points += 1; a.tick()
            with patch.object(Path, 'open', op):
                if method == 'reproduce_sources': proof = module.reproduce_sources(old_review['descriptor_ref'], read_ref=a.ref, tick=a.tick, consume_point=point)
                else: proof = module.verify_review(old_review, read_ref=a.ref, tick=a.tick, consume_point=point, now=NOW)
            return canonical_bytes(dict(result=proof, input_hashes=a.consumed, reads=a.reads,
                read_bytes=a.read_bytes, points=a.points, read_order=reads, open_order=opens,
                read_open_interleaving=interleaving))
        for method in ('reproduce_sources', 'verify_review'):
            with self.subTest(method=method): self.assertEqual(observe(frozen, method), observe(family, method))


if __name__ == '__main__':
    unittest.main()
