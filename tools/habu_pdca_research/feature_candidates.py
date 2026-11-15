"""Research-only diagnostics for search duration, area ranks and weather gaps.

Does not issue P0, invent zero observations, learn a hazard model, or inspect GPS.
Only receives caller-supplied records. The caller is responsible for keeping
individual records and local readings in a private execution environment.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from collections import defaultdict
import math


def _dt(s):
    result = datetime.fromisoformat(s)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('OFFSET_AWARE_REQUIRED')
    if result.utcoffset() != timedelta(hours=9):
        raise ValueError('JST_OFFSET_REQUIRED')
    return result


def _real(v, allow_zero=True):
    if type(v) not in (int, float) or not math.isfinite(v) or v < 0 or (not allow_zero and v == 0):
        raise ValueError('FINITE_NONNEGATIVE_VALUE_REQUIRED')
    return float(v)


def duration_candidate(rate_per_elapsed_hour, train_through_night, records, *, base_hours=5):
    """Compare frozen pre-heldout rate vs a predeclared planned-duration feature.

    Session elapsed hours are only a PROXY, not measured active-search effort.
    This returns an out-of-sample research counterfactual, not the frozen user
    forecast and not a retrospectively length-corrected official score.
    """
    rate = _real(rate_per_elapsed_hour, allow_zero=False)
    base_hours = _real(base_hours, allow_zero=False)
    rows = []
    for rec in records:
        night = rec['night']
        if night <= train_through_night:
            raise ValueError('TRAIN_TEST_TIME_LEAK')
        if rec.get('source_category') not in ('REFERENCE_BEFORE_SEARCH', 'REFERENCE_DURING_SEARCH_BEFORE_FIRST_CAPTURE'):
            raise ValueError('UNSUPPORTED_PREDICTION_PHASE')
        plan = _real(rec['planned_hours'], allow_zero=False)
        observed = rec['actual_captures']
        if type(observed) is not int or not 0 <= observed <= 100:
            raise ValueError('INVALID_COUNT')
        issued = _dt(rec['issued_at']); first_capture = _dt(rec['first_capture_at'])
        if issued >= first_capture:
            raise ValueError('FORECAST_AFTER_FIRST_CAPTURE')
        baseline = rate * base_hours
        candidate = rate * plan
        rows.append(dict(night=night, phase=rec['source_category'], planned_hours=plan,
                         actual_count=observed, baseline_lambda=round(baseline, 6),
                         plan_conditional_lambda=round(candidate, 6),
                         baseline_absolute_error=abs(baseline-observed),
                         candidate_absolute_error=abs(candidate-observed),
                         baseline_poisson_log_score=observed*math.log(baseline)-baseline-math.lgamma(observed+1),
                         candidate_poisson_log_score=observed*math.log(candidate)-candidate-math.lgamma(observed+1)))
    if not rows:
        raise ValueError('NO_HOLDOUT_ROWS')
    mean = lambda key: round(sum(x[key] for x in rows)/len(rows), 4)
    return dict(status='RESEARCH_EXANTE_INPUT_CONDITION_ONLY_NO_OFFICIAL_MODEL',
                training_through=train_through_night,
                baseline_hours=base_hours,rate_elapsed_session_proxy=rate,
                holdout_nights=len(rows),
                pre_search_reference_nights=sum(x['phase']=='REFERENCE_BEFORE_SEARCH' for x in rows),
                post_search_pre_capture_reference_nights=sum(x['phase']!='REFERENCE_BEFORE_SEARCH' for x in rows),
                baseline_mae=mean('baseline_absolute_error'),
                planned_hours_mae=mean('candidate_absolute_error'),
                baseline_mean_poisson_log_score=mean('baseline_poisson_log_score'),
                planned_hours_mean_poisson_log_score=mean('candidate_poisson_log_score'),
                rows=rows,active_search_hours_qualified=False,
                retrospective_actual_elapsed_never_used_as_predictor=True,
                independent_future_nights_proven=False,official_model_eligible=False)


def region_candidate_area_match(rows):
    """Only compare post-outcome settlement-name hits, never call it route recall."""
    result=[]; totals=defaultdict(int)
    for rec in rows:
        d=rec['area_diagnostic']
        known=d['known_settlement_capture_count']
        unknown=d['unknown_or_generic_area_capture_count']
        if (type(known) is not int or type(unknown) is not int or min(known,unknown)<0
                or known+unknown!=rec['actual_captures']):
            raise ValueError('AREA_DENOMINATOR_CONFLICT')
        a=d['primary_A_name_matches']; b=d['alternate_name_matches']['B']; c=d['alternate_name_matches']['C']
        if any(type(v) is not int or not 0<=v<=known for v in (a,b,c)):
            raise ValueError('AREA_OVERCOUNT')
        for label,val in [('A',a),('B',b),('C',c)]:totals[label]+=val
        totals['known']+=known;totals['unknown']+=unknown
        result.append(dict(night=rec['night'],settlement_named_captures=known,
                           unnamed_or_generic_capture_records=unknown,A_name_hits=a,B_name_hits=b,C_name_hits=c))
    return dict(status='DIAGNOSTIC_ONLY_NO_COVERAGE_OR_REGION_RECALL',
                known_settlement_captures=totals['known'],unassigned_or_generic_captures=totals['unknown'],
                primary_A_named_hits=totals['A'],alternate_B_named_hits=totals['B'],alternate_C_named_hits=totals['C'],
                region_ranked_exposure_denominators=None,unsearched_areas_are_not_negative=True,
                area_top10_recall=None,official_model_eligible=False,rows=result)


def field_station_temperature_candidate(station_hour_rows, field_readings):
    """Posthoc station-vs-hand-recorded local temperature calibration probe.

    Leave one *night* forward with offset learned only from earlier field nights.
    Uses historical JMA observations after the fact; not P0 available-at proof.
    """
    stations=[]
    for row in station_hour_rows:
        if row.get('station_id')!='88901' or row.get('support_kind')!='HOURLY_REFERENCE_STATION':
            raise ValueError('UNTRUSTED_REFERENCE_STATION')
        v=row.get('values',{}).get('temperature_c',{})
        if v.get('kind')!='OBSERVED' or v.get('quality')!='NORMAL':
            continue
        temp=v.get('value')
        if type(temp) not in (int,float) or not math.isfinite(temp):continue
        stations.append((_dt(row['valid_end']), float(temp)))
    stations.sort()
    if not stations:raise ValueError('NO_VERIFIED_STATION_DATA')
    lasttime=None; records=[]
    for obs in sorted(field_readings,key=lambda x:x['observed_at']):
        time=_dt(obs['observed_at'])
        if lasttime is not None and time==lasttime:raise ValueError('DUPLICATE_FIELD_TEMPERATURE_RECORD')
        lasttime=time
        local=float(obs['temperature_c'])
        if not math.isfinite(local) or not -30<=local<=55:raise ValueError('INVALID_FIELD_TEMPERATURE')
        if obs['night']!=time.date().isoformat() and not (time.hour < 7 and (time.date().toordinal()-datetime.fromisoformat(obs['night']).date().toordinal())==1):
            raise ValueError('OPERATIONAL_NIGHT_MISMATCH')
        found=[(dt, temp) for dt,temp in stations if dt<=time and 0<=(time-dt).total_seconds()<=3600]
        if not found:
            records.append(dict(night=obs['night'],pair_status='MISSING_PRECEDING_STATION_HOUR'))
            continue
        end,temp=max(found)
        records.append(dict(night=obs['night'],paired_at=obs['observed_at'],
                            station_at=end.isoformat(),station_age_min=round((time-end).total_seconds()/60,2),
                            field_c=local,station_c=temp,field_minus_station_c=round(local-temp,3),
                            pair_status='POSTHOC_STATION_FIELD_COMPARISON_ONLY'))
    grouped=defaultdict(list)
    for r in records:
        if 'field_minus_station_c' in r:
            grouped[r['night']].append(r)
    offsets=[]; evaluation=[]
    for night in sorted(grouped):
        prior=[r['field_minus_station_c'] for n in sorted(grouped) if n<night for r in grouped[n]]
        offset=sum(prior)/len(prior) if prior else None
        offsets.append(dict(night=night,trained_on_prior_nights=len([n for n in grouped if n<night]),
                            offset_from_prior_nights_c=None if offset is None else round(offset,3)))
        for r in grouped[night]:
            if offset is None:continue
            evaluation.append(dict(night=night,station_only_abs_err_c=abs(r['field_minus_station_c']),
                                   prior_night_offset_abs_err_c=abs(r['field_minus_station_c']-offset)))
    mean=lambda key:round(sum(x[key] for x in evaluation)/len(evaluation),4) if evaluation else None
    return dict(status='RESEARCH_STATION_LOCAL_DIAGNOSTIC_ONLY_NOT_VALIDATED_MICROCLIMATE',
                field_station_pairs=len([r for r in records if r['pair_status'].startswith('POSTHOC')]),
                distinct_field_nights=len(grouped),future_night_calibration_evaluation_nights=len(set(x['night'] for x in evaluation)),
                future_night_calibration_evaluation_points=len(evaluation),
                raw_station_mae_c=mean('station_only_abs_err_c'),
                prior_night_offset_mae_c=mean('prior_night_offset_abs_err_c'),
                trained_offset_history=offsets,point_records=records,
                observations_are_not_calibrated_route_microclimate=True,
                historical_archive_is_not_an_asof_forecast=True,
                historic_field_measurement_receipt_before_test_unverified=True,
                future_prospective_validation_passed=False,
                official_model_eligible=False)
