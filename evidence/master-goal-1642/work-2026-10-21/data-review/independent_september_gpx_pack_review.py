"""Read-only independent verification of September raw GPX evidence intake."""
from pathlib import Path,PurePosixPath
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from collections import Counter
import hashlib,zlib,io,json,csv,re,math

B=Path('/workspace/scratch/ded5451af149');R=B/'data-audit-gpx-pack';E=B/'data-audit-evidence'
receipt=json.loads((R/'evidence/raw_intake/2026-10-21-september-gpx-source-evidence.json').read_text())
transport=R/receipt['archive']['repository_path'];blob=transport.read_bytes()
def sha(b):return hashlib.sha256(b).hexdigest()
def gitsha(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
assert len(blob)==7945041==receipt['archive']['size_bytes']
assert sha(blob)=='162b01718cd2916e2b3bdfa61f506e54a63ee4d54e03bd73672cb9804e324ecb'==receipt['archive']['sha256']
assert gitsha(blob)=='d904bd93b6a5495c7040a22f583234b80a1002f0'==receipt['archive']['git_blob_sha1']
for flag in ('complete_search_coverage_claimed','search_role_assigned','negative_eligibility_assigned','gold_status_assigned','canonical_promotion'):
    assert receipt[flag] is False
assert receipt['added_observation_count']==0 and receipt['quality_status']=='BYTE_SOURCE_IDENTITY_VERIFIED_ONLY'
library=json.loads((E/'library-list-habuai.json').read_text())['structuredContent']['items']
byid={x['library_file_id']:x for x in library if x.get('library_file_id')}
main=json.loads((E/'independent-main-gpx-manifests.json').read_text())
main_bysha={x['manifest']['raw_sha256']:x for x in main}
pack=B/'data-audit-repair/incoming/2026-10-21/habu_db_september_51_validation.zip'
assert sha(pack.read_bytes())==receipt['source_log_evidence']['existing_corrected_validation_pack_sha256']
with ZipFile(pack) as z:
    log=z.read(receipt['source_log_evidence']['source_log_entry_in_existing_validation_pack'])
    events=list(csv.DictReader(io.StringIO(z.read('csv/新規イベント_2026-09_10.csv').decode('utf-8-sig'))))
assert len(log)==receipt['source_log_evidence']['size_bytes'] and sha(log)==receipt['source_log_evidence']['sha256']
lines=log.decode('utf-8-sig').splitlines();captures={x['record_id']:x for x in events if x['event_class']=='CAPTURE_HABU' and x['exploration_night'].startswith('2026-09')}
assert len(captures)==50 and sum(int(x['count_min']) for x in captures.values())==51
JST=ZoneInfo('Asia/Tokyo')
def night(t):return (t.astimezone(JST)-timedelta(hours=7)).date().isoformat()
def instant(text):
    t=datetime.fromisoformat(text.replace('Z','+00:00'));assert t.tzinfo is not None;return t
def hav(a,b,c,d):
    a,b,c,d=map(math.radians,(a,b,c,d));h=math.sin((c-a)/2)**2+math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2
    return 12742017.6*math.asin(min(1,math.sqrt(h)))
results=[];links=[];total=0;allpoints=0;dups=[]
with ZipFile(io.BytesIO(blob)) as z:
    assert z.testzip() is None
    assert len(z.infolist())==15==receipt['member_count']==len(receipt['sources'])
    assert len(set(z.namelist()))==15 and set(z.namelist())=={x['member_name'] for x in receipt['sources']}
    for source in receipt['sources']:
        name=source['member_name'];p=PurePosixPath(name);info=z.getinfo(name)
        assert not p.is_absolute() and p.parts[0]=='gpx' and '..' not in p.parts and '\\' not in name
        assert not info.flag_bits&1 and (info.external_attr>>16)&0o170000!=0o120000
        raw=z.read(name);total+=len(raw)
        assert len(raw)==source['size_bytes'] and sha(raw)==source['sha256'] and gitsha(raw)==source['git_blob_sha1']
        assert f'{zlib.crc32(raw):08x}'==source['crc32_hex'] and info.compress_size==source['compressed_size_bytes']
        original=B/'data-audit-work/library-originals'/source['source_library_path'].lstrip('/')
        assert original.read_bytes()==raw
        metadata=byid[source['library_file_id']]
        assert metadata['name']==source['original_filename'] and metadata['path']==source['source_library_path']
        assert metadata['size_bytes']==len(raw) and metadata['file_id']==source['source_file_id']
        assert metadata['created_at']==source['source_received_at_utc']
        assert metadata['model_generated'] is False and source['source_model_generated'] is False
        assert source['quality_status']=='BYTE_SOURCE_IDENTITY_VERIFIED_ONLY'
        assert source['search_role']=='UNKNOWN_NOT_ASSIGNED' and source['negative_eligibility']=='NOT_ASSIGNED' and source['gold_status']=='NOT_ASSIGNED'
        points=[];untimed=0
        for _,node in ET.iterparse(io.BytesIO(raw),events=('end',)):
            if node.tag.rsplit('}',1)[-1]!='trkpt':continue
            text=next((x.text for x in node if x.tag.rsplit('}',1)[-1]=='time'),None)
            if text:points.append((instant(text),float(node.attrib['lat']),float(node.attrib['lon'])))
            else:untimed+=1
            node.clear()
        allpoints+=len(points);span=source['file_point_span'];times=[p[0] for p in points]
        assert len(points)==span['timed_trackpoint_count'] and untimed==span['untimed_trackpoint_count']
        for field,value in [('first_stored_point_utc',times[0]),('last_stored_point_utc',times[-1]),('timestamp_min_utc',min(times)),('timestamp_max_utc',max(times)),('timestamp_min_jst',min(times)),('timestamp_max_jst',max(times))]:
            assert instant(span[field])==value
        actual_nights=Counter(night(t) for t in times)
        assert dict(actual_nights)==span['point_operational_night_counts']
        assert set(actual_nights)=={source['log_attributed_operational_night']}
        if source['duplicate_status']=='EXACT_RAW_SHA256_DUPLICATE_OF_MAIN':
            duplicate=main_bysha[source['sha256']]
            assert duplicate['manifest']['raw_size_bytes']==len(raw)
            assert duplicate['path'] in source['existing_main_duplicate_paths']
            dups.append(source['log_attributed_operational_night'])
        else:assert source['duplicate_status']=='NOT_PRESENT_IN_INSPECTED_CANONICAL_GPX_TREE'
        assert len(source['capture_log_links'])==source['associated_existing_capture_events']
        for link in source['capture_log_links']:
            cap=captures[link['corrected_source_record_id']]
            assert cap['source_locator']==link['source_locator']
            t=instant(link['capture_time_jst'])
            assert t==datetime.fromisoformat(cap['event_time_jst']).replace(tzinfo=JST)
            assert night(t)==link['operational_night']==cap['exploration_night']==source['log_attributed_operational_night']
            assert int(cap['count_min'])==link['corrected_log_individual_count']
            start=int(link['source_locator'].split('_')[1])-1;end=start+1
            while end<len(lines) and not re.fullmatch(r'\d{4}/\d{1,2}/\d{1,2} \d{1,2}:\d{2}',lines[end]):end+=1
            block='\n'.join(lines[start:end]).strip()
            assert sha(block.encode())==link['raw_log_block_sha256_normalized_newlines']
            assert datetime.strptime(lines[start],'%Y/%m/%d %H:%M').replace(tzinfo=JST)==t
            # Literal source block must identify a capture, not a bare filename/time match.
            assert '捕獲' in lines[start+1] and cap['event_class']=='CAPTURE_HABU'
            eligible=[(hav(float(cap['latitude']),float(cap['longitude']),lat,lon),abs((pt-t).total_seconds()),pt) for pt,lat,lon in points if abs((pt-t).total_seconds())<=600]
            nearest=min(eligible)
            assert nearest[0]<=100 and nearest[1]<=600
            assert abs(nearest[0]-link['nearest_distance_m'])<1e-8
            assert abs(nearest[1]-link['absolute_time_delta_seconds'])<1e-8
            assert nearest[2]==instant(link['nearest_actual_point_time_jst'])
            links.append(link['corrected_source_record_id'])
        results.append({'member':name,'bytes':len(raw),'timed_points':len(points),'untimed_points':untimed,'actual_operational_nights':dict(actual_nights),'capture_log_links':len(source['capture_log_links']),'original_library_bytes_identical':True})
assert total==69910267==receipt['total_raw_gpx_bytes']
assert len(links)==50==len(set(links)) and set(links)==set(captures)
assert sorted(dups)==['2026-09-02','2026-09-28']
manifest=[]
for p in sorted(R.rglob('*')):
    if p.is_file() and '__pycache__' not in str(p):
        raw=p.read_bytes();manifest.append({'path':str(p.relative_to(R)),'bytes':len(raw),'sha256':sha(raw),'git_blob_sha1':gitsha(raw)})
result={'status':'PASS_SOURCE_IDENTITY_ONLY','archive_bytes':len(blob),'archive_sha256':sha(blob),'archive_git_blob_sha1':gitsha(blob),'members':15,'total_raw_gpx_bytes':total,'timed_trackpoints':allpoints,'exact_received_original_comparisons':15,'library_metadata_matches':15,'capture_log_blocks_and_actual_point_correspondences':50,'existing_corrected_log_individuals':51,'main_duplicate_operational_nights':sorted(dups),'added_observation_count':0,'negative_or_gold_or_search_role_assigned':False,'filename_used_as_night_proof':False,'source_results':results,'final_candidate_manifest':manifest}
(E/'independent-september-gpx-pack-evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['source_results','final_candidate_manifest']},ensure_ascii=False,indent=2))
