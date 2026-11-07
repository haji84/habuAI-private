"""Synthetic byte-bound field events: no private originals or scientific labels."""
import copy
import hashlib
import importlib
import importlib.util
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import recover_private_route_evidence as runner


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture():
    return {'schema_version': 'habu-field-session-v1', 'id': 'synthetic-session-0001',
            'startedAt': '2026-10-01T10:00:00.000Z', 'endedAt': '2026-10-01T10:02:00.000Z',
            'status': 'stopped', 'revision': 5, 'gaps': [],
            'points': [{'time': '2026-10-01T10:00:20.000Z', 'lat': 28.0, 'lon': 129.3, 'accuracy': 5},
                       {'time': '2026-10-01T10:00:30.000Z', 'lat': 28.00001, 'lon': 129.3, 'accuracy': 6}],
            'events': [{'id': 'synthetic-event-0001', 'type': 'capture', 'species': 'ハブ',
                        'count': 2, 'time': '2026-10-01T10:00:30.000Z', 'owner': 'self', 'note': '',
                        'position': {'time': '2026-10-01T10:00:20.000Z', 'lat': 28.0, 'lon': 129.3, 'accuracy': 5}}]}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()


class FieldCandidateTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('src.field_capture_candidates'),
                             'Native field-event byte adapter is missing')
        self.api = importlib.import_module('src.field_capture_candidates')

    def build(self, value=None, **kwargs):
        raw = encoded(fixture() if value is None else value)
        return self.api.build_field_capture_candidates(raw, source_sha256=digest(raw), **kwargs)

    def test_recorded_time_never_becomes_observed_or_precise_location(self):
        value = fixture(); before = encoded(value)
        result = self.build(value); event = result['events'][0]; meta = result['source_metadata'][0]
        self.assertEqual(result['schema_version'], 'habu-capture-event-candidates-v1')
        self.assertEqual(event['event_id'], 'synthetic-event-0001')
        self.assertEqual(event['source_sha256'], digest(before))
        self.assertEqual(event['recorded_at'], '2026-10-01T10:00:30.000Z')
        self.assertEqual(event['time_semantics'], 'RECORDED_AT')
        self.assertIsNone(event['uncertainty_seconds'])
        self.assertIsNone(event['latitude']); self.assertIsNone(event['longitude'])
        self.assertEqual(event['count'], 2); self.assertEqual(event['individual_ids'], [])
        self.assertEqual(meta['event_index'], 0)
        self.assertEqual(meta['recorded_at'], value['events'][0]['time'])
        self.assertEqual(meta['gps_fix'], value['events'][0]['position'])
        self.assertEqual(encoded(value), before)
        from src.capture_route_evidence import match_captures
        matched = match_captures(result['events'], [], source_sha256=digest(before))
        self.assertTrue(matched['sidecars'][0]['capture_positive_evidence'])
        self.assertFalse(matched['sidecars'][0]['formal_positive'])

    def test_actual_native_field_export_is_consumed_without_event_reconstruction(self):
        core = runner.ROOT/'dashboard/field-core.js'
        js = '''const core=require(process.argv[1]);
const s=core.createSession('synthetic-native-session','2026-10-01T10:00:00Z');
core.recordPoint(s,{latitude:28,longitude:129.3,accuracy:8},'2026-10-01T10:00:10Z');
core.event(s,{id:'synthetic-native-event',type:'capture',species:'ハブ',count:1,
time:'2026-10-01T10:00:15Z',owner:'self',note:'literal\\nprivate',position:s.points[0]});
core.event(s,{id:'synthetic-observed-event',type:'capture',species:'ハブ',count:1,
time:'2026-10-01T10:00:20Z',owner:'self',position:s.points[0],
observation:{observed_at:'2026-10-01T19:00:12+09:00',uncertainty_seconds:5}});
core.stop(s,'2026-10-01T10:01:00Z');process.stdout.write(core.exportBackup(s));'''
        p=subprocess.run(['node','-e',js,str(core)],capture_output=True,check=True)
        source=json.loads(p.stdout)
        result=self.api.build_field_capture_candidates(p.stdout,source_sha256=digest(p.stdout))
        self.assertEqual(result['source_metadata'][0]['source_event'],source['events'][0])
        self.assertEqual(result['events'][0]['recorded_at'],'2026-10-01T10:00:15.000Z')
        self.assertIsNone(result['events'][0]['uncertainty_seconds'])
        self.assertIsNone(result['events'][0]['latitude'])
        declared = result['events'][1]
        raw_event = result['source_metadata'][1]['source_event']
        self.assertEqual(raw_event, source['events'][1])
        self.assertEqual(declared['time_semantics'], 'OBSERVED_AT')
        self.assertEqual(declared['recorded_at'], '2026-10-01T10:00:12.000Z')
        self.assertEqual(declared['uncertainty_seconds'], 5)
        self.assertIsNone(declared['latitude'])
        self.assertIsNone(declared['longitude'])
        self.assertEqual(raw_event['time'], '2026-10-01T10:00:20.000Z')
        self.assertEqual(raw_event['position']['time'], '2026-10-01T10:00:10.000Z')

    def test_zero_events_are_not_an_independent_complete_outcome_certificate(self):
        value=fixture();value['events']=[]
        result=self.build(value)
        self.assertEqual(result['events'],[])
        self.assertFalse(result['formal_negative_qualified'])
        self.assertEqual(result['source_authentication'],'NOT_ATTESTED')

    def test_declared_observation_preserves_recording_clock_and_fix_separately(self):
        value = fixture(); declaration = {'observed_at': '2026-10-01T19:00:10.123456+09:00', 'uncertainty_seconds': 7.5}
        value['events'][0]['observation'] = declaration
        result = self.build(value); event = result['events'][0]
        self.assertEqual(event['recorded_at'], declaration['observed_at'])
        self.assertEqual(event['time_semantics'], 'OBSERVED_AT')
        self.assertEqual(event['uncertainty_seconds'], 7.5)
        self.assertIsNone(event['latitude']); self.assertIsNone(event['longitude'])
        self.assertEqual(result['source_metadata'][0]['observation'], declaration)
        self.assertEqual(result['source_metadata'][0]['recorded_at'], '2026-10-01T10:00:30.000Z')

    def test_legacy_recording_grace_preserves_unknown_timing_and_no_location(self):
        for recorded in ['2026-10-01T09:59:30Z', '2026-10-01T09:59:00Z']:
            with self.subTest(recorded=recorded):
                value=fixture();value['events'][0]['time']=recorded
                try:
                    result=self.build(value)
                except ValueError as exc:
                    self.fail('Valid legacy recording grace rejected: '+str(exc))
                event=result['events'][0]
                self.assertEqual(event['recorded_at'],recorded)
                self.assertEqual(event['time_semantics'],'RECORDED_AT')
                self.assertIsNone(event['uncertainty_seconds'])
                self.assertIsNone(event['latitude']);self.assertIsNone(event['longitude'])
                self.assertEqual(result['source_metadata'][0]['recorded_at'],recorded)
        value=fixture();value['events'][0]['time']='2026-10-01T09:58:59.999999Z'
        with self.assertRaises(ValueError):self.build(value)
        value=fixture();value['events'][0]['time']='2026-10-01T09:59:30Z'
        value['events'][0]['observation']={'observed_at':'2026-10-01T09:59:30Z','uncertainty_seconds':0}
        with self.assertRaises(ValueError):self.build(value)

    def test_datetime_min_session_does_not_underflow_when_checking_grace(self):
        value=fixture();value.update(startedAt='0001-01-01T00:00:00Z',endedAt=None,status='active',points=[])
        value['events'][0].update(time='0001-01-01T00:00:01Z');del value['events'][0]['position']
        result=self.build(value)
        self.assertEqual(result['events'][0]['recorded_at'],'0001-01-01T00:00:01Z')
        self.assertIsNone(result['events'][0]['uncertainty_seconds'])

    def test_owner_species_and_event_roles_are_not_promoted(self):
        value = fixture(); value['events'] = []
        for index, (kind, species, owner) in enumerate([('capture', 'ヒメハブ', 'other'), ('sighting', 'ハブ', 'self'), ('roadkill', 'ハブ', 'self'), ('other', '不明', 'self')]):
            e = fixture()['events'][0]; e.update(id=f'synthetic-event-{index:04d}', type=kind, species=species, owner=owner); value['events'].append(e)
        result = self.build(value)
        self.assertEqual([e['event_type'] for e in result['events']], ['CAPTURE','SIGHTING','ROADKILL','UNKNOWN'])
        self.assertEqual(result['events'][0]['species'], 'HIMEHABU')
        self.assertEqual(result['events'][0]['owner_role'], 'OTHER')
        self.assertEqual(result['events'][3]['species'], 'UNKNOWN')

    def test_bad_hash_duplicate_json_nonfinite_and_depth_are_rejected(self):
        raw = encoded(fixture())
        with self.assertRaises(ValueError): self.api.build_field_capture_candidates(raw, source_sha256='0'*64)
        for bad in [b'{"events":[],"events":[]}', b'{"value":NaN}', b'{"value":1e999}', b'{"x":'+b'['*70+b'0'+b']'*70+b'}']:
            with self.subTest(raw=bad[:25]):
                with self.assertRaises(ValueError): self.api.build_field_capture_candidates(bad, source_sha256=digest(bad))

    def test_observation_clocks_and_bounds_fail_closed(self):
        for at, uncertainty in [('2026-10-01T09:59:59Z', 0), ('2026-10-01T10:00:31Z', 0),
                                ('2026-10-01T10:00:20', 0), ('2026-10-01T10:00:20.0000001Z', 0),
                                ('2026-10-01T10:00:20+00:00:00.1', 0), ('2026-10-01T10:00:20Z', True),
                                ('2026-10-01T10:00:20Z', -1), ('2026-10-01T10:00:20Z', None),
                                ('2026-10-01T10:00:20Z', 31536001)]:
            with self.subTest(at=at, uncertainty=uncertainty):
                value = fixture(); value['events'][0]['observation'] = dict(observed_at=at, uncertainty_seconds=uncertainty)
                with self.assertRaises(ValueError): self.build(value)
        value=fixture(); value['events'][0]['observation']={'observed_at':value['events'][0]['time'],'uncertainty_seconds':0,'source_auth':True}
        with self.assertRaises(ValueError):self.build(value)

    def test_event_source_shape_and_identity_are_strict(self):
        mutations = [('count', True), ('count', 0), ('owner', 'unknown'), ('time', '2026-10-01T10:02:01Z'), ('id', ''), ('position', {'time':'2026-10-01T10:00:20Z','lat':999,'lon':129.3,'accuracy':5})]
        for key,value in mutations:
            s=fixture(); s['events'][0][key]=value
            with self.subTest(key=key):
                with self.assertRaises(ValueError):self.build(s)
        s=fixture();s['events'].append(copy.deepcopy(s['events'][0]))
        with self.assertRaises(ValueError):self.build(s)
        s=fixture();s['events'][0]['formal_positive']=True
        with self.assertRaises(ValueError):self.build(s)

    def test_byte_event_and_deadline_caps_no_callback(self):
        raw=encoded(fixture())
        for budget in [True,0,-1,float('inf'),10**10000]:
            with self.assertRaises(ValueError):self.api.build_field_capture_candidates(raw,source_sha256=digest(raw),budget_seconds=budget)
        with patch.object(self.api,'MAX_BYTES',len(raw)-1):
            with self.assertRaises(ValueError):self.build()
        with patch.object(self.api,'MAX_EVENTS',0):
            with self.assertRaises(ValueError):self.build()
        with patch.object(self.api.time,'monotonic',side_effect=[0,31]):
            with self.assertRaises(ValueError):self.build()
        class Evil:
            def __bytes__(self):raise AssertionError('callback invoked')
        with self.assertRaises(ValueError):self.api.build_field_capture_candidates(Evil(),source_sha256=digest(raw))

    def test_custom_budget_type_never_invokes_equality_comparison_or_coercion(self):
        class Meta(type):
            def __eq__(self,other):raise AssertionError('custom metaclass equality')
            def __hash__(self):raise AssertionError('custom metaclass hash')
        class Budget(metaclass=Meta):
            def __float__(self):raise AssertionError('coercion')
        raw=encoded(fixture())
        with self.assertRaises(ValueError):self.api.build_field_capture_candidates(raw,source_sha256=digest(raw),budget_seconds=Budget())
        class Bytes(bytes):
            def __len__(self):raise AssertionError('custom byte callback')
        with self.assertRaises(ValueError):self.api.build_field_capture_candidates(Bytes(raw),source_sha256=digest(raw))


class FieldCandidateRunnerTests(unittest.TestCase):
    def setUp(self):
        self.assertIn('field_capture_candidates',inspect.signature(runner.run_recovery).parameters,
                      'Route runner opt-in missing')
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name);self.source=self.base/'inputs';self.source.mkdir();self.out=self.base/'output'
        self.raw=encoded(fixture());(self.source/'session.json').write_bytes(self.raw)
        self.item={'source_id':'session','kind':'field-session','path':'session.json','sha256':digest(self.raw),'size_bytes':len(self.raw),
                   'source_identity':'SYNTHETIC','received_at':'2026-10-02T00:00:00Z','original_timezone':'UTC','correction_revision':'original'}
        self.manifest={'schema_version':runner.SCHEMA,'sources':[self.item]};self.seal()

    def seal(self):
        self.path=self.source/'manifest.json';self.path.write_bytes(encoded(self.manifest));self.sha=digest(self.path.read_bytes())

    def test_optin_actual_native_match_and_repeat_source_immutability(self):
        r=runner.run_recovery(self.path,self.sha,self.out,field_capture_candidates=True)
        before=(self.out/'route-evidence.json').read_bytes(),(self.out/'completion-receipt.json').read_bytes()
        self.assertEqual(r['capture_sidecar_count'],1)
        payload=json.loads(before[0]);cap=payload['capture_evidence'];row=cap['sidecars'][0]
        self.assertEqual(row['event']['source_sha256'],digest(self.raw))
        self.assertEqual(cap['field_source_metadata'][0]['event_index'],0)
        self.assertFalse(payload['authority']['formal_positive_qualified'])
        self.assertIn('src/field_capture_candidates.py',payload['runtime_code_sha256'])
        self.assertEqual(runner.run_recovery(self.path,self.sha,self.out,field_capture_candidates=True),r)
        self.assertEqual(before,((self.out/'route-evidence.json').read_bytes(),(self.out/'completion-receipt.json').read_bytes()))
        self.assertEqual((self.source/'session.json').read_bytes(),self.raw)

    def test_default_does_not_autodiscover_events(self):
        r=runner.run_recovery(self.path,self.sha,self.out)
        self.assertEqual(r['capture_sidecar_count'],0)
        p=json.loads((self.out/'route-evidence.json').read_bytes())
        self.assertNotIn('field_source_metadata',p['capture_evidence'])

    def test_declared_time_only_capture_is_not_a_precise_sample_or_negative(self):
        value=fixture();value['events'][0]['observation']={'observed_at':'2026-10-01T10:00:20Z','uncertainty_seconds':0}
        self.raw=encoded(value);(self.source/'session.json').write_bytes(self.raw)
        self.item.update(sha256=digest(self.raw),size_bytes=len(self.raw));self.seal()
        runner.run_recovery(self.path,self.sha,self.out,field_capture_candidates=True)
        p=json.loads((self.out/'route-evidence.json').read_bytes());side=p['capture_evidence']['sidecars'][0]
        self.assertEqual(side['match_status'],'TIME_ONLY_POSITIVE_EVIDENCE')
        self.assertFalse(side['formal_positive']);self.assertFalse(side['formal_negative'])
        self.assertEqual(side['candidates'],[])
        window=p['routes'][0]['windows'][0]
        self.assertEqual(window['research_capture_outcome'],'UNKNOWN_CAPTURE_LOCATION_OR_TIME')
        self.assertFalse(window['capture_outcome_completeness_verified'])

    def test_field_source_mutated_after_native_recovery_never_gets_completion(self):
        actual=runner._recover_route
        def mutate(*args,**kwargs):
            value=actual(*args,**kwargs)
            (self.source/'session.json').write_bytes(self.raw+b' ')
            return value
        with patch.object(runner,'_recover_route',side_effect=mutate):
            with self.assertRaises(ValueError):runner.run_recovery(self.path,self.sha,self.out,field_capture_candidates=True)
        self.assertFalse((self.out/'completion-receipt.json').exists())

    def test_expired_parent_budget_during_adapter_never_creates_completion(self):
        from src import field_capture_candidates as adapter
        actual=adapter.build_field_capture_candidates
        def expire(*args,**kwargs):
            result=actual(*args,**kwargs)
            raise ValueError('FIELD_CAPTURE_DEADLINE')
        with patch.object(adapter,'build_field_capture_candidates',side_effect=expire):
            with self.assertRaises(ValueError):runner.run_recovery(self.path,self.sha,self.out,field_capture_candidates=True)
        self.assertFalse(self.out.exists())

    def test_explicit_capture_conflict_and_more_than_one_route_are_rejected(self):
        self.manifest['captures_source_id']='explicit';self.seal()
        with self.assertRaises(ValueError):runner.run_recovery(self.path,self.sha,self.out,field_capture_candidates=True)
        self.assertFalse(self.out.exists())
        del self.manifest['captures_source_id']
        second=dict(self.item,source_id='other',kind='gpx',path='other.gpx')
        raw=b'<gpx/>';second.update(sha256=digest(raw),size_bytes=len(raw));(self.source/'other.gpx').write_bytes(raw)
        self.manifest['sources'].append(second);self.seal()
        with self.assertRaises(ValueError):runner.run_recovery(self.path,self.sha,self.out,field_capture_candidates=True)
        self.assertFalse(self.out.exists())

    def test_false_is_only_default_and_nonboolean_optin_is_rejected(self):
        for flag in [0,1,None,'true']:
            with self.assertRaises(ValueError):runner.run_recovery(self.path,self.sha,self.out,field_capture_candidates=flag)
        self.assertFalse(self.out.exists())

    def test_actual_cli_optin_private_stdout_and_no_authority(self):
        process=subprocess.run([sys.executable,'-B','-X','utf8',str(runner.ROOT/'scripts/recover_private_route_evidence.py'),
            '--manifest',str(self.path),'--manifest-sha256',self.sha,'--private-output',str(self.out),'--field-capture-candidates'],capture_output=True,text=True)
        self.assertEqual(process.returncode,0,process.stderr)
        self.assertEqual(json.loads(process.stdout)['capture_sidecar_count'],1)
        self.assertNotIn('synthetic-event',process.stdout);self.assertNotIn('129.3',process.stdout)
        self.assertFalse(json.loads(process.stdout)['formal_training_qualified'])


if __name__=='__main__':unittest.main()
