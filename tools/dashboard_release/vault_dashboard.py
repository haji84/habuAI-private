"""Private execution only: existing encrypted vault -> deliberate public totals.

Uses the verified legacy vault format and existing owner overlay. No raw original
is written to the public directory. The key never reaches HTML, JavaScript or Git.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.apply_private_dashboard_overlay import apply_overlay
from tools.dashboard_release import habu_library_vault_tool as vault
from tools.dashboard_release.public_summary import project_public_summary, validate_public_summary

MAX_ARCHIVE=500*1024*1024
MAX_JSON=4*1024*1024
HEX=re.compile(r'[0-9a-f]{64}\Z')
TOKEN='__HABU_PUBLIC_SUMMARY_JSON__'


class ReleaseBlocked(ValueError):
    """Only fixed, non-sensitive reason codes may reach the command output."""


def sha(data):return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for piece in iter(lambda:f.read(1024*1024),b''):h.update(piece)
    return h.hexdigest()


def safe_input(path, limit):
    p=Path(path).absolute()
    for part in (p,*p.parents):
        if part.is_symlink() or (part/'.git').exists():raise ReleaseBlocked('PRIVATE_INPUT_IN_GIT_OR_SYMLINK')
    if not p.is_file() or not 0<p.stat().st_size<=limit:raise ReleaseBlocked('PRIVATE_INPUT_SIZE_OR_TYPE')
    return p


def json_object(data):
    def unique(pairs):
        obj={}
        for k,v in pairs:
            if k in obj:raise ReleaseBlocked('DUPLICATE_JSON_KEY')
            obj[k]=v
        return obj
    def no_constant(_):raise ReleaseBlocked('NONFINITE_JSON')
    obj=json.loads(data,object_pairs_hook=unique,parse_constant=no_constant)
    if not isinstance(obj,dict):raise ReleaseBlocked('JSON_OBJECT_REQUIRED')
    return obj


def public_files(summary, template):
    summary=validate_public_summary(summary)
    p=Path(template)
    if p.is_symlink() or not p.is_file() or p.stat().st_size>256*1024:raise ReleaseBlocked('INVALID_PUBLIC_TEMPLATE')
    text=p.read_text(encoding='utf-8')
    if text.count(TOKEN)!=1:raise ReleaseBlocked('PUBLIC_TEMPLATE_MARKER')
    encoded=json.dumps(summary,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    html=text.replace(TOKEN,encoded.replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026'))
    scripts=re.findall(r'<script data-runtime>(.*?)</script>',html,re.S)
    styles=re.findall(r'<style>(.*?)</style>',html,re.S)
    if len(scripts)!=1 or len(styles)!=1:raise ReleaseBlocked('PUBLIC_TEMPLATE_RUNTIME')
    sh=base64.b64encode(hashlib.sha256(scripts[0].encode()).digest()).decode()
    ch=base64.b64encode(hashlib.sha256(styles[0].encode()).digest()).decode()
    csp=("default-src 'none'; script-src 'sha256-"+sh+"'; style-src 'sha256-"+ch+
         "'; base-uri 'none'; form-action 'none'; connect-src 'none'; object-src 'none'")
    if html.count('__HABU_CSP__')!=1:raise ReleaseBlocked('PUBLIC_TEMPLATE_CSP')
    html=html.replace('__HABU_CSP__',csp)
    headers='/*\n  Content-Security-Policy: '+csp+"; frame-ancestors 'none'\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: no-referrer\n  Cache-Control: no-cache\n"
    return {'index.html':html.encode('utf-8'),
        'data/public_summary.json':(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode(),
        '_headers':headers.encode()}


def write_release(destination, files):
    dest=Path(destination).absolute()
    if any(p.is_symlink() for p in (dest,*dest.parents)):raise ReleaseBlocked('PUBLIC_OUTPUT_SYMLINK')
    if dest.exists():
        if not dest.is_dir():raise ReleaseBlocked('PUBLIC_OUTPUT_CONFLICT')
        paths=list(dest.rglob('*'))
        if any(p.is_symlink() for p in paths):raise ReleaseBlocked('PUBLIC_OUTPUT_SYMLINK')
        got={p.relative_to(dest).as_posix() for p in paths if p.is_file()}
        if got!=set(files) or any((dest/n).read_bytes()!=raw for n,raw in files.items()):
            raise ReleaseBlocked('PUBLIC_OUTPUT_CONFLICT')
        return True
    dest.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.public-aggregate-',dir=dest.parent))
    try:
        for name,raw in files.items():
            p=stage/name;p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as f:f.write(raw)
            if p.read_bytes()!=raw:raise ReleaseBlocked('PUBLIC_OUTPUT_READBACK')
        # A concurrent existing nonempty destination must never be replaced.
        if dest.exists():raise ReleaseBlocked('PUBLIC_OUTPUT_RACE')
        stage.rename(dest)
    finally:
        if stage.exists():shutil.rmtree(stage)
    return False


def build_from_vault(*, archive, key_file, base_entry, overlay_entry, destination, template,
                     expected_archive_sha256, expected_base_sha256, expected_overlay_sha256):
    if os.environ.get('GITHUB_ACTIONS','').lower()=='true':raise ReleaseBlocked('PUBLIC_ACTIONS_DECRYPTION_FORBIDDEN')
    for h in (expected_archive_sha256,expected_base_sha256,expected_overlay_sha256):
        if not isinstance(h,str) or not HEX.fullmatch(h):raise ReleaseBlocked('SOURCE_HASH_REQUIRED')
    arc=safe_input(archive,MAX_ARCHIVE);key=safe_input(key_file,4096)
    dest=Path(destination).absolute()
    if any(dest==p.parent or p.parent in dest.parents or dest in p.parents for p in (arc,key)):
        raise ReleaseBlocked('PUBLIC_OUTPUT_OVERLAPS_PRIVATE_INPUT')
    if file_sha(arc)!=expected_archive_sha256:raise ReleaseBlocked('ARCHIVE_SHA_MISMATCH')
    try:
        # Bound every ZIP read before the legacy verifier decrypts its members.
        with zipfile.ZipFile(arc) as z:
            infos=z.infolist()
            if len(infos)>vault.MAX_ITEMS+2 or len({i.filename for i in infos})!=len(infos):
                raise ReleaseBlocked('ARCHIVE_STRUCTURE')
            for i in infos:
                limit=4096 if i.filename=='header.json' else MAX_JSON if i.filename=='manifest.enc' else vault.MAX_PER_ITEM+28
                if i.compress_type!=zipfile.ZIP_STORED or not 0<i.file_size<=limit:
                    raise ReleaseBlocked('ARCHIVE_MEMBER_LIMIT')
            verified=vault.verify(arc,key)
            header=json_object(z.read('header.json'));aid=header['archive_id']
            cipher=vault.AESGCM(vault.load_key(key,aid))
            manifest=json_object(vault.decrypted_payload(cipher,z.read('manifest.enc'),aid,b'manifest'))
            sources={e['name']:e for e in manifest['files']}
            def read_bound(name, expected):
                vault.clean_rel(name)
                entry=sources.get(name)
                if entry is None or entry['sha256']!=expected or entry['size']>MAX_JSON:
                    raise ReleaseBlocked('SOURCE_BINDING_FAILED')
                data=vault.decrypted_payload(cipher,z.read(entry['cipher']),aid,bytes.fromhex(expected))
                if sha(data)!=expected or len(data)!=entry['size']:raise ReleaseBlocked('SOURCE_SHA_MISMATCH')
                return json_object(data)
            private=apply_overlay(read_bound(base_entry,expected_base_sha256),read_bound(overlay_entry,expected_overlay_sha256))
            public=project_public_summary(private)
            del private
        if file_sha(arc)!=expected_archive_sha256:raise ReleaseBlocked('SOURCE_CHANGED_DURING_READ')
        files=public_files(public,template)
        repeated=write_release(dest,files)
        return {'schema_version':'habu-private-to-public-release-receipt-v1',
            'status':'AGGREGATE_RELEASE_VERIFIED','authenticated_source_files':verified['verified_files'],
            'encrypted_archive_sha256':expected_archive_sha256,
            'private_base_sha256':expected_base_sha256,'private_overlay_sha256':expected_overlay_sha256,
            'public_summary_sha256':sha(files['data/public_summary.json']),
            'public_files_sha256':{n:sha(r) for n,r in files.items()},
            'identical_existing_release':repeated,'key_exported':False,'raw_original_exported':False,
            'official_model_promoted':False,'hosted_deployment_verified':False}
    except ReleaseBlocked:
        raise
    except Exception:
        raise ReleaseBlocked('AUTHENTICATION_OR_AGGREGATION_FAILED') from None


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('archive','key-file','destination','template'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('base-entry','overlay-entry','expected-archive-sha256','expected-base-sha256','expected-overlay-sha256'):
        p.add_argument('--'+name,required=True)
    a=p.parse_args()
    try:
        receipt=build_from_vault(**vars(a))
        print(json.dumps({k:receipt[k] for k in ('status','public_summary_sha256','identical_existing_release')},sort_keys=True))
        return 0
    except ValueError:
        print('{"status":"BLOCKED","reason":"PRIVATE_RELEASE_FAILED"}')
        return 2

if __name__=='__main__':raise SystemExit(main())
