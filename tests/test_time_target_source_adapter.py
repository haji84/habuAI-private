"""Synthetic caller target selection at declared G0 centres; no real forecast."""
import copy
from datetime import timedelta
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from codex_cycle_contract import POLICY_DIGEST
from master_contracts import canonical_bytes,digest
from prospective_inputs import _time,InputCapacityError
from test_g0_forecast_contract import base_ref
from test_stage1_configured_source_adapter import ConfiguredSourceFixture

try:
    from evaluation import time_target_source_adapter as adapter
except ImportError:
    adapter=None


class SourceTargets:
    def __init__(self,case):
        self.f=ConfiguredSourceFixture(case); self.refresh()

    def refresh(self,candidate_id=None):
        self.values=self.f.projections()
        context,forecast,prepared=self.values
        scope=self.f.source.scope
        self.universe=dict(schema_version='habu-time-target-universe-v1',
            **{key:copy.deepcopy(scope[key]) for key in ('operational_night','cutoff_time',
                'horizon_start','horizon_end','scope')},scope_sha256=digest(scope['scope']),
            forecast_receipt_sha256=digest(forecast['receipt']),
            joined_forecast_sha256=forecast['receipt']['canonical_joined_rows_sha256'],
            units=[{key:row[key] for key in ('row_id','window_start_jst','utm_x_m','utm_y_m')}
                for row in forecast['rows']])
        self.universe['universe_sha256']=digest(self.universe)
        candidate=next(c for c in prepared['candidates'] if c['candidate_id']==candidate_id) if candidate_id else prepared['candidates'][0]
        self.candidate_id=candidate['candidate_id']
        first=min(forecast['rows'],key=lambda row:(_time(row['window_start_jst']),row['utm_x_m'],row['utm_y_m']))
        self.targets=dict(schema_version='habu-time-target-set-v1',produced=True,
            model_sha256=candidate['model_sha256'],prediction_sha256=candidate['prediction_sha256'],
            universe_sha256=self.universe['universe_sha256'],targets=[dict(target_id='external-A',
                universe_row_id=first['row_id'],predicted_time=(_time(first['window_start_jst'])+timedelta(seconds=300)).isoformat())])
        self.protocol=dict(schema_version='habu-time-target-diagnostic-protocol-v1',phase='DEVELOPMENT',
            g0_policy_sha256=POLICY_DIGEST,target_semantics='OWNER_CAPTURE_EVENT_POINT_TIME',
            **{key:scope[key] for key in ('operational_night','cutoff_time','horizon_start','horizon_end')},
            scope_sha256=digest(scope['scope']),universe_sha256=self.universe['universe_sha256'],
            targets_sha256=None,frozen_at=scope['cutoff_time'],time_anchor='WINDOW_MIDPOINT_300_SECONDS',
            radius_m=100,tolerance_seconds=600,matching_policy='ORDERED_DFS_MAX_EVENT_CARDINALITY_V1')
        self.publish()

    def publish(self):
        self.targets['targets_sha256']=digest({k:v for k,v in self.targets.items() if k!='targets_sha256'})
        self.protocol['targets_sha256']=self.targets['targets_sha256']
        self.target_ref=self.bound('targets',self.targets,'2026-10-14T17:30:00+09:00')
        self.protocol_ref=self.bound('protocol',self.protocol,'2026-10-14T17:40:00+09:00')

    def bound(self,name,value,stamp):
        ref=base_ref(self.f.root,f'evidence/time-target/{name}.json',canonical_bytes(value))
        return dict(ref,readiness=self.f.source.ready(stamp),usable_at=stamp)

    def evaluate(self,**changes):
        context,forecast,prepared=self.values
        args=dict(candidate_config=self.f.config,expected_config_sha256=digest(self.f.config),
            feature_definition_sha256=self.f.parent.request['feature_definition_sha256'],
            candidate_id=self.candidate_id,frozen_targets_ref=self.target_ref,
            protocol_ref=self.protocol_ref,expected_protocol_sha256=digest(self.protocol),context=context)
        args.update(changes)
        return adapter.evaluate_time_target_sources_v1(self.f.root,self.f.source.ref,forecast,prepared,**args)


class TimeTargetSourceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(adapter,'Missing explicit declared-cell-centre T2 source adapter')
        self.f=SourceTargets(self)

    def test_full_source_projection_preserves_every_row_and_outside_event_fn(self):
        result=self.f.evaluate()
        self.assertEqual(result['universe'],self.f.universe)
        self.assertEqual(result['targets'],self.f.targets)
        metrics=result['time_target_result']['metrics']
        self.assertEqual((metrics['event_numerator'],metrics['event_denominator']),(1,2))
        self.assertEqual((metrics['individuals_in_matched_events'],metrics['individual_denominator']),(2,3))
        self.assertEqual(result['time_target_result']['outside_universe_event_ids'],['outside'])
        self.assertIs(result['scientific_authorized'],False)

    def test_missing_scope_preserves_source_summary_and_needs_universe(self):
        source=self.f.f.source; source.manifest['scope_id']=None; source.nodes.pop('scope'); self.f.f.publish()
        result=self.f.evaluate()
        self.assertIsNone(result['universe'])
        self.assertEqual(result['time_target_result']['status'],'NEED_MORE_DATA')
        self.assertEqual(result['time_target_result']['metrics'],{})
        self.assertEqual(result['stage1_bundle']['stage1_result']['source_summary'],dict(capture_events=2,individuals=3))

    def test_unknown_coverage_keeps_known_ledger_but_no_t2_metrics(self):
        self.f.f.source.coverage['declaration']='UNKNOWN'; self.f.f.source.publish(); self.f.f.publish()
        result=self.f.evaluate()
        self.assertEqual(result['stage1_bundle']['ledger']['complete_scopes'][0]['declaration'],'UNKNOWN')
        self.assertEqual(result['time_target_result']['metrics'],{})
        self.assertEqual(result['time_target_result']['status'],'NEED_MORE_DATA')

    def test_missing_forecast_or_prepared_never_creates_native_inputs(self):
        old=self.f.values
        for forecast,prepared in ((None,old[2]),(old[1],None)):
            self.f.values=(old[0],forecast,prepared)
            with patch.object(Path,'open',side_effect=AssertionError('missing native source read')):
                with self.assertRaises(ValueError): self.f.evaluate()

    def test_late_declared_freeze_rejects_before_any_outcome_open(self):
        self.f.protocol['frozen_at']='2026-10-14T18:00:01+09:00'; self.f.publish(); actual=Path.open
        def opening(path,*a,**kw):
            if path.name in ('captures.csv','individuals.csv','coverage.json'):
                raise AssertionError('bad prior freeze allowed outcomes')
            return actual(path,*a,**kw)
        with patch.object(Path,'open',new=opening):
            with self.assertRaises(ValueError): self.f.evaluate()

    def test_context_callback_exceptions_keep_identity_at_entry_and_inside_export(self):
        from evaluation import stage1_source_adapter as source
        context=self.f.values[0]; original_check=context.check; original_scope=source._scope_projection
        for kind in (FileNotFoundError,TypeError,KeyError,IndexError,OverflowError,RecursionError,RuntimeError,TimeoutError):
            for phase in ('entry','source'):
                with self.subTest(error=kind.__name__,phase=phase):
                    marker=kind('caller-check-sentinel')
                    def raising(): raise marker
                    def scope(*a,**kw):
                        context.check=raising
                        return original_scope(*a,**kw)
                    context.check=raising if phase=='entry' else original_check
                    try:
                        with patch.object(source,'_scope_projection',side_effect=scope):
                            with self.assertRaises(kind) as caught: self.f.evaluate()
                        self.assertIs(caught.exception,marker)
                    finally:
                        context.check=original_check

    def test_one_shot_callback_during_real_capture_read_is_never_classified_missing(self):
        from evaluation import stage1_source_adapter as source
        context=self.f.values[0]; original_check=context.check; actual=source.g0.G0ArtifactReader.read
        for marker in (FileNotFoundError('one-shot-caller'),ValueError('Missing prospective input')):
            phase=[False]; fired=[]
            def checked():
                if phase[0] and not fired:
                    fired.append(marker); raise marker
                return original_check()
            def reading(reader,ref,**kw):
                phase[0]=ref['path']==self.f.f.source.nodes['captures']['ref']['path']
                try: return actual(reader,ref,**kw)
                finally: phase[0]=False
            context.check=checked
            try:
                with patch.object(source.g0.G0ArtifactReader,'read',new=reading):
                    with self.assertRaises(type(marker)) as caught: self.f.evaluate()
                self.assertIs(caught.exception,marker); self.assertEqual(fired,[marker])
            finally: context.check=original_check

    def test_exact_owned_output_seals_native_inputs_and_external_selection_separately(self):
        before=copy.deepcopy(self.f.values[1:]); result=self.f.evaluate(); receipt=result['source_receipt']
        self.assertEqual(set(result),{'schema_version','purpose','point_geometry','stage1_bundle','universe',
            'targets','time_target_result','source_receipt','source_authentication','prereveal_authentication',
            'fit_authorized','scientific_authorized','confirmation_authorized','selection_authorized',
            'promotion_authorized','production_authorized','receipt_sha256'})
        self.assertEqual(result['point_geometry'],'DECLARED_G0_CELL_CENTRE')
        self.assertEqual(len(receipt),9); self.assertEqual(len(receipt['input_lineage']),10)
        self.assertEqual(len(receipt['external_target_selection']),6)
        self.assertEqual(result['receipt_sha256'],digest({k:v for k,v in result.items() if k!='receipt_sha256'}))
        for key in ('stage1_bundle','time_target_result'):
            nested=result[key]
            self.assertEqual(nested['receipt_sha256'],digest({k:v for k,v in nested.items() if k!='receipt_sha256'}))
        self.assertEqual(receipt['projection_sha256']['stage1_bundle'],digest(result['stage1_bundle']))
        for key in ('universe','targets','ledger'):
            value=result['stage1_bundle']['ledger'] if key=='ledger' else result[key]
            self.assertEqual(receipt['projection_sha256'][key],digest(value))
            self.assertEqual(receipt['projection_sha256'][key],result['time_target_result']['input_digests'][key])
        lineage=receipt['input_lineage']; selection=receipt['external_target_selection']
        self.assertEqual(lineage['prepared_input_sha256'],digest(before[1]))
        self.assertEqual(lineage['forecast_receipt_sha256'],digest(before[0]['receipt']))
        self.assertEqual(selection['origin'],'CALLER_PROVIDED_DECLARATION')
        self.assertEqual(selection['frozen_targets_ref'],self.f.target_ref)
        self.assertEqual(selection['targets_sha256'],self.f.targets['targets_sha256'])
        self.assertNotEqual(selection['targets_sha256'],digest(self.f.targets))
        self.assertEqual(self.f.values[1:],before)
        result['stage1_bundle']['ledger']['events'].clear(); result['targets']['targets'].clear()
        result['universe']['units'][0]['utm_x_m']=0
        self.assertEqual(self.f.values[1:],before); self.assertEqual(len(self.f.targets['targets']),1)
        for key in result:
            if key.endswith('_authorized'): self.assertIs(result[key],False)

    def test_six_orders_select_explicit_native_candidate_without_rank_conversion(self):
        recipe=copy.deepcopy(self.f.f.config['hba1_recipe'])
        for optional in itertools.permutations(('HB-A0','HB-B1','HB-A1'),2):
            with self.subTest(order=optional):
                self.f.f.config.update(candidate_ids=['uniform',*optional],
                    hba1_recipe=copy.deepcopy(recipe) if 'HB-A1' in optional else None)
                self.f.f.publish(); self.f.refresh(optional[-1]); result=self.f.evaluate()
                self.assertEqual(result['source_receipt']['candidate_id'],optional[-1])
                self.assertEqual(result['targets'],self.f.targets)
                self.assertEqual(result['universe'],self.f.universe)
                self.assertEqual(result['targets']['targets'][0]['target_id'],'external-A')

    def test_null_targets_null_lineage_unproduced_and_issued_empty_are_distinct(self):
        result=self.f.evaluate(frozen_targets_ref=None)
        self.assertIsNone(result['targets']); self.assertEqual(result['time_target_result']['metrics'],{})
        self.assertIn('TARGET_SET_REQUIRED',result['time_target_result']['blockers'])
        self.f.targets['model_sha256']=None; self.f.publish(); result=self.f.evaluate()
        self.assertIn('PREDICTION_LINEAGE_REQUIRED',result['time_target_result']['blockers'])
        self.f.targets.update(model_sha256=self.f.values[2]['candidates'][0]['model_sha256'],targets=[])
        self.f.publish(); result=self.f.evaluate()
        self.assertEqual(result['time_target_result']['status'],'DIAGNOSTIC_ONLY')
        self.assertEqual(result['time_target_result']['metrics']['event_recall'],0)
        self.f.targets['produced']=False; self.f.publish(); result=self.f.evaluate()
        self.assertIn('TARGETS_NOT_PRODUCED',result['time_target_result']['blockers'])
        self.assertEqual(result['time_target_result']['metrics'],{})

    def test_missing_provided_protocol_and_target_files_are_errors_not_null(self):
        for ref in (self.f.target_ref,self.f.protocol_ref):
            path=self.f.f.root/ref['path']; raw=path.read_bytes(); path.unlink()
            try:
                with self.assertRaises(ValueError): self.f.evaluate()
            finally: path.write_bytes(raw)

    def test_known_target_and_lineage_contradictions_reject_before_outcomes_even_without_scope(self):
        source=self.f.f.source; source.manifest['scope_id']=None; source.nodes.pop('scope'); self.f.f.publish()
        original=copy.deepcopy(self.f.targets); actual=Path.open
        for mutate in (lambda:self.f.targets.update(model_sha256='a'*64),
                lambda:self.f.targets.update(prediction_sha256='b'*64),
                lambda:self.f.targets['targets'][0].update(universe_row_id='foreign-row'),
                lambda:self.f.targets['targets'][0].update(predicted_time='2026-10-14T19:06:00+09:00'),
                lambda:self.f.targets.update(produced=False)):
            self.f.targets=copy.deepcopy(original); mutate(); self.f.publish()
            def opening(path,*a,**kw):
                if path.name in ('captures.csv','individuals.csv','coverage.json'):
                    raise AssertionError('known invalid target allowed outcomes')
                return actual(path,*a,**kw)
            with patch.object(Path,'open',new=opening):
                with self.assertRaises(ValueError): self.f.evaluate()

    def test_declared_prior_readiness_bounds_fit_parent_and_freeze(self):
        for key in self.f.target_ref['readiness']:
            bad=copy.deepcopy(self.f.target_ref); bad['readiness'][key]='2026-10-01T17:00:00+09:00'
            with self.assertRaises(ValueError): self.f.evaluate(frozen_targets_ref=bad)
        bad=copy.deepcopy(self.f.protocol_ref); bad['usable_at']='2026-10-14T17:30:00+09:00'
        with self.assertRaises(ValueError): self.f.evaluate(protocol_ref=bad)
        self.f.protocol['frozen_at']='2026-10-14T17:39:59+09:00'; self.f.publish()
        with self.assertRaises(ValueError): self.f.evaluate()
        self.f.protocol['frozen_at']=None; self.f.publish(); result=self.f.evaluate()
        self.assertIn('DECLARED_FREEZE_REQUIRED',result['time_target_result']['blockers'])

    def test_physical_pretty_json_hashes_do_not_replace_canonical_or_self_hashes(self):
        for name,value in (('target_ref',self.f.targets),('protocol_ref',self.f.protocol)):
            old=getattr(self.f,name)
            raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
            byte_ref=base_ref(self.f.f.root,old['path'],raw)
            setattr(self.f,name,dict(byte_ref,readiness=old['readiness'],usable_at=old['usable_at']))
        result=self.f.evaluate(); selection=result['source_receipt']['external_target_selection']
        self.assertNotEqual(selection['protocol_ref']['sha256'],selection['protocol_sha256'])
        self.assertNotEqual(selection['frozen_targets_ref']['sha256'],selection['targets_sha256'])
        self.assertEqual(result['targets'],self.f.targets)

    def test_selected_row_subset_or_different_scope_cannot_replace_full_universe(self):
        original=copy.deepcopy(self.f.protocol)
        for mode in ('subset','scope'):
            self.f.protocol=copy.deepcopy(original)
            if mode=='subset':
                subset=copy.deepcopy(self.f.universe); subset['units']=subset['units'][:1]
                subset['universe_sha256']=digest({k:v for k,v in subset.items() if k!='universe_sha256'})
                self.f.protocol['universe_sha256']=subset['universe_sha256']
                self.f.targets['universe_sha256']=subset['universe_sha256']
            else:
                self.f.protocol['scope_sha256']='a'*64
                self.f.targets['universe_sha256']=self.f.universe['universe_sha256']
            self.f.publish()
            with self.assertRaises(ValueError): self.f.evaluate()

    def test_original_read_counters_remain_declared_but_every_stable_field_is_rechecked(self):
        forecast=self.f.values[1]; receipt=forecast['receipt']
        receipt['actual_read_bytes']+=1
        self.f.universe['forecast_receipt_sha256']=digest(receipt)
        self.f.universe['universe_sha256']=digest({k:v for k,v in self.f.universe.items() if k!='universe_sha256'})
        self.f.targets['universe_sha256']=self.f.protocol['universe_sha256']=self.f.universe['universe_sha256']
        self.f.publish(); result=self.f.evaluate()
        self.assertEqual(result['universe']['forecast_receipt_sha256'],digest(receipt))
        self.assertGreater(result['source_receipt']['forecast_revalidation']['entry']['actual_read_bytes'],receipt['actual_read_bytes'])
        receipt['unknown_field']='not-native'
        with self.assertRaisesRegex(ValueError,'revalidation'): self.f.evaluate()
        receipt.pop('unknown_field'); receipt['validation_read_bytes']=True
        with self.assertRaises(ValueError): self.f.evaluate()

    def test_all_actual_reads_share_existing_counter_including_final_pass(self):
        context=self.f.values[0]; initial=context.bytes_read; deadline=context.deadline
        result=self.f.evaluate(); receipt=result['source_receipt']
        self.assertLessEqual(context.deadline,deadline)
        self.assertEqual(receipt['initial_read_bytes'],initial)
        self.assertEqual(receipt['actual_read_bytes'],context.bytes_read)
        self.assertEqual(receipt['validation_read_bytes'],context.bytes_read-initial)
        self.assertLess(result['stage1_bundle']['stage1_result']['source_receipt']['actual_read_bytes'],context.bytes_read)
        self.assertGreater(receipt['forecast_revalidation']['final']['actual_read_bytes'],
            receipt['forecast_revalidation']['entry']['actual_read_bytes'])
        for ref in (self.f.protocol_ref,self.f.target_ref,self.f.f.source.ref):
            self.assertEqual(receipt['consumed_sha256'][ref['path']],ref['sha256'])

    def test_global_read_ceiling_is_active_before_first_actual_metadata_open(self):
        context=self.f.values[0]; context.max_bytes=adapter.g0.MAX_TOTAL_READ_BYTES+1
        actual=Path.open; opened=[]
        def opening(path,*a,**kw):
            self.assertLessEqual(context.max_bytes,adapter.g0.MAX_TOTAL_READ_BYTES)
            opened.append(path); return actual(path,*a,**kw)
        with patch.object(Path,'open',new=opening): result=self.f.evaluate()
        self.assertTrue(opened)
        self.assertEqual(result['source_receipt']['actual_read_bytes'],context.bytes_read)

    def test_declared_file_caps_and_reserved_refs_reject_before_any_open(self):
        for name,limit in (('protocol_ref',adapter.MAX_PROTOCOL_BYTES),('frozen_targets_ref',adapter.MAX_TARGET_BYTES)):
            original=self.f.protocol_ref if name=='protocol_ref' else self.f.target_ref
            bad=dict(original,size_bytes=limit+1)
            with patch.object(Path,'open',side_effect=AssertionError('oversized source opened')):
                with self.assertRaises(InputCapacityError): self.f.evaluate(**{name:bad})
            for component in ('OrIgInAl','incoming','reports','sealed','confirmation','ORIGINAL.',
                    'incoming ','reports:stream','ORIGIN~1','bad\x00name','bad\x7fname'):
                bad=dict(original,path=f'evidence/{component}/file.json')
                with patch.object(Path,'open',side_effect=AssertionError('reserved source opened')):
                    with self.assertRaises(ValueError): self.f.evaluate(**{name:bad})

    def test_forecast_manifest_all_refs_preflight_before_any_source_payload(self):
        forecast=self.f.values[1]; ref=forecast['receipt']['manifest_ref']; path=self.f.f.root/ref['path']
        manifest=json.loads(path.read_bytes()); manifest['source_nodes'][-1]['ref']['path']='features/ORIGINAL/source.json'
        forecast['receipt']['manifest_ref']=base_ref(self.f.f.root,ref['path'],canonical_bytes(manifest))
        actual=Path.open; opened=[]
        def opening(target,*a,**kw):
            opened.append(target)
            if target!=path: raise AssertionError('manifest preflight allowed source payload')
            return actual(target,*a,**kw)
        with patch.object(Path,'open',new=opening):
            with self.assertRaisesRegex(ValueError,'Reserved'): self.f.evaluate()
        self.assertEqual(opened,[path])

    def test_native_structure_errors_stay_valueerror_without_source_reads(self):
        original=copy.deepcopy(self.f.values[2]); context,forecast,_=self.f.values
        for mutate in (lambda p:p.pop('fit_cutoff'),lambda p:p['candidates'][0].pop('model'),
                lambda p:p['candidates'][0].update(model=None),lambda p:p['candidates'][0]['prediction'].pop('unit_predictions')):
            prepared=copy.deepcopy(original); mutate(prepared)
            self.f.values=(context,forecast,prepared)
            with patch.object(Path,'open',side_effect=AssertionError('bad native shape opened sources')):
                with self.assertRaises(ValueError): self.f.evaluate()

    def test_late_mutations_of_forecast_targets_and_sources_reject_on_complete_and_need(self):
        actual=adapter.t2.evaluate_time_targets
        for unknown in (False,True):
            self.f.f.source.coverage['declaration']='UNKNOWN' if unknown else 'DECLARED_COMPLETE'
            self.f.f.source.publish(); self.f.f.publish()
            for ref in (self.f.protocol_ref,self.f.target_ref,self.f.f.source.nodes['captures']['ref'],
                    self.f.values[1]['receipt']['manifest_ref']):
                path=self.f.f.root/ref['path']; original=path.read_bytes(); visited=[]
                def change(*a,**kw):
                    result=actual(*a,**kw); visited.append(result['status'])
                    path.write_bytes(original+b'changed after T2'); return result
                try:
                    with patch.object(adapter.t2,'evaluate_time_targets',side_effect=change):
                        with self.assertRaises(ValueError): self.f.evaluate()
                    self.assertEqual(visited,['NEED_MORE_DATA' if unknown else 'DIAGNOSTIC_ONLY'])
                finally: path.write_bytes(original)

    def test_actual_remaining_plus_one_is_charged_at_entry_and_final_reload(self):
        context=self.f.values[0]; context.max_bytes=context.bytes_read+self.f.values[1]['receipt']['manifest_ref']['size_bytes']+1
        with self.assertRaises(InputCapacityError): self.f.evaluate()
        self.assertEqual(context.bytes_read,context.max_bytes+1)
        self.f.refresh(); context=self.f.values[0]; actual=adapter.t2.evaluate_time_targets
        def exhaust(*a,**kw):
            result=actual(*a,**kw); context.max_bytes=context.bytes_read+1; return result
        with patch.object(adapter.t2,'evaluate_time_targets',side_effect=exhaust):
            with self.assertRaises(InputCapacityError): self.f.evaluate()
        self.assertEqual(context.bytes_read,context.max_bytes+1)

    def test_combined_outer_copy_and_final_receipt_obey_actual_byte_cap(self):
        result=self.f.evaluate(); body={k:v for k,v in result.items() if k!='receipt_sha256'}
        caps=(max(len(canonical_bytes(v)) for v in body.values())+1,len(canonical_bytes(body)))
        self.assertLess(caps[0],caps[1]); self.assertLess(caps[1],len(canonical_bytes(result)))
        actual=adapter.pure._copy_json
        for cap in caps:
            self.f.refresh()
            def copy_json(value,check):
                if type(value) is dict and value.get('schema_version')==adapter.VERSION:
                    with patch.object(adapter.pure,'MAX_JSON_BYTES',cap): return actual(value,check)
                return actual(value,check)
            # Keep the tightened cap active through the actual final seal too.
            finish=adapter.pure._finish
            def sealing(value,check):
                if value.get('schema_version')==adapter.VERSION:
                    adapter.pure.MAX_JSON_BYTES=cap
                return finish(value,check)
            with patch.object(adapter.pure,'MAX_JSON_BYTES',adapter.pure.MAX_JSON_BYTES), \
                    patch.object(adapter.pure,'_copy_json',side_effect=copy_json), \
                    patch.object(adapter.pure,'_finish',side_effect=sealing):
                with self.assertRaises(InputCapacityError): self.f.evaluate()

    def test_expiry_before_and_after_final_outer_hash_never_returns_partial(self):
        actual=adapter.pure._finish
        for unknown in (False,True):
            self.f.f.source.coverage['declaration']='UNKNOWN' if unknown else 'DECLARED_COMPLETE'
            self.f.f.source.publish(); self.f.f.publish()
            for phase in ('before','after'):
                self.f.refresh(); context=self.f.values[0]; visited=[]
                def finish(value,check):
                    outer=value.get('schema_version')==adapter.VERSION
                    if outer:
                        visited.append(phase)
                        if phase=='before': context.deadline=0
                    sealed=actual(value,check)
                    if outer and phase=='after': context.deadline=0
                    return sealed
                with patch.object(adapter.pure,'_finish',side_effect=finish):
                    with self.assertRaises(TimeoutError): self.f.evaluate()
                self.assertEqual(visited,[phase])

    def test_actual_native_directory_link_rejects_before_protocol_read(self):
        context=self.f.values[0]
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory); raw=(self.f.f.root/self.f.protocol_ref['path']).read_bytes()
            (target/'protocol.json').write_bytes(raw)
            link=self.f.f.root/'evidence'/'t2-linked'
            if os.name=='nt':
                subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(link),str(target)],
                    capture_output=True,check=True)
            else: os.symlink(target,link,target_is_directory=True)
            try:
                ref=dict(self.f.protocol_ref,path='evidence/t2-linked/protocol.json')
                with patch.object(Path,'open',side_effect=AssertionError('linked source payload read')):
                    with self.assertRaisesRegex(ValueError,'Reparse'): self.f.evaluate(protocol_ref=ref)
                self.assertEqual((target/'protocol.json').read_bytes(),raw)
            finally:
                if os.name=='nt': os.rmdir(link)
                else: link.unlink()

    def test_actual_sept28_csvs_keep_five_six_need_with_synthetic_prerequisites(self):
        source=self.f.f.source; stamp='2026-10-25T18:00:00+09:00'
        for role,path in (('captures','data/processed/capture_events/2026/2026-09-28.csv'),
                ('individuals','data/processed/individuals/2026/2026-09-28.csv')):
            source.node(role,subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT),stamp)
        source.manifest['scope_id']=source.manifest['coverage_id']=None
        source.nodes.pop('scope'); source.nodes.pop('coverage')
        source.manifest.update(evaluation_as_of='2026-10-25T19:00:00+09:00',readiness=source.ready(stamp),usable_at=stamp)
        self.f.f.publish(); result=self.f.evaluate()
        self.assertEqual(result['stage1_bundle']['stage1_result']['source_summary'],dict(capture_events=5,individuals=6))
        self.assertIsNone(result['universe']); self.assertIsNone(result['stage1_bundle']['ledger'])
        self.assertEqual(result['time_target_result']['status'],'NEED_MORE_DATA')
        self.assertEqual(result['time_target_result']['metrics'],{})


if __name__=='__main__': unittest.main()
