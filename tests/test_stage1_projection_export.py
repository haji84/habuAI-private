"""Synthetic export controls; no source authentication or time-target generation."""
import copy
import itertools
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from master_contracts import canonical_bytes,digest
from prospective_inputs import InputCapacityError
from evaluation import stage1_source_adapter as adapter
from test_stage1_configured_source_adapter import ConfiguredSourceFixture,reseal


class Stage1ProjectionExportTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(adapter,'project_stage1_sources_v2',None)),
            'Missing explicit configured projection export API')
        self.f=ConfiguredSourceFixture(self)

    def export(self,values=None,reference=None):
        context,forecast,prepared=values or self.f.projections()
        return adapter.project_stage1_sources_v2(self.f.root,reference or self.f.source.ref,forecast,prepared,
            candidate_config=self.f.config,expected_config_sha256=digest(self.f.config),
            feature_definition_sha256=self.f.parent.request['feature_definition_sha256'],context=context)

    def test_exact_bundle_preserves_result_reads_and_projection_hashes(self):
        prior=self.f.evaluate()
        values=self.f.projections(); before=copy.deepcopy(values[1:])
        result=self.export(values)
        self.assertEqual(set(result),{'schema_version','purpose','stage1_result','universe','scores','ledger',
            'source_authentication','fit_authorized','scientific_authorized','confirmation_authorized',
            'selection_authorized','promotion_authorized','production_authorized','receipt_sha256'})
        self.assertEqual(result['schema_version'],'habu-stage1-source-projection-bundle-v1')
        self.assertEqual(result['purpose'],'DEVELOPMENT_EVALUATION_ONLY')
        self.assertEqual(canonical_bytes(result['stage1_result']),canonical_bytes(prior))
        self.assertEqual(values[1:],before)
        for key in ('universe','scores','ledger'):
            self.assertEqual(digest(result[key]),prior['source_receipt']['projection_sha256'][key])
        self.assertEqual(result['receipt_sha256'],digest({k:v for k,v in result.items() if k!='receipt_sha256'}))
        self.assertEqual(result['source_authentication'],'NOT_ATTESTED')
        for key in result:
            if key.endswith('_authorized'): self.assertIs(result[key],False)
        self.assertEqual(len(result['ledger']['events']),2)
        self.assertEqual(sum(len(e['individual_ids']) for e in result['ledger']['events']),3)
        self.assertEqual(result['stage1_result']['per_night'][0]['outside_universe_individuals'],1)

    def test_missing_scope_keeps_source_counts_and_null_projections(self):
        self.f.source.manifest['scope_id']=None; self.f.source.nodes.pop('scope'); self.f.publish()
        result=self.export()
        self.assertEqual(result['stage1_result']['status'],'NEED_MORE_DATA')
        self.assertEqual(result['stage1_result']['source_summary'],dict(capture_events=2,individuals=3))
        self.assertEqual([result[k] for k in ('universe','scores','ledger')],[None,None,None])

    def test_unknown_coverage_preserves_known_ledger_without_metrics(self):
        self.f.source.coverage['declaration']='UNKNOWN'; self.f.source.publish(); self.f.publish()
        result=self.export()
        self.assertEqual(result['ledger']['complete_scopes'][0]['declaration'],'UNKNOWN')
        self.assertEqual(result['stage1_result']['pooled'],{})
        self.assertEqual(result['stage1_result']['status'],'NEED_MORE_DATA')

    def test_default_api_never_calls_export_helper(self):
        with patch.object(adapter,'_export_projection_bundle',side_effect=AssertionError('default export')):
            result=self.f.evaluate()
        self.assertEqual(result['source_contract_version'],'habu-stage1-source-contract-v2')

    def test_reserved_first_manifest_is_rejected_before_open(self):
        values=self.f.projections()
        reference=dict(self.f.source.ref,path='evidence/ORIGINAL/manifest.json')
        with patch.object(Path,'open',side_effect=AssertionError('reserved manifest opened')):
            with self.assertRaises(ValueError): self.export(values,reference)

    def test_six_orders_keep_actual_validated_projections_and_native_bindings(self):
        recipe=copy.deepcopy(self.f.config['hba1_recipe'])
        for optional in itertools.permutations(('HB-A0','HB-B1','HB-A1'),2):
            with self.subTest(order=optional):
                self.f.config.update(candidate_ids=['uniform',*optional],
                    hba1_recipe=copy.deepcopy(recipe) if 'HB-A1' in optional else None)
                self.f.publish(); values=self.f.projections(); captured=[]
                actual=adapter.pure.evaluate_full_ledger_stage1_v2
                def evaluate(u,s,l,**kw):
                    captured.append(copy.deepcopy((u,s,l))); return actual(u,s,l,**kw)
                with patch.object(adapter.pure,'evaluate_full_ledger_stage1_v2',side_effect=evaluate):
                    result=self.export(values)
                self.assertEqual(tuple(result[k] for k in ('universe','scores','ledger')),captured[0])
                self.assertEqual(result['stage1_result']['candidate_ids'],['uniform',*optional])
                for source,score in zip(values[2]['candidates'],result['scores']['candidates']):
                    self.assertEqual((source['model_sha256'],source['prediction_sha256']),
                        (score['model_sha256'],score['prediction_sha256']))

    def test_export_is_owned_and_each_self_hash_has_its_declared_scope(self):
        values=self.f.projections(); original=copy.deepcopy(values[1:]); captured=[]
        actual=adapter.pure.evaluate_full_ledger_stage1_v2
        def evaluate(u,s,l,**kw):
            captured.append((u,s,l)); return actual(u,s,l,**kw)
        with patch.object(adapter.pure,'evaluate_full_ledger_stage1_v2',side_effect=evaluate):
            result=self.export(values)
        ledger=result['ledger']
        self.assertEqual(ledger['ledger_sha256'],digest({k:v for k,v in ledger.items() if k!='ledger_sha256'}))
        self.assertNotEqual(digest(ledger),ledger['ledger_sha256'])
        nested=result['stage1_result']
        self.assertEqual(nested['receipt_sha256'],digest({k:v for k,v in nested.items() if k!='receipt_sha256'}))
        saved=canonical_bytes(captured)
        result['ledger']['events'][0]['individual_ids'].append('not-source-data')
        result['scores']['candidates'][0]['model_sha256']='a'*64
        result['stage1_result']['source_receipt']['consumed_refs'].clear()
        self.assertEqual(values[1:],original)
        self.assertEqual(canonical_bytes(captured),saved)

    def test_missing_coverage_or_actual_file_preserves_null_ledger(self):
        self.f.source.manifest['coverage_id']=None; self.f.source.nodes.pop('coverage'); self.f.publish()
        result=self.export()
        self.assertIsNotNone(result['universe']); self.assertIsNotNone(result['scores'])
        self.assertIsNone(result['ledger'])
        path=self.f.root/self.f.source.nodes['individuals']['ref']['path']; path.unlink()
        result=self.export()
        self.assertIsNone(result['ledger'])
        self.assertIn('FILE:individuals',result['stage1_result']['source_receipt']['missing_inputs'])
        self.assertEqual(result['stage1_result']['pooled'],{})
        path.write_bytes(b'wrong supplied bytes')
        with self.assertRaises(ValueError): self.export()

    def test_missing_scope_and_unknown_do_not_hide_supplied_contradictions(self):
        self.f.source.manifest['scope_id']=None; self.f.source.nodes.pop('scope')
        self.f.source.coverage['declaration']='UNKNOWN'; self.f.source.publish()
        self.f.source.nodes.pop('scope'); self.f.publish()
        baseline=copy.deepcopy(self.f.source.nodes)
        for mutate in (lambda:self.f.source.nodes['captures']['ref'].update(sha256='a'*64),
                lambda:self.f.source.nodes['captures']['readiness'].update(source_received_at='2026-10-14T17:00:00+09:00'),
                lambda:self.f.source.nodes['individuals'].update(role='scope')):
            self.f.source.nodes=copy.deepcopy(baseline); mutate(); self.f.publish()
            with self.assertRaises(ValueError): self.export()

    def test_invalid_prepared_or_absent_native_inputs_reject_before_any_open(self):
        baseline=self.f.projections()
        for field,value in [('candidate_config_sha256','a'*64),('heldout_night','2026-10-13'),
                ('fit_cutoff','2026-10-15T07:00:00+09:00')]:
            values=(baseline[0],baseline[1],copy.deepcopy(baseline[2]))
            values[2][field]=value; reseal(values[2])
            with patch.object(Path,'open',side_effect=AssertionError('invalid prepared source read')):
                with self.assertRaises(ValueError): self.export(values)
        for values in ((baseline[0],None,baseline[2]),(baseline[0],baseline[1],None)):
            with patch.object(Path,'open',side_effect=AssertionError('missing native source read')):
                with self.assertRaises(ValueError): self.export(values)

    def test_first_and_forecast_refs_reject_reserved_controls_and_aliases_before_open(self):
        baseline=self.f.projections()
        paths=['evidence/'+part+'/manifest.json' for part in
            ('OrIgInAl','incoming','reports','sealed','Confirmation','ORIGINAL.','incoming ',
             'reports:stream','ORIGIN~1','bad\x00name','bad\x1fname','bad\x7fname','..')]
        for path in paths:
            for kind in ('first','forecast'):
                with self.subTest(path=repr(path),kind=kind):
                    values=(baseline[0],copy.deepcopy(baseline[1]),baseline[2])
                    ref=dict(self.f.source.ref,path=path)
                    if kind=='forecast': values[1]['receipt']['manifest_ref']['path']=path
                    with patch.object(Path,'open',side_effect=AssertionError('forbidden source read')):
                        with self.assertRaises(ValueError): self.export(values,ref if kind=='first' else None)

    def test_every_node_preflight_precedes_all_scope_or_outcome_reads(self):
        baseline=copy.deepcopy(self.f.source.nodes); values=self.f.projections(); actual=Path.open
        for component in ('ORIGINAL','incoming','RePoRtS','sealed','confirmation','ORIGINAL.',
                'incoming ','reports:stream','ORIGIN~1','bad\x00name','bad\x7fname'):
            with self.subTest(component=repr(component)):
                self.f.source.nodes=copy.deepcopy(baseline)
                self.f.source.nodes['individuals']['ref']['path']=f'evidence/{component}/individuals.csv'
                self.f.publish(); opened=[]
                def opening(path,*a,**kw):
                    opened.append(path)
                    if path!=self.f.root/self.f.source.ref['path']:
                        raise AssertionError('node preflight allowed payload open')
                    return actual(path,*a,**kw)
                with patch.object(Path,'open',new=opening):
                    with self.assertRaises(ValueError): self.export(values)
                self.assertEqual(opened,[self.f.root/self.f.source.ref['path']])

    def test_one_existing_context_accounts_reads_and_remaining_plus_one_rejection(self):
        values=self.f.projections(); context=values[0]; deadline=context.deadline; before=context.bytes_read
        result=self.export(values)
        self.assertEqual(context.deadline,deadline)
        self.assertGreater(context.bytes_read,before)
        self.assertEqual(context.bytes_read,result['stage1_result']['source_receipt']['actual_read_bytes'])
        values=self.f.projections(); context=values[0]
        context.max_bytes=context.bytes_read+self.f.source.ref['size_bytes']+5
        with self.assertRaises(InputCapacityError): self.export(values)
        self.assertEqual(context.bytes_read,context.max_bytes+1)

    def test_default_whole_result_and_read_order_are_exact_with_no_post_rescan_io(self):
        traces=[]; actual=Path.open
        for export in (False,True):
            values=self.f.projections(); opened=[]
            def opening(path,*a,**kw):
                opened.append((path.relative_to(self.f.root).as_posix(),a,kw))
                return actual(path,*a,**kw)
            helper=adapter._export_projection_bundle
            def no_io(*a):
                with patch.object(Path,'open',side_effect=AssertionError('post-rescan export source read')):
                    return helper(*a)
            with patch.object(Path,'open',new=opening), \
                    patch.object(adapter,'_export_projection_bundle',side_effect=no_io):
                result=self.export(values) if export else self.f.evaluate(values)
            traces.append((opened,values[0].bytes_read,result['stage1_result'] if export else result))
        self.assertEqual(traces[0],traces[1])

    def test_actual_sept28_sources_keep_five_six_need_without_scope_or_forecast_claim(self):
        # Native Git CSVs only; forecast/prepared prerequisites remain SYNTHETIC.
        # This checks source-summary mechanics, not an actual Sept28 forecast.
        source=self.f.source; stamp='2026-10-25T18:00:00+09:00'
        for role,path in [('captures','data/processed/capture_events/2026/2026-09-28.csv'),
                ('individuals','data/processed/individuals/2026/2026-09-28.csv')]:
            source.node(role,subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT),stamp)
        source.manifest['scope_id']=source.manifest['coverage_id']=None
        source.nodes.pop('scope'); source.nodes.pop('coverage')
        source.manifest.update(evaluation_as_of='2026-10-25T19:00:00+09:00',
            readiness=source.ready(stamp),usable_at=stamp)
        self.f.publish(); result=self.export(); nested=result['stage1_result']
        self.assertEqual(nested['source_summary'],dict(capture_events=5,individuals=6))
        self.assertEqual(nested['status'],'NEED_MORE_DATA')
        self.assertEqual((nested['per_night'],nested['pooled'],nested['paired_uncertainty']),([],{},{}))
        self.assertEqual([result[k] for k in ('universe','scores','ledger')],[None,None,None])
        self.assertIs(result['fit_authorized'],False)

    def test_combined_export_and_added_receipt_both_obey_actual_json_byte_cap(self):
        result=self.export(); body={k:v for k,v in result.items() if k!='receipt_sha256'}
        caps=[max(len(canonical_bytes(v)) for v in body.values())+1,len(canonical_bytes(body))]
        self.assertLess(caps[0],caps[1]); self.assertLess(caps[1],len(canonical_bytes(result)))
        actual=adapter._export_projection_bundle
        for cap in caps:
            with self.subTest(cap=cap):
                values=self.f.projections()
                def bounded(*a):
                    with patch.object(adapter.pure,'MAX_JSON_BYTES',cap): return actual(*a)
                with patch.object(adapter,'_export_projection_bundle',side_effect=bounded):
                    with self.assertRaises(InputCapacityError): self.export(values)

    def test_export_checks_complexity_before_encoding_or_oversized_copy(self):
        for limit,value in [('MAX_JSON_NODES',1),('MAX_JSON_BYTES',1)]:
            with patch.object(adapter.pure,limit,value):
                with self.assertRaises(adapter.pure.Stage1CapacityBlocked):
                    adapter._export_projection_bundle({},None,None,None,lambda:None)
        with self.assertRaises(ValueError):
            adapter._export_projection_bundle({'bad':float('nan')},None,None,None,lambda:None)

    def test_pure_validation_rescan_and_export_seal_all_share_deadline(self):
        actual=adapter.pure.evaluate_full_ledger_stage1_v2
        values=self.f.projections()
        def corrupt(*a,**kw):
            result=actual(*a,**kw)
            path=self.f.root/self.f.source.nodes['captures']['ref']['path']
            path.write_bytes(path.read_bytes()+b'changed'); return result
        with patch.object(adapter.pure,'evaluate_full_ledger_stage1_v2',side_effect=corrupt):
            with self.assertRaises(ValueError): self.export(values)
        self.f.source.publish(); self.f.publish()
        seal=adapter.pure._finish
        for mode in ('pure','bundle_before','bundle_after'):
            values=self.f.projections()
            def expire_pure(*a,**kw):
                result=actual(*a,**kw); values[0].deadline=0; return result
            def expire_seal(result,check):
                is_bundle=result.get('schema_version')=='habu-stage1-source-projection-bundle-v1'
                if is_bundle and mode=='bundle_before': values[0].deadline=0
                sealed=seal(result,check)
                if is_bundle and mode=='bundle_after': values[0].deadline=0
                return sealed
            with patch.object(adapter.pure,'evaluate_full_ledger_stage1_v2',
                    side_effect=expire_pure if mode=='pure' else actual), \
                    patch.object(adapter.pure,'_finish',side_effect=expire_seal):
                with self.assertRaises(TimeoutError): self.export(values)

    @unittest.skipUnless(os.name=='nt','Windows native junction guard')
    def test_actual_native_junction_node_is_rejected_before_any_payload_read(self):
        values=self.f.projections()
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory); (target/'individuals.csv').write_bytes(b'external sentinel')
            link=self.f.root/'evidence'/'export-junction'
            made=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(link),str(target)],
                capture_output=True,check=True)
            self.assertEqual(made.returncode,0)
            try:
                self.f.source.nodes['individuals']['ref']['path']='evidence/export-junction/individuals.csv'
                self.f.publish(); actual=Path.open
                def opening(path,*a,**kw):
                    if path!=self.f.root/self.f.source.ref['path']:
                        raise AssertionError('junction preflight reached payload')
                    return actual(path,*a,**kw)
                with patch.object(Path,'open',new=opening):
                    with self.assertRaisesRegex(ValueError,'Reparse'): self.export(values)
                self.assertEqual((target/'individuals.csv').read_bytes(),b'external sentinel')
            finally:
                os.rmdir(link)


if __name__=='__main__': unittest.main()
