"""Closed Aug27 three SOURCE occurrences; no biological identity or TRAIN."""
from copy import deepcopy
import csv
import hashlib
import io
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests')]
import august_positive_source_review as family
import evidence_audit as audit
import _owner_capture_occurrence_core as core
from master_contracts import canonical_bytes, digest
from master_inventory import local_path
from test_aug31_positive_source_review import native, reference, write
from test_august_source_batch_20260824 import source_bytes

STEM = '2026-08-27-batch-v1'
ADMISSION = 'evidence/source_reviews/august-2026/admissions/'+STEM+'.json'
CAPTURE = 'data/processed/capture_events/source_reviews/august-2026/'+STEM+'.csv'
INDIVIDUALS = 'data/processed/individuals/source_reviews/august-2026/'+STEM+'.csv'
REVIEW = 'evidence/source_reviews/august-2026/'+STEM+'.json'
IDS = ['AUG2026SRC-L7853', 'AUG2026SRC-L8052', 'AUG2026SRC-L8214']
NOW = '2026-10-26T01:50:24.770855+00:00'
EQUAL_EDGE = ((20155, 20156, '2026-08-27T17:58:40.519000+00:00'),)


def original_core():
    raw = (ROOT/'tests/fixtures/owner_capture_occurrence_core_297b_original.py.txt').read_text(encoding='utf-8').encode()
    if len(raw) != 14740 or hashlib.sha256(raw).hexdigest() != '297b2bb4301a0234b61e63abaf92076390095957be054bce008e7d49c5b1a914':
        raise AssertionError('Genuine original shared core capsule required')
    module = types.ModuleType('genuine_original_297b_core')
    exec(compile(raw, '<native-Git-297b-original-core>', 'exec'), module.__dict__)
    return module


def fixture(root):
    desc = json.loads(source_bytes(ADMISSION))
    for key in ('primary_ref', 'native_byte_proof_ref', 'owner_context_ref',
                'gpx_ref', 'captures_ref', 'occurrences_ref'):
        write(root, desc[key]['path'], source_bytes(desc[key]['path']))
    for path, *_ in family.ADMITTED:
        write(root, path, source_bytes(path))
    return desc


def reproduce(root, context=None, read_ref=None, tick=None, consume_point=None):
    context = context or audit.Audit(root, NOW)
    def point():
        context.points += 1
        context.tick()
    return family.reproduce_sources(reference(root, ADMISSION), read_ref=read_ref or context.ref,
        tick=tick or context.tick, consume_point=consume_point or point), context


def provisional(root, proof):
    return dict(schema_version='1.0', verification_profile=family.PROFILE,
        source_sha256=reference(root, CAPTURE)['sha256'], use_roles=['outcome_label'],
        reviewed_at=NOW, cohort_exposure='RESEARCH_EXPOSED', scope=family.SCOPE,
        independent_device_authentication='NOT_ESTABLISHED', permanent_biological_identity='NOT_ESTABLISHED',
        coordinate_method=family.COORDINATE_METHOD, recovery_class=family.RECOVERY_CLASS,
        source_refs=family._refs(json.loads((root/ADMISSION).read_bytes())),
        descriptor_ref=reference(root, ADMISSION), proof=deepcopy(proof), proof_sha256=digest(proof),
        **{k: False for k in family.FORBIDDEN_AUTHORITY})


class CoreEqualTimeTests(unittest.TestCase):
    def actual(self):
        desc = json.loads(source_bytes(ADMISSION))
        return desc, native(desc['gpx_ref']['path']), family._definition(desc)

    def test_closed_literal_definition_uses_exact_internal_edge(self):
        desc = json.loads(source_bytes(ADMISSION)); definition = family._definition(desc)
        self.assertEqual(getattr(definition, 'allowed_equal_time_edges', None), EQUAL_EDGE)
        raw = native(desc['gpx_ref']['path']); points = [0]
        def point(): points[0] += 1
        marked, qc = core._points(raw, lambda: None, point, definition=definition)
        self.assertEqual(points[0], 21005); self.assertEqual(qc, desc['expected_gpx_qc']['track'])
        self.assertEqual((marked[20156]['time_utc']-marked[20155]['time_utc']).total_seconds(), 0.0)
        self.assertTrue(marked[20156]['segment_break_before']); self.assertFalse(marked[20156]['exclude_point'])

    def test_original_and_current_strict_default_reject_actual_zero_after_all_charges(self):
        _, raw, definition = self.actual(); definition = replace(definition, allowed_equal_time_edges=())
        for module in (original_core(), core):
            count = [0]
            def point(): count[0] += 1
            with self.subTest(module=module.__name__), self.assertRaisesRegex(ValueError, 'GPX_CHRONOLOGY'):
                module._points(raw, lambda: None, point, definition=definition)
            self.assertEqual(count[0], 21005)

    def test_malformed_configured_edges_and_wrong_source_cannot_opt_in(self):
        _, raw, definition = self.actual(); edge = EQUAL_EDGE[0]
        class TupleSubclass(tuple): pass
        variants = [[], None, True, TupleSubclass(EQUAL_EDGE), [edge], (list(edge),),
            (TupleSubclass(edge),), (edge, edge), ((20155, 20156),),
            ((True, 20156, edge[2]),), ((20155.0, 20156, edge[2]),),
            ((20155, 20156.0, edge[2]),), ((20154, 20156, edge[2]),),
            ((20155, 20157, edge[2]),), ((20155, 21005, edge[2]),),
            ((20155, 20156, False),), ((20155, 20156, '2026-08-27T17:58:40.519Z'),),
            ((20155, 20156, '2026-08-27T17:58:40.518000+00:00'),)]
        for index, edges in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(ValueError):
                core._points(raw, lambda: None, lambda: None,
                    definition=replace(definition, allowed_equal_time_edges=edges))
        for field, value in (('night', '2026-08-28'), ('point_count', 21004)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                core._points(raw, lambda: None, lambda: None, definition=replace(definition, **{field:value}))
        refs = tuple((key, path.upper(), size, sha) if key == 'gpx' else (key,path,size,sha)
                     for key,path,size,sha in definition.references)
        with self.assertRaises(ValueError):
            core._points(raw, lambda: None, lambda: None, definition=replace(definition, references=refs))

    def test_no_other_literal_definition_or_declared_metadata_enables_the_edge(self):
        desc, _, _ = self.actual()
        for pin in family.ADMITTED[:2]:
            old = json.loads(source_bytes(pin[0]))
            self.assertEqual(family._definition(old).allowed_equal_time_edges, ())
        for key, value in (('path', 'data/raw/gpx/alias.gpx'), ('sha256', '0'*64),
                           ('size_bytes', 5561683), ('point_count', 21004),
                           ('size_bytes', 5561682.0), ('point_count', 21005.0)):
            changed = deepcopy(desc); changed['gpx_ref'][key] = value
            with self.subTest(key=key): self.assertEqual(family._definition(changed).allowed_equal_time_edges, ())
        changed = deepcopy(desc); changed['records'][-1]['event_id'] = 'other'
        self.assertEqual(family._definition(changed).allowed_equal_time_edges, ())

    def test_closed_opt_in_rejects_float_alias_for_point_and_byte_count(self):
        _, raw, definition = self.actual()
        refs = tuple((key,path,float(size),sha) if key == 'gpx' else (key,path,size,sha)
                     for key,path,size,sha in definition.references)
        for index, changed in enumerate((replace(definition,point_count=21005.0), replace(definition,references=refs))):
            with self.subTest(index=index), self.assertRaises(ValueError):
                core._points(raw,lambda:None,lambda:None,definition=changed)

    def test_negative_missing_extra_and_wrong_time_raw_edges_reject(self):
        _, raw, definition = self.actual()
        matches = list(re.finditer(rb'<trkpt\b[^>]*>.*?<time>([^<]+)</time>', raw, re.S))
        self.assertEqual(len(matches), 21005)
        def changed(values):
            result = raw
            for index, value in sorted(values.items(), reverse=True):
                start, end = matches[index].span(1); self.assertEqual(len(value), end-start)
                result = result[:start]+value+result[end:]
            self.assertEqual(len(result), len(raw)); return result
        stamp = matches[20156].group(1)
        cases = [changed({20156:stamp.replace(b'.519',b'.518')}),
                 changed({20156:stamp.replace(b'.519',b'.520')}),
                 changed({20155:stamp.replace(b'.519',b'.518'),20156:stamp.replace(b'.519',b'.518')}),
                 changed({101:matches[100].group(1)}),
                 changed({4272:matches[4271].group(1).replace(b'.500',b'.499')})]
        for index, payload in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(ValueError):
                core._points(payload, lambda: None, lambda: None, definition=definition)

    def test_marker_must_really_mark_nonexcluded_break_once(self):
        _, raw, definition = self.actual(); actual = core.mark_point_anomalies
        for field, value in (('segment_break_before',False), ('exclude_point',True)):
            calls = []
            def faulty(points):
                calls.append(len(points)); marked = actual(points); marked[20156][field] = value; return marked
            with self.subTest(field=field), patch.object(core,'mark_point_anomalies',faulty), self.assertRaisesRegex(ValueError,'GPX_EQUAL_TIME_BREAK'):
                core._points(raw, lambda: None, lambda: None, definition=definition)
            self.assertEqual(calls, [21005])

    def test_post_marker_parent_abort_retains_original_object(self):
        _, raw, definition = self.actual(); actual = core.mark_point_anomalies
        for error in (OverflowError('parent'), ValueError('parent capacity'), KeyboardInterrupt('parent')):
            phase = [False]
            def marker(points):
                result = actual(points); phase[0] = True; return result
            def tick():
                if phase[0]: raise error
            with self.subTest(error=type(error)), patch.object(core,'mark_point_anomalies',marker), self.assertRaises(type(error)) as caught:
                core._points(raw,tick,lambda:None,definition=definition)
            self.assertIs(caught.exception,error)


class Aug27BatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); fixture(root)
            cls.proof, _ = reproduce(root)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'workspace'; self.root.mkdir()
        self.desc = fixture(self.root)

    def test_closed_admission_is_present_without_registration(self):
        self.assertIn(ADMISSION, [pin[0] for pin in family.ADMITTED])
        self.assertEqual(family._BATCH_SHAPES[ADMISSION], ('2026-08-27', 3))
        self.assertFalse((ROOT/REVIEW).exists())

    def entry(self, review=None):
        write(self.root, REVIEW, canonical_bytes(provisional(self.root, self.proof) if review is None else review))
        return dict(reference(self.root, CAPTURE), review_ref=reference(self.root, REVIEW))

    def registered_entries(self):
        entries = []
        for path, *_rest in family.ADMITTED[:2]:
            desc = json.loads((self.root/path).read_bytes())
            for key in ('primary_ref', 'native_byte_proof_ref', 'owner_context_ref',
                        'gpx_ref', 'captures_ref', 'occurrences_ref'):
                write(self.root, desc[key]['path'], native(desc[key]['path']))
            review_path = next(pin[6] for pin in family.ADMITTED if pin[0] == path)
            write(self.root, review_path, native(review_path))
            entries.append(dict(reference(self.root, desc['captures_ref']['path']),
                                review_ref=reference(self.root, review_path)))
        return entries

    def declare(self, entries):
        write(self.root, 'policies/observation_evidence.json', canonical_bytes(dict(
            schema_version='1.0', sources=entries, sessions=[], outcome_coverage=[])))
        context = audit.Audit(self.root, NOW); audit._declarations(context)
        return context

    def assert_atomic_rejection(self, context):
        self.assertTrue(any(row['status'] == 'FAIL' for row in context.checks))
        for pin in family.ADMITTED:
            self.assertNotIn('outcome_label', context.sources.get(pin[3], {}).get('use_roles', []))

    def load_changed(self, desc):
        # Deliberately fault the code-pin boundary to exercise downstream schema;
        # arbitrary rehashed descriptors remain rejected by unpatched production.
        write(self.root, ADMISSION, canonical_bytes(desc)); ref = reference(self.root, ADMISSION)
        pins = tuple((p[0], ref['size_bytes'], ref['sha256'], *p[3:]) if p[0] == ADMISSION else p
                     for p in family.ADMITTED)
        context = audit.Audit(self.root, NOW)
        with patch.object(family, 'ADMITTED', pins), self.assertRaises(ValueError):
            family._load(ref, context.ref, context.tick)
        self.assertEqual(context.points, 0)

    def test_three_native_singular_statements_and_exact_real_qc(self):
        proof, context = reproduce(self.root)
        self.assertEqual((proof['event_count'], proof['individual_occurrence_count'], context.points), (3, 3, 21005))
        self.assertEqual([r['event_id'] for r in proof['crosswalk']], IDS)
        self.assertEqual(proof['gpx_qc'], dict(point_count=21005, excluded_points=2,
            segment_breaks=1, maximum_gap_seconds=29.604))
        for row, expected in zip(proof['crosswalk'], self.desc['expected_gpx_qc']['selected_points']):
            self.assertEqual(canonical_bytes({k: row[k] for k in expected}), canonical_bytes(expected))
        self.assertEqual([r['source_line_start'] for r in proof['crosswalk']], [7853, 8052, 8214])
        self.assertEqual([r['source_byte_start'] for r in proof['crosswalk']], [87936, 90248, 91934])
        self.assertEqual([r['source_byte_end_exclusive'] for r in proof['crosswalk']], [88061, 90358, 92056])
        self.assertEqual([r['individual_occurrence_id'] for r in proof['crosswalk']], [v+'-OCC01' for v in IDS])
        self.assertEqual(self.desc['expected_gpx_qc']['selected_points'][1]['time_delta_seconds'], 114.001)
        self.assertIs(proof['permanent_biological_identity_verified'], False)
        self.assertTrue(all(proof[k] is False for k in family.FORBIDDEN_AUTHORITY))

    def test_native_csv_coordinates_attributes_and_unknown_identity(self):
        primary = (self.root/self.desc['primary_ref']['path']).read_bytes(); lines = primary.decode().splitlines()
        events = list(csv.DictReader(io.StringIO((self.root/CAPTURE).read_text(encoding='utf-8'))))
        individuals = list(csv.DictReader(io.StringIO((self.root/INDIVIDUALS).read_text(encoding='utf-8'))))
        self.assertEqual(len(events), 3); self.assertEqual(len(individuals), 3)
        for i, (row, occurrence, record) in enumerate(zip(events, individuals, self.desc['records'])):
            line = record['source_line_start']; start = record['source_byte_start']; end = record['source_byte_end_exclusive']
            self.assertEqual(hashlib.sha256(primary[start:end]).hexdigest(), record['source_slice_sha256'])
            self.assertEqual((row['latitude'], row['longitude']), (lines[line+6], lines[line+7]))
            self.assertEqual(row['source_note'], lines[line+1]); self.assertEqual(row['event_count'], '1')
            self.assertEqual(row['operational_date'], '2026-08-27')
            self.assertEqual(row['event_place'], '瀬戸内町勝浦' if i == 0 else '')
            self.assertEqual(occurrence['individual_id'], IDS[i]+'-OCC01')
            self.assertEqual(occurrence['event_id'], row['event_id']); self.assertEqual(occurrence['sex'], '')
            self.assertEqual(occurrence['size_note'], '中' if i == 0 else '大')
            self.assertEqual(record['count_basis'], 'SINGULAR_STATEMENT_AS_ONE_RECORDED_OCCURRENCE')

    def test_all_three_record_and_selected_point_rows_are_typed_and_ordered(self):
        cases = []
        for index in range(3):
            for field, value in (('count', True), ('count', 2), ('source_line_start', 1.0),
                    ('operational_night', '2026-08-28'), ('source_time_jst', '2026-08-28T12:00:00+09:00'),
                    ('legacy_aliases', ['legacy']), ('event_id', 'other')):
                changed = deepcopy(self.desc); changed['records'][index][field] = value; cases.append(changed)
            changed = deepcopy(self.desc); del changed['records'][index]['behavior']; cases.append(changed)
            for field, value in (('gpx_trackpoint_index', True), ('distance_m', 101.0), ('hdop', 11.0),
                    ('neighboring_gap_seconds', [1.0, True]), ('event_id', IDS[(index+1)%3]),
                    ('gpx_time_utc', 'not-a-time')):
                changed = deepcopy(self.desc); changed['expected_gpx_qc']['selected_points'][index][field] = value; cases.append(changed)
        for field in ('records',):
            changed = deepcopy(self.desc); changed[field].reverse(); cases.append(changed)
        for value in (True, 1, 2, 4):
            changed = deepcopy(self.desc); changed['expected_counts']['events'] = value; cases.append(changed)
        for index, changed in enumerate(cases):
            with self.subTest(index=index): self.load_changed(changed)

    def test_wrong_pin_and_each_native_payload_change_are_rejected(self):
        for field, value in (('sha256', '0'*64), ('size_bytes', True), ('path', ADMISSION.upper())):
            ref = reference(self.root, ADMISSION); ref[field] = value; calls = []
            with self.subTest(field=field), self.assertRaises(ValueError):
                family.reproduce_sources(ref, read_ref=lambda v: calls.append(v), tick=lambda: None, consume_point=lambda: None)
            self.assertEqual(calls, [])
        for key in ('primary_ref', 'native_byte_proof_ref', 'owner_context_ref', 'gpx_ref', 'captures_ref', 'occurrences_ref'):
            path = self.root/self.desc[key]['path']; before = path.read_bytes(); path.write_bytes(before+b' ')
            with self.subTest(payload=key), self.assertRaises(ValueError): reproduce(self.root)
            path.write_bytes(before)

    def test_all_registered_family_orders_and_unregistered_new_source(self):
        prior = self.registered_entries(); new = self.entry()
        for entries in (prior+[new], [new]+prior[::-1]):
            context = self.declare(entries)
            self.assertFalse(any(c['status'] == 'FAIL' for c in context.checks))
            self.assertEqual(context.points, 13565+21246+21005)
            self.assertTrue(all(context.sources[e['path']]['use_roles'] == ['outcome_label'] for e in entries))
        context = self.declare(prior)
        self.assertNotIn(CAPTURE, context.sources)
        self.assertIn(ADMISSION, context.consumed)
        self.assertEqual(context.points, 13565+21246)

    def test_portable_alias_and_opaque_intent_all_positions_are_atomic(self):
        prior = self.registered_entries(); new = self.entry(); aliases = []
        for base in (CAPTURE, INDIVIDUALS):
            for i in range(len(base.split('/'))-1):
                parts = base.split('/'); parts[i] += '.'; aliases.append('/'.join(parts))
                parts = base.split('/'); parts[i] += ' '; aliases.append('\\'.join(parts).upper())
        aliases += [CAPTURE.upper(), CAPTURE.replace('/', '\\'), CAPTURE.replace('august-2026/', 'august-2026/./'),
                    CAPTURE.replace('august-2026/', 'august-2026:stream/'),
                    CAPTURE.replace('august-2026/', 'AUGUST~1/'), 'C:/'+CAPTURE,
                    CAPTURE.replace('august-2026/', 'august-2026\x00/'), CAPTURE.replace('august-2026/', 'august-2026\x7f/')]
        actual = Path.open
        for alias in aliases:
            bad = dict(new, path=alias)
            for entries in ([bad]+prior+[new], prior[:1]+[bad,new]+prior[1:], [new]+prior+[bad]):
                opened = []
                def observer(path, *args, **kw):
                    opened.append(path); return actual(path, *args, **kw)
                with self.subTest(path=alias, position=entries.index(bad)), patch.object(Path, 'open', observer):
                    context = self.declare(entries)
                self.assert_atomic_rejection(context)
                self.assertFalse(any(str(p).endswith(alias) for p in opened))
                self.assertEqual(context.points, 0)

    def test_malformed_known_review_intent_rejects_before_reads(self):
        new = self.entry()
        for value in (None, [], {}, True, 1):
            bad = dict(new, path=value); calls = []
            raw = canonical_bytes(dict(sources=[bad], schema_version='1.0', sessions=[], outcome_coverage=[]))
            with self.subTest(value=value), self.assertRaises(ValueError):
                family.preflight_declarations(raw, read_ref=lambda ref: calls.append(ref),
                    tick=lambda: None, consume_point=lambda: None, now=NOW)
            self.assertEqual(calls, [])

    def test_last_typed_proof_poison_missing_profile_and_authority_are_not_partial(self):
        prior = self.registered_entries(); valid = provisional(self.root, self.proof)
        variants = []
        for index in range(3):
            for field, value in (('count', True), ('csv_row', float(index+2))):
                bad = deepcopy(valid); bad['proof']['crosswalk'][index][field] = value
                bad['proof_sha256'] = digest(bad['proof']); variants.append(bad)
        for field, value in (('verification_profile', None), ('verification_profile', 'legacy'),
                ('permanent_biological_identity', 'ESTABLISHED'), ('training_authorized', True)):
            bad = deepcopy(valid)
            if value is None: del bad[field]
            else: bad[field] = value
            variants.append(bad)
        for index, review in enumerate(variants):
            new = self.entry(review)
            with self.subTest(index=index): self.assert_atomic_rejection(self.declare([new]+prior))

    def test_global_duplicate_id_and_overlap_even_when_batch_unregistered(self):
        prior = self.registered_entries()
        for source in (json.loads((self.root/family.ADMITTED[0][0]).read_bytes())['records'][0],
                       json.loads((self.root/family.ADMITTED[1][0]).read_bytes())['records'][-1]):
            changed = deepcopy(self.desc); row = changed['records'][-1]
            for field in ('source_line_start', 'source_line_end', 'source_byte_start', 'source_byte_end_exclusive',
                          'source_slice_sha256', 'coordinate_lines', 'event_id'):
                row[field] = source[field]
            changed['expected_gpx_qc']['selected_points'][-1]['event_id'] = row['event_id']
            write(self.root, ADMISSION, canonical_bytes(changed)); ref = reference(self.root, ADMISSION)
            pins = tuple((p[0],ref['size_bytes'],ref['sha256'],*p[3:]) if p[0] == ADMISSION else p for p in family.ADMITTED)
            with patch.object(family, 'ADMITTED', pins): context = self.declare(prior)
            self.assert_atomic_rejection(context)

    def test_all_public_apis_lend_owned_refs_and_keep_original_lineage(self):
        new = self.entry(); review = json.loads((self.root/REVIEW).read_bytes())
        for api in ('reproduce_sources', 'verify_review', 'preflight_declarations'):
            context = audit.Audit(self.root, NOW); borrowed = []
            def read(ref):
                raw = context.ref(ref); borrowed.append(dict(ref)); ref['sha256'] = '0'*64; return raw
            def point(): context.points += 1; context.tick()
            with self.subTest(api=api):
                if api == 'reproduce_sources': actual = family.reproduce_sources(reference(self.root, ADMISSION), read_ref=read, tick=context.tick, consume_point=point)
                elif api == 'verify_review': actual = family.verify_review(review, read_ref=read, tick=context.tick, consume_point=point, now=NOW)
                else:
                    staged = family.preflight_declarations(canonical_bytes(dict(sources=[new])), read_ref=read, tick=context.tick, consume_point=point, now=NOW)
                    self.assertEqual(staged[0]['entry']['review_ref'], reference(self.root, REVIEW)); actual = staged[0]['review']['proof']
                self.assertEqual(canonical_bytes(actual), canonical_bytes(self.proof))
                self.assertTrue(all(ref['sha256'] != '0'*64 for ref in borrowed))

    def test_caller_exception_identity_at_reader_tick_and_point_seams(self):
        class Capacity(ValueError): pass
        for error in (OverflowError('parent'), Capacity('parent'), KeyboardInterrupt('parent')):
            for seam in ('reader', 'tick', 'point'):
                context = audit.Audit(self.root, NOW)
                def fail(): raise error
                def read(ref):
                    raw = context.ref(ref)
                    if seam == 'reader': raise error
                    return raw
                def point():
                    context.points += 1; context.tick()
                    if seam == 'point': raise error
                with self.subTest(error=type(error), seam=seam), self.assertRaises(type(error)) as caught:
                    reproduce(self.root, context, read_ref=read, tick=fail if seam == 'tick' else context.tick, consume_point=point)
                self.assertIs(caught.exception, error)
                if seam == 'point': self.assertEqual(context.points, 1)

    def test_shared_budget_bad_year_and_late_source_mutation(self):
        context = audit.Audit(self.root, NOW); context.deadline = 0
        with self.assertRaises(audit.AuditBudgetExceeded): reproduce(self.root, context)
        for stamp in ('9999-12-31T23:59:00+00:00', '0001-01-01T00:00:00+23:00'):
            review = provisional(self.root, self.proof); review['reviewed_at'] = stamp; context = audit.Audit(self.root, NOW)
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                family.verify_review(review, read_ref=context.ref, tick=context.tick, consume_point=lambda: None, now=NOW)
            self.assertEqual(context.reads, 0)
        path = self.root/CAPTURE; original = path.read_bytes(); context = audit.Audit(self.root, NOW)
        def read(ref):
            raw = context.ref(ref)
            if ref['path'] == CAPTURE: path.write_bytes(original+b' ')
            return raw
        with self.assertRaises(ValueError): reproduce(self.root, context, read_ref=read)
        self.assertGreater(context.reads, 1)

    def test_public_source_audit_private_three_positive_without_denominator(self):
        self.declare([self.entry()]); result = audit.audit_evidence(self.root, '2026-08-27', verified_at=NOW)
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual([e['event_id'] for e in result['outcome_ledger']['events']], IDS)
        self.assertEqual(sum(u['label'] == 1 for u in result['observation_units']), 3)
        self.assertFalse(any(u['label'] == 0 for u in result['observation_units']))
        self.assertEqual(result['outcome_ledger']['denominator_coverage'], 'NOT_ESTABLISHED')
        self.assertEqual(result['scientific_validation'], 'NOT_VALIDATED')
        self.assertFalse((ROOT/REVIEW).exists())

    def test_success_hash_expiry_clears_all_public_qualification(self):
        self.declare([self.entry()]); instances = []; base = audit.Audit; actual = audit.digest
        class Observed(base):
            def __init__(context, *args, **kw): super().__init__(*args, **kw); instances.append(context)
        def expire(value):
            result = actual(value)
            if isinstance(value, dict) and value.get('observation_units'): instances[-1].deadline = 0
            return result
        with patch.object(audit, 'Audit', Observed), patch.object(audit, 'digest', expire):
            result = audit.audit_evidence(self.root, '2026-08-27', verified_at=NOW)
        self.assertEqual(result['status'], 'BLOCKED'); self.assertEqual(result['observation_units'], [])
        self.assertEqual(result['outcome_ledger']['events'], [])

    def test_real_link_guard_rejects_before_external_payload_open(self):
        external = Path(self.temp.name)/'external'; external.mkdir()
        target = self.root/self.desc['gpx_ref']['path']; original = target.read_bytes()
        outside = external/target.name; outside.write_bytes(original)
        parent = target.parent; backup = parent.with_name('gpx-backup'); parent.rename(backup)
        linked = False
        try:
            if os.name == 'nt':
                result = subprocess.run(['cmd','/c','mklink','/J',str(parent),str(external)], capture_output=True)
                self.assertEqual(result.returncode, 0); self.assertTrue(parent.is_junction())
            else:
                parent.symlink_to(external, target_is_directory=True); self.assertTrue(parent.is_symlink())
            linked = True; opened = []; actual = Path.open
            def observe(path,*args,**kw):
                if path == outside or path == target: opened.append(path)
                return actual(path,*args,**kw)
            with patch.object(Path,'open',observe), self.assertRaises(ValueError): reproduce(self.root)
            self.assertEqual(opened, []); self.assertEqual(outside.read_bytes(), original)
        finally:
            if linked:
                self.assertTrue(parent.absolute().is_relative_to(self.root))
                if os.name == 'nt': os.rmdir(parent)
                else: parent.unlink()
            backup.rename(parent)

    def test_hermetic_old_n1_and_n3_whole_program_outputs_and_ledgers(self):
        self.registered_entries()
        capsule = (ROOT/'tests/fixtures/august_positive_source_review_da9_original.py.txt').read_text(encoding='utf-8').encode()
        self.assertEqual(len(capsule), 18925)
        self.assertEqual(hashlib.sha256(capsule).hexdigest(), 'ad4673e0b191155343daebb3ba050e6908c6d6a8e7821095cd2fff8f7479a997')
        frozen = types.ModuleType('genuine_old_ad467_family')
        exec(compile(capsule,'<native-Git-ad467-family>','exec'),frozen.__dict__)
        frozen.core = original_core()
        def observed(module, method, review):
            reads=[];opens=[];inter=[];ticks=[0];actual=Path.open
            class Observed(audit.Audit):
                def read(context,path,*,max_bytes=None):
                    inter.append(['read',path,max_bytes]); raw=super().read(path,max_bytes=max_bytes)
                    row=[path,max_bytes,len(raw),hashlib.sha256(raw).hexdigest()]
                    reads.append(row);inter.append(['returned',*row]);return raw
            context=Observed(self.root,NOW)
            def op(path,*args,**kw):
                row=[path.relative_to(self.root).as_posix(),args[0] if args else kw.get('mode','r')]
                opens.append(row);inter.append(['open',*row]);return actual(path,*args,**kw)
            def tick(): ticks[0]+=1;context.tick()
            def point(): context.points+=1;context.tick()
            with patch.object(Path,'open',op):
                if method=='reproduce_sources': proof=module.reproduce_sources(review['descriptor_ref'],read_ref=context.ref,tick=tick,consume_point=point)
                else: proof=module.verify_review(review,read_ref=context.ref,tick=tick,consume_point=point,now=NOW)
            return canonical_bytes(dict(result=proof,input_hashes=context.consumed,reads=context.reads,
                read_bytes=context.read_bytes,points=context.points,read_order=reads,open_order=opens,interleaving=inter,tick_calls=ticks[0]))
        for pin in family.ADMITTED[:2]:
            review=json.loads((self.root/pin[6]).read_bytes())
            for method in ('reproduce_sources','verify_review'):
                with self.subTest(review=pin[6],method=method):
                    self.assertEqual(observed(frozen,method,review),observed(family,method,review))


if __name__ == '__main__':
    unittest.main()
