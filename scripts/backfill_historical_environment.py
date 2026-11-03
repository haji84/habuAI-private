#!/usr/bin/env python3
"""Normalize retained historical reference sources in a private local workspace.

No download, public upload, label creation, forecast issuance or promotion occurs.
An explicit existing audited corpus can invoke the existing TRAIN_ONLY selector
and optional development fitter. Historical research is never confirmation.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
import io
from pathlib import Path
import sys
import re

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from historical_environment import RECEIPT_FIELDS, antecedent_rainfall, normalize_jma_hourly
from historical_tides import (normalize_jcg_predictions, normalize_jma_tide_observations,
                              normalize_jma_finalized_tide_observations)
from historical_astronomy import normalize_naoj_moon_age
from master_contracts import canonical_bytes, digest, validate_night
from master_inventory import local_path

JST=timezone(timedelta(hours=9))
MAX_INPUT_BYTES=64*1024*1024
MAX_NORMALIZED_BYTES=128*1024*1024


def _unique_receipt_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('SOURCE_RECEIPT_DUPLICATE_KEY')
        result[key]=value
    return result


def assert_private_directory(value):
    path=Path(value).absolute()
    for parent in (path,*path.parents):
        if parent.is_symlink() or getattr(parent,'is_junction',lambda:False)():
            raise ValueError('PRIVATE_OUTPUT_REPARSE_FORBIDDEN')
        if (parent/'.git').exists():
            raise ValueError('PRIVATE_OUTPUT_IN_GIT_WORKTREE_FORBIDDEN')
    return path


def rain_memory_proxy(observations, *, window_start):
    """A fixed exploratory rainfall-memory hypothesis; no observed road wetness."""
    coverage=antecedent_rainfall(observations,window_start=window_start,horizons=(72,))['72']
    result=dict(kind='DERIVED_HYPOTHESIS',status='UNKNOWN',values_mm=None,
        surface_wetness_observed=False,empirically_validated=False,
        method='sum(hourly_rain_mm*exp(-hours_since_interval_end/tau)); past72h only',
        e_folding_hours=[12,24,48],coverage=coverage)
    if coverage['status']!='COMPLETE':return result
    end=datetime.fromisoformat(window_start.replace('Z','+00:00'))
    start=end-timedelta(hours=72)
    rows=[r for r in observations if
        start<=datetime.fromisoformat(r['valid_start']) and
        datetime.fromisoformat(r['valid_end'])<=end]
    result.update(status='COMPUTED_PROXY',values_mm={str(tau):math.fsum(
        r['values']['precipitation_mm']['value']*math.exp(
            -(end-datetime.fromisoformat(r['valid_end'])).total_seconds()/3600/tau)
        for r in rows) for tau in (12,24,48)})
    return result


def audit_training_source(*, corpus_root=None, corpus_path=None, corpus_sha256=None,
                          heldout_night=None, fit_cutoff=None, feature_names=(), run_fit=False):
    result=dict(status='BLOCKED',selector_ran=False,fitter_ran=False,
        fitted_training_rows=0,eligible_count_verified=False,model_sha256=None,
        independent_confirmation='NOT_PERFORMED',production_authorized=False,
        blockers=['MISSING_AUDITED_TRAIN_ONLY_CORPUS_AND_SOURCE_PROOFS'])
    if not all((corpus_root,corpus_path,corpus_sha256,heldout_night,fit_cutoff,feature_names)):
        return result
    from training_corpus import select_training_rows
    result['selector_ran']=True
    try:
        selection=select_training_rows(Path(corpus_root),corpus_path,corpus_sha256,
            heldout_night,fit_cutoff,require_features=tuple(feature_names))
    except (OSError,ValueError,KeyError,TypeError) as exc:
        result['blockers']=['SOURCE_SELECTOR_REJECTED_'+type(exc).__name__]
        return result
    result.update(selection_status=selection['status'],counts=selection['counts'],
        eligible_count_verified=True,selection_sha256=selection['selection_sha256'],
        blockers=selection['blockers'])
    if selection['status']!='DEVELOPMENT_TRAINING_ELIGIBLE':return result
    result['status']='SOURCE_SELECTED_NOT_FITTED'
    if not run_fit:return result
    from train_spacetime_candidate import fit_candidate
    fitted=fit_candidate(selection)
    result.update(status=fitted['status'],fitter_ran=True,
        fitted_training_rows=fitted['fit_evidence']['rows'],fit_evidence=fitted['fit_evidence'],
        model=fitted['model'],model_sha256=fitted['model']['model_sha256'])
    return result


def _write_new(path, value, *, limit=MAX_NORMALIZED_BYTES):
    raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    if len(raw)>limit:raise ValueError('DERIVED_OUTPUT_BYTE_LIMIT')
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('DERIVED_OUTPUT_COLLISION')
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
    return dict(path=path.name,sha256=hashlib.sha256(raw).hexdigest(),size_bytes=len(raw))


def _weather_index(observations):
    rows=sorted(observations,key=lambda r:datetime.fromisoformat(r['valid_end']).timestamp())
    return rows,[datetime.fromisoformat(r['valid_end']).timestamp() for r in rows]


def _prior_window(rows, endings, at):
    return rows[bisect_right(endings,(at-timedelta(hours=72)).timestamp()):bisect_right(endings,at.timestamp())]


def join_private_candidates(source, expected_sha256, observations, destination, *, source_usable_at,
                            astronomy_observations=()):
    """Append lagged reference-station features; never assign scientific labels."""
    source=Path(source);destination=Path(destination)
    assert_private_directory(source.parent);assert_private_directory(destination.parent)
    with source.open('rb') as stream: raw=stream.read(16*1024*1024+1)
    if len(raw)>16*1024*1024:raise ValueError('CANDIDATE_BYTE_LIMIT')
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('CANDIDATE_SHA_MISMATCH')
    ready=datetime.fromisoformat(source_usable_at.replace('Z','+00:00'))
    if ready.utcoffset() is None:raise ValueError('CANDIDATE_FEATURE_READY_TIME_NAIVE')
    derived_at=datetime.now(timezone.utc).isoformat()
    reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig'),newline=''))
    names=reader.fieldnames
    extra=['_env_status','_env_station_id','_env_reference_hour','_env_previous_hour_values',
           '_env_antecedent_rainfall','_env_rain_memory_proxy','_env_source_usable_at',
           '_env_geographic_support','_env_qualification',
           '_env_moon_status','_env_moon_age_reference']
    if (not names or len(names)>128 or len(set(names))!=len(names) or
        'event_time_jst' not in names or set(names).intersection(extra)):
        raise ValueError('CANDIDATE_HEADER_CONTRADICTION')
    indexed,endings=_weather_index(observations)
    lunar,lunar_endings=_weather_index(astronomy_observations)
    if len(set(lunar_endings))!=len(lunar_endings):raise ValueError('DUPLICATE_LUNAR_SAMPLE')
    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=names+extra,lineterminator='\n')
    writer.writeheader(); count=joined=unknown=missing=lunar_joined=0
    time_pattern=re.compile(r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:\+09:00)?\Z')
    for original in reader:
        count+=1
        if count>20000 or None in original or any(v is None for v in original.values()):
            raise ValueError('CANDIDATE_ROW_LIMIT_OR_SHAPE')
        row=dict(original);row.update({k:'' for k in extra})
        row.update(_env_status='UNKNOWN_TIMESTAMP',_env_station_id='88901',
                   _env_geographic_support='LAGGED_REFERENCE_STATION_ONLY',
                   _env_source_usable_at=source_usable_at,_env_qualification='NOT_ASSESSED',
                   _env_moon_status='UNKNOWN_TIMESTAMP')
        stamp=None
        if time_pattern.fullmatch(original['event_time_jst']):
            try:stamp=datetime.fromisoformat(original['event_time_jst'])
            except ValueError:pass
        if stamp is None:
            unknown+=1
        else:
            stamp=stamp.replace(tzinfo=JST) if stamp.tzinfo is None else stamp.astimezone(JST)
            row['_env_moon_status']='UNKNOWN_OR_STALE_NOON_CALCULATION'
            moon_stop=bisect_right(lunar_endings,stamp.timestamp())
            if moon_stop and 0<=stamp.timestamp()-lunar_endings[moon_stop-1]<86400:
                sample=lunar[moon_stop-1]
                age=sample['values']['moon_age_days']
                if (age['kind']=='ASTRONOMICAL_CALCULATION' and age['unit']=='day' and
                    type(age['value']) in (float,int) and math.isfinite(age['value']) and
                    0<=age['value']<31):
                    row['_env_moon_status']='LAGGED_NOON_CALCULATION_NOT_EVENT_MEASUREMENT'
                    row['_env_moon_age_reference']=json.dumps(sample,ensure_ascii=False,sort_keys=True)
                    lunar_joined+=1
            floor=stamp.replace(minute=0,second=0,microsecond=0)
            stop=bisect_right(endings,floor.timestamp())
            if not stop or endings[stop-1]!=floor.timestamp():
                row['_env_status']='MISSING_PREVIOUS_HOUR';missing+=1
            else:
                prior=indexed[stop-1]
                scope=_prior_window(indexed,endings,floor)
                row.update(_env_status='RETROSPECTIVE_REFERENCE_FEATURES',
                    _env_reference_hour=floor.isoformat(),
                    _env_previous_hour_values=json.dumps(prior['values'],ensure_ascii=False,sort_keys=True),
                    _env_antecedent_rainfall=json.dumps(antecedent_rainfall(scope,window_start=floor.isoformat()),sort_keys=True),
                    _env_rain_memory_proxy=json.dumps(rain_memory_proxy(scope,window_start=floor.isoformat()),sort_keys=True))
                joined+=1
        writer.writerow(row)
        if buffer.tell()>64*1024*1024:raise ValueError('CANDIDATE_OUTPUT_LIMIT')
    encoded=buffer.getvalue().encode('utf-8')
    if len(encoded)>64*1024*1024:raise ValueError('CANDIDATE_OUTPUT_LIMIT')
    if source.read_bytes()!=raw:raise ValueError('CANDIDATE_SOURCE_CHANGED')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as stream:stream.write(encoded)
    materialized_at=datetime.now(timezone.utc).isoformat()
    if destination.read_bytes()!=encoded:raise ValueError('CANDIDATE_DERIVED_READBACK_MISMATCH')
    audited_at=datetime.now(timezone.utc).isoformat()
    usable_at=max([ready,*map(datetime.fromisoformat,(derived_at,materialized_at,audited_at))]).isoformat()
    return dict(rows=count,joined_rows=joined,unknown_time_rows=unknown,missing_hour_rows=missing,
        all_original_fields_retained=True,labels_created=0,qualification='NOT_ASSESSED',
        exposure='RESEARCH_EXPOSED',source_sha256=expected_sha256,
        path=destination.name,derived_sha256=hashlib.sha256(encoded).hexdigest(),size_bytes=len(encoded),
        source_usable_at=source_usable_at,derived_at=derived_at,materialized_at=materialized_at,
        audited_at=audited_at,usable_at=usable_at,
        surface_wetness_measured=False,hourly_values_interpolated_to_ten_minutes=False,
        lunar_source_supplied=bool(lunar),lunar_joined_rows=lunar_joined,
        lunar_noon_samples_interpolated=False,moonlight_measured=False)


def process_evidence(evidence_dir, output_dir, *, operational_night='2026-11-01',
                     candidate_csv=None,candidate_sha256=None, **training_options):
    evidence_dir=assert_private_directory(evidence_dir)
    output_dir=assert_private_directory(output_dir)
    validate_night(operational_night)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError('Use a fresh append-only derived output directory')
    receipt_paths=sorted(local_path(evidence_dir,'receipts').glob('*.json'))
    if not 1<=len(receipt_paths)<=800:raise ValueError('SOURCE_RECEIPT_COUNT_LIMIT')
    source_refs=[]; outputs=[]; weather=[]; tides=[]; moon=[]; consumed=0; produced=0
    values=Counter(); missing=Counter(); days=[]; readiness=[]; seen_periods=set()
    code={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
          ('src/historical_environment.py','src/historical_tides.py','src/historical_astronomy.py',
           'scripts/backfill_historical_environment.py')}
    def read_bounded(path,limit):
        nonlocal consumed
        with path.open('rb') as stream:raw=stream.read(limit+1)
        consumed+=len(raw)
        if len(raw)>limit or consumed>MAX_INPUT_BYTES:raise ValueError('SOURCE_BYTE_LIMIT')
        return raw
    for file in receipt_paths:
        file=local_path(evidence_dir,'receipts/'+file.name)
        receipt_raw=read_bounded(file,65536)
        try:
            receipt=json.loads(receipt_raw,object_pairs_hook=_unique_receipt_object)
        except (json.JSONDecodeError,UnicodeError,RecursionError) as exc:
            raise ValueError('SOURCE_RECEIPT_JSON_INVALID') from exc
        if type(receipt) is not dict:raise ValueError('SOURCE_RECEIPT_OBJECT_REQUIRED')
        astronomical=receipt.get('provider')=='NAOJ'
        monthly=(receipt.get('provider')=='JMA' and receipt.get('source_type') in
                 ('OBSERVED_PROVISIONAL','OBSERVED_FINALIZED'))
        period_fields=('period_start','period_end') if astronomical else ('month' if monthly else 'day',)
        forbidden_fields={'day','month'} if astronomical else {'day' if monthly else 'month'}
        allowed=RECEIPT_FIELDS|set(period_fields)|{'raw_file','http_status','duplicate_status',
                                                'historical_publication_time','scope'}
        if astronomical:
            allowed|={'content_type','public_reference_only','historical_ex_ante_proven',
                      'training_eligibility','normalized_rows'}
        if forbidden_fields.intersection(receipt) or any(p not in receipt for p in period_fields) or set(receipt)-allowed:
            raise ValueError('SOURCE_PERIOD_OR_RECEIPT_FIELDS')
        if astronomical:
            fixed=dict(content_type='text/html; charset=EUC-JP',public_reference_only=True,
                       historical_ex_ante_proven=False,training_eligibility='NOT_ASSESSED')
            if any(key in receipt and (type(receipt[key]) is not type(value) or receipt[key]!=value)
                   for key,value in fixed.items()):raise ValueError('SOURCE_ACQUISITION_METADATA')
            if 'normalized_rows' in receipt and (type(receipt['normalized_rows']) is not int or
                receipt['normalized_rows']!=(date.fromisoformat(receipt['period_end'])-
                    date.fromisoformat(receipt['period_start'])).days+1):
                raise ValueError('SOURCE_ACQUISITION_METADATA')
        period=(receipt.get('provider'),receipt.get('station_id'),receipt.get('source_type'),
                *(receipt[p] for p in period_fields))
        if period in seen_periods:raise ValueError('DUPLICATE_SOURCE_PERIOD')
        seen_periods.add(period)
        filename=receipt['raw_file']
        if type(filename) is not str or Path(filename).name!=filename or '\\' in filename:
            raise ValueError('INVALID_SOURCE_FILENAME')
        raw_path=local_path(evidence_dir,'incoming/'+filename)
        raw=read_bounded(raw_path,2*1024*1024)
        source_refs.append(dict(receipt=file.name,receipt_sha256=hashlib.sha256(receipt_raw).hexdigest(),
            raw_file=filename,sha256=hashlib.sha256(raw).hexdigest(),size_bytes=len(raw)))
        stamp=datetime.now(timezone.utc).isoformat()
        provider_receipt={key:receipt[key] for key in RECEIPT_FIELDS
                          if key not in ('derived_at','materialized_at','audited_at')}
        provider_receipt.update(derived_at=stamp,materialized_at=stamp,audited_at=stamp)
        if astronomical:
            normalized=normalize_naoj_moon_age(raw,receipt['period_start'],receipt['period_end'],provider_receipt)
            moon.extend(normalized['observations'])
            if len({row['valid_start'] for row in moon})!=len(moon):raise ValueError('DUPLICATE_LUNAR_SAMPLE')
        elif receipt['source_type']=='STATION_OBSERVATION':
            normalized=normalize_jma_hourly(raw,day=receipt['day'],receipt=provider_receipt)
            weather.extend(normalized['observations']);days.append(receipt['day'])
        elif receipt['provider']=='JCG':
            normalized=normalize_jcg_predictions(raw,day=receipt['day'],receipt=provider_receipt)
            normalized['licence_status']='TERMS_NOT_VERIFIED'
            tides.append(dict(station=receipt['station_id'],source_type=receipt['source_type'],
                rows=len(normalized['observations']),numeric=sum(
                r['values']['tide_height_cm']['value'] is not None for r in normalized['observations'])))
        else:
            normalizer=(normalize_jma_finalized_tide_observations
                        if receipt['source_type']=='OBSERVED_FINALIZED'
                        else normalize_jma_tide_observations)
            normalized=normalizer(raw,month=receipt['month'],receipt=provider_receipt)
            tides.append(dict(station=receipt['station_id'],source_type=receipt['source_type'],
                rows=len(normalized['observations']),numeric=sum(
                r['values']['tide_height_cm']['value'] is not None for r in normalized['observations'])))
        if receipt['source_type']=='STATION_OBSERVATION':
            for row in normalized['observations']:
                for key,value in row['values'].items():
                    values[key]+=value['value'] is not None
                    missing[key]+=value['value'] is None
        # Pure normalizer validation is not physical derived-file availability.
        # Retain the actual acquisition receipt and bind post-write times in a
        # separate content-addressed receipt instead of predicting a write time.
        derived_at=datetime.now(timezone.utc).isoformat()
        normalized.update(schema_version='historical-environment-derived-v1',
            source=receipt,usable_at=None,readiness_status='REQUIRES_POST_WRITE_RECEIPT')
        output_path=output_dir/(file.stem+'.normalized.json')
        output=_write_new(output_path,normalized,
                          limit=MAX_NORMALIZED_BYTES-produced)
        with output_path.open('rb') as stream:readback=stream.read(output['size_bytes']+1)
        if (len(readback)!=output['size_bytes'] or hashlib.sha256(readback).hexdigest()!=output['sha256']):
            raise ValueError('DERIVED_READBACK_MISMATCH')
        materialized_at=datetime.now(timezone.utc).isoformat()
        audited_at=datetime.now(timezone.utc).isoformat()
        usable_at=max(map(lambda v:datetime.fromisoformat(v.replace('Z','+00:00')),
            (receipt['source_received_at'],derived_at,materialized_at,audited_at))).isoformat()
        derived_receipt=dict(schema_version='historical-environment-derived-readiness-v1',
            artifact=output,raw_source_sha256=source_refs[-1]['sha256'],
            source_receipt_sha256=source_refs[-1]['receipt_sha256'],
            source_received_at=receipt['source_received_at'],derived_at=derived_at,
            materialized_at=materialized_at,audited_at=audited_at,usable_at=usable_at,
            code_sha256=digest(code),scope='CONSISTENCY_NOT_SCIENTIFIC_OR_PRODUCTION_AUTHORITY')
        produced+=output['size_bytes']
        sealed=_write_new(output_dir/(file.stem+'.readiness.json'),derived_receipt,
                          limit=MAX_NORMALIZED_BYTES-produced)
        produced+=sealed['size_bytes'];outputs.append(dict(output,readiness_receipt=sealed))
        if receipt['source_type']=='STATION_OBSERVATION' or astronomical:readiness.append(usable_at)
        if read_bounded(raw_path,2*1024*1024)!=raw or read_bounded(file,65536)!=receipt_raw:
            raise ValueError('SOURCE_CHANGED_DURING_NORMALIZATION')
    weather,endings=_weather_index(weather)
    start=datetime.fromisoformat(operational_night+'T07:00:00+09:00')
    lag_rows=[]
    for offset in range(24):
        stamp=(start+timedelta(hours=offset)).isoformat()
        scope=_prior_window(weather,endings,start+timedelta(hours=offset))
        lag_rows.append(dict(window_start=stamp,antecedent_rainfall=antecedent_rainfall(
            scope,window_start=stamp),rain_memory_proxy=rain_memory_proxy(scope,window_start=stamp)))
    training=audit_training_source(**training_options)
    candidate_join=dict(status='MISSING_PRIVATE_CANDIDATE',labels_created=0)
    if candidate_csv is not None:
        if not candidate_sha256:raise ValueError('Candidate source digest required')
        candidate_join=join_private_candidates(candidate_csv,candidate_sha256,weather,
            output_dir/'historical_candidate_env_PRIVATE.csv',
            source_usable_at=max(readiness,key=lambda v:datetime.fromisoformat(v).timestamp()),
            astronomy_observations=moon)
    for ref in source_refs:
        if (hashlib.sha256(read_bounded(local_path(evidence_dir,'incoming/'+ref['raw_file']),2*1024*1024)).hexdigest()!=ref['sha256'] or
            hashlib.sha256(read_bounded(local_path(evidence_dir,'receipts/'+ref['receipt']),65536)).hexdigest()!=ref['receipt_sha256']):
            raise ValueError('SOURCE_CHANGED_AFTER_DERIVATION')
    if any(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=value for p,value in code.items()):
        raise ValueError('CODE_CHANGED_DURING_DERIVATION')
    # Completion binds the bytes still present after all dependent work, not
    # merely the bytes that were written/read back earlier in the run.
    final_outputs=[ref for output in outputs for ref in (output,output['readiness_receipt'])]
    if candidate_csv is not None:
        private_source=Path(candidate_csv)
        with local_path(private_source.parent,private_source.name).open('rb') as stream:
            retained=stream.read(16*1024*1024+1)
        if len(retained)>16*1024*1024 or hashlib.sha256(retained).hexdigest()!=candidate_sha256:
            raise ValueError('PRIVATE_SOURCE_CHANGED_BEFORE_COMPLETION')
        final_outputs.append(dict(path=candidate_join['path'],size_bytes=candidate_join['size_bytes'],
                                  sha256=candidate_join['derived_sha256']))
    for ref in final_outputs:
        with local_path(output_dir,ref['path']).open('rb') as stream:
            retained=stream.read(ref['size_bytes']+1)
        if len(retained)!=ref['size_bytes'] or hashlib.sha256(retained).hexdigest()!=ref['sha256']:
            raise ValueError('DERIVED_CHANGED_BEFORE_COMPLETION')
    target_start,target_end=date(2025,1,1),date(2026,11,1)
    expected={ (target_start+timedelta(days=i)).isoformat()
               for i in range((target_end-target_start).days+1)}
    covered=expected.intersection(days)
    report=dict(schema_version='historical-environment-backfill-v1',status='PARTIAL_BLOCKED',
        source_integrity_status='VERIFIED_BYTES_AND_PROVIDER_LAYOUT',
        requested_period=dict(start='2025-01-01',end='2026-11-01',expected_days=len(expected),
            covered_days=len(covered),missing_days=sorted(expected-set(days))),
        weather=dict(station_id='88901',source_days=len(days),hourly_rows=len(weather),
            known_values=dict(values),unknown_values=dict(missing),
            geographic_support='REFERENCE_STATION_ONLY',ten_minute_road_values_produced=False),
        tide_sources=tides,astronomy=dict(station_id='46525',daily_noon_points=len(moon),
            known_moon_age_days=sum(row['values']['moon_age_days']['value'] is not None for row in moon),
            unknown_moon_age_days=sum(row['values']['moon_age_days']['value'] is None for row in moon),
            kind='ASTRONOMICAL_CALCULATION_RETRIEVED_RETROSPECTIVELY',
            moonlight_measured=False,illumination_fraction_status='NOT_PRODUCED',
            geographic_support='REFERENCE_LOCATION_CALCULATION_ONLY'),
        rainfall_and_memory=lag_rows,training=training,candidate_join=candidate_join,
        evaluation=dict(status='NOT_VALIDATED',independent_confirmation='NOT_PERFORMED',
            historical_walkforward='BLOCKED_NEWLY_RETRIEVED_SOURCE_NOT_HISTORICALLY_READY',
            stage1_top10_recall=None,formal_100m_10min=None,improvement='NOT_EVALUATED'),
        unproduced=['ROAD_LEVEL_MICROCLIMATE','MEASURED_SURFACE_WETNESS','TERRAIN_SHELTER_JOIN',
                    'MEASURED_ROAD_MOONLIGHT','AUTHORIZED_PRODUCTION_P0'],
        observations_are_not_forecasts=True,qualified_negative_generated=0,
        official_e2e_complete=False,production_authorized=False,source_refs=source_refs,
        derived_refs=outputs,code_sha256=digest(code),code_files=code,
        source_bytes_consumed=consumed,normalized_bytes=produced)
    _write_new(output_dir/'report_PRIVATE.json',report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--night',default='2026-11-01')
    parser.add_argument('--training-corpus-root',type=Path)
    parser.add_argument('--training-corpus')
    parser.add_argument('--training-corpus-sha256')
    parser.add_argument('--heldout-night')
    parser.add_argument('--fit-cutoff')
    parser.add_argument('--feature',action='append',default=[])
    parser.add_argument('--run-fit',action='store_true',help='Existing source gates still apply')
    parser.add_argument('--candidate-csv',type=Path)
    parser.add_argument('--candidate-sha256')
    args=parser.parse_args()
    try:
        report=process_evidence(args.evidence_dir,args.output_dir,operational_night=args.night,
            candidate_csv=args.candidate_csv,candidate_sha256=args.candidate_sha256,
            corpus_root=args.training_corpus_root,corpus_path=args.training_corpus,
            corpus_sha256=args.training_corpus_sha256,heldout_night=args.heldout_night,
            fit_cutoff=args.fit_cutoff,feature_names=tuple(args.feature),run_fit=args.run_fit)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        # Source text, paths and coordinates never enter a public console error.
        reason=str(exc)
        if not re.fullmatch(r'[A-Z][A-Z0-9_]{1,100}',reason):reason='SOURCE_VALIDATION_FAILED'
        print(json.dumps(dict(status='BLOCKED',reason_code=reason,error_type=type(exc).__name__,
            completion_report_validated=False,official_e2e_complete=False,production_authorized=False)))
        return 2
    print(json.dumps({key:report[key] for key in ('status','source_integrity_status','requested_period',
        'weather','tide_sources','astronomy','evaluation','code_sha256','official_e2e_complete')},ensure_ascii=False,indent=2))
    return 2


if __name__=='__main__':raise SystemExit(main())
