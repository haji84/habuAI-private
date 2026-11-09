#!/usr/bin/env python3
"""Apply a private owner-night overlay to a HUB NATURAL v2 dashboard export.

This utility intentionally DOES NOT publish its output. Run against an already
built, local/private capture_summary.json. Never commit private overlay/output
or release it as an unprotected GitHub Pages artifact.
"""
from __future__ import annotations
import argparse
import copy
import datetime as dt
import json
import re
from collections import defaultdict
from pathlib import Path

SCHEMA = 'habu-private-dashboard-owner-overlay-v1'
ALLOWED_SOURCE = 'OWNER_LOG_AND_GPX_PRIVATE_REVIEW'
INFORMATION_LEAK_KEYS = ('lat', 'lon', 'lng', 'longitude', 'latitude', 'coords', 'coordinate', 'address', 'location', 'gps_points', 'track', 'raw_log')


def _check_no_private_coordinates(item, prefix=''):
    if isinstance(item, dict):
        for key, value in item.items():
            low = str(key).lower()
            if any(bad == low or low.endswith('_'+bad) for bad in INFORMATION_LEAK_KEYS):
                raise ValueError('Private/coordinate-bearing overlay field rejected: '+prefix+str(key))
            _check_no_private_coordinates(value, prefix+str(key)+'.')
    elif isinstance(item, list):
        for value in item:
            _check_no_private_coordinates(value, prefix)


def _date(s):
    if not isinstance(s, str) or not re.fullmatch(r'2026-\d{2}-\d{2}', s):
        raise ValueError('Invalid 2026 operational night')
    dt.date.fromisoformat(s)
    return s


def _calculate_effort(data):
    rows = []
    for m in data['months']:
        active = [n for n in data['nights'] if n['month']==m['key'] and n['effort_confirmed']]
        count=len(active)
        pos=sum(n['count']>0 for n in active)
        rows.append(dict(key=m['key'],captures=m['n'],nights=count,positive_nights=pos,
            zero_nights=count-pos,
            per_night_average=round(m['n']/count,4) if count else None,
            capture_success_rate=round(pos/count,4) if count else None))
    total_nights=sum(x['nights'] for x in rows)
    positive=sum(x['positive_nights'] for x in rows)
    return rows, dict(total_nights=total_nights,positive_nights=positive,
        zero_nights=total_nights-positive,
        per_night_average=round(data['total']/total_nights,4) if total_nights else None,
        capture_success_rate=round(positive/total_nights,4) if total_nights else None,
        classification='OWNER_CONFIRMED_PERSONAL_EFFORT', not_model_exposure=True,
        not_negative_training_labels=True)


def apply_overlay(base, overlay):
    if base.get('schema_version')!='habu-capture-dashboard-v2' or not isinstance(base.get('nights'),list):
        raise ValueError('Not the existing dashboard v2 capture summary')
    if overlay.get('schema_version') != SCHEMA or overlay.get('source') != ALLOWED_SOURCE or overlay.get('private_only') is not True:
        raise ValueError('Private owner overlay source contract mismatch')
    if set(overlay)-{'schema_version','source','private_only','nights','expected_monthly','owner_claimed_total','research_models','notes','status'}:
        raise ValueError('Unexpected owner overlay fields')
    if not isinstance(overlay.get('nights'), list) or len(overlay['nights'])>366:
        raise ValueError('Missing or unreasonable overlay nights')
    _check_no_private_coordinates(overlay)
    output=copy.deepcopy(base)
    by_date={n['night']:n for n in output['nights']}
    last_base=base.get('asof','')
    duplicate=set()
    delta=defaultdict(int)
    added=0
    for n in overlay['nights']:
        if set(n)-{'night','capture_count','session_kind','gpx_time_place_crosscheck','note'}:
            raise ValueError('Unexpected fields in night')
        date=_date(n.get('night'))
        if date in duplicate: raise ValueError('Duplicate night in overlay')
        duplicate.add(date)
        count=n.get('capture_count')
        if type(count)!=int or count<0 or count>100:raise ValueError('Invalid personal capture count')
        kind=n.get('session_kind')
        if kind not in ('SEARCH','RESEARCH_NON_SEARCH'):
            raise ValueError('Invalid search session kind')
        if kind=='RESEARCH_NON_SEARCH' and count:
            raise ValueError('Non-search day cannot contribute owner captures')
        if n.get('gpx_time_place_crosscheck') not in (True,False):
            raise ValueError('GPX source-check flag must be boolean')
        note=n.get('note','')
        if not isinstance(note,str) or len(note)>150 or '\n' in note:
            raise ValueError('Night note invalid')
        if date in by_date:
            prev=by_date[date]
            if prev['count']!=count or prev['effort_confirmed']!=(kind=='SEARCH'):
                raise ValueError('Existing captured night conflicts; do not overwrite frozen source')
            continue
        if date<=last_base:
            raise ValueError('New night overlaps the existing dashboard cutoff')
        effort=kind=='SEARCH'
        status='CAPTURE_CONFIRMED_NIGHT' if count>0 else ('OWNER_CONFIRMED_ZERO' if effort else 'EXCLUDED_NOT_SEARCH')
        record={
           'night':date,'month':date[:7],'count':count,'start':'不明','end':'不明',
           'events':count if count else None,'sighting':None,'roadkill':None,'other_capture':None,
           'status':'本人ハブログ・GPX照合済み（研究用）' if n['gpx_time_place_crosscheck'] else '本人申告・調査記録',
           'note':note or '捕獲数とGPXの時空間整合性確認。正式100m学習の独立証明ではない。',
           'effort_confirmed':effort,'effort_status':status,
           'pdca_status':'REFERENCE_ONLY_NOT_OFFICIAL_P0' if effort else 'NOT_SCORED_NON_SEARCH'
        }
        by_date[date]=record
        delta[date[:7]]+=count
        added+=1
    expected=overlay.get('expected_monthly')
    if not isinstance(expected,dict) or any(not re.fullmatch('2026-\\d{2}',m) or type(n)!=int or n<0 for m,n in expected.items()):
        raise ValueError('Invalid expected-month mapping')
    if dict(delta)!= {m:v for m,v in expected.items() if v}:
        raise ValueError('Owner monthly count fails independent overlay count check')
    months={m['key']:m['n'] for m in base['months']}
    for month,num in delta.items():months[month]=months.get(month,0)+num
    cumulative=0
    output['months']=[]
    for month,num in sorted(months.items()):
        cumulative+=num
        output['months'].append({'key':month,'n':num,'cum':cumulative})
    output['total']=cumulative
    output['asof']=max(by_date)
    output['nights']=sorted(by_date.values(),key=lambda x:x['night'])
    for month,num in months.items():
        if sum(x['count'] for x in output['nights'] if x['month']==month)!=num:
            raise ValueError('Historical month integrity violation: '+month)
    output['effort_months'],output['effort']=_calculate_effort(output)
    claim=overlay.get('owner_claimed_total')
    if type(claim)!=int or claim<0:raise ValueError('Owner-reported count missing')
    models=overlay.get('research_models')
    if not isinstance(models,dict) or models.get('official_100m_10min_status')!='BLOCKED':
        raise ValueError('Model authority not verified for reference overlay')
    output['new_confirmed_nights']=base.get('new_confirmed_nights',0)+sum(v['effort_confirmed'] for v in by_date.values() if v['night']>last_base)
    output['research_models']=models
    output['private_tally_reconciliation']={'log_derived_total':cumulative,'owner_reported_total_reference':claim,
        'difference_log_minus_reported':cumulative-claim,
        'status':'PENDING_EVENT_LEVEL_RECONCILIATION',
        'note':'本人申告の基準日時が不明。265+等と補正せず両方を別に保持。'}
    output['review_status']='PERSONAL_CAPTURE_AGGREGATE_UNRECONCILED_OFFICIAL_G0_BLOCKED'
    output['warnings']=list(base.get('warnings',[]))+['11月分は非公開Libraryの本人ログ・GPXに基づく参考集計。公開リポジトリへアップロードしない。',
      '本人申告と日別集計に差異がある。解消まで年間捕獲数は暫定。研究学習と正式100m予測モデルは区別。']
    output['privacy']='PRIVATE_RESEARCH_DASHBOARD_NO_COORDINATES'
    output['source']='Existing 2026-10-30 aggregate snapshot + owner-logged private Nov reviewed nights'
    output['generated_at_utc']=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True)
    p.add_argument('--overlay',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.resolve()==args.base.resolve():raise ValueError('Refusing to overwrite source dashboard')
    d=apply_overlay(json.loads(args.base.read_text(encoding='utf-8')),json.loads(args.overlay.read_text(encoding='utf-8')))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PRIVATE DASHBOARD READY',d['asof'],d['total'],d['private_tally_reconciliation'])

if __name__=='__main__':main()