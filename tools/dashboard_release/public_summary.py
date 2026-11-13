"""Allowlisted public projection. Never pass private notes, event rows or source paths."""
from __future__ import annotations
from collections import Counter
from datetime import date
import json
import re

SCHEMA = 'habu-public-aggregate-v1'
ROOT_FIELDS = {'schema_version','asof','year','capture_total','owner_reported_total',
    'total_difference','capture_total_status','effort_nights','non_search_days',
    'months','models','official_model_status','publication_scope'}
MONTH_FIELDS = {'month','captures','cumulative','effort_nights','positive_nights','zero_nights'}
MODEL_FIELDS = {'kind','status','nights','events','individuals'}
KINDS = ('night_count','capture_clock','spatial_positive','all_owner_nights')
EFFORT = {'CAPTURE_CONFIRMED_NIGHT','OWNER_CONFIRMED_ZERO','EXCLUDED_NOT_SEARCH',
          'OWNER_AMENDED_CAPTURE','OWNER_AMENDED_ZERO','OWNER_AMENDED_NOT_SEARCH','UNVERIFIED_EFFORT'}


def integer(value, *, optional=False, signed=False):
    if optional and value is None:
        return None
    low = -10_000_000 if signed else 0
    if type(value) is not int or not low <= value <= 10_000_000:
        raise ValueError('INVALID_AGGREGATE_INTEGER')
    return value


def day(value):
    if not isinstance(value,str) or not re.fullmatch(r'20\d\d-\d\d-\d\d',value):
        raise ValueError('INVALID_DATE')
    date.fromisoformat(value)
    return value


def month(value):
    if not isinstance(value,str) or not re.fullmatch(r'20\d\d-\d\d',value):
        raise ValueError('INVALID_MONTH')
    day(value+'-01')
    return value


def project_public_summary(private: dict) -> dict:
    if not isinstance(private,dict) or private.get('schema_version')!='habu-capture-dashboard-v2':
        raise ValueError('PRIVATE_SUMMARY_SCHEMA')
    asof=day(private.get('asof')); year=integer(private.get('year',int(asof[:4])))
    if year!=int(asof[:4]):raise ValueError('YEAR_MISMATCH')
    rows=private.get('nights'); months=private.get('months')
    if not isinstance(rows,list) or len(rows)>366 or not isinstance(months,list) or not 1<=len(months)<=12:
        raise ValueError('PRIVATE_SUMMARY_SIZE')
    counts=Counter();active=Counter();positive=Counter();seen=set();non_search=0
    for row in rows:
        if not isinstance(row,dict):raise ValueError('INVALID_NIGHT')
        d=day(row.get('night'));m=month(row.get('month'));n=integer(row.get('count'))
        flag=row.get('effort_confirmed');status=row.get('effort_status')
        if d in seen or m!=d[:7] or int(d[:4])!=year or d>asof:
            raise ValueError('DUPLICATE_OR_MISMATCHED_NIGHT')
        if type(flag) is not bool or status not in EFFORT or (not flag and n>0):
            raise ValueError('INVALID_SEARCH_CLASSIFICATION')
        if flag and status in ('EXCLUDED_NOT_SEARCH','OWNER_AMENDED_NOT_SEARCH','UNVERIFIED_EFFORT'):
            raise ValueError('INVALID_SEARCH_CLASSIFICATION')
        if not flag and status not in ('EXCLUDED_NOT_SEARCH','OWNER_AMENDED_NOT_SEARCH','UNVERIFIED_EFFORT'):
            raise ValueError('INVALID_SEARCH_CLASSIFICATION')
        seen.add(d);counts[m]+=n
        if flag:active[m]+=1;positive[m]+=int(n>0)
        else:non_search+=1
    undated=private.get('undated_captures',[])
    if not isinstance(undated,list) or len(undated)>12:raise ValueError('UNDATED_SCHEMA')
    for row in undated:
        if not isinstance(row,dict) or row.get('review_status')!='MONTH_TOTAL_ONLY_UNDATED_PENDING_SOURCE_RECONCILIATION':
            raise ValueError('UNDATED_SCHEMA')
        counts[month(row.get('month'))]+=integer(row.get('count'))
    public_months=[];total=0;seen_months=set()
    for row in months:
        if not isinstance(row,dict):raise ValueError('MONTH_SCHEMA')
        m=month(row.get('key'));n=integer(row.get('n'))
        if m in seen_months or int(m[:4])!=year or m>asof[:7] or n!=counts[m]:
            raise ValueError('MONTH_TOTAL_MISMATCH')
        seen_months.add(m);total+=n
        if integer(row.get('cum'))!=total:raise ValueError('CUMULATIVE_MISMATCH')
        public_months.append({'month':m,'captures':n,'cumulative':total,'effort_nights':active[m],
                             'positive_nights':positive[m],'zero_nights':active[m]-positive[m]})
    if [m['month'] for m in public_months]!=sorted(seen_months) or set(counts)-seen_months:
        raise ValueError('MONTH_ORDER_OR_COVERAGE')
    if integer(private.get('total'))!=total:raise ValueError('TOTAL_MISMATCH')
    recon=private.get('private_tally_reconciliation')
    if not isinstance(recon,dict):raise ValueError('MISSING_OWNER_RECONCILIATION')
    claim=integer(recon.get('owner_reported_total_reference'))
    if integer(recon.get('log_derived_total'))!=total or integer(recon.get('difference_log_minus_reported'),signed=True)!=total-claim:
        raise ValueError('RECONCILIATION_MISMATCH')
    rm=private.get('research_models')
    if not isinstance(rm,dict) or rm.get('official_100m_10min_status')!='BLOCKED':
        raise ValueError('UNAPPROVED_MODEL_AUTHORITY')
    models=[]
    for kind,source,fields in (
        ('night_count','night_count',('training_nights',None,'owner_captures')),
        ('capture_clock','recorded_capture_clock',(None,'event_records',None)),
        ('spatial_positive','positive_spatial',(None,'positive_events','individual_units')),
        ('all_owner_nights','all_owner_search_night_research',('search_nights',None,'captures'))):
        item=rm.get(source,{})
        if not isinstance(item,dict) or (item and item.get('mode')!='REFERENCE_ONLY' and not
            (kind=='all_owner_nights' and item.get('status')=='RESEARCH_ONLY_UNRECONCILED_269_VS_270')):
            raise ValueError('MODEL_NOT_REFERENCE_ONLY')
        values=[integer(item.get(f),optional=True) if f else None for f in fields]
        models.append(dict(zip(('kind','status','nights','events','individuals'),
                               (kind,'RESEARCH_ONLY',*values))))
    result={'schema_version':SCHEMA,'asof':asof,'year':year,'capture_total':total,
        'owner_reported_total':claim,'total_difference':total-claim,
        'capture_total_status':'UNRECONCILED' if total!=claim else 'CONSISTENT',
        'effort_nights':sum(active.values()),'non_search_days':non_search,
        'months':public_months,'models':models,'official_model_status':'BLOCKED',
        'publication_scope':'MONTHLY_AGGREGATES_ONLY_NO_INDIVIDUAL_RECORDS'}
    return validate_public_summary(result)


def validate_public_summary(value: dict) -> dict:
    if not isinstance(value,dict) or set(value)!=ROOT_FIELDS or value.get('schema_version')!=SCHEMA:
        raise ValueError('PUBLIC_FIELD_ALLOWLIST')
    asof=day(value['asof']);year=integer(value['year'])
    if int(asof[:4])!=year:raise ValueError('PUBLIC_YEAR')
    total=integer(value['capture_total']);claim=integer(value['owner_reported_total'])
    if integer(value['total_difference'],signed=True)!=total-claim:raise ValueError('PUBLIC_DISCREPANCY')
    if value['capture_total_status']!=('UNRECONCILED' if total!=claim else 'CONSISTENT'):
        raise ValueError('PUBLIC_COUNT_STATUS')
    if (value['official_model_status']!='BLOCKED' or
        value['publication_scope']!='MONTHLY_AGGREGATES_ONLY_NO_INDIVIDUAL_RECORDS'):
        raise ValueError('PUBLIC_AUTHORITY_OR_SCOPE')
    integer(value['non_search_days']);effort=integer(value['effort_nights'])
    if not isinstance(value['months'],list) or not 1<=len(value['months'])<=12:raise ValueError('PUBLIC_MONTHS')
    acc=0;nights=0;previous=''
    for m in value['months']:
        if not isinstance(m,dict) or set(m)!=MONTH_FIELDS:raise ValueError('PUBLIC_MONTH_FIELD_ALLOWLIST')
        key=month(m['month'])
        if key<=previous or int(key[:4])!=year or key>asof[:7]:raise ValueError('PUBLIC_MONTH_ORDER')
        previous=key;acc+=integer(m['captures']);nights+=integer(m['effort_nights'])
        if integer(m['cumulative'])!=acc or integer(m['positive_nights'])+integer(m['zero_nights'])!=m['effort_nights']:
            raise ValueError('PUBLIC_MONTH_TOTAL')
        if m['positive_nights']>m['captures']:raise ValueError('PUBLIC_POSITIVE_NIGHTS')
    if acc!=total or nights!=effort:raise ValueError('PUBLIC_TOTAL')
    if not isinstance(value['models'],list) or len(value['models'])!=len(KINDS):raise ValueError('PUBLIC_MODELS')
    for kind,m in zip(KINDS,value['models']):
        if not isinstance(m,dict) or set(m)!=MODEL_FIELDS or m['kind']!=kind or m['status']!='RESEARCH_ONLY':
            raise ValueError('PUBLIC_MODEL_FIELD_ALLOWLIST')
        for field in ('nights','events','individuals'):integer(m[field],optional=True)
    # Return a new object, so a caller cannot append private fields by alias.
    return json.loads(json.dumps(value,ensure_ascii=False,allow_nan=False))
