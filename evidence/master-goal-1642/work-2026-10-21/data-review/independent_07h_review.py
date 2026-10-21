"""Read-only inspection of workbook and packed CSV operational-night attribution."""
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as E
from datetime import datetime,timedelta
import csv,io,json
base=Path('/workspace/scratch/ded5451af149')
book=base/'data-audit-repair/incoming/2026-10-21/habu_db_september_51_corrected.xlsx'
pack=book.with_name('habu_db_september_51_validation.zip')
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def sheet_rows(z,n):
    rr=[]
    for row in E.fromstring(z.read(f'xl/worksheets/sheet{n}.xml')).findall('m:sheetData/m:row',ns):
        rr.append({c.attrib['r'].rstrip('0123456789'):(''.join(c.find('m:is',ns).itertext()) if c.attrib.get('t')=='inlineStr' else c.findtext('m:v','',ns)) for c in row})
    return rr
result={}
with ZipFile(book) as z:
    for name,n,columns in [('capture_legacy_view',12,('B','C','D')),('new_events',5,('B',None,'C')),('all_period_events',7,('B',None,'C')),('new_capture_view',3,('C',None,'B')),('individual_view',4,('D',None,'E'))]:
        data=sheet_rows(z,n)[1:];errors=[];unparsed=[]
        for row in data:
            try:
                stamp=row.get(columns[0],'')+(' '+row.get(columns[1],'') if columns[1] else '')
                dt=datetime.fromisoformat(stamp)
            except (ValueError,TypeError):unparsed.append(row.get('A'));continue
            expected=(dt-timedelta(hours=7)).date().isoformat()
            if row.get(columns[2])!=expected:errors.append({'id':row.get('A'),'source_date_time':stamp,'stored_night':row.get(columns[2]),'expected_07h_night':expected})
        result[name]={'rows':len(data),'wrong_07h_nights':len(errors),'unparseable_time_rows':len(unparsed),'errors':errors,'unparseable_ids':unparsed}
with ZipFile(pack) as z:
    data=list(csv.DictReader(io.StringIO(z.read('csv/本人捕獲_全期間原DB+追加.csv').decode('utf-8-sig'))));errors=[];unparsed=[]
    for row in data:
        try:dt=datetime.fromisoformat(row['date']+' '+row['time'])
        except (ValueError,TypeError):unparsed.append(row['source_record']);continue
        expected=(dt-timedelta(hours=7)).date().isoformat()
        if expected!=row['night']:errors.append({'id':row['source_record'],'stored_night':row['night'],'expected_07h_night':expected})
    result['capture_legacy_csv']={'rows':len(data),'wrong_07h_nights':len(errors),'errors':errors,'unparseable_time_rows':len(unparsed),'unparseable_ids':unparsed}
p=base/'data-audit-evidence/independent-07h-view-check.json'
p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:{kk:vv for kk,vv in v.items() if kk not in ['errors','unparseable_ids']} for k,v in result.items()},ensure_ascii=False,indent=2))
