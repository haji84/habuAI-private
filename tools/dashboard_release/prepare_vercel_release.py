#!/usr/bin/env python3
"""Prepare a fail-closed, static Vercel release from a *public-aggregate-only* archive.

Never accepts encrypted originals, raw observations, model artifacts, or credentials.
Vercel never runs the decryptor: decryption and source qualification finish
inside the protected environment that produced the input three-file bundle.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import zipfile

EXPECTED = {'index.html', 'data/public_summary.json', '_headers'}
MODEL_KEYS = {'kind', 'nights', 'events', 'individuals', 'status'}
MONTH_KEYS = {'month', 'captures', 'cumulative', 'effort_nights', 'positive_nights', 'zero_nights'}
TOP_KEYS = {'asof','capture_total','capture_total_status','effort_nights','models',
            'months','non_search_days','official_model_status','owner_reported_total',
            'publication_scope','schema_version','total_difference','year',
            'owner_confirmation_day_jst','owner_confirmation_scope'}
MAX_FILE_BYTES = 256 * 1024

class ReleaseRejected(ValueError):
    pass

def sha256(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def reject(message:str):
    raise ReleaseRejected(message)

def load_three_file_archive(path:Path)->dict[str,bytes]:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 1024 * 1024:
        reject('ARCHIVE_INVALID')
    with zipfile.ZipFile(path) as archive:
        if set(archive.namelist()) != EXPECTED or len(archive.namelist()) != 3:
            reject('NONPUBLIC_FILE_IN_RELEASE')
        result={}
        for member in archive.infolist():
            if member.is_dir() or member.file_size > MAX_FILE_BYTES or member.flag_bits & 1:
                reject('ARCHIVE_MEMBER_INVALID')
            if member.filename.startswith('/') or '..' in Path(member.filename).parts:
                reject('ARCHIVE_PATH_INVALID')
            # Do not allow symlink members to point outside the bundle.
            if (member.external_attr >> 16) & 0o170000 == 0o120000:
                reject('ARCHIVE_LINK_INVALID')
            value=archive.read(member)
            if len(value) != member.file_size:
                reject('ARCHIVE_MEMBER_MISMATCH')
            result[member.filename] = value
    return result

def validate_counts(body:bytes)->dict:
    try:
        def no_duplicate(pairs):
            out={}
            for k,v in pairs:
                if k in out: reject('DUPLICATE_JSON_KEY')
                out[k]=v
            return out
        j=json.loads(body,object_pairs_hook=no_duplicate)
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:
        raise ReleaseRejected('JSON_FORMAT_INVALID') from exc
    if not isinstance(j,dict) or set(j)!=TOP_KEYS or j['schema_version']!='habu-public-aggregate-v1':
        reject('AGGREGATE_SCHEMA_INVALID')
    if j['publication_scope']!='MONTHLY_AGGREGATES_ONLY_NO_INDIVIDUAL_RECORDS':
        reject('PUBLICATION_SCOPE_INVALID')
    if not isinstance(j['year'],int) or isinstance(j['year'],bool) or j['year'] < 2025 or j['year'] > 2100:
        reject('YEAR_INVALID')
    if not isinstance(j['capture_total'],int) or isinstance(j['capture_total'],bool) or j['capture_total'] < 0:
        reject('CAPTURE_TOTAL_INVALID')
    if not isinstance(j['owner_reported_total'],int) or isinstance(j['owner_reported_total'],bool):
        reject('OWNER_REPORT_INVALID')
    if not isinstance(j['total_difference'],int) or isinstance(j['total_difference'],bool):
        reject('DIFFERENCE_INVALID')
    if j['capture_total']-j['owner_reported_total'] != j['total_difference']:
        reject('OWNER_COUNT_RECONCILIATION_INVALID')
    if j['capture_total_status'] not in ('OWNER_CONFIRMED_RECONCILED','UNRECONCILED'):
        reject('OWNER_CONFIRMATION_STATUS_INVALID')
    if (j['capture_total_status']=='OWNER_CONFIRMED_RECONCILED') != (j['total_difference']==0):
        reject('OWNER_CONFIRMATION_STATUS_MISMATCH')
    if j['official_model_status']!='BLOCKED':
        reject('UNVERIFIED_FORMAL_MODEL_CLAIM')
    for field in ('asof','owner_confirmation_day_jst'):
        if not isinstance(j[field],str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',j[field]):
            reject('DATE_INVALID')
    if j['owner_confirmation_scope']!='ANNUAL_AGGREGATE_ONLY_NOT_INDIVIDUAL_EVIDENCE':
        reject('OWNER_SCOPE_INVALID')
    m=j['months']
    if not isinstance(m,list) or not 1 <= len(m) <= 12:
        reject('MONTHS_INVALID')
    running=0
    for row in m:
        if not isinstance(row,dict) or set(row)!=MONTH_KEYS:
            reject('MONTH_SCHEMA_INVALID')
        if not isinstance(row['month'],str) or not re.fullmatch(r'\d{4}-\d{2}',row['month']):
            reject('MONTH_KEY_INVALID')
        for k in MONTH_KEYS-{'month'}:
            if not isinstance(row[k],int) or isinstance(row[k],bool) or row[k]<0:
                reject('MONTH_VALUE_INVALID')
        running+=row['captures']
        if row['cumulative']!=running or row['positive_nights']+row['zero_nights']!=row['effort_nights']:
            reject('MONTH_RECONCILIATION_INVALID')
    if [z['month'] for z in m]!=sorted(set(z['month'] for z in m)) or running!=j['capture_total']:
        reject('AGGREGATE_RECONCILIATION_INVALID')
    if (not isinstance(j['effort_nights'],int) or isinstance(j['effort_nights'],bool)
        or j['effort_nights']!=sum(row['effort_nights'] for row in m)):
        reject('EFFORT_TOTAL_INVALID')
    if not isinstance(j['non_search_days'],int) or isinstance(j['non_search_days'],bool) or j['non_search_days']<0:
        reject('NON_SEARCH_INVALID')
    mods=j['models']
    if not isinstance(mods,list) or len(mods)!=4:
        reject('MODEL_LIST_INVALID')
    for row in mods:
        if not isinstance(row,dict) or set(row)!=MODEL_KEYS or row['status']!='RESEARCH_ONLY':
            reject('MODEL_SCHEMA_INVALID')
        if row['kind'] not in ('night_count','capture_clock','spatial_positive','all_owner_nights'):
            reject('MODEL_KIND_INVALID')
        for key in ('nights','events','individuals'):
            v=row[key]
            if v is not None and (not isinstance(v,int) or isinstance(v,bool) or v<0):
                reject('MODEL_COUNT_INVALID')
    if len(set(z['kind'] for z in mods))!=4:
        reject('MODEL_KIND_DUPLICATED')
    return j

def vercel_config(files:dict[str,bytes])->dict:
    validate_counts(files['data/public_summary.json'])
    try:
        html=files['index.html'].decode('utf-8')
        headers=files['_headers'].decode('utf-8')
    except UnicodeDecodeError as exc:
        raise ReleaseRejected('NONUTF8_RELEASE') from exc
    embedded=re.findall(r'<script id="public-summary" type="application/json">(.*?)</script>',html,re.S)
    if len(embedded)!=1:
        reject('HTML_JSON_MISMATCH')
    try:
        if json.loads(embedded[0])!=json.loads(files['data/public_summary.json']):
            reject('HTML_JSON_MISMATCH')
    except json.JSONDecodeError as exc:
        raise ReleaseRejected('HTML_JSON_INVALID') from exc
    runtimes=re.findall(r'<script data-runtime>(.*?)</script>',html,re.S)
    styles=re.findall(r'<style>(.*?)</style>',html,re.S)
    if len(runtimes)!=1 or len(styles)!=1 or len(re.findall(r'<script\b',html))!=2:
        reject('RUNTIME_SCRIPT_SHAPE_INVALID')
    sh=base64.b64encode(hashlib.sha256(runtimes[0].encode('utf-8')).digest()).decode('ascii')
    st=base64.b64encode(hashlib.sha256(styles[0].encode('utf-8')).digest()).decode('ascii')
    meta=re.findall(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">',html)
    lines=[l.strip() for l in headers.splitlines() if l.strip()]
    if len(meta)!=1 or not lines or lines[0]!='/*':
        reject('SECURITY_HEADER_FORMAT_INVALID')
    line_map={}
    for line in lines[1:]:
        if ':' not in line: reject('SECURITY_HEADER_FORMAT_INVALID')
        k,v=line.split(':',1)
        if k in line_map: reject('DUPLICATE_SECURITY_HEADER')
        line_map[k]=v.strip()
    needed={'Content-Security-Policy','X-Content-Type-Options','Referrer-Policy','Cache-Control'}
    if set(line_map)!=needed or line_map['X-Content-Type-Options']!='nosniff' or line_map['Referrer-Policy']!='no-referrer':
        reject('SECURITY_HEADER_MISSING')
    csp=line_map['Content-Security-Policy']
    if csp!=meta[0]+"; frame-ancestors 'none'":
        reject('CSP_MISMATCH')
    if ("script-src 'sha256-"+sh+"'" not in csp or
            "style-src 'sha256-"+st+"'" not in csp):
        reject('CSP_HASH_MISMATCH')
    for rule in ("default-src 'none'", "connect-src 'none'", "object-src 'none'", "form-action 'none'", "base-uri 'none'"):
        if rule not in csp: reject('CSP_POLICY_WEAK')
    # Vercel ignores the Cloudflare/Netlify _headers file. Transfer those
    # protections to native Vercel configuration (same CSP hashes).
    hs=[{'key':k,'value':v} for k,v in line_map.items()]
    return {'$schema':'https://openapi.vercel.sh/vercel.json', 'framework':None,
            'public':False, 'headers':[{'source':'/(.*)','headers':hs}]}

def build_release(source_archive:Path,out:Path)->dict:
    files=load_three_file_archive(source_archive)
    cfg=vercel_config(files)
    out=out.absolute()
    if out.exists():
        reject('DESTINATION_ALREADY_EXISTS')
    out.mkdir(parents=True)
    (out/'data').mkdir()
    (out/'index.html').write_bytes(files['index.html'])
    (out/'data/public_summary.json').write_bytes(files['data/public_summary.json'])
    (out/'vercel.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if (out/'index.html').read_bytes()!=files['index.html'] or (out/'data/public_summary.json').read_bytes()!=files['data/public_summary.json']:
        reject('OUTPUT_READBACK_FAILED')
    return {'status':'READY_FOR_AUTHORIZED_VERCEL_DEPLOYMENT',
            'count':json.loads(files['data/public_summary.json'])['capture_total'],
            'allowed_files':['index.html','data/public_summary.json','vercel.json'],
            'sha256':{name:sha256((out/name).read_bytes()) for name in ('index.html','data/public_summary.json','vercel.json')},
            'not_deployed':True}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source-zip',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    res=build_release(a.source_zip,a.out)
    print(json.dumps(res,ensure_ascii=False,indent=2))
if __name__=='__main__':main()