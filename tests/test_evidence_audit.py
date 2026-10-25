import csv
import importlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from master_contracts import canonical_bytes,file_hash,digest
NIGHT='2026-09-28'
VERIFIED='2026-09-30T20:00:00+09:00'


def write(root,path,value):
    dest=root/path; dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(value if isinstance(value,bytes) else canonical_bytes(value))
    return {'path':path,'sha256':file_hash(dest)}


def receipt(root,ref,at='2026-09-30T10:00:00+09:00'):
    return write(root,'evidence/raw_intake/'+ref['sha256']+'.json',{
        'raw_path':ref['path'],'sha256':ref['sha256'],'bytes':(root/ref['path']).stat().st_size,
        'received_at_utc':at,'source':'synthetic explicit field evidence'})


def fixture(root,qualified=False,empty=False,*,capture_bytes=None,gpx_bytes=None,search_role='SEARCH'):
    gpx=write(root,'data/raw/gpx/track.gpx',gpx_bytes if gpx_bytes is not None else b'<gpx><trk><trkseg><trkpt lat="28.15" lon="129.3"><time>2026-09-28T12:00:00Z</time></trkpt><trkpt lat="28.15" lon="129.3"><time>2026-09-28T12:00:10Z</time></trkpt></trkseg></trk></gpx>')
    caps=write(root,'data/processed/capture_events/captures.csv',capture_bytes if capture_bytes is not None else b'event_id,event_type,event_count,datetime_jst,latitude,longitude,operational_date\n'+(b'' if empty else b'C,capture,2,2026-09-28T21:20:00+09:00,28.151,129.31,2026-09-28\n'))
    receipt(root,gpx); receipt(root,caps)
    if qualified:
        sources=[]
        for ref,roles in [(gpx,['observed_exposure']),(caps,['outcome_label'])]:
            review=write(root,'evidence/reviews/'+ref['sha256']+'.json',{'schema_version':'1.0',
                'source_sha256':ref['sha256'],'use_roles':roles,'coordinate_method':'field GPS',
                'recovery_class':'COMPLETE_REAL_GPX','reviewed_at':VERIFIED})
            sources.append(dict(ref,review_ref=review))
        evidence=write(root,'evidence/search.json',{'schema_version':'1.0','trajectory_sha256':gpx['sha256'],
             'search_role':search_role,'start':NIGHT+'T20:50:00+09:00','end':NIGHT+'T22:00:00+09:00'})
        recording=write(root,'policies/recording.json',{'schema_version':'1.0','search_evidence_ref':evidence,
             'capture_sources':[caps], 'recording_rule':'ALL_CAPTURES_RECORDED',
             'start':NIGHT+'T20:50:00+09:00','end':NIGHT+'T22:00:00+09:00'})
        write(root,'policies/observation_evidence.json',{'schema_version':'1.0','sources':sources,
             'sessions':[{'session_id':'S','trajectory':gpx,'recording_ref':recording}]})
    return gpx,caps


def complete_coverage(root,cap,*,bbox=None):
    domain=write(root,'evidence/domain.json',{'schema_version':'1.0','crs':'EPSG:4326','bbox':bbox or [129.2,28.1,129.4,28.2]})
    evidence=write(root,'evidence/outcome-coverage.json',{'schema_version':'1.0',
        'coverage_kind':'COMPLETE_CAPTURE_LOG_FOR_DOMAIN_AND_NIGHT','night':NIGHT,
        'domain_sha256':domain['sha256'],'capture_source_sha256s':[cap['sha256']],
        'start':NIGHT+'T07:00:00+09:00','end':'2026-09-29T07:00:00+09:00'})
    declaration=write(root,'policies/outcome-coverage.json',{'schema_version':'1.0','night':NIGHT,
        'domain_ref':domain,'capture_sources':[cap],'coverage_evidence_ref':evidence})
    path=root/'policies/observation_evidence.json';policy=json.loads(path.read_text())
    policy['outcome_coverage']=[declaration];path.write_bytes(canonical_bytes(policy))


class EvidenceAuditTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('evidence_audit'))
        self.a=importlib.import_module('evidence_audit')
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

    def audit(self):return self.a.audit_evidence(self.root,NIGHT,verified_at=VERIFIED)

    def test_gpx_without_role_or_capture_completeness_is_unknown(self):
        fixture(self.root)
        result=self.audit()
        self.assertEqual(result['observation_units'][0]['label'],None)
        self.assertEqual(result['observation_units'][0]['observation'],'UNKNOWN')
        self.assertEqual(result['capture_audit']['diagnostic_individuals'],2)
        self.assertEqual(result['outcome_ledger']['events'],[])
        self.assertIn('SEARCH_ROLE',str(result['input_requirements']))
        self.assertEqual(result['trajectory_audit'][0]['point_count'],2)

    def test_qualified_session_alone_cannot_create_negative_without_complete_outcomes(self):
        fixture(self.root,True);result=self.audit()
        self.assertIsNone(result['observation_units'][0]['label'])
        self.assertEqual(result['observation_units'][0]['observation'],'UNKNOWN')
        self.assertIsNone(result['observation_units'][0]['duration_seconds'])
        self.assertEqual(result['outcome_ledger']['events'][0]['capture_count'],2)
        self.assertEqual(result['outcome_ledger']['events'][0]['event_id'],'C')
        self.assertEqual(result['outcome_ledger']['denominator_coverage'],'NOT_ESTABLISHED')
        self.assertFalse(result['observation_units'][0]['source_refs'])
        self.assertIn('FULL_OUTCOME_COVERAGE',[r['code'] for r in result['input_requirements']])

    def test_declared_passage_stays_unknown_even_with_complete_capture_log(self):
        _,cap=fixture(self.root,True,empty=True,search_role='PASSAGE')
        complete_coverage(self.root,cap)
        result=self.audit()
        self.assertEqual(result['outcome_ledger']['denominator_coverage'],'ESTABLISHED_FOR_DECLARED_DOMAIN')
        self.assertFalse(any(u['label']==0 for u in result['observation_units']))
        self.assertTrue(all(u['observation']=='UNKNOWN' for u in result['observation_units']))

    def test_complete_capture_log_for_other_domain_cannot_label_outside_region(self):
        _,cap=fixture(self.root,True,empty=True)
        complete_coverage(self.root,cap,bbox=[129.5,28.4,129.6,28.5])
        result=self.audit()
        self.assertEqual(result['outcome_ledger']['denominator_coverage'],'ESTABLISHED_FOR_DECLARED_DOMAIN')
        self.assertEqual(result['observation_units'][0]['label'],None)
        self.assertEqual(result['observation_units'][0]['observation'],'UNKNOWN')

    def test_passage_without_explicit_search_evidence_and_missing_capturefile_are_unknown(self):
        for case in ['passage','missing']:
            with self.subTest(case=case):
                fixture(self.root,True)
                if case=='passage':
                    p=self.root/'evidence/search.json';d=json.loads(p.read_text());d['search_role']='NONSEARCH';p.write_bytes(canonical_bytes(d))
                else:(self.root/'data/processed/capture_events/captures.csv').unlink()
                result=self.audit()
                self.assertFalse(any(u['label']==0 for u in result['observation_units']))
                self.assertNotEqual(result['status'],'PASS')

    def test_receipt_hash_tamper_is_fail(self):
        ref,_=fixture(self.root);(self.root/ref['path']).write_bytes(b'<gpx/>')
        self.assertEqual(self.audit()['status'],'FAIL')

    def test_strict_gpx_segment_and_zero_backward_naive_time_checks(self):
        ref,_=fixture(self.root)
        raw=b'<gpx><trk><trkseg><trkpt lat="28.15" lon="129.3"><time>2026-09-28T12:00:00Z</time></trkpt><trkpt lat="28.15" lon="129.3"><time>2026-09-28T12:00:00Z</time></trkpt><trkpt lat="28.15" lon="129.3"><time>2026-09-28T11:00:00Z</time></trkpt></trkseg><trkseg><trkpt lat="28.15" lon="129.3"><time>2026-09-28T12:00:00</time></trkpt></trkseg></trk></gpx>'
        (self.root/ref['path']).write_bytes(raw)
        for p in (self.root/'evidence/raw_intake').glob('*.json'):p.unlink()
        result=self.audit();track=result['trajectory_audit'][0]
        self.assertEqual(track['segment_count'],2)
        self.assertIn('ZERO_TIME_DELTA',str(track));self.assertIn('BACKWARD_TIME',str(track));self.assertIn('TIMEZONE_REQUIRED',str(track))
        self.assertFalse(any(u['label']==0 for u in result['observation_units']))

    def test_duplicate_capture_conflict_quarantines_event_not_silently_deduped(self):
        _,cap=fixture(self.root,True)
        path=self.root/cap['path'];path.write_bytes(path.read_bytes()+b'C,capture,3,2026-09-28T21:20:00+09:00,28.151,129.31,2026-09-28\n')
        result=self.audit()
        self.assertTrue(result['capture_audit']['conflicts'])
        self.assertEqual(result['outcome_ledger']['events'],[])
        self.assertEqual(result['status'],'FAIL')

    def test_invalid_counts_and_missing_count_never_invent_individual(self):
        fixture(self.root)
        cap=self.root/'data/processed/capture_events/captures.csv'
        cap.write_text('event_id,event_type,event_count,datetime_jst,latitude,longitude\nA,capture,,2026-09-28T21:00:00+09:00,28.15,129.3\nB,capture,1.5,2026-09-28T21:00:00+09:00,28.15,129.3\n')
        result=self.audit();self.assertEqual(result['capture_audit']['diagnostic_individuals'],0)
        self.assertEqual(len(result['capture_audit']['rejected']),2)

    def test_count_two_individual_links_are_not_double_counted(self):
        fixture(self.root,True)
        write(self.root,'data/processed/individuals/individuals.csv',b'individual_id,event_id,individual_index\nI1,C,1\nI2,C,2\n')
        result=self.audit();self.assertEqual(result['capture_audit']['diagnostic_individuals'],2)
        self.assertEqual(result['capture_audit']['individual_link_status'],'PASS')
        self.assertEqual(result['outcome_ledger']['events'][0]['individual_ids'],['I1','I2'])

    def test_receipt_availability_not_event_time(self):
        fixture(self.root,True);result=self.audit()
        source=next(s for s in result['source_manifest'] if s['path']=='data/raw/gpx/track.gpx')
        self.assertEqual(source['first_verified_received_at'],'2026-09-30T10:00:00+09:00')
        self.assertIsNone(source['historical_available_at'])
        self.assertGreaterEqual(source['available_at'],'2026-09-30')

    def test_line_archive_hash_mismatch_fails(self):
        base='data/raw/gpx_archives/test.lines/'
        write(self.root,base+'part_0.txt',b'<gpx/>')
        write(self.root,base+'manifest.json',{'part_count':1,'part_glob':'part_*.txt','encoding':'utf-8',
             'raw_size_bytes':6,'raw_sha256':'0'*64,'trackpoint_count':0})
        self.assertEqual(self.audit()['status'],'FAIL')

    def test_valid_archive_keeps_container_and_reconstructed_hashes_separate(self):
        raw=b'<gpx><trk><trkseg><trkpt lat="28.15" lon="129.3"><time>2026-09-28T12:00:00Z</time></trkpt></trkseg></trk></gpx>'
        import hashlib
        base='data/raw/gpx_archives/test.lines/'
        write(self.root,base+'part_0.txt',raw)
        manifest=write(self.root,base+'manifest.json',{'part_count':1,'part_glob':'part_*.txt','encoding':'utf-8',
             'raw_size_bytes':len(raw),'raw_sha256':hashlib.sha256(raw).hexdigest(),'trackpoint_count':1})
        result=self.audit();source=next(s for s in result['source_manifest'] if s['path']==manifest['path'])
        self.assertEqual(source['sha256'],manifest['sha256'])
        self.assertEqual(source['reconstructed_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['trajectory_audit'][0]['point_count'],1)

    def test_missing_osm_payload_is_requirement_not_forecast_universe(self):
        write(self.root,'evidence/osm/osm_road_evidence_manifest.csv',b'path,bytes,sha256\n/old/grid.csv,3,0000000000000000000000000000000000000000000000000000000000000000\n')
        result=self.audit();self.assertIn('OSM_PAYLOAD',str(result['input_requirements']))
        self.assertEqual(result['osm_audit']['resolved'],0)

    def test_master_executes_audit_and_preserves_snapshot_inventory(self):
        import master_orchestrator as m
        fixture(self.root)
        result=m.run_master(self.root,NIGHT)
        run=self.root/f"reports/pdca/{NIGHT}/runs/{result['run_id']}"
        report=run/f'snapshot/reports/evidence_audit/{NIGHT}/audit.json'
        self.assertTrue(report.is_file())
        audit=json.loads(report.read_text())
        self.assertEqual(audit['trajectory_audit'][0]['point_count'],2)
        stage=next(s for s in result['stages'] if s['name']=='evidence_audit')
        self.assertEqual(stage['execution_status'],'EXECUTED')
        self.assertEqual(stage['status'],'PARTIAL')
        inputs=m._inventory(self.root)
        self.assertTrue(m._snapshot_matches(run/'snapshot',inputs))
        self.assertEqual(m.run_master(self.root,NIGHT),result)

    def test_only_exact_osm_archive_is_inventoried_not_bridge_runtime(self):
        import master_orchestrator as m
        write(self.root,'artifacts/Habu_AI_OSM_Road_Grid_2026-09-25.zip.parts/README.md',b'archive')
        write(self.root,'artifacts/bridge/runtime.json',{'not':'scientific input'})
        inventory=m._inventory(self.root)
        self.assertIn('artifacts/Habu_AI_OSM_Road_Grid_2026-09-25.zip.parts/README.md',inventory)
        self.assertNotIn('artifacts/bridge/runtime.json',inventory)

    def test_complete_domain_night_contract_establishes_bound_denominator(self):
        _,cap=fixture(self.root,True);complete_coverage(self.root,cap)
        result=self.audit();ledger=result['outcome_ledger']
        self.assertEqual(ledger['denominator_coverage'],'ESTABLISHED_FOR_DECLARED_DOMAIN')
        self.assertEqual(ledger['complete_scopes'][0]['confirmed_individuals'],2)
        self.assertEqual(ledger['complete_scopes'][0]['event_ids'],['C'])
        self.assertNotIn('FULL_OUTCOME_COVERAGE',[r['code'] for r in result['input_requirements']])

    def test_empty_explicit_complete_capture_log_differs_from_missing_log(self):
        _,cap=fixture(self.root,True,empty=True);complete_coverage(self.root,cap)
        result=self.audit()
        self.assertEqual(result['outcome_ledger']['complete_scopes'][0]['confirmed_individuals'],0)
        self.assertEqual(result['observation_units'][0]['label'],0)
        self.assertNotIn('OUTCOME_LOG',[r['code'] for r in result['input_requirements']])
        (self.root/cap['path']).unlink()
        missing=self.audit()
        self.assertNotEqual(missing['outcome_ledger']['denominator_coverage'],'ESTABLISHED_FOR_DECLARED_DOMAIN')
        self.assertFalse(any(u['label']==0 for u in missing['observation_units']))

    def test_unqualified_known_capture_prevents_complete_denominator(self):
        _,cap=fixture(self.root,True);complete_coverage(self.root,cap)
        write(self.root,'data/processed/capture_events/unqualified.csv',b'event_id,event_type,event_count,datetime_jst,latitude,longitude\nOTHER,capture,1,2026-09-28T21:25:00+09:00,28.15,129.3\n')
        result=self.audit()
        self.assertEqual(result['outcome_ledger']['denominator_coverage'],'NOT_ESTABLISHED')
        self.assertIn('UNRESOLVED_KNOWN_CAPTURE',str(result['input_requirements']))

    def test_osm_counts_file_members_separately_from_duplicate_content_hashes(self):
        import base64,hashlib,io,zipfile
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as archive:
            archive.writestr('first.json',b'{}');archive.writestr('second.json',b'{}')
        raw=buf.getvalue();base='artifacts/Habu_AI_OSM_Road_Grid_2026-09-25.zip.parts/'
        write(self.root,base+'README.md',('Original SHA-256: `'+hashlib.sha256(raw).hexdigest()+'`').encode())
        for i in range(33):write(self.root,base+f'part_{i:03}.b64',base64.b64encode(raw) if i==0 else b'')
        result=self.audit()
        self.assertEqual(result['osm_audit']['archive_members'],2)
        self.assertEqual(result['osm_audit']['unique_payload_hashes'],1)

    def test_raw_log_count_links_are_checked_without_inventing_coordinate_authority(self):
        fixture(self.root)
        write(self.root,'data/raw/habu_logs/log.json',{'operational_date':NIGHT,
            'capture_summary':{'individuals':2,'capture_events':1},
            'events':[{'type':'capture','time_local':NIGHT+'T21:20:00+09:00','individual_count':2}]})
        result=self.audit()
        self.assertEqual(result['capture_audit']['raw_log_candidates'][0]['matched_event_id'],'C')
        self.assertEqual(result['outcome_ledger']['events'],[])
        self.assertTrue(any(c['check']=='raw_log_counts' and c['status']=='PASS' for c in result['checks']))
        write(self.root,'data/raw/habu_logs/log.json',{'operational_date':NIGHT,
            'capture_summary':{'individuals':3,'capture_events':1},
            'events':[{'type':'capture','time_local':NIGHT+'T21:20:00+09:00','individual_count':3}]})
        self.assertEqual(self.audit()['status'],'FAIL')

    def test_zero_master_budget_never_invokes_auditor(self):
        from unittest.mock import patch
        import master_orchestrator as m
        fixture(self.root)
        with patch('evidence_audit.audit_evidence',side_effect=AssertionError('must not scan')) as auditor:
            result=m.run_master(self.root,NIGHT,0)
        auditor.assert_not_called()
        self.assertEqual(result['overall_status'],'BLOCKED')
        self.assertEqual(len(result['stages']),9)
        self.assertTrue(all(s['status']!='FAIL' for s in result['stages']))

    def test_failed_raw_capture_cannot_establish_negative_or_complete_ledger(self):
        from learning_snapshot import build_learning_snapshot
        for count,summary,reason,pointer in (
            (None,{},'RAW_LOG_EXACT_COUNT_REQUIRED','/events/0'),
            (1,{'individuals':2,'capture_events':1},'RAW_LOG_SUMMARY_CONFLICT','/capture_summary'),
        ):
            for empty in (True,False):
                with self.subTest(reason=reason,empty=empty),tempfile.TemporaryDirectory() as tmp:
                    root=Path(tmp);_,cap=fixture(root,True,empty=empty);complete_coverage(root,cap)
                    raw=write(root,'data/raw/habu_logs/known.json',{'operational_date':NIGHT,
                        'capture_summary':summary,
                        'events':[{'type':'capture','time_local':NIGHT+'T21:00:00+09:00','individual_count':count}]})
                    receipt(root,raw)
                    result=self.a.audit_evidence(root,NIGHT,verified_at=VERIFIED)
                    self.assertEqual(result['status'],'FAIL')
                    self.assertIsNone(result['observation_units'][0]['label'])
                    self.assertEqual(result['observation_units'][0]['observation'],'UNKNOWN')
                    self.assertFalse(any(u['label']==0 for u in result['observation_units']))
                    self.assertEqual(result['outcome_ledger']['denominator_coverage'],'NOT_ESTABLISHED')
                    self.assertEqual(result['outcome_ledger']['complete_scopes'],[])
                    self.assertEqual([e['event_id'] for e in result['outcome_ledger']['events']],[] if empty else ['C'])
                    self.assertEqual([u['label'] for u in result['observation_units']],[None] if empty else [None,1])
                    rejected=result['capture_audit']['rejected'][0]
                    self.assertEqual(rejected['source'],raw['path'])
                    self.assertEqual(rejected['reason'],reason)
                    self.assertEqual(rejected['source_ref'],dict(raw,selector={'json_pointer':pointer}))
                    self.assertTrue(any(c['check']=='raw_log_counts' and c['status']=='FAIL' and c['reason']==reason for c in result['checks']))
                    built=build_learning_snapshot(root,NIGHT,result)
                    self.assertEqual(built['status'],'FAIL')
                    self.assertEqual(built['reason'],'UPSTREAM_AUDIT_FAILED')

    def test_valid_qualified_raw_capture_reconciliation_preserves_eligibility(self):
        _,cap=fixture(self.root,True);complete_coverage(self.root,cap)
        raw=write(self.root,'data/raw/habu_logs/known.json',{'operational_date':NIGHT,
            'capture_summary':{'individuals':2,'capture_events':1},
            'events':[{'type':'capture','time_local':NIGHT+'T21:20:00+09:00','individual_count':2}]})
        receipt(self.root,raw);result=self.audit()
        self.assertEqual(result['status'],'PASS')
        self.assertEqual([u['label'] for u in result['observation_units']],[0,1])
        self.assertEqual(result['outcome_ledger']['denominator_coverage'],'ESTABLISHED_FOR_DECLARED_DOMAIN')
        self.assertEqual(result['capture_audit']['raw_log_candidates'][0]['capture_count'],2)
        self.assertTrue(result['capture_audit']['raw_log_candidates'][0]['canonical_match'])
        self.assertEqual(result['capture_audit']['rejected'],[])

    def test_audit_runtime_limits_are_not_data_or_integrity_failures(self):
        from unittest.mock import patch
        fixture(self.root)
        with patch.object(self.a,'MAX_POINTS',1):
            result=self.audit()
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['input_requirements'][-1]['kind'],'RUNTIME_BLOCKED')
        self.assertEqual(result['observation_units'],[])
        result=self.a.audit_evidence(self.root,NIGHT,budget_seconds=0)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['input_hashes'],{})

    def test_future_review_cannot_make_a_negative_available_at_earlier_audit(self):
        fixture(self.root,True)
        policy=json.loads((self.root/'policies/observation_evidence.json').read_text())
        entry=policy['sources'][0];path=self.root/entry['review_ref']['path']
        review=json.loads(path.read_text());review['reviewed_at']='2026-10-02T20:00:00+09:00'
        path.write_bytes(canonical_bytes(review));entry['review_ref']['sha256']=file_hash(path)
        (self.root/'policies/observation_evidence.json').write_bytes(canonical_bytes(policy))
        result=self.audit()
        self.assertFalse(any(u['label']==0 for u in result['observation_units']))
        self.assertEqual(result['status'],'FAIL')

    def test_unqualified_known_capture_blocks_negative_without_becoming_positive(self):
        fixture(self.root,True,empty=True)
        write(self.root,'data/processed/capture_events/unqualified.csv',
              b'event_id,event_type,event_count,datetime_jst,latitude,longitude\nU,capture,1,2026-09-28T21:00:00+09:00,28.15,129.3\n')
        result=self.audit()
        self.assertIsNone(result['observation_units'][0]['label'])
        self.assertEqual(result['outcome_ledger']['events'],[])
        from test_learning_snapshot import build_request
        from learning_snapshot import build_learning_snapshot
        build_request(self.root);result=self.audit()
        built=build_learning_snapshot(self.root,NIGHT,result)
        rows=json.loads((self.root/built['evaluation_root']/'data/processed/model_learning.json').read_text())['rows']
        self.assertTrue(all(row['label'] is None for row in rows))

    def test_unlocated_rejected_capture_blocks_negatives_conservatively(self):
        fixture(self.root,True,empty=True)
        write(self.root,'data/processed/capture_events/unlocated.csv',
              b'event_id,event_type,event_count,datetime_jst,latitude,longitude\nU,capture,1,2026-09-28T21:00:00+09:00,,\n')
        result=self.audit()
        self.assertTrue(all(u['label'] is None for u in result['observation_units']))

    def test_complete_empty_log_requires_capture_schema(self):
        for raw in (b'',b'not_a_capture_schema\n'):
            with self.subTest(raw=raw),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);_,cap=fixture(root,True,capture_bytes=raw);complete_coverage(root,cap)
                result=self.a.audit_evidence(root,NIGHT,verified_at=VERIFIED)
                self.assertEqual(result['status'],'FAIL')
                self.assertEqual(result['outcome_ledger']['denominator_coverage'],'NOT_ESTABLISHED')
                self.assertFalse(any(u['label']==0 for u in result['observation_units']))

    def test_explicit_noncaptures_are_not_ambiguous_capture_rejections(self):
        raw=b'event_id,event_type,event_count,datetime_jst,latitude,longitude\nS,sighting,1,2026-09-28T21:00:00+09:00,28.15,129.3\nR,roadkill,1,2026-09-28T21:00:00+09:00,28.15,129.3\nC,capture,2,2026-09-28T21:20:00+09:00,28.15,129.3\n'
        _,cap=fixture(self.root,True,capture_bytes=raw);complete_coverage(self.root,cap)
        result=self.audit()
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['capture_audit']['diagnostic_individuals'],2)
        self.assertEqual(len(result['capture_audit']['noncapture_records']),2)
        self.assertEqual(result['observation_units'][0]['label'],0)
        self.assertEqual(result['outcome_ledger']['denominator_coverage'],'ESTABLISHED_FOR_DECLARED_DOMAIN')

    def test_unknown_event_kind_remains_unresolved(self):
        raw=b'event_id,event_type,event_count,datetime_jst,latitude,longitude\nU,maybe,1,2026-09-28T21:00:00+09:00,28.15,129.3\n'
        fixture(self.root,True,capture_bytes=raw);result=self.audit()
        self.assertTrue(result['capture_audit']['rejected'])
        self.assertFalse(any(u['label']==0 for u in result['observation_units']))

    def test_strict_gpx_schema_failure_is_aggregate_failure(self):
        _,cap=fixture(self.root,True,gpx_bytes=b'<gpx><trk><trkseg><trkpt lat="28.15" lon="129.3"><time>2026-09-28T21:00:00</time></trkpt></trkseg></trk></gpx>')
        complete_coverage(self.root,cap);result=self.audit()
        self.assertEqual(result['status'],'FAIL')
        self.assertTrue(any(c['status']=='FAIL' and c['check']=='gpx_schema' for c in result['checks']))

    def test_orphan_individual_link_is_aggregate_failure(self):
        fixture(self.root,True)
        write(self.root,'data/processed/individuals/individuals.csv',b'individual_id,event_id\nI1,C\nI2,C\nORPHAN,NO_EVENT\n')
        result=self.audit()
        self.assertEqual(result['status'],'FAIL')
        self.assertTrue(any(c['status']=='FAIL' and c['check']=='individual_links' for c in result['checks']))
        self.assertFalse(any(u['label']==0 for u in result['observation_units']))

    def test_hash_valid_non_capture_namespace_cannot_establish_empty_log(self):
        _,cap=fixture(self.root,True,empty=True)
        old=cap['path'];new='evidence/unparsed.csv'
        (self.root/new).write_bytes((self.root/old).read_bytes());(self.root/old).unlink()
        p=self.root/'policies/observation_evidence.json';p.write_text(p.read_text().replace(old,new))
        r=self.root/'evidence/raw_intake'/f"{cap['sha256']}.json"
        r.write_text(r.read_text().replace(old,new))
        cap['path']=new;complete_coverage(self.root,cap);result=self.audit()
        self.assertFalse(any(u['label']==0 for u in result['observation_units']))
        self.assertEqual(result['outcome_ledger']['denominator_coverage'],'NOT_ESTABLISHED')
