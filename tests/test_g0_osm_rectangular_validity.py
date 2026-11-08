"""Synthetic typed codec tests; no actual source availability or science claims."""
import copy
import contextlib
import hashlib
import io
import json
import math
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import g0_forecast_contract as g0
import prospective_inputs as pi
from master_contracts import canonical_bytes, digest
from test_g0_forecast_contract import SyntheticOsmContract, NIGHT, NOW, START, READY, CUTOFF, definition_hash
import test_build_osm_prospective_universe as producer_tests

SCHEMA='habu-g0-osm-static-validity-v1'
RULE='EACH_CANONICAL_UNIT_WINDOW_600S'


class ThreeFeatureContract(SyntheticOsmContract):
    def __init__(self,root):
        super().__init__(root)
        code=self.features[0]['code_ref']
        for suffix,name,value in (('cos','road_axial_cos',math.cos(math.radians(30))),
                                  ('sin','road_axial_sin',math.sin(math.radians(30)))):
            text='Synthetic '+name
            self.features.append(dict(name=name,units='1',version='1',definition=text,
                definition_sha256=hashlib.sha256(text.encode()).hexdigest(),code_ref=copy.deepcopy(code),
                deployment='static_predictor',required_source_ids=[suffix]))
            self.add(suffix,'features/sources/'+suffix+'.json','osm_static_projection','feature',['csv'],
                dict(schema_version='habu-g0-osm-static-projection-v1',operation=name,version='1',
                     source_csv_node_id='csv',code_ref=copy.deepcopy(code)))
            for shard in self.manifest['shards']:
                sid=shard['shard_id'];snap=self.objects[self.nodes[sid+'-s']['ref']['path']]
                existing=self.objects[snap['features'][0]['path']]
                fid=sid+'-'+suffix;path='features/'+fid+'.json'
                self.add(fid,path,'feature_values','feature',[suffix],dict(existing,feature_name=name,
                    values={key:value for key in existing['values']}))
                snap['features'].append(dict(path=path))
                self.nodes[sid+'-s']['parents'].append(fid)
                self.nodes[sid+'-v']['parents'].append(fid)
                validity=self.objects[self.nodes[sid+'-v']['ref']['path']]
                validity['feature_sources'][name]=[fid]
                for fields in validity['rows'].values():fields[name]=self.valid.copy()
        for node in self.nodes.values():node['source_class']='auxiliary'
        for sid in self.snapshots:
            self.objects[self.nodes[sid]['ref']['path']]['feature_schema_sha256']=digest(sorted(g0.OSM_FEATURE_UNITS))
        # One two-cell partition distinguishes absolute [0,2] from partition #0.
        for ti in range(2):
            left,right=f'c0t{ti}',f'c1t{ti}'
            for suffix in ('u','f','cos','sin','v'):
                a=self.objects[self.nodes[left+'-'+suffix]['ref']['path']]
                b=self.objects[self.nodes[right+'-'+suffix]['ref']['path']]
                if suffix=='u':a['rows'].extend(b['rows'])
                elif suffix=='v':a['rows'].update(b['rows'])
                else:a['values'].update(b['values'])
            for suffix in ('u','f','cos','sin','v','s'):
                node=self.nodes.pop(right+'-'+suffix);del self.objects[node['ref']['path']]
            self.snapshots.remove(right+'-s')
        self.manifest['cell_partitions']=[[0,2]]
        self.manifest['shards']=[s for s in self.manifest['shards'] if s['cell_partition']==0]
        self.publish()

    def rectangular(self,shard):
        old=self.objects[self.nodes[shard['validity_id']]['ref']['path']]
        self.objects[self.nodes[shard['validity_id']]['ref']['path']]=dict(schema_version=SCHEMA,
            domain_id=self.manifest['domain_id'],snapshot_id=shard['snapshot_id'],
            cell_range=copy.deepcopy(self.manifest['cell_partitions'][shard['cell_partition']]),
            time_range=copy.deepcopy(self.manifest['time_partitions'][shard['time_partition']]),
            feature_sources=copy.deepcopy(old['feature_sources']),rule=RULE)


class RectangularValidityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.fixture=ThreeFeatureContract(self.root)
        self.original=copy.deepcopy(self.fixture);f=self.fixture
        p=patch.multiple(g0,OSM_ARCHIVE_SHA256=hashlib.sha256(f.archive).hexdigest(),OSM_ARCHIVE_BYTES=len(f.archive),
            OSM_CSV_SHA256=hashlib.sha256(f.csv).hexdigest(),OSM_CSV_BYTES=len(f.csv),
            OSM_EXPECTED_CELLS=2,OSM_PART_CHUNK_BYTES=f.chunk_size)
        p.start();self.addCleanup(p.stop)

    def reset(self,compact=True):
        self.fixture=copy.deepcopy(self.original)
        if compact:
            for shard in self.fixture.manifest['shards']:self.fixture.rectangular(shard)
        self.fixture.publish()
        return self.fixture

    def call(self,**kwargs):
        return g0.load_g0_forecast_rows(self.root,self.fixture.ref,NIGHT,NOW,
            expected_feature_definition_sha256=definition_hash(self.fixture.features),**kwargs)

    def test_rectangular_and_per_row_have_identical_complete_owned_rows_and_hash(self):
        legacy=self.call();self.reset();compact=self.call()
        self.assertEqual(compact['rows'],legacy['rows'])
        self.assertEqual(compact['receipt']['canonical_joined_rows_sha256'],legacy['receipt']['canonical_joined_rows_sha256'])
        self.assertEqual(compact['receipt']['row_count'],4)
        self.assertNotEqual(compact['receipt']['manifest_ref'],legacy['receipt']['manifest_ref'])
        self.assertFalse(compact['receipt']['fit_authorized'])
        self.assertFalse(compact['receipt']['scientific_execution_authorized'])
        self.assertFalse(compact['receipt']['production_authorized'])

    def test_mixed_individually_checked_shards_are_legal(self):
        legacy=self.call();self.fixture.rectangular(self.fixture.manifest['shards'][1]);self.fixture.publish()
        self.assertEqual(self.call()['rows'],legacy['rows'])

    def test_exact_schema_ranges_and_source_ids_reject_mutations(self):
        mutations=[('schema_version','unknown'),('rule','any'),('domain_id','roads'),('snapshot_id','c0t1-s'),
            ('domain_id',[]),('cell_range',[0,1]),('cell_range',[True,2]),('cell_range',[0,2.0]),
            ('cell_range',[2,0]),('cell_range',0),('time_range',[0,2]),('time_range',[False,1]),
            ('time_range',[0]),('feature_sources',{}),('rows',{}),('trusted',True)]
        for key,value in mutations:
            f=self.reset();node=f.nodes[f.manifest['shards'][0]['validity_id']]
            f.objects[node['ref']['path']][key]=value;f.publish()
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.call()
        f=self.reset();node=f.nodes[f.manifest['shards'][0]['validity_id']]
        del f.objects[node['ref']['path']]['rule'];f.publish()
        with self.assertRaises(ValueError):self.call()

    def test_range_is_absolute_endpoints_not_partition_number(self):
        f=self.reset();self.call()
        node=f.nodes[f.manifest['shards'][0]['validity_id']]
        f.objects[node['ref']['path']]['cell_range']=[0,1];f.publish()
        with self.assertRaises(ValueError):self.call()

    def test_generic_same_named_predictor_and_generic_domain_cannot_claim_typed_mode(self):
        for case in ('length','roads','forecast'):
            f=self.reset(compact=False);identifier='length' if case=='forecast' else case;node=f.nodes[identifier]
            kind='forecast' if case=='forecast' else 'static'
            node.update(source_kind=kind,parents=[],event_time=NIGHT+'T16:00:00+09:00')
            f.objects[node['ref']['path']]=dict(schema_version='habu-g0-source-v1',source_kind=kind,
                source_class='auxiliary',event_time=node['event_time'],valid_time=f.valid.copy(),data={'synthetic':1})
            if case=='forecast':
                f.features[0]['deployment']='forecast_predictor'
                for shard in f.manifest['shards']:
                    f.objects[f.nodes[shard['shard_id']+'-f']['ref']['path']]['use_role']='forecast_predictor'
            f.publish();self.call() # Old per-row remains a supported generic contract.
            for shard in f.manifest['shards']:f.rectangular(shard)
            f.publish()
            with self.subTest(case=case),self.assertRaises(ValueError):self.call()

    def test_two_typed_features_are_not_the_fixed_three_feature_capability(self):
        f=self.reset(compact=False);f.features=[v for v in f.features if v['name']!='road_axial_cos']
        f.manifest['features']=f.features
        for shard in f.manifest['shards']:
            sid=shard['shard_id'];fid=sid+'-cos';node=f.nodes.pop(fid);del f.objects[node['ref']['path']]
            snap=f.objects[f.nodes[sid+'-s']['ref']['path']]
            snap['features']=[ref for ref in snap['features'] if ref['path']!=node['ref']['path']]
            snap['feature_schema_sha256']=digest(sorted(v['name'] for v in f.features))
            f.nodes[sid+'-s']['parents'].remove(fid);f.nodes[sid+'-v']['parents'].remove(fid)
            validity=f.objects[f.nodes[sid+'-v']['ref']['path']];del validity['feature_sources']['road_axial_cos']
            for physical in validity['rows'].values():del physical['road_axial_cos']
        node=f.nodes.pop('cos');del f.objects[node['ref']['path']]
        f.publish();self.call()
        for shard in f.manifest['shards']:f.rectangular(shard)
        f.publish()
        with self.assertRaises(ValueError):self.call()

    def test_duplicate_json_keys_and_cross_shard_feature_binding_reject(self):
        for bad in ('duplicate_rule','duplicate_nested','wrong_feature_source'):
            f=self.reset();shard=f.manifest['shards'][0];identifier=shard['validity_id'];node=f.nodes[identifier]
            value=f.objects[node['ref']['path']]
            if bad=='wrong_feature_source':
                value['feature_sources']['road_length_m']=[f.manifest['shards'][1]['shard_id']+'-f'];f.publish()
            else:
                raw=canonical_bytes(value)
                if bad=='duplicate_rule':raw=raw.replace(b'"rule":',b'"rule":"bad","rule":')
                else:raw=raw.replace(b'"road_length_m":',b'"road_length_m":[],"road_length_m":')
                f.overwrite_node_raw(identifier,raw)
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.call()

    def test_every_canonical_unit_value_center_and_validity_remain_checked(self):
        for bad in ('value','center','missing','source_validity','feature_validity','validity_node','universe','snapshot'):
            f=self.reset();shard=f.manifest['shards'][0];sid=shard['shard_id']
            if bad=='value':
                values=f.objects[f.nodes[sid+'-f']['ref']['path']]['values'];values[next(iter(values))]=99
            elif bad in ('center','missing'):
                rows=f.objects[f.nodes[sid+'-u']['ref']['path']]['rows']
                if bad=='center':rows[0]['utm_x_m']+=1
                else:rows.pop()
            else:
                identifier={'source_validity':'length','feature_validity':sid+'-f','validity_node':sid+'-v','universe':sid+'-u','snapshot':sid+'-s'}[bad]
                f.nodes[identifier]['valid_time']['end']=START
            f.publish()
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.call()

    def test_same_context_read_account_and_every_sidecar_initial_read_and_rescan(self):
        self.reset();context=pi.ProspectiveReadContext(300,g0.MAX_TOTAL_READ_BYTES);context.account(23)
        before=context.deadline;counts={};original=g0.G0ArtifactReader.read
        def read(reader,ref,**kwargs):
            counts[ref['path']]=counts.get(ref['path'],0)+1
            return original(reader,ref,**kwargs)
        with patch.object(g0.G0ArtifactReader,'read',read):result=self.call(_read_context=context)
        self.assertLessEqual(context.deadline,before)
        self.assertEqual(result['receipt']['actual_read_bytes'],context.bytes_read)
        for shard in self.fixture.manifest['shards']:
            self.assertEqual(counts[self.fixture.nodes[shard['validity_id']]['ref']['path']],2)
        context=pi.ProspectiveReadContext(300,1)
        with self.assertRaises(pi.InputCapacityError):self.call(_read_context=context)
        self.assertEqual(context.bytes_read,2) # The bounded rejection byte is real and billed.

    def test_compact_mode_does_not_remove_collector_join_or_source_capacity_caps(self):
        for name,cap in (('MAX_MODEL_ROWS',3),('MAX_MODEL_ROW_BYTES',128)):
            self.reset()
            with self.subTest(name=name),patch.object(g0,name,cap),self.assertRaises(pi.InputCapacityError):self.call()
        self.reset()
        with patch.object(pi,'MAX_JOIN_CELLS',5),self.assertRaises(pi.InputCapacityError):self.call()

    def test_new_checker_preserves_caller_callback_exception_identity(self):
        self.reset();original=g0._osm_rectangular_validity;error=RuntimeError('compact callback')
        def checked(*args):
            def failed():raise error
            return original(*args[:-1],failed)
        with patch.object(g0,'_osm_rectangular_validity',side_effect=checked),self.assertRaises(RuntimeError) as caught:self.call()
        self.assertIs(caught.exception,error)

    def test_all_four_sidecar_readiness_equalities_remain_rejected(self):
        for field in pi.READINESS_FIELDS:
            f=self.reset();node=f.nodes[f.manifest['shards'][0]['validity_id']]
            node['readiness'][field]=CUTOFF;node['usable_at']=CUTOFF;f.publish()
            with self.subTest(field=field),self.assertRaises(ValueError):self.call()

    def test_final_rescan_mutation_and_final_callback_expiry_return_no_result(self):
        f=self.reset();original=g0.G0ArtifactReader.rescan
        def rescan(reader):
            target=f.root/f.nodes[f.manifest['shards'][-1]['validity_id']]['ref']['path']
            target.write_bytes(target.read_bytes()+b' ')
            original(reader)
        with patch.object(g0.G0ArtifactReader,'rescan',rescan),self.assertRaises(ValueError):self.call()
        self.reset();context=pi.ProspectiveReadContext(300,g0.MAX_TOTAL_READ_BYTES);error=TimeoutError('after final rescan')
        def expire(reader):
            original(reader)
            def failed():raise error
            context.check=failed
        with patch.object(g0.G0ArtifactReader,'rescan',expire),self.assertRaises(TimeoutError) as caught:self.call(_read_context=context)
        self.assertIs(caught.exception,error)


class CompactProducerTests(unittest.TestCase):
    def setUp(self):
        self.harness=producer_tests.StrictOsmProducerTests(methodName='runTest')
        self.harness.setUp();self.addCleanup(self.harness.doCleanups)
        self.module=producer_tests.module;self.output=self.harness.output

    def test_explicit_compact_producer_and_default_share_fixed_rows_and_native_publication(self):
        old=self.harness.call(windows=2)
        old_data=g0.load_g0_forecast_rows(self.output,old['manifest_ref'],producer_tests.NIGHT,
            datetime.fromisoformat(producer_tests.CUTOFF),expected_feature_definition_sha256=old['feature_definition_sha256'])
        self.harness.output=self.output.parent/'compact'
        new=self.harness.call(windows=2,validity_encoding='osm_rectangular_v1')
        new_data=g0.load_g0_forecast_rows(self.harness.output,new['manifest_ref'],producer_tests.NIGHT,
            datetime.fromisoformat(producer_tests.CUTOFF),expected_feature_definition_sha256=new['feature_definition_sha256'])
        self.assertEqual(old_data['rows'],new_data['rows'])
        self.assertEqual(old_data['receipt']['canonical_joined_rows_sha256'],new_data['receipt']['canonical_joined_rows_sha256'])
        self.assertLess(new['actual_read_bytes'],old['actual_read_bytes'])
        for root,schema in ((self.output,'habu-g0-validity-v1'),(self.harness.output,SCHEMA)):
            sidecars=list(root.glob('features/shards/*-v.json'));self.assertEqual(len(sidecars),2)
            for path in sidecars:self.assertEqual(json.loads(path.read_bytes())['schema_version'],schema)
        for path,raw in self.harness.parts:self.assertEqual(path.read_bytes(),raw)

    def test_bad_modes_reject_before_git_source_read_or_output(self):
        for mode in ('other',None,True,[],{}):
            with self.subTest(mode=mode),patch.object(self.module,'_git_head',side_effect=AssertionError('source read')),\
                    self.assertRaises(ValueError):self.harness.call(validity_encoding=mode)
            self.assertFalse(self.output.exists())

    def test_cli_explicit_mode_requires_strict_and_dispatches_selected_mode(self):
        common=['builder','--output-root',str(self.output),'--night',producer_tests.NIGHT,
            '--cutoff',producer_tests.CUTOFF,'--first-window',producer_tests.START,'--validity-encoding','osm_rectangular_v1']
        with contextlib.redirect_stderr(io.StringIO()),patch.object(sys,'argv',common),patch.object(self.module,'materialize',side_effect=AssertionError('legacy write')),\
                self.assertRaises(SystemExit) as caught:self.module.main()
        self.assertEqual(caught.exception.code,2)
        with contextlib.redirect_stdout(io.StringIO()),patch.object(sys,'argv',common+['--strict-g0']),patch.object(self.module,'materialize_g0',return_value={}) as call:
            self.module.main()
        self.assertEqual(call.call_args.kwargs['validity_encoding'],'osm_rectangular_v1')

    def test_compact_sidecar_is_really_read_three_times_under_same_context(self):
        context=pi.ProspectiveReadContext(300,g0.MAX_TOTAL_READ_BYTES);counts={};original=g0.G0ArtifactReader.read
        def read(reader,ref,**kwargs):
            self.assertIs(reader.context,context)
            if ref['path'].endswith('-v.json'):counts[ref['path']]=counts.get(ref['path'],0)+1
            return original(reader,ref,**kwargs)
        with patch.object(g0.G0ArtifactReader,'read',read):result=self.harness.call(windows=2,
            validity_encoding='osm_rectangular_v1',_read_context=context)
        self.assertEqual(list(counts.values()),[3,3])
        self.assertEqual(result['actual_read_bytes'],context.bytes_read)

    def test_compact_builder_never_constructs_per_unit_interval_dictionary(self):
        cells=g0.parse_osm_road_csv(producer_tests.csv_source([producer_tests.row(4000,30000),
            producer_tests.row(4001,30000)]))
        class Writer:
            context=pi.ProspectiveReadContext(300,g0.MAX_TOTAL_READ_BYTES)
            objects={}
            def now(self):return producer_tests.READY
            def json(self,path,value):
                self.objects[path]=value;raw=canonical_bytes(value)
                return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),size_bytes=len(raw),
                    readiness={key:self.now() for key in pi.READINESS_FIELDS},usable_at=self.now())
        count=[]
        def interval_dict(*args,**kwargs):
            if set(kwargs)=={'start','end'}:count.append(True)
            return dict(*args,**kwargs)
        with patch.object(self.module,'dict',side_effect=interval_dict,create=True):
            writer=Writer()
            self.module._g0_shard(writer,cells,datetime.fromisoformat(producer_tests.START),0,2,
                producer_tests.NIGHT,datetime.fromisoformat(producer_tests.CUTOFF),[],validity_encoding='osm_rectangular_v1')
        self.assertEqual(len(count),1) # Only the shard scope; no rows x features interval tree.
        sidecar=next(value for path,value in writer.objects.items() if path.endswith('-v.json'))
        self.assertNotIn('rows',sidecar)

    def test_compact_native_publication_late_cutoff_deadline_and_interrupt_cleanup(self):
        for mode in ('cutoff','deadline','interrupt'):
            context=pi.ProspectiveReadContext(30,g0.MAX_TOTAL_READ_BYTES)
            native=self.module._noreplace_publisher();published=[];clock=[datetime.fromisoformat(producer_tests.READY)]
            class Clock(datetime):
                @classmethod
                def now(cls,tz=None):return clock[0].astimezone(tz)
            def publish(source,destination):
                native(source,destination);published.append(destination.is_dir())
                if mode=='cutoff':clock[0]=datetime.fromisoformat(producer_tests.CUTOFF)
                elif mode=='deadline':context.deadline=0
                else:raise KeyboardInterrupt('after native publication')
            expected={'cutoff':ValueError,'deadline':TimeoutError,'interrupt':KeyboardInterrupt}[mode]
            with self.subTest(mode=mode),patch.object(self.module,'datetime',Clock),\
                    patch.object(self.module,'_noreplace_publisher',return_value=publish),self.assertRaises(expected):
                self.harness.call(windows=2,validity_encoding='osm_rectangular_v1',_read_context=context)
            self.assertEqual(published,[True]);self.assertFalse(self.output.exists())
            self.assertEqual(list(self.output.parent.glob('.g0-osm-pending-*')),[])
            for path,raw in self.harness.parts:self.assertEqual(path.read_bytes(),raw)


if __name__=='__main__':unittest.main()
