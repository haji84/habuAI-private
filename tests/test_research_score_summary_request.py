"""No-fit diagnostic request frontend; synthetic engineering, not SCI."""
from pathlib import Path
import importlib.util
import json
import base64
import copy
import hashlib
import io
import shutil
import zlib
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]


class PublicSeamTests(unittest.TestCase):
    def test_explicit_separate_no_fit_public_entry(self):
        spec = importlib.util.find_spec('research_score_summary_request')
        self.assertIsNotNone(spec, 'Missing separate diagnostic request frontend')
        module = __import__('research_score_summary_request')
        self.assertTrue(callable(module.evaluate_research_score_summary_request))
        self.assertTrue(callable(module.main))


class RequestSyntaxTests(unittest.TestCase):
    def test_known_invalid_requests_never_enter_child(self):
        import research_score_summary_request as request
        import prospective_inputs as pi
        value = dict(schema_version='habu-research-score-summary-request-v1',
            mode='DEVELOPMENT_ONLY', operational_night='2026-10-14',
            forecast_as_of='2026-10-14T19:00:00+09:00',
            feature_definition_sha256='a'*64, candidate_config_sha256='b'*64,
            summary_manifest=dict(path='config/summary.json', sha256='c'*64, size_bytes=2),
            stage1_manifest=dict(path='evidence/stage1.json', sha256='d'*64, size_bytes=2))
        cases = [dict(value, mode=True), dict(value, operational_night='2026-10-15'),
            dict(value, forecast_as_of='2026-10-14T19:00:00'), dict(value, extra=None),
            dict(value, feature_definition_sha256=True),
            dict(value, summary_manifest=dict(value['summary_manifest'], path='config/../x.json')),
            dict(value, stage1_manifest=dict(value['stage1_manifest'], path='config/captures.json'))]
        for bad in cases:
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as td:
                root=Path(td); (root/'config').mkdir()
                (root/request.REQUEST_PATH).write_text(json.dumps(bad), encoding='utf-8')
                c=pi.ProspectiveReadContext(300, 2*1024**3)
                with patch.object(request.bridge, 'evaluate_stage1_summary_sources_v2', side_effect=AssertionError('Invalid request entered child')):
                    with self.assertRaises(ValueError):
                        request.evaluate_research_score_summary_request(root, '2026-10-14', context=c)
                self.assertGreater(c.bytes_read, 0)

    def test_duplicate_depth_and_request_bytes_are_bounded(self):
        import research_score_summary_request as request
        import prospective_inputs as pi
        for raw in (b'{"mode":1,"mode":2}', b'['*14+b'0'+b']'*14, b' '*65537):
            with self.subTest(raw=raw[:20]), tempfile.TemporaryDirectory() as td:
                root=Path(td); (root/'config').mkdir(); (root/request.REQUEST_PATH).write_bytes(raw)
                c=pi.ProspectiveReadContext(300,2*1024**3)
                with self.assertRaises(ValueError):
                    request.evaluate_research_score_summary_request(root,'2026-10-14',context=c)


def materialize(root):
    """Physical current-code fixture + unchanged genuine frozen model bytes."""
    import codex_cycle_contract as cycle
    import prospective_inputs as pi
    import g0_full_universe_score_summary_v2 as producer
    from master_contracts import canonical_bytes, digest
    from test_g0_forecast_contract import base_ref
    from test_stage1_score_summary_transport_v2 import projection
    raw=zlib.decompress(base64.b64decode(_FROZEN))
    assert hashlib.sha256(raw).hexdigest()=='67f8c60c91a23bc3e88bc0b608e697fbdaa7e83d34fc6baffb56410be7b73220'
    payload=json.loads(raw)
    for name, data in payload.items():
        assert not name.startswith('/') and '..' not in name.split('/')
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(data))
    for name in cycle.code_paths(ROOT):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
    sourcepath='config/synthetic-candidate-source.json'
    source=json.loads((root/sourcepath).read_bytes())
    availability={p['path']:p for p in source['code_availability']};sample=next(iter(availability.values()))
    paths=cycle.code_paths(root)
    cp=root/source['cycle']['ref']['path'];body=json.loads(cp.read_bytes())
    body['code_manifest']=[dict(path=p,sha256=hashlib.sha256((root/p).read_bytes()).hexdigest())for p in paths]
    source['cycle']['ref']=base_ref(root,source['cycle']['ref']['path'],canonical_bytes(body))
    source['code_availability']=[dict(availability.get(p,dict(sample,path=p)),size_bytes=(root/p).stat().st_size)for p in paths]
    source_ref=base_ref(root,sourcepath,canonical_bytes(source))
    profile=json.loads((root/'config/summary-v2.json').read_bytes());profile['candidate_config_manifest']=source_ref
    summary_ref=base_ref(root,'config/summary-v2.json',canonical_bytes(profile))
    config=json.loads((root/'config/synthetic-candidates.json').read_bytes())
    # One genuine setup producer is needed to bind the refreshed full code map.
    # This is separate from each tested frontend's actual mandatory producer.
    actual=producer.score_g0_forecast_summary_v2(root,summary_ref,profile['operational_night'],pi._time(profile['forecast_cutoff']),
        expected_feature_definition_sha256=profile['feature_definition_sha256'],expected_candidate_config_sha256=digest(config),
        context=pi.ProspectiveReadContext(300,2*1024**3))
    forecast=type('PhysicalForecast',(),{'manifest':json.loads((root/profile['forecast_manifest']['path']).read_bytes())})()
    p2=projection(actual,forecast)
    mpath='evidence/stage1/manifest.json';target=json.loads((root/mpath).read_bytes());target['score_summary_projection_sha256']=digest(p2)
    target_ref=base_ref(root,mpath,canonical_bytes(target))
    value=dict(schema_version='habu-research-score-summary-request-v1',mode='DEVELOPMENT_ONLY',
        operational_night=profile['operational_night'],forecast_as_of=profile['forecast_cutoff'],
        feature_definition_sha256=profile['feature_definition_sha256'],candidate_config_sha256=digest(config),
        summary_manifest=summary_ref,stage1_manifest=target_ref)
    base_ref(root,'config/research-score-summary-request.json',canonical_bytes(value))
    return value,actual,p2


class ActualFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.base=Path(cls.temp.name)
        cls.request,cls.execution,cls.p2=materialize(cls.base)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        import prospective_inputs as pi
        import research_score_summary_request as request
        self.api=request;self.pi=pi
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'fixture';shutil.copytree(self.base,self.root)
        self.c=pi.ProspectiveReadContext(300,2*1024**3)

    def call(self,context=None):
        from models import hba1_feature_candidate as a1,hba2_feature_candidate as a2
        with patch.object(a1,'fit_hba1',side_effect=AssertionError('Frontend fit')),patch.object(a2,'_backend',side_effect=AssertionError('Frontend backend')):
            return self.api.evaluate_research_score_summary_request(self.root,self.request['operational_night'],context=self.c if context is None else context)

    def publish(self,value):
        from master_contracts import canonical_bytes
        (self.root/self.api.REQUEST_PATH).write_bytes(canonical_bytes(value))

    def rebind_profile(self,profile):
        from master_contracts import canonical_bytes
        from test_g0_forecast_contract import base_ref
        value=copy.deepcopy(self.request)
        value['summary_manifest']=base_ref(self.root,'config/summary-v2.json',canonical_bytes(profile))
        self.publish(value)

    def test_one_real_child_two_loads_owned_children_no_fit(self):
        from master_contracts import digest
        bridge=self.api.bridge;actual=bridge.evaluate_stage1_summary_sources_v2;children=[]
        def child(*a,**kw):
            v=actual(*a,**kw);children.append(json.dumps(v,ensure_ascii=False));return v
        with patch.object(bridge,'evaluate_stage1_summary_sources_v2',side_effect=child)as called:
            value=self.call()
        self.assertEqual(called.call_count,1);self.assertEqual(set(value),{'request_ref','request_canonical_sha256','request','child'})
        self.assertEqual(json.dumps(value['child'],ensure_ascii=False),children[0])
        c=value['child'];self.assertEqual(c['score_summary_projection'],self.p2)
        self.assertEqual(c['stage1_result']['per_night'][0]['outside_universe_individuals'],2)
        self.assertEqual(c['entry_initial_read_bytes'],value['request_ref']['size_bytes'])
        self.assertEqual(c['receipt_sha256'],digest({k:v for k,v in c.items()if k!='receipt_sha256'}))
        value['request']['mode']='changed';self.assertEqual(json.loads((self.root/self.api.REQUEST_PATH).read_bytes()),self.request)

    def test_command_one_buffer_original_child_and_phase_ledgers(self):
        from master_contracts import digest
        from test_g0_forecast_contract import base_ref
        import g0_forecast_contract as g0
        import g0_full_universe_score_summary_v2 as producer
        ref=base_ref(self.root,'config/one.bin',b'x');fired=[];root=self.root;pi=self.pi
        class Context(pi.ProspectiveReadContext):
            def check(c):
                super().check()
                if not fired and sys._getframe(1).f_code is producer._context.__code__:
                    fired.append(1);g0.G0ArtifactReader(root,c).read(ref,parse=False)
        self.c=Context(300,2*1024**3)
        g0.G0ArtifactReader(root,self.c).read(ref,parse=False)
        actual=self.api.bridge.evaluate_stage1_summary_sources_v2;children=[]
        def child(*a,**kw):
            v=actual(*a,**kw);children.append(json.dumps(v,ensure_ascii=False))
            g0.G0ArtifactReader(root,self.c).read(ref,parse=False)
            return v
        identity=self.c.deadline,self.c.max_bytes,self.c.check
        with patch.object(self.api.bridge,'evaluate_stage1_summary_sources_v2',side_effect=child):
            raw=self.api._command(self.root,self.request['operational_night'],self.c)
        value=json.loads(raw);self.assertEqual(len(value),19)
        self.assertEqual(json.dumps(value['child'],ensure_ascii=False),children[0])
        self.assertEqual(value['child_return_read_bytes'],value['child']['actual_read_bytes'])
        self.assertEqual(value['entry_initial_read_bytes'],1);self.assertEqual(fired,[1])
        summary=value['child']['summary_execution_receipt'];phases=value['child']['phase_read_ledger']
        self.assertEqual(summary['actual_read_bytes']-summary['summary_read_bytes'],phases['after_post_admission_metadata']+1)
        self.assertEqual(value['final_read_bytes'],self.c.bytes_read)
        self.assertGreater(value['final_read_bytes'],value['child_return_read_bytes'])
        self.assertEqual(sum(value['phase_read_ledger'].values()),value['command_read_bytes'])
        self.assertEqual((self.c.deadline,self.c.max_bytes,self.c.check),identity)
        self.assertEqual(value['receipt_sha256'],digest({k:v for k,v in value.items()if k!='receipt_sha256'}))
        self.assertTrue(all(v is False for v in value['authorities'].values()))

    def test_main_publishes_one_complete_buffer_only(self):
        class Sink:
            def __init__(s):s.values=[]
            def write(s,b):s.values.append(b);return len(b)
        sink=Sink();stdout=type('Output',(),{'buffer':sink})()
        with patch.object(sys,'stdout',stdout):
            result=self.api.main(['--root',str(self.root),'--night',self.request['operational_night']])
        self.assertEqual(result,0);self.assertEqual(len(sink.values),1)
        body=json.loads(sink.values[0]);self.assertEqual(len(body),19)
        self.assertEqual(body['schema_version'],self.api.COMMAND_VERSION)

    def test_short_stdout_write_is_failure_without_retry(self):
        class Sink:
            def __init__(s):s.calls=0
            def write(s,b):s.calls+=1;return 1
        sink=Sink();stdout=type('Output',(),{'buffer':sink})()
        with patch.object(sys,'stdout',stdout),self.assertRaisesRegex(OSError,'Incomplete'):
            self.api.main(['--root',str(self.root),'--night',self.request['operational_night']])
        self.assertEqual(sink.calls,1)

    def test_actual_deadline_and_global_bytes_never_reset(self):
        for kind in('expired','broader','exhausted'):
            c=self.pi.ProspectiveReadContext(300,2*1024**3)
            if kind=='expired':c.deadline=0
            elif kind=='broader':c.max_bytes+=1
            else:c.bytes_read=c.max_bytes
            before=c.deadline,c.max_bytes,c.bytes_read
            with self.subTest(kind=kind),self.assertRaises((ValueError,TimeoutError)):self.call(c)
            self.assertEqual((c.deadline,c.max_bytes,c.bytes_read),before)

    def test_fully_sealed_outer_cap_includes_own_sha_before_stdout(self):
        from master_contracts import canonical_bytes
        pure=self.api.pure;actual=self.api._bound;old=pure.MAX_JSON_BYTES;fired=[];sink=io.BytesIO()
        def bound(v,g):
            if type(v)is dict and v.get('schema_version')==self.api.COMMAND_VERSION and not fired:
                fired.append(1);pure.MAX_JSON_BYTES=len(canonical_bytes(v))+10
            return actual(v,g)
        try:
            stdout=type('Output',(),{'buffer':sink})()
            with patch.object(self.api,'_bound',side_effect=bound),patch.object(sys,'stdout',stdout),self.assertRaises(self.pi.InputCapacityError):
                self.api.main(['--root',str(self.root),'--night',self.request['operational_night']])
        finally:pure.MAX_JSON_BYTES=old
        self.assertEqual(fired,[1]);self.assertEqual(sink.getvalue(),b'')

    def test_source2_late_blocks_before_poisoned_forecast(self):
        from master_contracts import canonical_bytes
        from test_g0_forecast_contract import base_ref
        profile=json.loads((self.root/'config/summary-v2.json').read_bytes())
        path=profile['candidate_config_manifest']['path'];source=json.loads((self.root/path).read_bytes())
        source['readiness']['audited_at']=source['usable_at']=profile['fit_cutoff']
        profile['candidate_config_manifest']=base_ref(self.root,path,canonical_bytes(source));self.rebind_profile(profile)
        (self.root/profile['forecast_manifest']['path']).write_bytes(b'{}')
        opened=[];original=Path.open
        def opening(p,*a,**kw):
            if p.is_relative_to(self.root)and p.relative_to(self.root).parts[0]in('features','models'):opened.append(p)
            return original(p,*a,**kw)
        with patch.object(Path,'open',opening),self.assertRaises(self.api.bridge.source2.CandidateConfigSourceBlocked):self.call()
        self.assertEqual(opened,[])

    def test_whole_nmd_does_not_read_outcomes(self):
        profile=json.loads((self.root/'config/summary-v2.json').read_bytes())
        profile['fit_lineage']=None;profile['models'][2]['artifact']=None;self.rebind_profile(profile)
        original=Path.open
        def opening(p,*a,**kw):
            if p.name in('captures.csv','individuals.csv','coverage.json'):raise AssertionError('NMD outcomes read')
            return original(p,*a,**kw)
        with patch.object(Path,'open',opening):value=self.call()
        self.assertEqual(value['child']['status'],'NEED_MORE_DATA');self.assertIsNone(value['child']['stage1_result'])

    def test_command_whole_nmd_does_not_open_unadmitted_target_manifest(self):
        from master_contracts import canonical_bytes
        from test_g0_forecast_contract import base_ref
        profile=json.loads((self.root/'config/summary-v2.json').read_bytes())
        profile['fit_lineage']=None;profile['models'][2]['artifact']=None
        value=copy.deepcopy(self.request)
        value['summary_manifest']=base_ref(self.root,'config/summary-v2.json',canonical_bytes(profile))
        target=self.root/value['stage1_manifest']['path']
        value['stage1_manifest']=base_ref(self.root,value['stage1_manifest']['path'],b'{"schema_version":"poison-unused-v1"}')
        self.publish(value);opens=[];original=Path.open;sink=io.BytesIO()
        def opening(p,*a,**kw):
            if p==target:opens.append(a[0]if a else kw.get('mode','r'))
            return original(p,*a,**kw)
        stdout=type('Output',(),{'buffer':sink})()
        with patch.object(Path,'open',opening),patch.object(sys,'stdout',stdout):
            code=self.api.main(['--root',str(self.root),'--night',self.request['operational_night']])
        self.assertEqual(opens,[],'NMD target manifest was never admitted by the child')
        result=json.loads(sink.getvalue());self.assertEqual(code,0)
        self.assertEqual(result['status'],'NEED_MORE_DATA')
        self.assertIsNone(result['child']['stage1_result']);self.assertIsNone(result['child']['source_receipt'])

    def test_complete_final_union_keeps_every_consumed_original_ref(self):
        value=self.call();child=value['child'];refs={value['request_ref']['path']:value['request_ref']}
        for receipt in(child['source_admission_receipt'],child['summary_execution_receipt'],child['source_receipt']):
            for ref in receipt['consumed_refs']:
                self.assertIn(ref['size_bytes'],range(1,128*1024**2+1))
                if ref['path']in refs:self.assertEqual(refs[ref['path']],ref)
                refs[ref['path']]=ref
        self.assertIn(value['request']['summary_manifest']['path'],refs)
        self.assertIn(value['request']['stage1_manifest']['path'],refs)
        actual=self.api.bridge._Reader.read;seen=[]
        def read(reader,ref,**kwargs):
            seen.append(dict(ref));return actual(reader,ref,**kwargs)
        before=self.c.bytes_read
        with patch.object(self.api.bridge._Reader,'read',read):
            self.api._recheck(self.root,value,self.c,self.api._Guard(self.c))
        self.assertEqual({r['path']:r for r in seen},refs)
        self.assertEqual(len(seen),len(refs))
        self.assertEqual(self.c.bytes_read-before,sum(r['size_bytes']for r in refs.values()))

    def test_first_falsey_baseexception_identity_and_failed_charge(self):
        class Stop(BaseException):
            def __bool__(self):return False
        for seam in('check','account'):
            marker=Stop(seam);fired=[];pi=self.pi
            class Context(pi.ProspectiveReadContext):
                def check(c):
                    super().check()
                    if seam=='check'and not fired:fired.append(1);raise marker
                def account(c,n):
                    super().account(n)
                    if seam=='account'and not fired:fired.append(1);raise marker
            c=Context(300,2*1024**3)
            with self.subTest(seam=seam),self.assertRaises(Stop)as caught:self.call(c)
            self.assertIs(caught.exception,marker)
            if seam=='account':self.assertGreater(c.bytes_read,0)

    def test_actual_csv_read_error_and_final_pure_guard_keep_same_instance(self):
        pure=self.api.pure;marker=pure.Stage1CapacityBlocked('caller CSV origin');original=Path.open;seen=[]
        def opening(p,*a,**kw):
            if p.name=='captures.csv':seen.append(1);raise marker
            return original(p,*a,**kw)
        with patch.object(Path,'open',opening),self.assertRaises(pure.Stage1CapacityBlocked)as caught:self.call()
        self.assertIs(caught.exception,marker);self.assertEqual(seen,[1])
        stop=pure.Stage1BudgetBlocked('caller final seal origin');fired=[];pi=self.pi
        class Context(pi.ProspectiveReadContext):
            def check(c):
                super().check();frame=sys._getframe(1)
                while frame:
                    if frame.f_code.co_name=='_command'and 'receipt_sha256'in frame.f_locals.get('result',{})and not fired:
                        fired.append(1);raise stop
                    frame=frame.f_back
        with self.assertRaises(pure.Stage1BudgetBlocked)as caught:self.api._command(self.root,self.request['operational_night'],Context(300,2*1024**3))
        self.assertIs(caught.exception,stop);self.assertEqual(fired,[1])

    def test_g0_ordinary_late_remains_value_error(self):
        from master_contracts import canonical_bytes
        from test_g0_forecast_contract import base_ref
        profile=json.loads((self.root/'config/summary-v2.json').read_bytes())
        path=profile['forecast_manifest']['path'];forecast=json.loads((self.root/path).read_bytes())
        forecast['readiness']['audited_at']=forecast['usable_at']=forecast['cutoff_time']
        profile['readiness']['audited_at']=profile['usable_at']=forecast['cutoff_time']
        profile['forecast_manifest']=base_ref(self.root,path,canonical_bytes(forecast));self.rebind_profile(profile)
        with self.assertRaisesRegex(ValueError,'strictly before cutoff'):self.call()

    def test_post_child_original_size_mutation_blocks_before_stdout(self):
        actual=self.api.evaluate_research_score_summary_request;sink=io.BytesIO()
        def evaluate(*a,**kw):
            v=actual(*a,**kw)
            with (self.root/self.api.REQUEST_PATH).open('ab')as f:f.write(b' ')
            return v
        stdout=type('Output',(),{'buffer':sink})()
        with patch.object(self.api,'evaluate_research_score_summary_request',side_effect=evaluate),patch.object(sys,'stdout',stdout),self.assertRaises(ValueError):
            self.api.main(['--root',str(self.root),'--night',self.request['operational_night']])
        self.assertEqual(sink.getvalue(),b'')

    def test_final_actual_check_charged_byte_cannot_publish_stale_ledger(self):
        import g0_forecast_contract as g0
        from test_g0_forecast_contract import base_ref
        ref=base_ref(self.root,'config/one.bin',b'x');fired=[];root=self.root;pi=self.pi
        class Context(pi.ProspectiveReadContext):
            def check(c):
                super().check()
                caller=sys._getframe(2)
                if not fired and caller.f_code.co_name=='_command'and 'buffer'in caller.f_locals:
                    fired.append(1);g0.G0ArtifactReader(root,c).read(ref,parse=False)
        c=Context(300,2*1024**3)
        with self.assertRaisesRegex(ValueError,'ledger changed'):self.api._command(self.root,self.request['operational_night'],c)
        self.assertEqual(fired,[1])


# Frozen genuine synthetic Oct14 fitted children from the accepted105 capsule.
# This is bounded TEST input, not raw observation or claimed source availability.
# sha256 of uncompressed canonical path/base64 map:67f8c60c91a23bc3e88bc0b608e697fbdaa7e83d34fc6baffb56410be7b73220.
# No fitter/preparer/backend is used to reconstruct these88 physical inputs.
_FROZEN = (
    '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'
    'rPXJDdylrOan9Mm6fzfzq2xa9ujZClnSebl1zHdbJu15xk/3wrOCSJx0LyiGg/0xPL5vnHKt3/jhjBB1Mh5s4zfojBDeEbEc/7bJ'
    'D7Y9Zj/Kz0axdfo9aPHqp5yjrjhhXaIi7v31GROHfxeTvr71L1qb0yjveY8vTybvm5lEozV/O/yAcNpaUCOvRnTKmuhmDlGxza3R'
    'xgQNnJQ2OxGnDGEemgNlzu/YF3RmBGs8pnPrz21OrglzxhXT4QnX38yov9vNmbZr39A3bHN18rU380qn91Q36JleSeKUod4w2PdM'
    '2j2q+TyItpe7qTdP85Pao7c9mZveDAlMxB9eZoy3/nj/2SoeDfUJsf96Nt2a8zDb9NRvz4Pa1Q2nPXvV1DvJdH7C3sn1LOtZffFN'
    'lF611o2xNVvPuPmOPclJLlsd2a8jQZTXbHl6Hbn1RxkrLkrI/obvfotHo+2dacrdOVzNzuA3sge8p8kVfU0u9O2XEdb8iXo2Whu1'
    '30Y5gXvpnMFGrc9g+YPvwinuZnaGd+79Qb0ZrX1qmvMU94Kr09snrLOmGbPEXTyzk0fo8LpXpt2HvfsQRKHFT7cPz+KeF7N7mW3m'
    'NhZ4z/vbFHYJa2xqba2PaOCrjE+JaZ9ntgW7eZG1vcVNPvnSCk7YBzbzx0rg+7E2eet/G3teatj908UITj9HLHA384sV8BBku133'
    'ht6KmqsT9ho5/Xrq8JXxrYa7bSsGSF5mvbd2p6mOD1t/OrvzZfQ8c/qFcNbzXyHzq/mkreU08/KE3RPinfczrfD3gZLUP5+2tqiR'
    'AzpaOCe0RRb28UFYF5QPavmoGnifYXNOd64Wz4XYyuQd3tl+4sAtb9O3fqJ2PxriXz08ZX6OuPEKw4c02M1dU31flsX9FhdG2+/Y'
    'zBtZsRP2wm/nIrZz1hPgJzkxM8ZMbmLiiNZfN9V6XNY5YZ5oW0/WOBXrA9u1Ih/Z7kFTLeFSn8lWbfjqBznNz205AZp5DYMoPCFm'
    'WvPnQT6fiA/gNu22675/tmF9Un9gJ6u5O+y2HFU/FTd0mY5P13/q8N70nubFjCl2eK1ntj6gwQ+f7pwUYb6a+OVfeDxf+y7aOQxN'
    'edMV06ezQ3O/eMJ3dOCD7yH/bT/eYb1fHe6e7vzN5uzN3czpZ5CV9bnxtpfigDpZfkos2kEMhrWFnbcu6Jzmat7aoMa520yxn5wv'
    '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'
    'xT8='
)
