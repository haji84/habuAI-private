"""Synthetic orchestration controls; no test fixture is field qualification."""
from datetime import datetime, timedelta, timezone
import importlib.util
import csv
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
JST=timezone(timedelta(hours=9))


class HistoricalBackfillTests(unittest.TestCase):
    def setUp(self):
        path=ROOT/'scripts/backfill_historical_environment.py'
        self.assertTrue(path.is_file(),'Missing bounded historical source backfill')
        spec=importlib.util.spec_from_file_location('historical_backfill_cli',path)
        self.module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def rows(self):
        finish=datetime(2026,11,1,7,tzinfo=JST)
        return [dict(valid_start=(finish-timedelta(hours=i+1)).isoformat(),
                     valid_end=(finish-timedelta(hours=i)).isoformat(),
                     support_kind='HOURLY_REFERENCE_STATION',
                     values={'precipitation_mm':dict(value=1.0 if i==0 else 0.0,
                        unit='mm',kind='OBSERVED',quality='NORMAL')}) for i in range(72)]

    def test_rain_memory_is_explicit_unvalidated_proxy_not_surface_measurement(self):
        result=self.module.rain_memory_proxy(self.rows(),window_start='2026-11-01T07:00:00+09:00')
        self.assertEqual(result['kind'],'DERIVED_HYPOTHESIS')
        self.assertEqual(result['surface_wetness_observed'],False)
        self.assertEqual(result['values_mm'],{'12':1.0,'24':1.0,'48':1.0})
        self.assertFalse(result['empirically_validated'])

    def test_missing_old_rain_does_not_create_dry_surface(self):
        result=self.module.rain_memory_proxy(self.rows()[:-1],window_start='2026-11-01T07:00:00+09:00')
        self.assertIsNone(result['values_mm'])
        self.assertEqual(result['status'],'UNKNOWN')

    def test_missing_corpus_is_explicit_and_does_not_fit(self):
        result=self.module.audit_training_source()
        self.assertEqual(result['status'],'BLOCKED')
        self.assertFalse(result['selector_ran'])
        self.assertFalse(result['fitter_ran'])
        self.assertEqual(result['fitted_training_rows'],0)
        self.assertIsNone(result['model_sha256'])
        self.assertFalse(result['eligible_count_verified'])

    def test_real_selector_rejects_missing_source_without_fitting(self):
        with tempfile.TemporaryDirectory() as folder:
            result=self.module.audit_training_source(corpus_root=Path(folder),
                corpus_path='missing.json',corpus_sha256='a'*64,
                heldout_night='2026-11-04',fit_cutoff='2026-11-03T18:00:00+09:00',
                feature_names=('temperature_c',))
        self.assertTrue(result['selector_ran'])
        self.assertFalse(result['fitter_ran'])
        self.assertEqual(result['status'],'BLOCKED')

    def test_private_output_refuses_any_git_worktree(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'.git').mkdir()
            with self.assertRaisesRegex(ValueError,'GIT_WORKTREE'):
                self.module.assert_private_directory(root/'private'/'outputs')

    def test_private_output_accepts_external_directory_but_rejects_code_reports(self):
        self.module.assert_private_directory(Path(tempfile.gettempdir())/'habu-private-test-destination')
        with self.assertRaisesRegex(ValueError,'GIT_WORKTREE'):
            self.module.assert_private_directory(ROOT/'reports'/'private')

    def training_fixture(self):
        import test_training_corpus
        fixture=test_training_corpus.AuditedTrainingTests()
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        return fixture

    def test_existing_selector_and_fitter_run_only_on_synthetic_eligible_source(self):
        fixture=self.training_fixture()
        result=self.module.audit_training_source(corpus_root=fixture.root,
            corpus_path=fixture.path,corpus_sha256=fixture.sha,
            heldout_night='2026-10-21',fit_cutoff='2026-10-20T18:00:00+09:00',
            feature_names=('road_length_m',),run_fit=True)
        self.assertEqual(result['status'],'DEVELOPMENT_FIT_ONLY')
        self.assertTrue(result['selector_ran']);self.assertTrue(result['fitter_ran'])
        self.assertEqual(result['fitted_training_rows'],4)
        self.assertEqual(result['fit_evidence']['prior_nights'],3)
        self.assertEqual(len(result['model_sha256']),64)
        self.assertFalse(result['production_authorized'])
        self.assertEqual(result['independent_confirmation'],'NOT_PERFORMED')

    def test_unknown_rows_never_run_fitter(self):
        fixture=self.training_fixture()
        for row in fixture.rows:
            row.update(observation='UNKNOWN',label=None,quality='UNKNOWN')
        fixture.publish()
        result=self.module.audit_training_source(corpus_root=fixture.root,
            corpus_path=fixture.path,corpus_sha256=fixture.sha,
            heldout_night='2026-10-21',fit_cutoff='2026-10-20T18:00:00+09:00',
            feature_names=('road_length_m',),run_fit=True)
        self.assertTrue(result['selector_ran']);self.assertFalse(result['fitter_ran'])
        self.assertEqual(result['fitted_training_rows'],0)
        self.assertIsNone(result['model_sha256'])

    def test_private_join_keeps_original_fields_and_never_uses_next_hour(self):
        self.assertTrue(hasattr(self.module,'join_private_candidates'),'Missing private feature join')
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder); source=base/'candidate.csv'
            source.write_text('event_time_jst,note\n2026-11-01 07:35,original note\n2026-11-01 07:00-08:00,range\n',encoding='utf-8')
            rows=self.rows()
            rows[0]['values']['temperature_c']={'value':17.0,'kind':'OBSERVED'}
            future=dict(valid_start='2026-11-01T07:00:00+09:00',
                valid_end='2026-11-01T08:00:00+09:00',support_kind='HOURLY_REFERENCE_STATION',
                values={'temperature_c':{'value':99.0,'kind':'OBSERVED'}})
            result=self.module.join_private_candidates(source,hashlib.sha256(source.read_bytes()).hexdigest(),
                [*rows,future],base/'joined.csv',source_usable_at='2026-11-03T10:00:00+09:00')
            with (base/'joined.csv').open(encoding='utf-8-sig',newline='') as stream:
                joined=list(csv.DictReader(stream))
            self.assertEqual(result['rows'],2);self.assertEqual(result['joined_rows'],1)
            self.assertEqual(joined[0]['note'],'original note')
            self.assertEqual(json.loads(joined[0]['_env_previous_hour_values'])['temperature_c']['value'],17.0)
            self.assertEqual(joined[1]['event_time_jst'],'2026-11-01 07:00-08:00')
            self.assertEqual(joined[1]['_env_status'],'UNKNOWN_TIMESTAMP')
            self.assertEqual(result['labels_created'],0)
            self.assertIn('usable_at',result,'Derived features need their own actual materialization readiness')
            ready=datetime.fromisoformat(result['usable_at'])
            self.assertGreaterEqual(ready,datetime.fromisoformat('2026-11-03T10:00:00+09:00'))
            for field in ('derived_at','materialized_at','audited_at'):
                self.assertGreaterEqual(ready,datetime.fromisoformat(result[field]))

    def test_private_candidate_digest_mismatch_is_not_joined(self):
        self.assertTrue(hasattr(self.module,'join_private_candidates'),'Missing private feature join')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/'candidate.csv'; source.write_text('event_time_jst\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'CANDIDATE_SHA'):
                self.module.join_private_candidates(source,'0'*64,[],root/'out.csv',
                    source_usable_at='2026-11-03T10:00:00+09:00')
            self.assertFalse((root/'out.csv').exists())

    def test_lunar_join_keeps_last_noon_calculation_separate_from_event_measurement(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);source=base/'candidate.csv'
            source.write_text('event_time_jst,note\n2026-11-01 07:35,unchanged\n',encoding='utf-8')
            lunar=[dict(valid_start=day+'T12:00:00+09:00',valid_end=day+'T12:00:00+09:00',
                values={'moon_age_days':dict(value=value,unit='day',kind='ASTRONOMICAL_CALCULATION')})
                for day,value in [('2026-10-31',18.4),('2026-11-01',19.4)]]
            result=self.module.join_private_candidates(source,hashlib.sha256(source.read_bytes()).hexdigest(),
                self.rows(),base/'joined.csv',source_usable_at='2026-11-03T10:00:00+09:00',
                astronomy_observations=lunar)
            with (base/'joined.csv').open(encoding='utf-8',newline='') as stream:row=next(csv.DictReader(stream))
            sample=json.loads(row['_env_moon_age_reference'])
            self.assertEqual(sample['valid_start'],'2026-10-31T12:00:00+09:00')
            self.assertEqual(sample['values']['moon_age_days']['value'],18.4)
            self.assertEqual(row['_env_moon_status'],'LAGGED_NOON_CALCULATION_NOT_EVENT_MEASUREMENT')
            self.assertEqual(result['lunar_joined_rows'],1)
            self.assertFalse(result['moonlight_measured'])
            self.assertEqual(row['note'],'unchanged')

    def test_missing_or_stale_lunar_sample_does_not_create_zero_or_future_value(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);source=base/'candidate.csv'
            source.write_text('event_time_jst\n2026-11-01 07:35\n',encoding='utf-8')
            for index,kind,value,at in [(0,'UNKNOWN',None,'2026-10-31'),
                    (1,'ASTRONOMICAL_CALCULATION',18.4,'2026-10-30'),
                    (2,'ASTRONOMICAL_CALCULATION',19.4,'2026-11-01')]:
                lunar=[dict(valid_start=at+'T12:00:00+09:00',valid_end=at+'T12:00:00+09:00',
                    values={'moon_age_days':dict(value=value,unit='day',kind=kind)})]
                result=self.module.join_private_candidates(source,hashlib.sha256(source.read_bytes()).hexdigest(),
                    self.rows(),base/(str(index)+'.csv'),source_usable_at='2026-11-03T10:00:00+09:00',
                    astronomy_observations=lunar)
                self.assertEqual(result['lunar_joined_rows'],0)

    def test_alias_receipts_cannot_double_count_one_station_day(self):
        import test_historical_environment as fixture
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder); evidence=base/'evidence'
            (evidence/'receipts').mkdir(parents=True);(evidence/'incoming').mkdir()
            raw=fixture.table();(evidence/'incoming'/'public.source').write_bytes(raw)
            receipt=dict(fixture.receipt(raw),raw_file='public.source',day='2026-11-01')
            for name in ('one','alias'):
                (evidence/'receipts'/(name+'.json')).write_text(json.dumps(receipt),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'DUPLICATE_SOURCE_PERIOD'):
                self.module.process_evidence(evidence,base/'out')

    def test_monthly_tide_receipt_cannot_add_day_to_evade_period_identity(self):
        import test_historical_tides as fixture
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);evidence=base/'evidence'
            (evidence/'receipts').mkdir(parents=True);(evidence/'incoming').mkdir()
            raw=fixture.jma();(evidence/'incoming'/'tide.source').write_bytes(raw)
            for day in ('2026-11-01','2026-11-02'):
                receipt=dict(fixture.receipt(raw,'JMA'),raw_file='tide.source',month='2026-11',day=day)
                (evidence/'receipts'/(day+'.json')).write_text(json.dumps(receipt),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'PERIOD'):
                self.module.process_evidence(evidence,base/'out')

    def test_finalized_month_uses_distinct_adapter_and_preserves_observation_kind(self):
        import test_historical_tides as fixture
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);evidence=base/'evidence'
            (evidence/'receipts').mkdir(parents=True);(evidence/'incoming').mkdir()
            raw=fixture.jma(day='2025-01-01').rstrip(b'\n')+b' '*56+b'\n'
            (evidence/'incoming'/'final.source').write_bytes(raw)
            url='https://www.data.jma.go.jp/kaiyou/data/db/tide/genbo/2025/202501/hry202501O9.txt'
            rec=dict(fixture.receipt(raw,'JMA'),source_type='OBSERVED_FINALIZED',
                requested_url=url,resolved_url=url,raw_file='final.source',month='2025-01')
            (evidence/'receipts'/'final.json').write_text(json.dumps(rec),encoding='utf-8')
            result=self.module.process_evidence(evidence,base/'out')
            self.assertEqual(result['tide_sources'],[dict(station='O9',source_type='OBSERVED_FINALIZED',
                rows=24,numeric=24)])
            ref=result['derived_refs'][0]
            payload=json.loads((base/'out'/ref['path']).read_bytes())
            self.assertEqual(payload['observations'][0]['values']['tide_height_cm']['kind'],'OBSERVED_FINALIZED')
            self.assertFalse(result['training']['fitter_ran'])

    def test_naoj_period_retains_calculated_noon_points_and_coverage(self):
        import test_historical_astronomy as fixture
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);evidence=base/'evidence'
            (evidence/'receipts').mkdir(parents=True);(evidence/'incoming').mkdir()
            raw=fixture.body();(evidence/'incoming'/'moon.source').write_bytes(raw)
            rec=dict(fixture.provenance(raw),raw_file='moon.source',
                period_start='2025-01-01',period_end='2025-01-02')
            rec.update(content_type='text/html; charset=EUC-JP',public_reference_only=True,
                historical_ex_ante_proven=False,training_eligibility='NOT_ASSESSED',normalized_rows=2)
            (evidence/'receipts'/'moon.json').write_text(json.dumps(rec),encoding='utf-8')
            result=self.module.process_evidence(evidence,base/'out')
            self.assertEqual(result['astronomy']['daily_noon_points'],2)
            self.assertEqual(result['astronomy']['known_moon_age_days'],2)
            self.assertFalse(result['astronomy']['moonlight_measured'])
            self.assertFalse(result['training']['fitter_ran'])
            ref=result['derived_refs'][0]
            payload=json.loads((base/'out'/ref['path']).read_bytes())
            self.assertEqual(payload['observations'][0]['valid_start'],'2025-01-01T12:00:00+09:00')
            self.assertEqual(payload['observations'][0]['values']['moon_age_days']['kind'],
                'ASTRONOMICAL_CALCULATION')

    def test_naoj_period_cannot_accept_alias_calendar_fields(self):
        import test_historical_astronomy as fixture
        for alias in ('day','month','production_authorized'):
            with self.subTest(alias=alias),tempfile.TemporaryDirectory() as folder:
                base=Path(folder);evidence=base/'evidence'
                (evidence/'receipts').mkdir(parents=True);(evidence/'incoming').mkdir()
                raw=fixture.body();(evidence/'incoming'/'moon.source').write_bytes(raw)
                rec=dict(fixture.provenance(raw),raw_file='moon.source',
                    period_start='2025-01-01',period_end='2025-01-02')
                rec[alias]='2025-01-01'
                (evidence/'receipts'/'moon.json').write_text(json.dumps(rec),encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'PERIOD'):
                    self.module.process_evidence(evidence,base/'out')

    def test_derived_readiness_is_bound_after_physical_write_and_readback(self):
        import test_historical_environment as fixture
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);evidence=base/'evidence';output=base/'out'
            (evidence/'receipts').mkdir(parents=True);(evidence/'incoming').mkdir()
            raw=fixture.table();(evidence/'incoming'/'public.source').write_bytes(raw)
            rec=dict(fixture.receipt(raw),raw_file='public.source',day='2026-11-01')
            (evidence/'receipts'/'one.json').write_text(json.dumps(rec),encoding='utf-8')
            native=self.module._write_new
            completed=[]
            def delayed(path,value,**kwargs):
                if path.name.endswith('.normalized.json'):time.sleep(.05)
                result=native(path,value,**kwargs)
                if path.name.endswith('.normalized.json'):completed.append(datetime.now(timezone.utc))
                return result
            with patch.object(self.module,'_write_new',delayed):
                result=self.module.process_evidence(evidence,output)
            reference=result['derived_refs'][0]
            self.assertIn('readiness_receipt',reference)
            ready=json.loads((output/reference['readiness_receipt']['path']).read_bytes())
            payload=output/reference['path']
            self.assertEqual(ready['artifact']['sha256'],hashlib.sha256(payload.read_bytes()).hexdigest())
            # Compare the same clock/precision at the observable write boundary;
            # Windows file timestamps can retain sub-microseconds absent in ISO.
            self.assertGreaterEqual(datetime.fromisoformat(ready['materialized_at']),completed[0])
            self.assertGreaterEqual(datetime.fromisoformat(ready['usable_at']),datetime.fromisoformat(ready['audited_at']))

    def test_completion_rechecks_payload_sidecar_candidate_and_private_source(self):
        import test_historical_environment as fixture
        for kind in ('payload','sidecar','candidate','private_source'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as folder:
                base=Path(folder);evidence=base/'evidence';output=base/'out'
                (evidence/'receipts').mkdir(parents=True);(evidence/'incoming').mkdir()
                raw=fixture.table();(evidence/'incoming'/'public.source').write_bytes(raw)
                rec=dict(fixture.receipt(raw),raw_file='public.source',day='2026-11-01')
                (evidence/'receipts'/'one.json').write_text(json.dumps(rec),encoding='utf-8')
                source=base/'candidate.csv'
                source.write_text('event_time_jst,note\n2026-11-01 07:35,original\n',encoding='utf-8')
                native=self.module.join_private_candidates
                def mutate(*args,**kwargs):
                    result=native(*args,**kwargs)
                    target={'payload':output/'one.normalized.json','sidecar':output/'one.readiness.json',
                        'candidate':output/'historical_candidate_env_PRIVATE.csv','private_source':source}[kind]
                    with target.open('ab') as stream:stream.write(b' ')
                    return result
                with patch.object(self.module,'join_private_candidates',mutate):
                    with self.assertRaisesRegex(ValueError,'CHANGED_BEFORE_COMPLETION'):
                        self.module.process_evidence(evidence,output,candidate_csv=source,
                            candidate_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
                self.assertFalse((output/'report_PRIVATE.json').exists())

    def test_cli_validation_gate_returns_blocked_without_private_paths(self):
        args=['backfill','--evidence-dir',str(ROOT),'--output-dir',str(ROOT/'private')]
        with patch.object(self.module.sys,'argv',args),contextlib.redirect_stdout(io.StringIO()) as output:
            status=self.module.main()
        self.assertEqual(status,2)
        result=json.loads(output.getvalue())
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['reason_code'],'PRIVATE_OUTPUT_IN_GIT_WORKTREE_FORBIDDEN')
        self.assertNotIn(str(ROOT),output.getvalue())

    def test_cli_rejects_nonobject_duplicate_and_deep_receipts_without_tracebacks(self):
        cases=[(raw,'SOURCE_RECEIPT_OBJECT_REQUIRED') for raw in (b'[]',b'null',b'0',b'"text"')]
        cases.extend([(b'{"provider":"JMA","provider":"JCG"}','SOURCE_RECEIPT_DUPLICATE_KEY'),
                      (b'['*2000+b'0'+b']'*2000,
                       ('SOURCE_RECEIPT_JSON_INVALID','SOURCE_RECEIPT_OBJECT_REQUIRED'))])
        for raw,reason in cases:
            with self.subTest(reason=reason,head=raw[:8]),tempfile.TemporaryDirectory() as folder:
                base=Path(folder);evidence=base/'evidence';(evidence/'receipts').mkdir(parents=True)
                (evidence/'receipts'/'invalid.json').write_bytes(raw)
                args=['backfill','--evidence-dir',str(evidence),'--output-dir',str(base/'out')]
                with patch.object(self.module.sys,'argv',args),contextlib.redirect_stdout(io.StringIO()) as output:
                    status=self.module.main()
                self.assertEqual(status,2)
                # Decoder recursion limits differ; either path must reject the
                # receipt and keep private paths out of the actual CLI output.
                self.assertIn(json.loads(output.getvalue())['reason_code'],
                    reason if isinstance(reason,tuple) else (reason,))
                self.assertNotIn(str(base),output.getvalue())


if __name__=='__main__': unittest.main()
