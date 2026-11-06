"""Build a prospective display CSV, preserving received workbook and ZIP bytes.

The workbook XML identifies the 101 display-night corrections. The companion
ZIP CSV supplies the same rows with full coordinate precision and preserved
notes. All output fields except `night` remain byte-value equivalent to that
source CSV. This display contains noncapture and unresolved legacy categories.
"""
import argparse
import csv
from datetime import datetime, timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import stat
from xml.etree import ElementTree as ET
from zipfile import ZipFile

N = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
HEADERS = {'記録ID':'source_record', '日付':'date', '時刻':'time', '探索夜':'night',
           '元イベント分類':'event_type_original', '取込判定':'classification',
           '生物種':'species', '数量':'count', 'サイズ':'size', '地域':'area',
           '緯度':'lat', '経度':'lon', '路面':'surface', 'GPX判定':'gpx_status', 'ソース':'source'}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def relative_parts(value, *, incoming=False):
    if not isinstance(value, str) or '\\' in value:
        raise ValueError('expected a relative POSIX repository path')
    parts = tuple(value.split('/'))
    if any(part in ('', '.', '..') for part in parts):
        raise ValueError('repository path must not be absolute or traverse directories')
    if incoming and (len(parts) < 2 or parts[0] != 'incoming'):
        raise ValueError('received source must remain under incoming/')
    return parts

def directory_fd(start_fd, parts, *, create=False):
    current = os.dup(start_fd)
    try:
        for part in parts:
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=current)
                except FileExistsError:
                    pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=current)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise

def read_regular(root_fd, parts):
    parent = directory_fd(root_fd, parts[:-1])
    try:
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise ValueError('expected a regular file')
        with os.fdopen(fd, 'rb') as source:
            return source.read()
    finally:
        os.close(parent)

def verified_source(root_fd, item):
    parts = relative_parts(item['repository_path'], incoming=True)
    raw = read_regular(root_fd, parts)
    if len(raw) != item['size_bytes'] or sha(raw) != item['sha256']:
        raise ValueError('source integrity mismatch: ' + item['repository_path'])
    return raw

def publish_candidate(root_fd, parts, payload):
    parent = directory_fd(root_fd, parts[:-1], create=True)
    try:
        try:
            fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=parent)
        except FileExistsError:
            if read_regular(root_fd, parts) != payload:
                raise ValueError('different candidate already exists; refusing overwrite')
            return
        with os.fdopen(fd, 'wb') as target:
            target.write(payload)
    finally:
        os.close(parent)

def xml_display_rows(path):
    with ZipFile(path) as z:
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            shared=[''.join(v.itertext()) for v in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        sheets=ET.fromstring(z.read('xl/workbook.xml')).find('m:sheets',N)
        sheet=next(s for s in sheets if s.attrib['name']=='捕獲原DBと追加_314件')
        rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        target=next(r.attrib['Target'] for r in rels if r.attrib['Id']==sheet.attrib[R])
        target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
        root=ET.fromstring(z.read(target))
        values=[]
        for row in root.findall('.//m:row',N):
            result={}
            for cell in row:
                if cell.tag.split('}')[-1]!='c':
                    continue
                column=''.join(c for c in cell.attrib['r'] if c.isalpha())
                kind=cell.attrib.get('t')
                v=cell.find('m:v',N)
                if kind=='inlineStr':
                    value=''.join(cell.find('m:is',N).itertext())
                elif kind=='s':
                    value=shared[int(v.text)]
                else:
                    value=v.text if v is not None else ''
                result[column]=value
            values.append(result)
        columns={column:HEADERS[label] for column,label in values[0].items()}
        return [{field:row.get(column,'') for column,field in columns.items()} for row in values[1:]]

def build(root):
    root = Path(os.path.abspath(root))
    filesystem_root = os.open(root.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        root_fd = directory_fd(filesystem_root, root.parts[1:])
    finally:
        os.close(filesystem_root)
    try:
        return build_checked(root_fd)
    finally:
        os.close(root_fd)

def build_checked(root_fd):
    receipt_parts=relative_parts('evidence/raw_intake/2026-10-21-september-corrected-source-receipt.json')
    receipt_bytes=read_regular(root_fd, receipt_parts)
    receipt=json.loads(receipt_bytes.decode('utf-8'))
    items={x['kind']:x for x in receipt['sources']}
    snapshots={kind:verified_source(root_fd,item) for kind,item in items.items()}
    display=xml_display_rows(io.BytesIO(snapshots['corrected_workbook']))
    with ZipFile(io.BytesIO(snapshots['validation_pack'])) as z:
        original=z.read('csv/本人捕獲_全期間原DB+追加.csv')
    rows=list(csv.DictReader(io.StringIO(original.decode('utf-8-sig'))))
    if len(rows)!=314 or len(display)!=314:
        raise ValueError('display row count mismatch')
    indexed={r['source_record']:r for r in rows}
    if len(indexed)!=314:
        raise ValueError('duplicate source_record in display')
    changes=[]
    unknown=[]
    for xmlrow in display:
        source=indexed[xmlrow['source_record']]
        for field,value in xmlrow.items():
            if field in ('lat','lon') and value and source[field]:
                if abs(float(value)-float(source[field]))>1e-10:
                    raise ValueError('workbook/CSV coordinate disagreement')
            elif source[field]!=value:
                raise ValueError('workbook/CSV field disagreement: '+field)
        try:
            instant=datetime.fromisoformat(xmlrow['date']+' '+xmlrow['time'])
        except ValueError:
            unknown.append(xmlrow['source_record'])
            continue
        expected=(instant-timedelta(hours=7)).date().isoformat()
        if expected!=xmlrow['night']:
            changes.append({'source_record':xmlrow['source_record'], 'old_night':xmlrow['night'],
                            'corrected_night':expected, 'classification':xmlrow['classification']})
            source['night']=expected
    if len(changes)!=101 or len(unknown)!=23:
        raise ValueError('source display changed; requires fresh independent review')
    target='data/processed/reconciliation_candidates/2026-10-21/historical_capture_display_september51_07h.csv'
    buffer=io.StringIO(newline='')
    writer=csv.DictWriter(buffer,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    payload=buffer.getvalue().encode('utf-8-sig')
    if read_regular(root_fd, receipt_parts)!=receipt_bytes:
        raise ValueError('intake receipt changed during derivation')
    for kind,item in items.items():
        if verified_source(root_fd,item)!=snapshots[kind]:
            raise ValueError('source changed during derivation')
    publish_candidate(root_fd,relative_parts(target),payload)
    return {'output_path':target, 'output_sha256':sha(payload),
            'source_workbook_sha256':items['corrected_workbook']['sha256'],
            'source_zip_sha256':items['validation_pack']['sha256'],
            'source_entry_sha256':sha(original), 'rows':314, 'night_changes':len(changes),
            'strict_iso_unparseable_rows_preserved':unknown,
            'status':'DERIVED_PROSPECTIVE_CANDIDATE_CI_AND_INDEPENDENT_REVIEW_PENDING',
            'other_fields_preserved':True, 'source_bytes_unchanged':True, 'changes':changes}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    result=build(parser.parse_args().root)
    print(json.dumps(result,ensure_ascii=False,indent=2))
