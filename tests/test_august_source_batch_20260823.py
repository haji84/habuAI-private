"""Closed Aug23 SOURCE statements; not unique animals, SEARCH or TRAIN."""
from copy import deepcopy
import csv
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
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
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests')]
import august_positive_source_review as family
import evidence_audit as audit
import _owner_capture_occurrence_core as core
from master_contracts import canonical_bytes, digest
from test_aug31_positive_source_review import native, reference, write
from test_august_source_batch_20260824 import source_bytes

STEM = '2026-08-23-batch-v1'
ADMISSION = 'evidence/source_reviews/august-2026/admissions/'+STEM+'.json'
CAPTURE = 'data/processed/capture_events/source_reviews/august-2026/'+STEM+'.csv'
INDIVIDUALS = 'data/processed/individuals/source_reviews/august-2026/'+STEM+'.csv'
REVIEW = 'evidence/source_reviews/august-2026/'+STEM+'.json'
IDS = ['AUG2026SRC-L6199', 'AUG2026SRC-L6209', 'AUG2026SRC-L6672']
NOW = datetime.now(timezone.utc).isoformat()


def fixture(root):
    desc = json.loads(source_bytes(ADMISSION))
    for key in ('primary_ref', 'native_byte_proof_ref', 'owner_context_ref',
                'gpx_ref', 'captures_ref', 'occurrences_ref'):
        ref = desc[key]; write(root, ref['path'], source_bytes(ref['path']))
    for path, *_ in family.ADMITTED:
        write(root, path, source_bytes(path))
    return desc


def reproduce(root, context=None, read_ref=None, tick=None, consume_point=None):
    context = context or audit.Audit(root, NOW)
    def point():
        context.points += 1; context.tick()
    proof = family.reproduce_sources(reference(root, ADMISSION), read_ref=read_ref or context.ref,
        tick=tick or context.tick, consume_point=consume_point or point)
    return proof, context


def provisional(root, proof):
    return dict(schema_version='1.0', verification_profile=family.PROFILE,
        source_sha256=reference(root, CAPTURE)['sha256'], use_roles=['outcome_label'], reviewed_at=NOW,
        cohort_exposure='RESEARCH_EXPOSED', scope=family.SCOPE,
        independent_device_authentication='NOT_ESTABLISHED', permanent_biological_identity='NOT_ESTABLISHED',
        coordinate_method=family.COORDINATE_METHOD, recovery_class=family.RECOVERY_CLASS,
        source_refs=family._refs(json.loads((root/ADMISSION).read_bytes())),
        descriptor_ref=reference(root, ADMISSION), proof=deepcopy(proof), proof_sha256=digest(proof),
        **{key: False for key in family.FORBIDDEN_AUTHORITY})


class ClosedAdmissionTests(unittest.TestCase):
    def test_literal_aug23_three_statement_admission_is_present(self):
        self.assertIn(ADMISSION, [pin[0] for pin in family.ADMITTED])
        self.assertEqual(family._BATCH_SHAPES[ADMISSION], ('2026-08-23', 3))


class Aug23BatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); fixture(root); cls.proof, context = reproduce(root)
            if context.points != 23086:
                raise AssertionError('Every actual shared-track point must be charged')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'workspace'; self.root.mkdir()
        self.desc = fixture(self.root)

    def entry(self, review=None):
        write(self.root, REVIEW, canonical_bytes(provisional(self.root, self.proof) if review is None else review))
        return dict(reference(self.root, CAPTURE), review_ref=reference(self.root, REVIEW))

    def registered_entries(self):
        entries = []
        for pin in family.ADMITTED[:3]:
            desc = json.loads((self.root/pin[0]).read_bytes())
            for key in ('primary_ref', 'native_byte_proof_ref', 'owner_context_ref',
                        'gpx_ref', 'captures_ref', 'occurrences_ref'):
                ref = desc[key]; write(self.root, ref['path'], native(ref['path']))
            write(self.root, pin[6], native(pin[6]))
            entries.append(dict(reference(self.root, desc['captures_ref']['path']),
                                review_ref=reference(self.root, pin[6])))
        return entries

    def declare(self, entries):
        write(self.root, 'policies/observation_evidence.json', canonical_bytes(dict(
            schema_version='1.0', sources=entries, sessions=[], outcome_coverage=[])))
        context = audit.Audit(self.root, NOW); audit._declarations(context)
        return context

    def assert_no_family_roles(self, context):
        self.assertTrue(any(row['status'] == 'FAIL' for row in context.checks))
        for pin in family.ADMITTED:
            self.assertNotIn('outcome_label', context.sources.get(pin[3], {}).get('use_roles', []))

    def load_poison(self, desc):
        # Fault the literal pin only in a scoped test to reach the existing
        # descriptor validator; production never accepts arbitrary rehashes.
        write(self.root, ADMISSION, canonical_bytes(desc)); ref = reference(self.root, ADMISSION)
        pins = tuple((p[0], ref['size_bytes'], ref['sha256'], *p[3:]) if p[0] == ADMISSION else p
                     for p in family.ADMITTED)
        context = audit.Audit(self.root, NOW)
        with patch.object(family, 'ADMITTED', pins), self.assertRaises(ValueError):
            family._load(ref, context.ref, context.tick)
        self.assertEqual(context.points, 0)

    def test_three_exact_native_statements_csv_attributes_and_source_semantics(self):
        proof, context = reproduce(self.root)
        self.assertEqual((proof['event_count'], proof['individual_occurrence_count'], context.points), (3, 3, 23086))
        self.assertEqual([r['event_id'] for r in proof['crosswalk']], IDS)
        self.assertEqual(proof['gpx_qc'], dict(point_count=23086, excluded_points=0,
            segment_breaks=0, maximum_gap_seconds=17.216))
        for actual, expected in zip(proof['crosswalk'], self.desc['expected_gpx_qc']['selected_points']):
            self.assertEqual(canonical_bytes({k: actual[k] for k in expected}), canonical_bytes(expected))
        primary = (self.root/self.desc['primary_ref']['path']).read_bytes(); lines = primary.decode().splitlines()
        events = list(csv.DictReader(io.StringIO((self.root/CAPTURE).read_text(encoding='utf-8'))))
        occurrences = list(csv.DictReader(io.StringIO((self.root/INDIVIDUALS).read_text(encoding='utf-8'))))
        self.assertEqual(len(events), 3); self.assertEqual(len(occurrences), 3)
        for row, occurrence, record in zip(events, occurrences, self.desc['records']):
            n = record['source_line_start']; start = record['source_byte_start']; end = record['source_byte_end_exclusive']
            self.assertEqual(hashlib.sha256(primary[start:end]).hexdigest(), record['source_slice_sha256'])
            self.assertEqual((row['latitude'], row['longitude']), (lines[n+6], lines[n+7]))
            self.assertEqual((row['source_note'], row['event_place']), (lines[n+1], lines[n+5]))
            self.assertEqual((row['event_count'], row['operational_date']), ('1', '2026-08-23'))
            self.assertEqual(occurrence['event_id'], row['event_id'])
            self.assertEqual(occurrence['individual_id'], row['event_id']+'-OCC01')
            self.assertEqual((occurrence['size_note'], occurrence['sex']), ('小', ''))
            self.assertEqual(record['count_basis'], 'SINGULAR_STATEMENT_AS_ONE_RECORDED_OCCURRENCE')
        self.assertEqual((self.desc['records'][1]['source_byte_start'],
                          self.desc['records'][0]['source_byte_end_exclusive']), (70412, 70412))
        self.assertIs(proof['permanent_biological_identity_verified'], False)
        self.assertTrue(all(proof[k] is False for k in family.FORBIDDEN_AUTHORITY))

    def test_strict_empty_edge_actual_track_and_no_aug27_optin_reuse(self):
        definition = family._definition(self.desc)
        self.assertEqual(definition.allowed_equal_time_edges, ())
        raw = native(self.desc['gpx_ref']['path']); calls = [0]
        def point(): calls[0] += 1
        points, qc = core._points(raw, lambda: None, point, definition=definition)
        gaps = [(b['time_utc']-a['time_utc']).total_seconds() for a, b in zip(points, points[1:])]
        self.assertEqual((calls[0], len(points)), (23086, 23086)); self.assertTrue(all(g > 0 for g in gaps))
        self.assertEqual(qc, self.desc['expected_gpx_qc']['track'])
        with self.assertRaises(ValueError):
            core._points(raw, lambda: None, lambda: None, definition=replace(definition,
                allowed_equal_time_edges=((20155,20156,'2026-08-27T17:58:40.519000+00:00'),)))

    def test_each_record_and_selected_row_poison_rejects_before_points(self):
        for index in range(3):
            for field, value in (('count', True), ('count', 2), ('source_line_start', 1.0),
                    ('operational_night', '2026-08-24'), ('event_id', 'other'), ('legacy_aliases', ['old']),
                    ('source_time_jst', '2026-08-24T12:00:00+09:00')):
                changed = deepcopy(self.desc); changed['records'][index][field] = value
                with self.subTest(index=index, field=field): self.load_poison(changed)
            for field, value in (('event_id', IDS[(index+1)%3]), ('gpx_trackpoint_index', True),
                    ('hdop', 11.0), ('distance_m', 101.0), ('neighboring_gap_seconds', [1.0, True])):
                changed = deepcopy(self.desc); changed['expected_gpx_qc']['selected_points'][index][field] = value
                with self.subTest(index=index, field=field): self.load_poison(changed)
        for field in ('records',):
            changed = deepcopy(self.desc); changed[field].reverse(); self.load_poison(changed)

    def test_native_pin_all_payloads_and_typed_proof_reject(self):
        for field, value in (('sha256', '0'*64), ('path', ADMISSION.upper()), ('size_bytes', True)):
            ref = reference(self.root, ADMISSION); ref[field] = value; seen = []
            with self.subTest(field=field), self.assertRaises(ValueError):
                family.reproduce_sources(ref, read_ref=lambda r: seen.append(r), tick=lambda: None, consume_point=lambda: None)
            self.assertEqual(seen, [])
        for key in ('primary_ref', 'native_byte_proof_ref', 'owner_context_ref', 'gpx_ref', 'captures_ref', 'occurrences_ref'):
            p = self.root/self.desc[key]['path']; original = p.read_bytes(); p.write_bytes(original+b' ')
            with self.subTest(key=key), self.assertRaises(ValueError): reproduce(self.root)
            p.write_bytes(original)
        for index in range(3):
            review = provisional(self.root, self.proof); review['proof']['crosswalk'][index]['count'] = True
            review['proof_sha256'] = digest(review['proof']); context = audit.Audit(self.root, NOW)
            def point(): context.points += 1; context.tick()
            with self.subTest(index=index), self.assertRaises(ValueError):
                family.verify_review(review, read_ref=context.ref, tick=context.tick, consume_point=point, now=NOW)

    def test_all_four_batches_both_orders_and_unregistered_metadata(self):
        canonical_review = ROOT/REVIEW
        canonical_before = canonical_review.read_bytes() if canonical_review.exists() else None
        old = self.registered_entries(); new = self.entry()
        for entries in (old+[new], [new]+old[::-1]):
            context = self.declare(entries)
            self.assertFalse(any(c['status'] == 'FAIL' for c in context.checks))
            self.assertEqual(context.points, 13565+21246+21005+23086)
            self.assertTrue(all(context.sources[e['path']]['use_roles'] == ['outcome_label'] for e in entries))
        context = self.declare(old)
        self.assertNotIn(CAPTURE, context.sources); self.assertIn(ADMISSION, context.consumed)
        self.assertEqual(context.points, 13565+21246+21005)
        self.assertEqual(canonical_review.read_bytes() if canonical_review.exists() else None,
                         canonical_before)

    def test_alias_opaque_intent_and_bad_last_review_are_atomic(self):
        old = self.registered_entries(); new = self.entry(); aliases = [CAPTURE.upper(), CAPTURE.replace('/', '\\'),
            CAPTURE.replace('august-2026/', 'august-2026./'), CAPTURE.replace('august-2026/', 'august-2026 /'),
            CAPTURE.replace('august-2026/', 'AUGUST~1/'), CAPTURE.replace('august-2026/', 'august-2026:stream/'),
            'C:/'+CAPTURE, CAPTURE.replace('august-2026/', 'august-2026\x00/'),
            INDIVIDUALS.replace('august-2026/', 'august-2026./')]
        for alias in aliases:
            bad = dict(new, path=alias)
            for entries in ([bad]+old+[new], old[:1]+[bad,new]+old[1:], [new]+old+[bad]):
                with self.subTest(alias=alias):
                    context = self.declare(entries); self.assert_no_family_roles(context); self.assertEqual(context.points, 0)
        review = provisional(self.root, self.proof); review['training_authorized'] = True
        bad = self.entry(review)
        for entries in (old+[bad], [bad]+old[::-1]): self.assert_no_family_roles(self.declare(entries))

    def test_global_overlap_duplicate_ids_and_malformed_intent_no_partial_role(self):
        old = self.registered_entries()
        for source in (json.loads((self.root/family.ADMITTED[0][0]).read_bytes())['records'][0],
                       json.loads((self.root/family.ADMITTED[2][0]).read_bytes())['records'][-1]):
            changed = deepcopy(self.desc)
            for key in ('event_id','source_line_start','source_line_end','source_byte_start','source_byte_end_exclusive',
                        'source_slice_sha256','coordinate_lines'): changed['records'][-1][key] = source[key]
            changed['expected_gpx_qc']['selected_points'][-1]['event_id'] = source['event_id']
            write(self.root, ADMISSION, canonical_bytes(changed)); ref = reference(self.root, ADMISSION)
            pins = tuple((p[0],ref['size_bytes'],ref['sha256'],*p[3:]) if p[0] == ADMISSION else p for p in family.ADMITTED)
            with patch.object(family, 'ADMITTED', pins): self.assert_no_family_roles(self.declare(old))
        write(self.root, ADMISSION, source_bytes(ADMISSION)); new = self.entry()
        for value in (None, [], {}, True, 1):
            bad = dict(new, path=value); seen = []
            with self.subTest(value=value), self.assertRaises(ValueError):
                family.preflight_declarations(canonical_bytes(dict(sources=[bad])), read_ref=lambda r: seen.append(r),
                    tick=lambda: None, consume_point=lambda: None, now=NOW)
            self.assertEqual(seen, [])

    def test_all_public_seams_own_reader_refs_and_preserve_lineage(self):
        new = self.entry(); review = json.loads((self.root/REVIEW).read_bytes())
        for api in ('reproduce', 'verify', 'preflight'):
            context = audit.Audit(self.root, NOW)
            def read(ref):
                raw = context.ref(ref); ref['sha256'] = '0'*64; return raw
            def point(): context.points += 1; context.tick()
            if api == 'reproduce': proof = family.reproduce_sources(reference(self.root, ADMISSION), read_ref=read, tick=context.tick, consume_point=point)
            elif api == 'verify': proof = family.verify_review(review, read_ref=read, tick=context.tick, consume_point=point, now=NOW)
            else:
                staged = family.preflight_declarations(canonical_bytes(dict(sources=[new])), read_ref=read, tick=context.tick, consume_point=point, now=NOW)
                self.assertEqual(staged[0]['entry']['review_ref'], reference(self.root, REVIEW)); proof = staged[0]['review']['proof']
            self.assertEqual(canonical_bytes(proof), canonical_bytes(self.proof))

    def test_same_object_reader_tick_point_cancellation_and_bad_time(self):
        for error in (OverflowError('parent'), KeyboardInterrupt('parent'), audit.AuditBudgetExceeded('parent capacity')):
            for seam in ('reader', 'tick', 'point'):
                context = audit.Audit(self.root, NOW)
                def tick():
                    context.tick()
                    if seam == 'tick': raise error
                def read(ref):
                    raw = context.ref(ref)
                    if seam == 'reader': raise error
                    return raw
                def point():
                    context.points += 1; context.tick()
                    if seam == 'point': raise error
                with self.subTest(error=type(error), seam=seam), self.assertRaises(type(error)) as caught:
                    reproduce(self.root, context, read_ref=read, tick=tick, consume_point=point)
                self.assertIs(caught.exception, error)
        for stamp in ('9999-12-31T23:59:00+00:00','0001-01-01T00:00:00+23:00'):
            review = provisional(self.root, self.proof); review['reviewed_at'] = stamp; context = audit.Audit(self.root, NOW)
            with self.assertRaises(ValueError): family.verify_review(review, read_ref=context.ref,
                tick=context.tick, consume_point=lambda: None, now=NOW)
            self.assertEqual(context.reads, 0)

    def test_deadline_byte_capacity_and_late_source_changes_reject(self):
        context = audit.Audit(self.root, NOW); context.deadline = 0
        with self.assertRaises(audit.AuditBudgetExceeded): reproduce(self.root, context)
        context = audit.Audit(self.root, NOW)
        with patch.object(audit, 'MAX_READ_BYTES', 32), self.assertRaises((ValueError, audit.AuditBudgetExceeded)):
            reproduce(self.root, context)
        self.assertGreater(context.read_bytes, 0)
        p = self.root/CAPTURE; original = p.read_bytes(); context = audit.Audit(self.root, NOW)
        def read(ref):
            raw = context.ref(ref)
            if ref['path'] == CAPTURE: p.write_bytes(original+b' ')
            return raw
        with self.assertRaises(ValueError): reproduce(self.root, context, read_ref=read)
        self.assertGreater(context.reads, 1)

    def test_private_three_positive_fixture_never_modifies_repository_review(self):
        before = (ROOT/REVIEW).read_bytes() if (ROOT/REVIEW).exists() else None
        self.declare([self.entry()]); result = audit.audit_evidence(self.root, '2026-08-23', verified_at=NOW)
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual([e['event_id'] for e in result['outcome_ledger']['events']], IDS)
        self.assertEqual(sum(u['label'] == 1 for u in result['observation_units']), 3)
        self.assertFalse(any(u['label'] == 0 for u in result['observation_units']))
        self.assertEqual(result['outcome_ledger']['denominator_coverage'], 'NOT_ESTABLISHED')
        self.assertEqual(result['scientific_validation'], 'NOT_VALIDATED')
        self.assertEqual((ROOT/REVIEW).read_bytes() if (ROOT/REVIEW).exists() else None, before)

    def test_late_read_and_point_abort_keep_the_exact_caller_object(self):
        for seam, threshold in (('reader', 13), ('point', 23086)):
            error = OverflowError('late original caller'); context = audit.Audit(self.root, NOW); reads = [0]
            def read(ref):
                raw = context.ref(ref); reads[0] += 1
                if seam == 'reader' and reads[0] == threshold: raise error
                return raw
            def point():
                context.points += 1; context.tick()
                if seam == 'point' and context.points == threshold: raise error
            with self.subTest(seam=seam), self.assertRaises(OverflowError) as caught:
                reproduce(self.root, context, read_ref=read, consume_point=point)
            self.assertIs(caught.exception, error)
            self.assertGreater(context.read_bytes, 0)

    def test_final_success_hash_expiry_clears_all_private_fixture_roles(self):
        self.declare([self.entry()]); instances = []; base = audit.Audit; original = audit.digest
        class Observed(base):
            def __init__(context, *args, **kwargs):
                super().__init__(*args, **kwargs); instances.append(context)
        def expire(value):
            result = original(value)
            if isinstance(value, dict) and value.get('observation_units'): instances[-1].deadline = 0
            return result
        with patch.object(audit, 'Audit', Observed), patch.object(audit, 'digest', expire):
            result = audit.audit_evidence(self.root, '2026-08-23', verified_at=NOW)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['observation_units'], []); self.assertEqual(result['outcome_ledger']['events'], [])

    def test_real_link_rejects_before_external_gpx_payload_open(self):
        target = self.root/self.desc['gpx_ref']['path']; original = target.read_bytes()
        external = Path(self.temp.name)/'external'; external.mkdir(); outside = external/target.name; outside.write_bytes(original)
        parent = target.parent; backup = parent.with_name('gpx-backup'); parent.rename(backup); linked = False
        try:
            if os.name == 'nt':
                result = subprocess.run(['cmd','/c','mklink','/J',str(parent),str(external)],capture_output=True)
                self.assertEqual(result.returncode, 0); self.assertTrue(parent.is_junction())
            else:
                parent.symlink_to(external,target_is_directory=True); self.assertTrue(parent.is_symlink())
            linked = True; seen = []; actual = Path.open
            def observe(p,*args,**kwargs):
                if p in (outside,target): seen.append(p)
                return actual(p,*args,**kwargs)
            with patch.object(Path,'open',observe), self.assertRaises(ValueError): reproduce(self.root)
            self.assertEqual(seen, []); self.assertEqual(outside.read_bytes(), original)
        finally:
            if linked:
                self.assertTrue(parent.absolute().is_relative_to(self.root))
                if os.name == 'nt': os.rmdir(parent)
                else: parent.unlink()
            backup.rename(parent)


if __name__ == '__main__':
    unittest.main()
