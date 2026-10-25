"""Closed native-source occurrence admission; neither animal identity nor TRAIN."""
from copy import deepcopy
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests')]
import evidence_audit as audit
from master_contracts import canonical_bytes, digest
from master_inventory import local_path
from test_aug31_positive_source_review import csv_bytes, native, reference, write

STEM = '2026-08-29-line9654-v1'
CAPTURE = 'data/processed/capture_events/source_reviews/august-2026/'+STEM+'.csv'
INDIVIDUALS = 'data/processed/individuals/source_reviews/august-2026/'+STEM+'.csv'
ADMISSION = 'evidence/source_reviews/august-2026/admissions/'+STEM+'.json'
REVIEW = 'evidence/source_reviews/august-2026/'+STEM+'.json'
NATIVE = 'evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt'
PROFILE = 'august-owner-capture-source-occurrence-v1'
EVENT = 'AUG2026SRC-L9654'
NOW = '2026-10-25T19:00:00+00:00'
SOURCE_PATHS = {
    'native_log': NATIVE,
    'native_byte_proof': 'evidence/recovered_sources/2026-08-native-original-library-byte-proof.json',
    'gpx': 'data/raw/gpx/2026-08-29__legacy.gpx',
    'owner_count_record': 'data/reconstructions/habu_captures/2026-08-count-correction-owner-confirmed-47.json',
    'captures': CAPTURE, 'individuals': INDIVIDUALS,
}

def projected_tables(raw):
    lines = raw.decode('utf-8').splitlines()
    event = dict(event_id=EVENT, operational_date='2026-08-29',
        event_time_local='2026-08-29T23:58:00+09:00', event_place='',
        event_type='capture', event_count=1, latitude=lines[9660], longitude=lines[9661],
        surface=lines[9658], source_note=lines[9655])
    occurrence = dict(individual_id=EVENT+'-OCC01', event_id=EVENT, individual_index=1,
        operational_date='2026-08-29', event_time_local=event['event_time_local'], event_place='',
        size_note='130~150', sex='メス', behavior=lines[9656], microhabitat=lines[9657])
    return csv_bytes(list(event), [event]), csv_bytes(list(occurrence), [occurrence])

def fixture(root):
    for role, path in SOURCE_PATHS.items():
        if role not in {'captures', 'individuals'}:
            write(root, path, native(path))
    captures, individuals = projected_tables((root/NATIVE).read_bytes())
    write(root, CAPTURE, captures)
    write(root, INDIVIDUALS, individuals)
    if (ROOT/ADMISSION).exists():
        tracked = subprocess.run(['git','cat-file','-e','HEAD:'+ADMISSION],cwd=ROOT,capture_output=True).returncode == 0
        write(root, ADMISSION, native(ADMISSION) if tracked else (ROOT/ADMISSION).read_bytes())

def policy(root, entries):
    write(root, 'policies/observation_evidence.json', canonical_bytes(dict(
        schema_version='1.0', sources=entries, sessions=[], outcome_coverage=[])))

class InitialAdmissionTests(unittest.TestCase):
    def test_closed_family_api_is_present(self):
        self.assertIsNotNone(importlib.util.find_spec('august_positive_source_review'))

    def test_new_family_prefix_cannot_downgrade_to_legacy_outcome_flag(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);fixture(root)
            review = dict(schema_version='1.0', source_sha256=reference(root,CAPTURE)['sha256'],
                reviewed_at=NOW, use_roles=['outcome_label'], coordinate_method='flag alone')
            write(root, REVIEW, canonical_bytes(review))
            policy(root,[dict(reference(root,CAPTURE),review_ref=reference(root,REVIEW))])
            context = audit.Audit(root,NOW);audit._declarations(context)
            self.assertNotIn('outcome_label',context.sources.get(CAPTURE,{}).get('use_roles',[]))
            self.assertTrue(any(c['status']=='FAIL' for c in context.checks))

def provisional_review(root, proof=None):
    import august_positive_source_review as module
    context=audit.Audit(root,NOW)
    def point():context.points+=1;context.tick()
    ref=reference(root,ADMISSION)
    if proof is None:
        proof=module.reproduce_sources(ref,read_ref=context.ref,tick=context.tick,consume_point=point)
    return dict(schema_version='1.0',verification_profile=PROFILE,
        descriptor_ref=ref,source_refs={k:reference(root,v) for k,v in SOURCE_PATHS.items()},
        source_sha256=reference(root,CAPTURE)['sha256'],use_roles=['outcome_label'],
        reviewed_at=NOW,cohort_exposure='RESEARCH_EXPOSED',scope=module.SCOPE,
        independent_device_authentication='NOT_ESTABLISHED',permanent_biological_identity='NOT_ESTABLISHED',
        coordinate_method=module.COORDINATE_METHOD,recovery_class=module.RECOVERY_CLASS,
        proof=deepcopy(proof),proof_sha256=digest(proof),**{key:False for key in module.FORBIDDEN_AUTHORITY})

class FamilySourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);fixture(root);cls.valid=provisional_review(root)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'workspace';fixture(self.root)

    def verify(self, review=None, context=None, read_ref=None, tick=None):
        import august_positive_source_review as module
        context=context or audit.Audit(self.root,NOW)
        def point():context.points+=1;context.tick()
        return module.verify_review(deepcopy(self.valid) if review is None else review,
            read_ref=read_ref or context.ref,tick=tick or context.tick,consume_point=point,now=NOW)

    def declare(self, review=None, entries=None):
        write(self.root,REVIEW,canonical_bytes(self.valid if review is None else review))
        entry=dict(reference(self.root,CAPTURE),review_ref=reference(self.root,REVIEW))
        policy(self.root,[entry] if entries is None else entries)
        context=audit.Audit(self.root,NOW);audit._declarations(context)
        return context

    def assert_no_family_role(self, context):
        self.assertNotIn('outcome_label',context.sources.get(CAPTURE,{}).get('use_roles',[]))
        self.assertTrue(any(c['status']=='FAIL' for c in context.checks))

    def test_actual_one_record_bytes_attributes_and_qc(self):
        proof=self.verify()
        self.assertEqual(proof['event_count'],1);self.assertEqual(proof['individual_occurrence_count'],1)
        row=proof['crosswalk'][0]
        self.assertEqual(row['event_id'],EVENT);self.assertEqual(row['individual_occurrence_id'],EVENT+'-OCC01')
        self.assertEqual((row['source_line_start'],row['source_line_end']),(9654,9663))
        self.assertEqual((row['source_byte_start'],row['source_byte_end_exclusive']),(107486,107604))
        self.assertEqual(row['source_slice_sha256'],'5ccb0b1454360fe58a638f3eea54b86922aab3d7ffe78d87bd19d164b09b33d4')
        self.assertEqual(proof['gpx_qc'],dict(point_count=13565,excluded_points=0,segment_breaks=1,maximum_gap_seconds=148.999))
        self.assertEqual((row['gpx_sequence'],row['gpx_trackpoint_index']),(28616,3222))
        self.assertEqual((row['distance_m'],row['time_delta_seconds'],row['hdop']),(0.573,47.999,4.687))
        self.assertEqual(row['neighboring_gap_seconds'],[1.0,1.0])
        self.assertIs(proof['permanent_biological_identity_verified'],False)
        import august_positive_source_review as module
        self.assertTrue(all(proof[k] is False for k in module.FORBIDDEN_AUTHORITY))
        desc=json.loads((self.root/ADMISSION).read_bytes())
        self.assertEqual(desc['expected_counts'],dict(events=1,source_occurrences=1))
        self.assertEqual(len(desc['records']),1)
        self.assertEqual(desc['records'][0]['legacy_aliases'],[])
        for path,expected in zip((CAPTURE,INDIVIDUALS),projected_tables((self.root/NATIVE).read_bytes())):
            self.assertEqual((self.root/path).read_bytes(),expected)

    def test_only_provisional_private_registration_qualifies_one_positive(self):
        context=self.declare();self.assertEqual(context.sources[CAPTURE]['use_roles'],['outcome_label'])
        result=audit.audit_evidence(self.root,'2026-08-29',verified_at=NOW)
        self.assertEqual(result['status'],'PARTIAL')
        self.assertEqual([e['event_id'] for e in result['outcome_ledger']['events']],[EVENT])
        self.assertEqual(sum(u['label']==1 for u in result['observation_units']),1)
        self.assertFalse(any(u['label']==0 for u in result['observation_units']))
        self.assertEqual(result['outcome_ledger']['denominator_coverage'],'NOT_ESTABLISHED')
        self.assertEqual(result['scientific_validation'],'NOT_VALIDATED')
        self.assertFalse((ROOT/REVIEW).exists(),'Software phase must not publish final review')

    def test_derived_csv_without_policy_remains_diagnostic(self):
        result=audit.audit_evidence(self.root,'2026-08-29',verified_at=NOW)
        self.assertEqual(result['outcome_ledger']['events'],[])
        self.assertFalse(any(u['label'] is not None for u in result['observation_units']))

    def test_descriptor_pins_and_types_reject_before_source_read(self):
        import august_positive_source_review as module
        for field,value in (('path',ADMISSION.replace('9654','5249')),('sha256','0'*64),('size_bytes',True),('size_bytes',2424.0)):
            ref=module.admission_ref();ref[field]=value;calls=[]
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                module.reproduce_sources(ref,read_ref=lambda r:calls.append(r),tick=lambda:None,consume_point=lambda:None)
            self.assertEqual(calls,[])

    def test_public_descriptor_reference_is_owned_before_caller_reader_runs(self):
        import august_positive_source_review as module
        ref=module.admission_ref();expected=ref['sha256'];context=audit.Audit(self.root,NOW);calls=0
        def read(value):
            nonlocal calls
            raw=context.ref(value)
            if value['path']==ADMISSION:
                calls+=1
                if calls==2:ref['sha256']='0'*64
            return raw
        def point():context.points+=1;context.tick()
        proof=module.reproduce_sources(ref,read_ref=read,tick=context.tick,consume_point=point)
        self.assertEqual(ref['sha256'],'0'*64)
        self.assertEqual(proof['descriptor_sha256'],expected)

    def test_changed_or_rehashed_descriptor_cannot_admit_other_records(self):
        import august_positive_source_review as module
        original=(self.root/ADMISSION).read_bytes()
        for key,value in (('source_line_start',5249),('count',2),('count',True),('event_id','NEW'),('legacy_aliases',['alias'])):
            desc=json.loads(original);desc['records'][0][key]=value
            write(self.root,ADMISSION,canonical_bytes(desc))
            for ref in (module.admission_ref(),reference(self.root,ADMISSION)):
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                    a=audit.Audit(self.root,NOW)
                    module.reproduce_sources(ref,read_ref=a.ref,tick=a.tick,consume_point=lambda:None)
        write(self.root,ADMISSION,original)

    def test_each_actual_source_tamper_is_rejected(self):
        for role,path in SOURCE_PATHS.items():
            raw=(self.root/path).read_bytes();write(self.root,path,raw+b' ')
            with self.subTest(role=role),self.assertRaises(ValueError):self.verify()
            write(self.root,path,raw)

    def test_typed_rehashed_proof_and_authority_are_not_flags(self):
        for kind in ('bool','float','identity','authority','profile','roles','backdate','future','source'):
            review=deepcopy(self.valid)
            if kind in ('bool','float'):
                review['proof']['crosswalk'][0]['count']=True if kind=='bool' else 1.0
                review['proof_sha256']=digest(review['proof'])
            elif kind=='identity':review['permanent_biological_identity']='ESTABLISHED'
            elif kind=='authority':review['training_authorized']=True
            elif kind=='profile':review['verification_profile']='unknown'
            elif kind=='roles':review['use_roles']=['outcome_label','observed_exposure']
            elif kind=='backdate':review['reviewed_at']='2026-08-29T00:00:00+00:00'
            elif kind=='future':review['reviewed_at']='2026-10-26T00:00:00+00:00'
            else:review['source_refs']['gpx']['path']='arbitrary.gpx'
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.verify(review)

    def test_all_policy_duplicate_alias_and_bad_orders_stage_before_roles(self):
        write(self.root,REVIEW,canonical_bytes(self.valid))
        good=dict(reference(self.root,CAPTURE),review_ref=reference(self.root,REVIEW))
        for alias in (CAPTURE,CAPTURE.replace('/','\\'),CAPTURE.replace('august-2026/','august-2026/./'),
                      CAPTURE.replace('august-2026','AUGUST-2026'),CAPTURE.replace('.csv','.CSV'),
                      CAPTURE.replace('9654','5249')):
            bad=deepcopy(good);bad['path']=alias
            combinations=([bad],) if alias!=CAPTURE else ()
            for entries in (*combinations,[good,bad],[bad,good]):
                with self.subTest(alias=alias,order=len(entries)):
                    self.assert_no_family_role(self.declare(entries=entries))

    def test_invalid_new_family_set_preserves_both_legacy_profile_roles(self):
        import test_sept28_positive_source_review as sept
        from test_aug31_positive_source_review import snapshot as aug31_snapshot,REVIEW as AUG31_REVIEW
        sept.snapshot(self.root);aug31_snapshot(self.root)
        write(self.root,AUG31_REVIEW,native(AUG31_REVIEW))
        old=json.loads(native('policies/observation_evidence.json'))['sources']
        write(self.root,REVIEW,canonical_bytes(self.valid))
        new=dict(reference(self.root,CAPTURE),review_ref=reference(self.root,REVIEW))
        bad=deepcopy(new);bad['path']=CAPTURE.replace('.csv','.CSV')
        for entries in (old+[new,bad],[bad,new]+old):
            policy(self.root,entries);context=audit.Audit(self.root,NOW);audit._declarations(context)
            self.assert_no_family_role(context)
            self.assertTrue(all(context.sources[e['path']]['use_roles']==['outcome_label'] for e in old))
            self.assertEqual(context.points,22990+17906)

    def test_unknown_missing_and_out_of_family_profile_reject(self):
        for profile in (None,'unknown'):
            review=deepcopy(self.valid)
            if profile is None:del review['verification_profile']
            else:review['verification_profile']=profile
            with self.subTest(profile=profile):self.assert_no_family_role(self.declare(review))
        other='data/processed/capture_events/other.csv'
        write(self.root,other,(self.root/CAPTURE).read_bytes())
        write(self.root,REVIEW,canonical_bytes(self.valid))
        entry=dict(reference(self.root,other),review_ref=reference(self.root,REVIEW))
        context=self.declare(entries=[entry])
        self.assertNotIn('outcome_label',context.sources[other]['use_roles'])

    def test_strict_review_and_policy_duplicate_json_and_nested_limits(self):
        write(self.root,REVIEW,canonical_bytes(self.valid))
        entry=dict(reference(self.root,CAPTURE),review_ref=reference(self.root,REVIEW))
        valid_policy=canonical_bytes(dict(schema_version='1.0',sources=[entry],sessions=[],outcome_coverage=[]))
        for raw in (b'{"sources":[],'+valid_policy[1:],valid_policy.replace(b'"sessions":[]',b'"sessions":[1e999]')):
            write(self.root,'policies/observation_evidence.json',raw)
            context=audit.Audit(self.root,NOW);audit._declarations(context);self.assert_no_family_role(context)
        import august_positive_source_review as module
        for raw in (b'['*65+b'0'+b']'*65,b'{"x":1,"x":2}',b'{"outer":{"x":1e999}}'):
            with self.subTest(raw=raw[:40]),self.assertRaises(ValueError):module._bounded_json(raw,lambda:None)

    def test_global_primary_overlap_includes_other_batch_and_old_aug31(self):
        import august_positive_source_review as module
        checksum=self.valid['source_refs']['native_log']['sha256']
        for keys in ([(checksum,107486,107604)]*2,[(checksum,107485,107600),(checksum,107486,107604)],
                     module._protected_aug31_keys()+[(checksum,112400,112500)]):
            with self.subTest(keys=keys),self.assertRaises(ValueError):module._assert_disjoint(keys,lambda:None)

    def test_shared_caps_and_ordinary_caller_exception_identity(self):
        for resource in ('point','bytes','time'):
            context=audit.Audit(self.root,NOW)
            if resource=='point':context.points=audit.MAX_POINTS
            elif resource=='bytes':context.read_bytes=audit.MAX_READ_BYTES-1
            else:context.deadline=0
            with self.subTest(resource=resource),self.assertRaises(audit.AuditBudgetExceeded):self.verify(context=context)
        for error in (ValueError('caller'),TimeoutError('caller'),audit.AuditBudgetExceeded('caller'),MemoryError('caller')):
            for stop in (1,30,2000):
                calls=0
                def check():
                    nonlocal calls
                    calls+=1
                    if calls==stop:raise error
                with self.subTest(error=type(error),at=stop),self.assertRaises(type(error)) as caught:self.verify(tick=check)
                self.assertIs(caught.exception,error)

    def test_owned_review_and_final_descriptor_rescan(self):
        review=deepcopy(self.valid);context=audit.Audit(self.root,NOW)
        def mutate_caller(ref):
            review['proof']['event_count']=999
            return context.ref(ref)
        self.assertEqual(self.verify(review,context,mutate_caller)['event_count'],1)
        context=audit.Audit(self.root,NOW);calls=[]
        def late(ref):
            raw=context.ref(ref);calls.append(ref['path'])
            if len(calls)==13:write(self.root,ADMISSION,(self.root/ADMISSION).read_bytes()+b' ')
            return raw
        with self.assertRaises(ValueError):self.verify(context=context,read_ref=late)

    def test_parent_late_input_change_and_final_seal_expiry_clear_units(self):
        self.declare();original=audit._osm
        def mutate(context):
            result=original(context);write(self.root,NATIVE,(self.root/NATIVE).read_bytes()+b' ');return result
        with patch.object(audit,'_osm',mutate):result=audit.audit_evidence(self.root,'2026-08-29',verified_at=NOW)
        self.assertEqual(result['observation_units'],[]);self.assertEqual(result['outcome_ledger']['events'],[])
        fixture(self.root);self.declare();instances=[];base=audit.Audit;native_digest=audit.digest
        class Observed(base):
            def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);instances.append(self)
        def expire(value):
            output=native_digest(value)
            if isinstance(value,dict) and value.get('observation_units'):instances[-1].deadline=0
            return output
        with patch.object(audit,'Audit',Observed),patch.object(audit,'digest',expire):
            result=audit.audit_evidence(self.root,'2026-08-29',verified_at=NOW)
        self.assertEqual(result['status'],'BLOCKED');self.assertEqual(result['observation_units'],[])
        self.assertEqual(result['outcome_ledger']['events'],[])

    def test_genuine_directory_links_reject_without_external_payload_open(self):
        self.declare()
        for path in (CAPTURE,REVIEW,ADMISSION):
            parent=(self.root/path).parent;outside=Path(self.temp.name)/'outside'
            self.assertTrue(parent.resolve().is_relative_to(self.root.resolve()))
            self.assertTrue(outside.absolute().is_relative_to(Path(self.temp.name).resolve()))
            preserved={p.relative_to(parent).as_posix():p.read_bytes() for p in parent.rglob('*') if p.is_file()}
            parent.rename(outside)
            try:
                if os.name=='nt':
                    subprocess.run(['cmd','/c','mklink','/J',str(parent),str(outside)],check=True,capture_output=True)
                    self.assertTrue(parent.is_junction());self.assertFalse(parent.is_symlink())
                else:parent.symlink_to(outside,target_is_directory=True);self.assertTrue(parent.is_symlink())
                observed=[];original=Path.open
                def observe(target,*args,**kwargs):
                    if target.resolve().is_relative_to(outside):observed.append(str(target))
                    return original(target,*args,**kwargs)
                with patch.object(Path,'open',observe):
                    context=audit.Audit(self.root,NOW);audit._declarations(context)
                self.assert_no_family_role(context);self.assertEqual(observed,[])
            finally:
                if parent.is_symlink():parent.unlink()
                elif os.name=='nt' and parent.is_junction():os.rmdir(parent)
                outside.rename(parent)
            self.assertEqual({p.relative_to(parent).as_posix():p.read_bytes() for p in parent.rglob('*') if p.is_file()},preserved)

class LegacyCapsuleTests(unittest.TestCase):
    def test_immutable_old_profile_whole_proof_and_read_open_order(self):
        import aug31_positive_source_review as current
        from test_aug31_positive_source_review import snapshot,provisional_review as old_review,SOURCE_PATHS as OLD_PATHS
        path=ROOT/'tests/fixtures/aug31_positive_source_review_original.py.txt'
        raw=path.read_text(encoding='utf-8').encode('utf-8')
        self.assertEqual(len(raw),16887)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'bf5d204ab2f2d2ea39df2e2824f2e10f04eedc7bdd3a0cfc91237d2929841e41')
        old=types.ModuleType('frozen_aug31_original');exec(compile(raw,str(path),'exec'),old.__dict__)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);snapshot(root);review=old_review(root,now=NOW)
            values=[]
            for module in (old,current):
                context=audit.Audit(root,NOW);order=[];opened=[];actual=Path.open
                def read(ref):
                    raw=context.ref(ref);order.append(dict(ref=ref,size=len(raw),sha256=hashlib.sha256(raw).hexdigest()));return raw
                def op(target,*args,**kwargs):opened.append(target.relative_to(root).as_posix());return actual(target,*args,**kwargs)
                def point():context.points+=1;context.tick()
                with patch.object(Path,'open',op):proof=module.verify_review(review,read_ref=read,tick=context.tick,consume_point=point,now=NOW)
                values.append(canonical_bytes(dict(proof=proof,order=order,opened=opened,reads=context.reads,bytes=context.read_bytes,points=context.points)))
            self.assertEqual(values[0],values[1])

    def test_hermetic_old_auditor_whole_results_read_and_open_ledgers(self):
        from test_aug31_positive_source_review import snapshot,provisional_review as old_review,REVIEW as OLD_REVIEW,CAPTURE as OLD_CAPTURE
        path=ROOT/'tests/fixtures/evidence_audit_before_august_family.py.txt'
        raw=path.read_text(encoding='utf-8').encode('utf-8')
        self.assertEqual(len(raw),45897)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'4329ed74e1f58b63b3010beda76859beabe9b5f3be2f517efc8bc904a209cd4b')
        old=types.ModuleType('frozen_auditor_before_family');exec(compile(raw,str(path),'exec'),old.__dict__)
        self.assertIsNot(old.audit_evidence,audit.audit_evidence)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);snapshot(root)
            write(root,OLD_REVIEW,canonical_bytes(old_review(root,now=NOW)))
            policy(root,[dict(reference(root,OLD_CAPTURE),review_ref=reference(root,OLD_REVIEW))])
            values=[]
            for module in (old,audit):
                instances=[];base=module.Audit;opened=[];actual=Path.open
                class Observed(base):
                    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.order=[];instances.append(self)
                    def read(self,path,*,max_bytes=None):
                        raw=super().read(path,max_bytes=max_bytes)
                        self.order.append(dict(path=path,max_bytes=max_bytes,size=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
                        return raw
                def op(target,*args,**kwargs):opened.append(target.relative_to(root).as_posix());return actual(target,*args,**kwargs)
                with patch.object(module,'Audit',Observed),patch.object(Path,'open',op):
                    result=module.audit_evidence(root,'2026-08-31',verified_at=NOW)
                context=instances[0]
                self.assertEqual(result['status'],'PARTIAL')
                self.assertEqual(len(result['outcome_ledger']['events']),2)
                self.assertTrue(all('august-2026/' not in r['path'] for r in context.order))
                values.append(canonical_bytes(dict(result=result,reads=context.reads,bytes=context.read_bytes,
                    points=context.points,order=context.order,opened=opened)))
            self.assertEqual(values[0],values[1])

if __name__ == '__main__':
    unittest.main()
