"""Synthetic planned intent only; no observation, source or forecast authority."""
import copy
from datetime import datetime
import hashlib
import importlib
import importlib.util
import json
import random
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from master_contracts import canonical_bytes, digest
from prospective_inputs import ProspectiveReadContext, READINESS_FIELDS

NIGHT='2026-10-26'
CUTOFF=NIGHT+'T19:00:00+09:00'
ASOF=NIGHT+'T19:05:00+09:00'
ISSUED=NIGHT+'T18:00:00+09:00'
READY=NIGHT+'T18:30:00+09:00'
PROJECTED=NIGHT+'T18:45:00+09:00'
START=NIGHT+'T20:00:00+09:00'
END=NIGHT+'T20:20:00+09:00'


def bound(path,stamp=READY,sha='a'*64,size=128):
    return dict(ref=dict(path=path,sha256=sha,size_bytes=size),
        readiness=dict.fromkeys(READINESS_FIELDS,stamp),usable_at=stamp)


class PlanFixture:
    def __init__(self):
        self.domain=dict(schema_version='habu-planned-effort-domain-v1',operational_night=NIGHT,
            cutoff_time=CUTOFF,horizon=dict(start=START,end=END),cells=[[4000,30000],[4001,30000]])
        self.identity=dict(owner_id='synthetic-owner',observer_id='synthetic-observer',method_version='synthetic-v1',crew_size=1)
        self.plan=dict(schema_version='habu-planned-search-source-v1',plan_id='synthetic-plan',revision_id='revision-1',
            issued_at=ISSUED,purpose='FUTURE_DECLARED_ACTIVE_HABU_SEARCH',operational_night=NIGHT,
            domain_sha256=digest(self.domain),horizon=dict(start=START,end=END),coverage='DECLARED_COMPLETE',
            allocations=[dict(allocation_id='a',cell_x=4000,cell_y=30000,start=NIGHT+'T20:05:00+09:00',
                end=NIGHT+'T20:15:00+09:00',planned_active_search_seconds=600),
                dict(allocation_id='b',cell_x=4001,cell_y=30000,start=NIGHT+'T20:15:00+09:00',
                end=END,planned_active_search_seconds=300)],**self.identity)
        self.bindings=dict(source=bound('data/raw/planned_search/synthetic.json'),
            domain=bound('features/synthetic-domain.json',NIGHT+'T17:00:00+09:00',sha='d'*64),
            code=bound('src/g0_planned_effort_projection.py',NIGHT+'T17:00:00+09:00',sha='c'*64),
            projection=dict(readiness=dict.fromkeys(READINESS_FIELDS,PROJECTED),usable_at=PROJECTED))
        self.publish()

    def publish(self,raw=None):
        self.raw=canonical_bytes(self.plan) if raw is None else raw
        self.bindings['source']['ref'].update(sha256=hashlib.sha256(self.raw).hexdigest(),size_bytes=len(self.raw))

    def delay(self,role,field,stamp):
        item=self.bindings[role]
        item['readiness'][field]=stamp
        item['usable_at']=max(item['readiness'].values(),key=datetime.fromisoformat)
        projection=self.bindings['projection']
        projection['usable_at']=max([*projection['readiness'].values(),
            *(self.bindings[r]['usable_at'] for r in ('source','domain','code'))],key=datetime.fromisoformat)


class PlannedEffortTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('g0_planned_effort_projection'),'typed projection is missing')
        self.module=importlib.import_module('g0_planned_effort_projection')
        self.fixture=PlanFixture()
        self.context=ProspectiveReadContext(300,2*1024**3)

    def call(self,raw='fixture',**kwargs):
        f=self.fixture
        return self.module.project_planned_effort(f.raw if raw=='fixture' else raw,f.domain,f.bindings,
            expected_domain_sha256=kwargs.pop('expected_domain_sha256',digest(f.domain)),
            expected_identity=kwargs.pop('expected_identity',f.identity),as_of_time=kwargs.pop('as_of_time',ASOF),
            context=kwargs.pop('context',self.context),**kwargs)

    def test_complete_rows_use_exact_half_open_intersections_and_no_authority(self):
        value=self.call()
        self.assertEqual(value['status'],'DECLARED_PLAN_PROJECTED')
        self.assertEqual([r['planned_active_search_seconds'] for r in value['rows']],[300,300,0,300])
        self.assertEqual([r['row_id'] for r in value['rows']],
            ['4000:30000@2026-10-26T11:00:00Z','4000:30000@2026-10-26T11:10:00Z',
             '4001:30000@2026-10-26T11:00:00Z','4001:30000@2026-10-26T11:10:00Z'])
        self.assertEqual(value['counts']['total_planned_active_search_seconds'],900)
        self.assertEqual(value['counts']['projected_rows'],4)
        self.assertEqual(value['source_authenticity'],'NOT_ATTESTED')
        self.assertEqual(value['source_authentication'],'CALLER_DEPENDENCY_REQUIRED')
        for key in ('fit_authorized','scientific_execution_authorized','selection_authorized','promotion_authorized',
                    'confirmation_authorized','official_issuance_authorized','production_authorized',
                    'g0_forecast_authorized','count_denominator_authorized'):
            self.assertIs(value[key],False)
        self.assertEqual(value['receipt_sha256'],digest({k:v for k,v in value.items() if k!='receipt_sha256'}))

    def test_physical_source_hash_and_canonical_domain_hash_do_not_authenticate_other_files(self):
        f=self.fixture
        f.publish(json.dumps(f.plan,ensure_ascii=False,indent=2).encode())
        value=self.call()
        self.assertEqual(value['source_sha256'],hashlib.sha256(f.raw).hexdigest())
        self.assertEqual(value['source_canonical_sha256'],digest(f.plan))
        self.assertNotEqual(value['source_sha256'],value['source_canonical_sha256'])
        self.assertEqual(value['domain_canonical_sha256'],digest(f.domain))
        self.assertNotEqual(value['domain_canonical_sha256'],f.bindings['domain']['ref']['sha256'])
        self.assertFalse(value['domain_physical_bytes_verified'])
        self.assertFalse(value['code_physical_bytes_verified'])

    def test_complete_empty_plan_is_planned_zero_not_a_measured_denominator(self):
        self.fixture.plan['allocations']=[];self.fixture.publish()
        value=self.call()
        self.assertEqual(value['status'],'DECLARED_PLAN_PROJECTED')
        self.assertEqual([r['planned_active_search_seconds'] for r in value['rows']],[0,0,0,0])
        self.assertEqual(value['counts']['total_planned_active_search_seconds'],0)
        self.assertFalse(value['count_denominator_authorized'])
        self.assertNotIn('label',value['rows'][0])
        self.assertNotIn('active_search_seconds',value['rows'][0])

    def test_missing_or_unknown_plan_does_not_publish_zero_rows_or_partial_totals(self):
        self.fixture.plan['coverage']='UNKNOWN';self.fixture.publish()
        for raw in (self.fixture.raw,None):
            with self.subTest(raw_present=raw is not None):
                value=self.call(raw)
                self.assertEqual(value['status'],'NEED_MORE_DATA')
                self.assertEqual(value['rows'],[])
                self.assertIsNone(value['counts']['total_planned_active_search_seconds'])
                self.assertEqual(value['blocker_kind'],'DATA_BLOCKED')

    def test_none_and_unknown_do_not_mask_known_schema_scope_or_readiness_conflicts(self):
        for missing in (False,True):
            for bad in ('domain','code','max','owner','scope'):
                self.fixture=PlanFixture();f=self.fixture
                f.plan['coverage']='UNKNOWN'
                if bad=='domain':f.domain['cells'][0][0]=999
                elif bad=='code':f.bindings['code']['ref']['path']='src/other.py'
                elif bad=='max':f.bindings['source']['usable_at']=ISSUED
                elif bad=='owner':f.identity['owner_id']=''
                else:f.domain['horizon']['end']=START
                f.publish()
                with self.subTest(missing=missing,bad=bad),self.assertRaises(ValueError):self.call(None if missing else f.raw)

    def test_unknown_coverage_does_not_mask_outside_allocation_or_source_hash_conflicts(self):
        for bad in ('cell','time','seconds','hash'):
            self.fixture=PlanFixture();f=self.fixture;f.plan['coverage']='UNKNOWN'
            if bad=='cell':f.plan['allocations'][0]['cell_x']=4002
            elif bad=='time':f.plan['allocations'][0]['start']=NIGHT+'T19:59:59+09:00'
            elif bad=='seconds':f.plan['allocations'][0]['planned_active_search_seconds']=599
            f.publish()
            if bad=='hash':f.bindings['source']['ref']['sha256']='f'*64
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.call()

    def test_duplicate_ids_and_same_observer_overlap_across_cells_or_timezone_aliases_reject(self):
        for bad in ('id','same_cell','other_cell','timezone'):
            self.fixture=PlanFixture();f=self.fixture;a,b=f.plan['allocations']
            if bad=='id':b['allocation_id']='a'
            else:
                b.update(start=NIGHT+'T20:10:00+09:00',end=END,planned_active_search_seconds=600)
                if bad=='same_cell':b['cell_x']=4000
                if bad=='timezone':b['start']='2026-10-26T11:10:00Z';b['end']='2026-10-26T11:20:00Z'
            f.publish()
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.call()

    def test_adjacent_same_cell_intervals_conserve_explicit_seconds(self):
        f=self.fixture
        f.plan['allocations'][1]['cell_x']=4000;f.publish()
        value=self.call()
        self.assertEqual([r['planned_active_search_seconds'] for r in value['rows']],[300,600,0,0])

    def test_every_readiness_field_at_cutoff_is_data_blocked_without_hiding_bad_max(self):
        for role in ('source','domain','code','projection'):
            for field in READINESS_FIELDS:
                self.fixture=PlanFixture();self.fixture.delay(role,field,CUTOFF)
                with self.subTest(role=role,field=field):
                    value=self.call()
                    self.assertEqual(value['status'],'NEED_MORE_DATA')
                    self.assertEqual(value['rows'],[])
                    self.assertEqual(value['blocker_kind'],'DATA_BLOCKED')
        self.fixture.bindings['projection']['usable_at']=ISSUED
        with self.assertRaises(ValueError):self.call()

    def test_source_and_projection_each_own_stage_cannot_precede_plan_issue(self):
        for role in ('source','projection'):
            for field in READINESS_FIELDS:
                self.fixture=PlanFixture()
                self.fixture.bindings[role]['readiness'][field]=NIGHT+'T17:59:59+09:00'
                with self.subTest(role=role,field=field),self.assertRaises(ValueError):self.call()

    def test_missing_readiness_unknown_trust_or_actual_measurement_fields_reject(self):
        for bad in ('ready','trust','gpx','measured','extra_domain'):
            self.fixture=PlanFixture();f=self.fixture
            if bad=='ready':f.bindings['source']['readiness'].pop('audited_at')
            elif bad=='extra_domain':f.domain['is_plan']=True
            else:f.plan[{'trust':'trusted','gpx':'gpx_trace','measured':'active_search_seconds'}[bad]]=0
            f.publish()
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.call()

    def test_integer_only_raw_boolean_float_nonfinite_and_big_integer_reject_before_decode(self):
        f=self.fixture
        for token in (b'true',b'1.0',b'1e0',b'NaN',b'Infinity',b'9'*21):
            raw=f.raw.replace(b'"crew_size":1',b'"crew_size":'+token)
            f.publish(raw)
            original=self.module.json.loads
            def loads(value,*args,**kwargs):
                if value==raw or value==raw.decode():raise AssertionError('unsafe raw token reached decoder')
                return original(value,*args,**kwargs)
            with self.subTest(token=token),patch.object(self.module.json,'loads',side_effect=loads),self.assertRaises(ValueError):self.call()
            f.publish()

    def test_depth_long_token_and_oversized_raw_are_blocked_before_decoding(self):
        for raw in (b'['*13+b'{}'+b']'*13,b'{"x":"'+b'a'*30000+b'"}',b' '* (4*1024**2+1)):
            self.fixture.publish(raw)
            original=self.module.json.loads
            def loads(value,*args,**kwargs):
                if value==raw or value==raw.decode():raise AssertionError('raw resource limit reached decoder')
                return original(value,*args,**kwargs)
            with self.subTest(size=len(raw)),patch.object(self.module.json,'loads',side_effect=loads),self.assertRaises(self.module.PlannedEffortCapacityError):self.call()

    def test_duplicate_json_keys_at_top_and_nested_depth_reject(self):
        f=self.fixture
        for old,new in ((b'"crew_size":1',b'"crew_size":2,"crew_size":1'),
                        (b'"cell_x":4000',b'"cell_x":4001,"cell_x":4000')):
            raw=f.raw.replace(old,new);f.publish(raw)
            with self.subTest(old=old),self.assertRaises(ValueError):self.call()
            f.publish()

    def test_unicode_and_escaped_string_tokens_are_not_misread_as_json_structure(self):
        self.fixture.plan['plan_id']='計画-"\\[{true,012.3'
        self.fixture.publish()
        self.assertEqual(self.call()['status'],'DECLARED_PLAN_PROJECTED')

    def test_physical_domain_hash_identity_bad_coordinates_and_ambiguous_seconds_reject(self):
        for bad in ('expected_hash','header_hash','owner','method','cellbool','unsorted','fraction','zero_interval'):
            self.fixture=PlanFixture();f=self.fixture
            kwargs={}
            if bad=='expected_hash':kwargs['expected_domain_sha256']='f'*64
            elif bad=='header_hash':f.plan['domain_sha256']='f'*64
            elif bad=='owner':f.identity['owner_id']='other'
            elif bad=='method':f.identity['method_version']='other'
            elif bad=='cellbool':f.domain['cells'][0][0]=True
            elif bad=='unsorted':f.domain['cells'].reverse()
            elif bad=='fraction':f.plan['allocations'][0]['start']=NIGHT+'T20:05:00.5+09:00'
            else:f.plan['allocations'][0].update(end=NIGHT+'T20:05:00+09:00',planned_active_search_seconds=0)
            f.publish()
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.call(**kwargs)

    def test_multi_crew_is_explicitly_unsupported_and_identity_mismatch_is_invalid(self):
        f=self.fixture;f.plan['crew_size']=2;f.identity['crew_size']=2;f.publish()
        with self.assertRaises(self.module.PlannedEffortCapabilityBlocked):self.call()
        f.identity['crew_size']=1
        with self.assertRaises(ValueError):self.call()

    def test_malformed_night_or_container_fields_raise_valueerror(self):
        for value in (None,1,[],{}):
            self.fixture=PlanFixture();self.fixture.domain['operational_night']=value
            with self.subTest(value=value),self.assertRaises(ValueError):self.call()

    def test_end_at_next_07_is_half_open_but_cross_night_or_asof_equality_reject(self):
        f=self.fixture
        f.domain['horizon']=dict(start='2026-10-27T06:50:00+09:00',end='2026-10-27T07:00:00+09:00')
        f.plan.update(domain_sha256=digest(f.domain),horizon=copy.deepcopy(f.domain['horizon']),allocations=[]);f.publish()
        self.assertEqual(len(self.call()['rows']),2)
        for bad in ('end','asof','night'):
            self.fixture=PlanFixture();f=self.fixture
            kwargs={}
            if bad=='end':f.domain['horizon']['end']='2026-10-27T07:10:00+09:00'
            elif bad=='asof':kwargs['as_of_time']=START
            else:f.domain['cutoff_time']=NIGHT+'T06:00:00+09:00'
            f.publish()
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.call(**kwargs)

    def test_pre_copy_complexity_and_combined_byte_capacity_do_not_allocate_owned_json(self):
        for constant,limit in (('MAX_JSON_NODES',10),('MAX_INPUT_BYTES',len(self.fixture.raw)+10)):
            with self.subTest(constant=constant),patch.object(self.module,constant,limit),\
                    patch.object(self.module.json,'loads',side_effect=AssertionError('copied before resource check')),\
                    self.assertRaises(self.module.PlannedEffortCapacityError):self.call()

    def test_huge_negative_object_integer_is_blocked_before_abs_or_encoding(self):
        huge=-(1<<1_000_000)
        for location in ('domain','bindings','identity'):
            self.fixture=PlanFixture();f=self.fixture;expected=digest(f.domain)
            huge_abs=[]
            def observed_abs(value):
                if value is huge:
                    huge_abs.append(True);raise AssertionError('oversized integer reached abs')
                return abs(value)
            if location=='domain':f.domain['cells'][0][0]=huge
            elif location=='bindings':f.bindings['source']['ref']['size_bytes']=huge
            else:f.identity['crew_size']=huge
            with self.subTest(location=location),\
                    patch.object(self.module,'abs',side_effect=observed_abs,create=True),\
                    patch.object(self.module,'_encode',side_effect=AssertionError('oversized integer reached encoder')),\
                    self.assertRaises(self.module.PlannedEffortCapacityError):
                self.module.project_planned_effort(f.raw,f.domain,f.bindings,expected_domain_sha256=expected,
                    expected_identity=f.identity,as_of_time=ASOF,context=self.context)
            self.assertEqual(huge_abs,[])

    def test_in_memory_integer_magnitude_keeps_signed_twenty_digit_boundary(self):
        for value in (-10**20+1,-1,0,1,10**20-1):
            with self.subTest(value=value):self.module._preflight(value,self.context.check)
        for value in (-10**20,10**20):
            with self.subTest(value=value),self.assertRaises(self.module.PlannedEffortCapacityError):
                self.module._preflight(value,self.context.check)

    def test_row_and_output_capacity_never_return_a_partial_projection(self):
        with patch.object(self.module,'MAX_OUTPUT_ROWS',3),self.assertRaises(self.module.PlannedEffortCapacityError):self.call()
        original=self.module._rows;built=[]
        def rows(*args,**kwargs):
            value=original(*args,**kwargs);built.append(len(value[0]));return value
        with patch.object(self.module,'MAX_OUTPUT_BYTES',100),patch.object(self.module,'_rows',side_effect=rows),\
                self.assertRaises(self.module.PlannedEffortCapacityError):self.call()
        self.assertEqual(built,[4],'output cap must exercise the output encoder, not an unrelated input hash')

    def test_sealed_result_size_includes_hash_field_and_exact_boundary_passes(self):
        baseline=self.call();size=len(canonical_bytes(baseline))
        with patch.object(self.module,'MAX_OUTPUT_BYTES',size-1),self.assertRaises(self.module.PlannedEffortCapacityError):
            self.call()
        with patch.object(self.module,'MAX_OUTPUT_BYTES',size):value=self.call()
        self.assertEqual(value,baseline)
        self.assertEqual(value['receipt_sha256'],digest({k:v for k,v in value.items() if k!='receipt_sha256'}))

    def test_final_sealed_encoding_is_checked_and_preserves_context_exception_identity(self):
        original=self.module._encode;seen=[];error=TimeoutError('after sealed encoding')
        def encode(value,check,limit):
            yield from original(value,check,limit)
            if type(value) is dict and 'receipt_sha256' in value:
                seen.append(True)
        # The public function captures the existing bound check. Its context must
        # expire at the end of the actual final encoding, before any return.
        original_check=self.context.check
        def check():
            if seen:raise error
            original_check()
        self.context.check=check
        with patch.object(self.module,'_encode',side_effect=encode),self.assertRaises(TimeoutError) as raised:self.call()
        self.assertEqual(seen,[True])
        self.assertIs(raised.exception,error)

    def test_native_audit_observer_confirms_no_filesystem_or_network_operations(self):
        active=[True];seen=[]
        def observe(event,args):
            if active[0] and (event=='open' or event.startswith(('socket.','subprocess.')) or event in ('os.listdir','os.scandir')):
                seen.append(event);raise AssertionError('pure projection performed I/O: '+event)
        sys.addaudithook(observe)
        try:value=self.call()
        finally:active[0]=False
        self.assertEqual(seen,[])
        self.assertEqual(value['status'],'DECLARED_PLAN_PROJECTED')

    def test_actual_read_ledger_deadline_and_inputs_are_not_mutated(self):
        f=self.fixture;before=copy.deepcopy((f.domain,f.bindings,f.identity,f.plan))
        self.context.account(17)
        original=(self.context.bytes_read,self.context.max_bytes,self.context.deadline)
        first=self.call();second=self.call()
        self.assertEqual(first,second)
        self.assertEqual(original,(self.context.bytes_read,self.context.max_bytes,self.context.deadline))
        self.assertEqual(before,(f.domain,f.bindings,f.identity,f.plan))

    def test_context_exceptions_propagate_by_identity(self):
        for count,error in ((1,RuntimeError('first')),(50,ValueError('middle')),(200,TimeoutError('later'))):
            original=self.context.check;calls=[]
            def check():
                calls.append(True)
                if len(calls)==count:raise error
                original()
            self.context.check=check
            try:
                with self.subTest(count=count),self.assertRaises(type(error)) as raised:self.call()
                self.assertIs(raised.exception,error)
            finally:self.context.check=original

    def test_owned_snapshot_survives_caller_mutation_during_hash(self):
        f=self.fixture;original=self.module._digest;changed=[]
        def hashing(value,*args,**kwargs):
            if not changed:
                changed.append(True);f.domain['cells'][0][0]=4500;f.bindings['source']['ref']['sha256']='e'*64
            return original(value,*args,**kwargs)
        with patch.object(self.module,'_digest',side_effect=hashing):value=self.call()
        self.assertEqual(value['rows'][0]['cell_x'],4000)
        self.assertEqual(value['source_sha256'],hashlib.sha256(f.raw).hexdigest())

    def test_final_seal_expiry_cannot_return_success(self):
        original=self.module._digest
        def hashing(value,*args,**kwargs):
            result=original(value,*args,**kwargs)
            if type(value) is dict and value.get('status')=='DECLARED_PLAN_PROJECTED':self.context.deadline=0
            return result
        with patch.object(self.module,'_digest',side_effect=hashing),self.assertRaises(TimeoutError):self.call()

    def test_incomplete_receipt_final_hash_is_also_deadline_checked(self):
        for missing in (False,True):
            self.context=ProspectiveReadContext(300,2*1024**3)
            self.fixture=PlanFixture();self.fixture.plan['coverage']='UNKNOWN';self.fixture.publish()
            original=self.module._digest
            def hashing(value,*args,**kwargs):
                result=original(value,*args,**kwargs)
                if type(value) is dict and value.get('status')=='NEED_MORE_DATA':self.context.deadline=0
                return result
            with self.subTest(missing=missing),patch.object(self.module,'_digest',side_effect=hashing),self.assertRaises(TimeoutError):
                self.call(None if missing else self.fixture.raw)

    def test_forbidden_ref_paths_physical_size_and_wrong_context_reject_without_reads(self):
        for path in ('/absolute.json','data/../outside.json','data//x.json','C:/source.json',
                     'data/sealed/plan.json','data/Confirmation/plan.json','data/ORIGINAL/plan.json','data/x\\plan.json'):
            self.fixture=PlanFixture();self.fixture.bindings['source']['ref']['path']=path
            with self.subTest(path=path),self.assertRaises(ValueError):self.call()
        self.fixture=PlanFixture();self.fixture.bindings['source']['ref']['size_bytes']+=1
        with self.assertRaises(ValueError):self.call()
        self.fixture=PlanFixture()
        with self.assertRaises(ValueError):self.call(context=None)

    def test_deterministic_random_allocations_match_independent_one_second_oracle(self):
        from datetime import timedelta
        rng=random.Random(1642)
        for trial in range(40):
            self.fixture=PlanFixture();f=self.fixture
            f.domain['cells'].append([4002,30000]);f.domain['horizon']['end']=NIGHT+'T21:00:00+09:00'
            f.plan.update(domain_sha256=digest(f.domain),horizon=copy.deepcopy(f.domain['horizon']),allocations=[])
            expected={(cell,window):0 for cell in range(4000,4003) for window in range(6)}
            second=0;origin=datetime.fromisoformat(START)
            for index in range(35):
                second+=rng.randrange(0,31)
                if second>=3600:break
                stop=min(3600,second+rng.randrange(1,151));cell=rng.randrange(4000,4003)
                f.plan['allocations'].append(dict(allocation_id=f'{trial}-{index}',cell_x=cell,cell_y=30000,
                    start=(origin+timedelta(seconds=second)).isoformat(),end=(origin+timedelta(seconds=stop)).isoformat(),
                    planned_active_search_seconds=stop-second))
                for tick in range(second,stop):expected[(cell,tick//600)]+=1
                second=stop
            rng.shuffle(f.plan['allocations']);f.publish()
            value=self.call()
            actual={(row['cell_x'],index%6):row['planned_active_search_seconds'] for index,row in enumerate(value['rows'])}
            self.assertEqual(actual,expected)
            self.assertEqual(value['counts']['total_planned_active_search_seconds'],sum(expected.values()))


if __name__=='__main__':unittest.main()
