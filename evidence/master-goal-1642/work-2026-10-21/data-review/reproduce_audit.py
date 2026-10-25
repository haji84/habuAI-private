"""Read-only independent source and GPX audit; outputs JSON outside repository."""
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import csv, json, hashlib, math, collections, io

B=Path('/workspace/scratch/ded5451af149')
W=B/'data-audit-work'
E=B/'data-audit-evidence'
SRC=W/'restored/source/監査CSV・レポート'
JST=ZoneInfo('Asia/Tokyo')
def sha(raw): return hashlib.sha256(raw).hexdigest()
def csvload(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
new=csvload(SRC/'新規イベント_2026-09_10.csv')
report=csvload(SRC/'GPS照合_新規本人捕獲.csv')
captures=[r for r in new if r['event_class']=='CAPTURE_HABU']
sources={}
download_result=json.loads((E/'library-download-result.json').read_text())
library_integrity=[]
for filename in download_result['files']:
    p=Path(filename);raw=p.read_bytes()
    library_integrity.append({'path':str(p),'bytes':len(raw),'sha256':sha(raw)})
    if p.suffix=='.gpx':sources[sha(raw)]={'raw':raw,'path':str(p)}
(E/'library-source-integrity.json').write_text(json.dumps(library_integrity,ensure_ascii=False,indent=2))

# Reconstruct PR39 GPX in disposable output, independently of its unit test.
gpx39=[]
for mf in sorted((W/'pr39/evidence/gpx/2026').glob('*.manifest.json')):
    m=json.loads(mf.read_text());s=m['storage'];p=W/'pr39'/s['path']
    if s['type']=='direct-gpx': raw=p.read_bytes()
    else:
        a=json.loads((p/'manifest.json').read_text())
        parts=sorted(p.glob(a['part_glob']))
        assert len(parts)==a['part_count']
        raw='\n'.join(q.read_text(encoding='utf-8') for q in parts).encode('utf-8')
        assert sha(raw)==a['raw_sha256']
    assert sha(raw)==m['raw_sha256'] and len(raw)==m['raw_size_bytes']
    out=W/'restored/pr39'/mf.name.replace('.manifest.json','.gpx')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
    sources[sha(raw)]={'raw':raw,'path':str(out)}
    gpx39.append({'night':mf.stem.split('.')[0],'bytes':len(raw),'sha256':sha(raw)})
for p in (W/'restored/pr41').glob('*.gpx'):
    raw=p.read_bytes();sources[sha(raw)]={'raw':raw,'path':str(p)}

def hav(a,b,c,d):
    a,b,c,d=map(math.radians,(a,b,c,d))
    v=math.sin((c-a)/2)**2+math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2
    return 12742017.6*math.asin(min(1,math.sqrt(v)))

results=[];tracks=[]
for digest,source in sources.items():
    rows=[r for r in report if r['gpx_sha256']==digest]
    root=ET.fromstring(source['raw']);pts=[]
    for node in root.iter():
        if node.tag.endswith('trkpt'):
            t=next((x.text for x in node if x.tag.endswith('time')),None)
            if t:pts.append((datetime.fromisoformat(t.replace('Z','+00:00')),float(node.attrib['lat']),float(node.attrib['lon'])))
    tracks.append({'sha256':digest,'path':source['path'],'trackpoints':len(pts),'first_time':str(pts[0][0]),'last_time':str(pts[-1][0]),'capture_rows':len(rows)})
    for r in rows:
        dt=datetime.fromisoformat(r['capture_time_jst']).replace(tzinfo=JST) if '+' not in r['capture_time_jst'] else datetime.fromisoformat(r['capture_time_jst'])
        options=[(hav(float(r['lat']),float(r['lon']),lat,lon),abs((t-dt).total_seconds()),t) for t,lat,lon in pts if abs((t-dt).total_seconds())<=600]
        closest=min(options,default=None)
        results.append({'record_id':r['record_id'],'night':r['exploration_night'],'source_sha256':digest,'source_path':source['path'],'source_sha_verified':True,'match':bool(closest and closest[0]<=100),'nearest_distance_m':closest[0] if closest else None,'nearest_time_jst':closest[2].astimezone(JST).isoformat() if closest else None,'abs_time_delta_seconds':closest[1] if closest else None,'claimed_distance_m':float(r['nearest_distance_m']),'distance_difference_m':closest[0]-float(r['nearest_distance_m']) if closest else None})
missing=[r for r in report if r['gpx_sha256'] not in sources]
assert len(results)==67 and not missing
assert all(r['match'] for r in results)
(E/'gpx-independent-results.json').write_text(json.dumps({'method':'WGS84 haversine R=6371008.8m, actual trackpoints only, absolute timestamp difference <=600s, nearest spatial distance <=100m','matched_capture_events':len(results),'matched_individuals_after_multiplicity_correction':68,'missing':missing,'sources':tracks,'results':results},ensure_ascii=False,indent=2))

# Event identity reconciliation: same minute + class + coordinates (1m tolerance).
identity=[]
candidate_by_night=collections.defaultdict(list)
for r in captures:candidate_by_night[r['exploration_night']].append(r)
for label,root,nightpaths in [
    ('main',B/'habuAI-private',['2026-09-28']),
    ('PR39',W/'pr39',['2026-10-14','2026-10-15'])]:
    for night in nightpaths:
        for r in csvload(root/f'data/processed/capture_events/2026/{night}.csv'):
            dt=datetime.fromisoformat(r['event_time_local']).strftime('%Y-%m-%d %H:%M')
            matches=[x for x in candidate_by_night[night] if x['event_time_jst']==dt and hav(float(r['latitude']),float(r['longitude']),float(x['latitude']),float(x['longitude']))<=1]
            identity.append({'existing_source':label,'existing_event_id':r['event_id'],'time_jst':dt,'night':night,'canonical_event_count':int(r['event_count']),'candidate_record_ids':[x['record_id'] for x in matches],'candidate_old_count_min':[x['count_min'] for x in matches],'candidate_match_count':len(matches),'ingestion_action':'link_existing_event_not_append'})
assert len(identity)==11 and all(r['candidate_match_count']==1 for r in identity)
with ZipFile(W/'library-originals/ハブAI/ハブAI_2025-2026_9月51匹訂正_統合DB検証パック.zip') as z:
    corrected_capture_rows=list(csv.DictReader(io.StringIO(z.read('csv/新規ハブ捕獲_2026-09_10.csv').decode('utf-8-sig'))))
    corrected_new=list(csv.DictReader(io.StringIO(z.read('csv/新規イベント_2026-09_10.csv').decode('utf-8-sig'))))
    source_changes=[]
    for old_row,new_row in zip(new,corrected_new):
        delta={key:{'old':old_row[key],'new':new_row[key]} for key in old_row if old_row[key]!=new_row[key]}
        if delta:source_changes.append({'time_jst':old_row['event_time_jst'],'event_class':old_row['event_class'],'source_locator':old_row['source_locator'],'changed_fields':delta})
    (E/'corrected-row-changes.json').write_text(json.dumps(source_changes,ensure_ascii=False,indent=2))
    for item in identity:
        matches=[r for r in corrected_capture_rows if r['event_time_jst']==item['time_jst'] and r['exploration_night']==item['night']]
        assert len(matches)==1
        item['corrected_candidate_record_id']=matches[0]['record_id']
        item['corrected_candidate_individual_count']=int(matches[0]['count_min'])
(E/'event-identity-reconciliation.json').write_text(json.dumps(identity,ensure_ascii=False,indent=2))

# Read-only XLSX cell extraction, no rewrite/recalculation.
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def workbook(path):
    with ZipFile(path) as z:
        assert z.testzip() is None
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            shared=[''.join(s.itertext()) for s in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        wb=ET.fromstring(z.read('xl/workbook.xml'))
        out={}
        for i,s in enumerate(wb.find('m:sheets',NS)):
            root=ET.fromstring(z.read(f'xl/worksheets/sheet{i+1}.xml'));rows=[]
            for r in root.findall('.//m:row',NS):
                row={}
                for c in r:
                    if c.tag.split('}')[-1]!='c':continue
                    if c.attrib.get('t')=='inlineStr':v=''.join(c.find('m:is',NS).itertext())
                    elif c.attrib.get('t')=='s':v=shared[int(c.find('m:v',NS).text)]
                    else:
                        value=c.find('m:v',NS);v=value.text if value is not None else ''
                    row[c.attrib['r']]=v
                rows.append(row)
            out[s.attrib['name']]=rows
        return out
oldpath=W/'restored/source/更新版Excel/ハブDB_2025-2026_10-20統合更新版.xlsx'
sevenpath=W/'restored/corrected07h.xlsx'
latestpath=W/'library-originals/ハブAI/ハブDB_2025-2026_10-20統合更新版_9月51匹訂正版.xlsx'
old,seven,latest=map(workbook,(oldpath,sevenpath,latestpath))
changes=[]
for sheet in old:
    for i,row in enumerate(old[sheet]):
        assert len(old[sheet])==len(seven[sheet])
        for cell,v in row.items():
            newv=seven[sheet][i].get(cell,'')
            if v!=newv:changes.append({'sheet':sheet,'cell':cell,'old':v,'new':newv})
individual=latest['本人捕獲個体_68匹'];month=collections.Counter()
for row in individual[1:]:
    vals=list(row.values());month[vals[4][:7]]+=1
assert len(individual)-1==68 and month=={'2026-09':51,'2026-10':17}
latest_night_errors=[];latest_missing=0
for row in latest['捕獲原DBと追加_314件'][1:]:
    by_letter={''.join(c for c in k if c.isalpha()):v for k,v in row.items()}
    try:instant=datetime.fromisoformat(by_letter['B']+' '+by_letter['C'])
    except ValueError:latest_missing+=1;continue
    expected=(instant-timedelta(hours=7)).date().isoformat()
    if expected!=by_letter['D']:latest_night_errors.append({'record_id':by_letter['A'],'expected':expected,'actual':by_letter['D']})
assert latest_missing==23 and len(latest_night_errors)==101
corrected_zip=W/'library-originals/ハブAI/ハブAI_2025-2026_9月51匹訂正_統合DB検証パック.zip'
zip_files=[]
with ZipFile(corrected_zip) as z:
    assert z.testzip() is None
    for item in z.infolist():
        if item.is_dir():continue
        raw=z.read(item.filename);zip_files.append({'path':item.filename,'bytes':len(raw),'sha256':sha(raw)})
        if item.filename.endswith('.csv'):
            rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
            zip_files[-1]['rows']=len(rows);zip_files[-1]['columns']=list(rows[0]) if rows else []
            if 'event_count' in zip_files[-1]['columns']:zip_files[-1]['sum_event_count']=sum(int(r['event_count']) for r in rows)
(E/'workbook-audit.json').write_text(json.dumps({'old_sha256':sha(oldpath.read_bytes()),'seven_sha256':sha(sevenpath.read_bytes()),'latest_sha256':sha(latestpath.read_bytes()),'07h_cell_changes':changes,'07h_change_count':len(changes),'latest_view_night_errors':latest_night_errors,'latest_view_unparseable_times':latest_missing,'latest_individual_rows':len(individual)-1,'latest_individual_counts_by_month':month,'latest_corrected_zip_sha256':sha(corrected_zip.read_bytes()),'latest_corrected_zip_files':zip_files},ensure_ascii=False,indent=2))
print(json.dumps({'gpx_event_matches':len(results),'gpx_pass':sum(r['match'] for r in results),'gpx_sources':len(tracks),'largest_claimed_distance_difference_m':max(abs(r['distance_difference_m']) for r in results),'existing_event_overlap':len(identity),'overlap_by_source':dict(collections.Counter(r['existing_source'] for r in identity)),'07h_cell_changes':len(changes),'07h_changed_sheets':dict(collections.Counter(r['sheet'] for r in changes)),'latest_individual_counts':month,'corrected_zip_files':zip_files},ensure_ascii=False,indent=2))
