"""Private-source runner for the existing, single-entry Habu PDCA engine.

This adapter intentionally does not declare imported raw files eligible scientific data.
Run receipts and stdout logs remain within a private filesystem outside GitHub.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
import re
import secrets
import stat
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from datetime import datetime, timezone
from private_pdca_intake import (IntakeError, MAX_RAW_BYTES, MAX_RECEIPT_BYTES,
                                 _ReadBudget, _chunks, _digest, _read_bytes, _encoded_report,
                                 cleanup_owned_temp, guard_private_path, source_receipt_id)

SHA = re.compile(r"[a-f0-9]{64}\Z")
NIGHT = re.compile(r"20\d{2}-\d{2}-\d{2}\Z")


class PrivateRunError(ValueError):
    pass


# B1 is deliberately not called by run_private. B2 supervision is not installed.
B1_MAX_FILES = 2000
B1_MAX_ENTRIES = 4000
B1_MAX_JSON = 5 * 1024 * 1024
B1_MAX_REPORT = 20 * 1024 * 1024
B1_MAX_NODES = 100_000
B1_MAX_DEPTH = 32
B1_EXECUTION_POLICY = {'version':'private-pdca-bound-execution-v2','scientific_budget_seconds':300,
                       'parent_whole_seconds_max':330,'parent_read_bytes':2147483648,
                       'stdout_cap_reserved_for_B2':5242880,'stderr_cap_reserved_for_B2':1048576,
                       'max_candidates':3,'max_rounds':2,'source_eligible_for_model':False,
                       'p0_certified':False,'model_validation_certified':False,'champion_activation':False}


def _b1_selected_root(code_root, budget):
    budget.check()
    selected = Path(__file__).absolute().parents[1]
    _guard_private_path(selected, selected / 'scripts' / 'private_pdca_runner.py')
    if Path(code_root).resolve(strict=True) != selected.resolve(strict=True):
        raise PrivateRunError('B1_INSTALLED_ROOT_REQUIRED')
    budget.check()
    return selected.resolve(strict=True)


def _b1_modules(budget, *, engine=False, cycle=False):
    """Normal installed-src imports; never import from a caller's code root."""
    selected = _b1_selected_root(Path(__file__).absolute().parents[1], budget)
    names = ['master_contracts', 'master_inventory']
    if cycle:
        names.append('codex_cycle_contract')
    if engine:
        if os.name != 'posix':
            raise PrivateRunError('B1_NOT_STARTED_CAPABILITY: genuine POSIX master required')
        names.append('master_orchestrator')
    for name in names:
        existing = sys.modules.get(name)
        expected = selected / 'src' / (name + '.py')
        _guard_private_path(selected, expected)
        if existing is not None and Path(getattr(existing, '__file__', '')).absolute() != expected:
            raise PrivateRunError('B1_CONFLICTING_INSTALLED_MODULE')
    original = sys.path[:]
    try:
        sys.path.insert(0, str(selected / 'src'))
        modules = [importlib.import_module(name) for name in names]
    finally:
        sys.path[:] = original
    for name, module in zip(names, modules):
        if Path(module.__file__).absolute() != selected / 'src' / (name + '.py'):
            raise PrivateRunError('B1_CONFLICTING_INSTALLED_MODULE')
    budget.check()  # imports/version discovery are not artifact byte charges
    return modules


def _b1_document(raw, budget):
    """Bound tokens/nesting before the decoder allocates its object graph."""
    if type(raw) is not bytes or len(raw) > B1_MAX_JSON:
        raise PrivateRunError('B1_JSON_LIMIT')
    depth = nodes = 0
    tokens = rb'"(?:[^"\\]|\\.)*"|true|false|null|-?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|[^\s]'
    for match in re.finditer(tokens, raw):
        budget.check()
        token = match[0]
        if token in (b'{', b'['):
            depth += 1
        elif token in (b'}', b']'):
            depth -= 1
        if token not in (b'}', b']', b',', b':'):
            nodes += 1
        if depth > B1_MAX_DEPTH or nodes > B1_MAX_NODES:
            raise PrivateRunError('B1_JSON_STRUCTURE_LIMIT')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise PrivateRunError('B1_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def nonfinite(_):
        raise PrivateRunError('B1_NONFINITE_JSON')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=nonfinite)
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, PrivateRunError):
            raise
        raise PrivateRunError('B1_INVALID_JSON') from exc
    budget.check()
    return value


def _b1_canonical(value, budget):
    # Bound caller-owned graphs before pure canonical serialization/copy.
    nodes = 0
    def visit(item, depth):
        nonlocal nodes
        budget.check()
        nodes += 1
        if nodes > B1_MAX_NODES or depth > B1_MAX_DEPTH:
            raise PrivateRunError('B1_METADATA_STRUCTURE_LIMIT')
        if type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    raise PrivateRunError('B1_METADATA_KEY')
                visit(key, depth+1)
                visit(child, depth+1)
        elif type(item) is list:
            for child in item:
                visit(child, depth+1)
        elif type(item) is str:
            if len(item) > B1_MAX_JSON:
                raise PrivateRunError('B1_METADATA_STRING_LIMIT')
        elif item is not None and type(item) not in (int, float, bool):
            raise PrivateRunError('B1_METADATA_TYPE')
        elif type(item) is float and not math.isfinite(item):
            raise PrivateRunError('B1_NONFINITE_JSON')
    visit(value, 0)
    length = 0
    try:
        for piece in json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).iterencode(value):
            for start in range(0, len(piece), 4096):
                budget.check()
                length += len(piece[start:start+4096].encode('utf-8'))
                if length > B1_MAX_JSON:
                    raise PrivateRunError('B1_METADATA_BYTES_LIMIT')
        contracts, _ = _b1_modules(budget)
        raw = contracts.canonical_bytes(value)
    except ValueError as exc:
        if isinstance(exc, PrivateRunError):
            raise
        raise PrivateRunError('B1_METADATA_VALUE') from exc
    budget.check()
    return raw


def _b1_hash(domain, value, budget):
    return hashlib.sha256(domain.encode('ascii') + b'\0' + _b1_canonical(value, budget)).hexdigest()


def _b1_raw(path, cap, budget):
    """A owns positive reads; inventory empties need a genuine checked EOF."""
    path = Path(path)
    budget.check()
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise PrivateRunError('B1_NONREGULAR_FILE')
    if info.st_size:
        return _read_bytes(path, cap, budget)
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino, opened.st_size) != (info.st_dev, info.st_ino, 0):
            raise PrivateRunError('B1_EMPTY_DESCRIPTOR_CHANGED')
        budget.check()
        raw = stream.read(1)
        budget.bytes_read += len(raw)
        budget.check()
        if raw:
            raise PrivateRunError('B1_EMPTY_FILE_GREW')
    return b''


def _b1_file_ref(path, budget, *, cap=MAX_RAW_BYTES):
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise PrivateRunError('B1_NONREGULAR_FILE')
    if info.st_size > cap:
        raise PrivateRunError('B1_FILE_LIMIT')
    h = hashlib.sha256()
    if info.st_size == 0:
        h.update(_b1_raw(path, cap, budget))
    else:
        for chunk in _chunks(path, cap, budget, expected_size=info.st_size):
            h.update(chunk)
    budget.check()
    return {'sha256': h.hexdigest(), 'size_bytes': info.st_size}


def _b1_view(root, budget, *, code=False, whole=False):
    """Bounded physical counterpart of inventory/code_paths; no facade calls."""
    _, inventory = _b1_modules(budget)
    root = inventory.local_path(Path(root))
    starts = ('',) if whole else ('src', 'scripts', 'schemas') if code else inventory.SOURCE_DIRS
    pending, result, seen = [], {}, set()
    entries = total = encoded = 0
    def retain(path):
        nonlocal total, encoded
        relative = path.relative_to(root).as_posix()
        if relative in result:
            return
        if len(result) >= min(B1_MAX_FILES, 256 if code else B1_MAX_FILES):
            raise PrivateRunError('B1_VIEW_FILE_LIMIT')
        if len(relative.encode('utf-8')) > 1024:
            raise PrivateRunError('B1_PATH_LIMIT')
        cap = 4*1024*1024 if code else B1_MAX_JSON if path.suffix == '.json' else MAX_RAW_BYTES
        declared = path.lstat().st_size
        if code and total + declared > 16*1024*1024:
            raise PrivateRunError('B1_CODE_TOTAL_LIMIT')
        row = _b1_file_ref(path, budget, cap=cap)
        # Exact row serialization plus path overhead, before growing the map.
        encoded += len(json.dumps({relative: row}, ensure_ascii=False).encode('utf-8'))
        if encoded > B1_MAX_JSON:
            raise PrivateRunError('B1_VIEW_METADATA_LIMIT')
        result[relative] = row
        total += row['size_bytes']
    for name in starts:
        path = inventory.local_path(root, name) if name else inventory.local_path(root)
        if path.is_dir():
            pending.append((path, 1))
        elif code:
            raise PrivateRunError('B1_MISSING_CODE_DIRECTORY')
    while pending:
        directory, depth = pending.pop()
        if depth > 64:
            raise PrivateRunError('B1_DIRECTORY_DEPTH')
        relative = directory.relative_to(root).as_posix()
        directory = inventory.local_path(root, relative) if relative != '.' else inventory.local_path(root)
        if relative in seen:
            continue
        seen.add(relative)
        with os.scandir(directory) as iterator:
            for entry in iterator:
                budget.check()
                entries += 1
                if entries > B1_MAX_ENTRIES:
                    raise PrivateRunError('B1_VIEW_ENTRY_LIMIT')
                path = inventory.local_path(root, (directory/entry.name).relative_to(root).as_posix())
                if len(path.relative_to(root).as_posix().encode('utf-8')) > 1024:
                    raise PrivateRunError('B1_PATH_LIMIT')
                if not code and not whole and (entry.name == '__pycache__' or path.suffix == '.pyc'):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if len(pending) >= B1_MAX_ENTRIES or depth >= 64:
                        raise PrivateRunError('B1_DIRECTORY_LIMIT')
                    pending.append((path, depth+1))
                elif entry.is_file(follow_symlinks=False):
                    if not code or path.suffix == ('.json' if path.is_relative_to(root/'schemas') else '.py'):
                        retain(path)
                else:
                    raise PrivateRunError('B1_NONREGULAR_ENTRY')
    if whole:
        specials = []
    elif code:
        specials = ['requirements-analysis.txt', 'requirements-osm.txt']
    else:
        specials = ['pyproject.toml', 'uv.lock', 'poetry.lock', 'AGENTS.md', inventory.LEGACY_INPUT]
        with os.scandir(root) as iterator:
            for entry in iterator:
                budget.check()
                entries += 1
                if entries > B1_MAX_ENTRIES:
                    raise PrivateRunError('B1_VIEW_ENTRY_LIMIT')
                if Path(entry.name).match('requirements*.txt'):
                    if len(specials) >= B1_MAX_FILES:
                        raise PrivateRunError('B1_VIEW_FILE_LIMIT')
                    specials.append(entry.name)
    for name in specials:
        path = inventory.local_path(root, name)
        if path.exists():
            retain(path)
        elif code:
            raise PrivateRunError('B1_MISSING_REQUIREMENTS')
    budget.check()
    return {path: result[path] for path in sorted(result)}


def _b1_identity(night, inputs, code_view, budget):
    contracts, _, master = _b1_modules(budget, engine=True)
    contracts.validate_night(night)
    _b1_canonical(inputs, budget)
    code = {p: row['sha256'] for p, row in code_view.items()
            if p.endswith('.py') and p.split('/')[0] in ('src', 'scripts')}
    code_sha = contracts.digest(code)
    budget.check()
    runtime = master._runtime()
    budget.check()
    _b1_canonical(runtime, budget)
    value = master._scientific_identity(night, inputs, code_sha, runtime, None)
    _b1_canonical(value, budget)
    return value, contracts.digest(value)


def _b1_cycle(root, code_view, budget):
    contracts, inventory, cycle = _b1_modules(budget, cycle=True)
    pointer_path = inventory.local_path(root, 'protocols/development/current-cycle.json')
    pointer_raw = _b1_raw(pointer_path, 4*1024*1024, budget)
    pointer = _b1_document(pointer_raw, budget)
    if type(pointer) is not dict or set(pointer) != {'path', 'sha256'}:
        raise PrivateRunError('B1_CURSOR_FIELDS')
    if (type(pointer['path']) is not str or not re.fullmatch(r'protocols/development/cycles/[A-Za-z0-9_-]+\.json', pointer['path'])
            or type(pointer['sha256']) is not str or not SHA.fullmatch(pointer['sha256'])):
        raise PrivateRunError('B1_CURSOR_PATH_HASH')
    manifest_path = inventory.local_path(root, pointer['path'])
    raw = _b1_raw(manifest_path, 4*1024*1024, budget)
    if hashlib.sha256(raw).hexdigest() != pointer['sha256']:
        raise PrivateRunError('B1_CURSOR_HASH')
    manifest = _b1_document(raw, budget)
    if (type(manifest) is not dict or set(manifest) != cycle.MANIFEST_FIELDS
            or manifest['schema_version'] != cycle.VERSION or manifest['kind'] != 'DEVELOPMENT_CONTRACT_ONLY'):
        raise PrivateRunError('B1_CYCLE_FIELDS')
    if (type(manifest['cycle_id']) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',manifest['cycle_id'])
            or type(manifest['base_main_sha']) is not str or not re.fullmatch(r'[a-f0-9]{40}',manifest['base_main_sha'])
            or type(manifest['frozen_at']) is not str or len(manifest['frozen_at'])>128):
        raise PrivateRunError('B1_CYCLE_SCALARS')
    try:
        aware=datetime.fromisoformat(manifest['frozen_at']).utcoffset() is not None
    except ValueError as exc:
        raise PrivateRunError('B1_CYCLE_TIME') from exc
    if not aware:raise PrivateRunError('B1_CYCLE_TIME')
    rows = manifest['code_manifest']
    if type(rows) is not list or not 1 <= len(rows) <= 256:
        raise PrivateRunError('B1_CYCLE_REFS')
    observed = {}
    for row in rows:
        budget.check()
        if type(row) is not dict or set(row) != {'path','sha256'}:
            raise PrivateRunError('B1_CYCLE_REF_FIELDS')
        path = row['path']
        if type(path) is not str or path in observed or path not in code_view:
            raise PrivateRunError('B1_CYCLE_MEMBERSHIP')
        if type(row['sha256']) is not str or row['sha256'] != code_view[path]['sha256']:
            raise PrivateRunError('B1_CYCLE_CHANGED')
        observed[path] = code_view[path]
    if observed != code_view:
        raise PrivateRunError('B1_CYCLE_MEMBERSHIP')
    policy = manifest['policy_ref']
    if (type(policy) is not dict or set(policy) != {'path','sha256'}
            or policy['path'] != cycle.POLICY_PATH or type(policy['sha256']) is not str or not SHA.fullmatch(policy['sha256'])):
        raise PrivateRunError('B1_CYCLE_POLICY')
    policy_path = inventory.local_path(root, policy['path'])
    policy_raw = _b1_raw(policy_path, 4*1024*1024, budget)
    if (hashlib.sha256(policy_raw).hexdigest() != policy['sha256']
            or contracts.digest(_b1_document(policy_raw,budget)) != cycle.POLICY_DIGEST):
        raise PrivateRunError('B1_CYCLE_POLICY')
    if _b1_raw(pointer_path, 4*1024*1024, budget) != pointer_raw or _b1_raw(manifest_path,4*1024*1024,budget) != raw:
        raise PrivateRunError('B1_CYCLE_CHANGED')
    return {'pointer':dict(path='protocols/development/current-cycle.json',sha256=hashlib.sha256(pointer_raw).hexdigest(),size_bytes=len(pointer_raw)),
            'manifest':dict(path=pointer['path'],sha256=hashlib.sha256(raw).hexdigest(),size_bytes=len(raw)),
            'policy':dict(policy,size_bytes=len(policy_raw))}


def _b1_prepare(code_root, workspace, store, receipt_path, night, revision, budget):
    """Physical binding only, with no claim/engine. Requires real POSIX identity."""
    selected = _b1_selected_root(code_root, budget)
    contracts, _, _ = _b1_modules(budget, engine=True)
    code_root, workspace, store = _validate_roots(selected, Path(workspace), Path(store))
    contracts.validate_night(night)
    if type(revision) is not str or not re.fullmatch(r'r[1-9][0-9]{0,5}', revision):
        raise PrivateRunError('B1_REVISION')
    receipt_id, rows = _receipt_sources(Path(receipt_path), store, budget)
    inbox = []
    for row in rows:
        relative = 'incoming/private_pdca/' + row['sha256'] + ('.txt' if row['type'] == 'log' else '.gpx')
        target = workspace/relative
        _copy_verified(Path(row['private_archive']), target, row['sha256'], workspace, budget, row['size_bytes'])
        inbox.append({'type':row['type'],'path':relative,'sha256':row['sha256'],'size_bytes':row['size_bytes']})
    source = {'schema':'habu-private-pdca-source-scope-v2','night':night,
              'intake_receipt_ref':dict(path=Path(receipt_path).resolve().relative_to(store).as_posix(),
                                       **_b1_file_ref(Path(receipt_path),budget,cap=MAX_RECEIPT_BYTES)),
              'source_receipt_id':receipt_id,'sources':rows,'verified_inbox':inbox}
    scope = _b1_hash('habu-private-pdca-source-scope-v2',source,budget)
    tool, inputs, code = _b1_view(selected,budget), _b1_view(workspace,budget), _b1_view(selected,budget,code=True)
    cycle = _b1_cycle(selected,code,budget)
    identity, run_id = _b1_identity(night,inputs,code,budget)
    refs = []
    for label, view in (('tool',tool),('workspace',inputs)):
        for path, ref in view.items():
            if path.startswith(('protocols/','policies/')):
                refs.append(dict(root=label,path=path,**ref))
    binding = {'schema':'habu-private-pdca-binding-v2','scope_id':scope,'revision':revision,
               'selected_code_root':str(selected),'workspace_root':str(workspace),'tool_input_view':tool,
               'workspace_input_view':inputs,'complete_code_view':code,
               'complete_code_sha256':contracts.digest({p:v['sha256'] for p,v in code.items()}),
               'protocol_policy_refs':refs,'cycle_refs':cycle,'master_identity':identity,'master_run_id':run_id,
               'execution_policy':dict(B1_EXECUTION_POLICY)}
    _b1_recheck(source,binding,store,budget)
    binding_sha = _b1_hash('habu-private-pdca-binding-v2',binding,budget)
    attempt = _b1_hash('habu-private-pdca-attempt-v2',{'scope_id':scope,'revision':revision,'binding_sha256':binding_sha},budget)
    return {'source':source,'binding':binding,'scope_id':scope,'attempt_id':attempt,'state':'BINDING_ONLY_NO_EXECUTION'}


def _b1_recheck(source, binding, store, budget):
    _b1_binding_shape(source,binding,budget)
    selected = _b1_selected_root(binding['selected_code_root'],budget)
    workspace, store = Path(binding['workspace_root']), Path(store)
    receipt = store/source['intake_receipt_ref']['path']
    _guard_private_path(store,receipt)
    rid, rows = _receipt_sources(receipt,store,budget)
    if rid != source['source_receipt_id'] or rows != source['sources']:
        raise PrivateRunError('B1_SOURCE_CHANGED')
    if _b1_file_ref(receipt,budget,cap=MAX_RECEIPT_BYTES) != {k:source['intake_receipt_ref'][k] for k in ('sha256','size_bytes')}:
        raise PrivateRunError('B1_RECEIPT_CHANGED')
    for row in source['verified_inbox']:
        path = workspace/row['path']
        _guard_private_path(workspace,path)
        if _b1_file_ref(path,budget) != {k:row[k] for k in ('sha256','size_bytes')}:
            raise PrivateRunError('B1_INBOX_CHANGED')
    tool, inputs, code = _b1_view(selected,budget), _b1_view(workspace,budget), _b1_view(selected,budget,code=True)
    if (tool != binding['tool_input_view'] or inputs != binding['workspace_input_view']
            or code != binding['complete_code_view'] or _b1_cycle(selected,code,budget) != binding['cycle_refs']):
        raise PrivateRunError('B1_PHYSICAL_VIEW_CHANGED')
    identity, run_id = _b1_identity(source['night'],inputs,code,budget)
    if identity != binding['master_identity'] or run_id != binding['master_run_id']:
        raise PrivateRunError('B1_NATIVE_IDENTITY_CHANGED')
    budget.check()


def _b1_binding_shape(source, binding, budget):
    """Structural consistency only; physical preflight remains mandatory."""
    contracts, _ = _b1_modules(budget)
    def fields(value, expected):
        if type(value) is not dict or set(value) != set(expected.split()):
            raise PrivateRunError('B1_FIELDS')
    def sha(value):
        if type(value) is not str or not SHA.fullmatch(value):
            raise PrivateRunError('B1_SHA')
    def path(value):
        if (type(value) is not str or len(value.encode('utf-8')) > 1024 or not value
                or '\\' in value or ':' in value or any(ord(c)<32 or ord(c)==127 for c in value)
                or any(p in ('','.','..') or p.endswith(('.', ' ')) or re.search(r'~[0-9]+(?:\.|$)',p) for p in value.split('/'))):
            raise PrivateRunError('B1_RELATIVE_PATH')
    def ref(value):
        fields(value,'path sha256 size_bytes');path(value['path']);sha(value['sha256'])
        if type(value['size_bytes']) is not int or not 0 <= value['size_bytes'] <= MAX_RAW_BYTES:
            raise PrivateRunError('B1_REF_SIZE')
    def view(value):
        if type(value) is not dict or len(value) > B1_MAX_FILES:
            raise PrivateRunError('B1_VIEW_FIELDS')
        for p, row in value.items():
            path(p);fields(row,'sha256 size_bytes');ref(dict(path=p,**row))
    _b1_canonical(source,budget);_b1_canonical(binding,budget)
    fields(source,'schema night intake_receipt_ref source_receipt_id sources verified_inbox')
    if source['schema'] != 'habu-private-pdca-source-scope-v2':
        raise PrivateRunError('B1_SOURCE_SCHEMA')
    contracts.validate_night(source['night']);sha(source['source_receipt_id']);ref(source['intake_receipt_ref'])
    if not 0 < source['intake_receipt_ref']['size_bytes'] <= MAX_RECEIPT_BYTES:
        raise PrivateRunError('B1_RECEIPT_SIZE')
    rows, inbox = source['sources'], source['verified_inbox']
    if type(rows) is not list or not 1 <= len(rows) <= 2 or type(inbox) is not list or len(inbox) != len(rows):
        raise PrivateRunError('B1_SOURCE_ROWS')
    kinds = set()
    for row, copied in zip(rows,inbox):
        fields(row,'type sha256 size_bytes private_archive');fields(copied,'type path sha256 size_bytes')
        if type(row['type']) is not str or row['type'] not in ('log','gpx') or row['type'] in kinds:
            raise PrivateRunError('B1_SOURCE_KIND')
        kinds.add(row['type']);sha(row['sha256'])
        if (type(row['size_bytes']) is not int or not 0 < row['size_bytes'] <= MAX_RAW_BYTES
                or type(row['private_archive']) is not str or not Path(row['private_archive']).is_absolute()):
            raise PrivateRunError('B1_SOURCE_ROW')
        expected = dict(type=row['type'],path='incoming/private_pdca/'+row['sha256']+('.txt' if row['type']=='log' else '.gpx'),
                        sha256=row['sha256'],size_bytes=row['size_bytes'])
        if copied != expected or type(copied['size_bytes']) is not int:
            raise PrivateRunError('B1_INBOX_ROW')
    if source_receipt_id(rows) != source['source_receipt_id']:
        raise PrivateRunError('B1_SOURCE_ID')
    fields(binding,'schema scope_id revision selected_code_root workspace_root tool_input_view workspace_input_view complete_code_view complete_code_sha256 protocol_policy_refs cycle_refs master_identity master_run_id execution_policy')
    if (binding['schema'] != 'habu-private-pdca-binding-v2' or type(binding['revision']) is not str
            or not re.fullmatch(r'r[1-9][0-9]{0,5}',binding['revision'])):
        raise PrivateRunError('B1_BINDING_SCHEMA')
    if binding['scope_id'] != _b1_hash('habu-private-pdca-source-scope-v2',source,budget):
        raise PrivateRunError('B1_SCOPE_BINDING')
    for name in ('selected_code_root','workspace_root'):
        if type(binding[name]) is not str or not Path(binding[name]).is_absolute():
            raise PrivateRunError('B1_ROOT')
    for name in ('tool_input_view','workspace_input_view','complete_code_view'):
        view(binding[name])
    code = binding['complete_code_view']
    if not 1 <= len(code) <= 256 or sum(v['size_bytes'] for v in code.values()) > 16*1024*1024 or any(v['size_bytes']>4*1024*1024 for v in code.values()):
        raise PrivateRunError('B1_CODE_LIMIT')
    if binding['complete_code_sha256'] != contracts.digest({p:v['sha256'] for p,v in code.items()}):
        raise PrivateRunError('B1_COMPLETE_CODE_HASH')
    fields(binding['cycle_refs'],'pointer manifest policy')
    for value in binding['cycle_refs'].values():ref(value)
    expected_refs = [dict(root=label,path=p,**v) for label,key in (('tool','tool_input_view'),('workspace','workspace_input_view'))
                     for p,v in binding[key].items() if p.startswith(('protocols/','policies/'))]
    if binding['protocol_policy_refs'] != expected_refs:
        raise PrivateRunError('B1_PROTOCOL_REFS')
    ident = binding['master_identity']
    fields(ident,'night inputs code policy runtime inventory_error')
    if (ident['night'] != source['night'] or ident['inputs'] != binding['workspace_input_view'] or ident['inventory_error'] is not None
            or ident['code'] != contracts.digest({p:v['sha256'] for p,v in code.items() if p.endswith('.py') and p.split('/')[0] in ('src','scripts')})
            or binding['master_run_id'] != contracts.digest(ident)):
        raise PrivateRunError('B1_MASTER_IDENTITY')
    policy = binding['execution_policy']
    if type(policy) is not dict or set(policy) != set(B1_EXECUTION_POLICY):
        raise PrivateRunError('B1_EXECUTION_POLICY')
    for key, expected in B1_EXECUTION_POLICY.items():
        if type(policy[key]) is not type(expected) or policy[key] != expected:
            raise PrivateRunError('B1_EXECUTION_POLICY')


def _b1_report(directory, identity, budget):
    """Bound native checkpoint chain only; never B2 terminal/reuse acceptance."""
    contracts, inventory = _b1_modules(budget)
    directory = inventory.local_path(Path(directory))
    def raw(name):
        return _b1_raw(inventory.local_path(directory,name),B1_MAX_JSON,budget)
    before = raw('checkpoint.json')
    cp = _b1_document(before,budget)
    checksum = _b1_document(raw('checkpoint.sha256.json'),budget)
    run_id = contracts.digest(identity)
    def checkpoint_shape(value):
        if (type(value) is not dict or set(value) != {'schema_version','run_id','outputs','elapsed_seconds','round_number','created_at','result_sha256','active_stage','active_since','attempt_deadline'}
                or value['schema_version'] != '1.0' or value['run_id'] != run_id
                or type(value['outputs']) is not dict or len(value['outputs']) > B1_MAX_FILES
                or type(value['round_number']) is not int or not 0 <= value['round_number'] <= 2
                or type(value['elapsed_seconds']) not in (int,float) or value['elapsed_seconds'] > sys.float_info.max
                or not math.isfinite(value['elapsed_seconds']) or value['elapsed_seconds'] < 0):
            raise PrivateRunError('B1_CHECKPOINT_FIELDS')
        for name, sha in value['outputs'].items():
            if type(name) is not str or type(sha) is not str or not SHA.fullmatch(sha):
                raise PrivateRunError('B1_CHECKPOINT_OUTPUT')
        for key in ('created_at','active_since','attempt_deadline'):
            stamp=value[key]
            if stamp is None and key != 'created_at':continue
            if type(stamp) is not str or len(stamp)>128:
                raise PrivateRunError('B1_CHECKPOINT_TIME')
            try:
                aware=datetime.fromisoformat(stamp).utcoffset() is not None
            except ValueError as exc:
                raise PrivateRunError('B1_CHECKPOINT_TIME') from exc
            if not aware:raise PrivateRunError('B1_CHECKPOINT_TIME')
        if value['active_stage'] is not None and value['active_stage'] not in contracts.STAGE_NAMES:
            raise PrivateRunError('B1_CHECKPOINT_STAGE')
        if value['result_sha256'] is not None and (type(value['result_sha256']) is not str or not SHA.fullmatch(value['result_sha256'])):
            raise PrivateRunError('B1_CHECKPOINT_RESULT')
    checkpoint_shape(cp)
    if (type(cp) is not dict or cp.get('run_id') != run_id or type(checksum) is not dict
            or checksum != {'sha256':contracts.digest(cp)} or type(cp.get('outputs')) is not dict):
        raise PrivateRunError('B1_CHECKPOINT_CHAIN')
    names = set(cp['outputs']) | {'checkpoint.json','checkpoint.sha256.json','evidence_manifest.json','finalization_checkpoint.json','run_manifest.json'}
    if len(names) > B1_MAX_FILES:
        raise PrivateRunError('B1_REPORT_FILE_LIMIT')
    view, total = {}, 0
    for name in sorted(names):
        if type(name) is not str:
            raise PrivateRunError('B1_REPORT_PATH')
        path = inventory.local_path(directory,name)
        size = path.lstat().st_size
        if size > B1_MAX_JSON or total+size > B1_MAX_REPORT:
            raise PrivateRunError('B1_REPORT_BYTES_LIMIT')
        ref = _b1_file_ref(path,budget,cap=B1_MAX_JSON)
        if name in cp['outputs'] and cp['outputs'][name] != ref['sha256']:
            raise PrivateRunError('B1_REPORT_CHANGED')
        view[name] = ref
        total += size
    evidence = _b1_document(raw('evidence_manifest.json'),budget)
    finalization = _b1_document(raw('finalization_checkpoint.json'),budget)
    checkpoint_shape(finalization)
    if (finalization['outputs'] != {p:h for p,h in cp['outputs'].items() if p!='finalization_checkpoint.json'}
            or finalization['result_sha256'] is not None or finalization['round_number'] != cp['round_number']
            or finalization['created_at'] != cp['created_at'] or finalization['elapsed_seconds']>cp['elapsed_seconds']):
        raise PrivateRunError('B1_FINALIZATION_CHAIN')
    result = _b1_document(raw('run_manifest.json'),budget)
    expected = [('run_id',run_id),('operational_night',identity['night']),('code_sha256',identity['code']),
                ('policy_sha256',contracts.digest(identity['policy'])),('runtime',identity['runtime']),
                ('input_manifest_sha256',contracts.digest(evidence)),('checkpoint_sha256',contracts.digest(finalization))]
    if type(result) is not dict or any(result.get(k) != v for k,v in expected):
        raise PrivateRunError('B1_RESULT_BINDING')
    if (view['run_manifest.json']['sha256'] != cp.get('result_sha256') or type(evidence) is not dict
            or evidence.get('input_snapshot_sha256') != contracts.digest(identity['inputs'])):
        raise PrivateRunError('B1_RESULT_CHECKPOINT')
    entries = evidence.get('entries')
    if type(entries) is not list or len(entries) != len(identity['inputs']):
        raise PrivateRunError('B1_EVIDENCE_MEMBERSHIP')
    projected = {}
    for row in entries:
        if (type(row) is not dict or type(row.get('path')) is not str or row['path'] in projected
                or type(row.get('size_bytes')) is not int or row['size_bytes']<0
                or type(row.get('sha256')) is not str or not SHA.fullmatch(row['sha256'])):
            raise PrivateRunError('B1_EVIDENCE_MEMBERSHIP')
        projected[row['path']] = {k:row.get(k) for k in ('sha256','size_bytes')}
    if projected != identity['inputs']:
        raise PrivateRunError('B1_EVIDENCE_MEMBERSHIP')
    stages = result.get('stages')
    if (type(stages) is not list or len(stages) != len(contracts.STAGE_NAMES)
            or {s.get('name') for s in stages if type(s) is dict} != set(contracts.STAGE_NAMES)):
        raise PrivateRunError('B1_RESULT_STAGES')
    for stage in stages:
        _b1_canonical(stage,budget)
        contracts.validate_stage(stage,stage['name'])
        wrapper=_b1_document(raw('stages/'+stage['name']+'.json'),budget)
        if (type(wrapper) is not dict or set(wrapper) != {'stage','payload'}
                or _b1_canonical(wrapper['stage'],budget) != _b1_canonical(stage,budget)):
            raise PrivateRunError('B1_STAGE_WRAPPER_CHANGED')
    if (contracts.overall_status(stages) != result.get('overall_status') or type(result.get('completed')) is not bool
            or result['completed'] != (result['overall_status'] == 'PASS')):
        raise PrivateRunError('B1_RESULT_AGGREGATE')
    actual = _b1_view(directory,budget,whole=True)
    expected_members = names | {'snapshot/'+p for p in identity['inputs']}
    if set(actual) != expected_members:
        raise PrivateRunError('B1_UNCOMMITTED_REPORT_ARTIFACT')
    for path, ref in identity['inputs'].items():
        if actual.get('snapshot/'+path) != ref:
            raise PrivateRunError('B1_SNAPSHOT_CHANGED')
    for name, ref in view.items():
        if actual[name] != ref:
            raise PrivateRunError('B1_REPORT_CHANGED')
    if raw('checkpoint.json') != before:
        raise PrivateRunError('B1_CHECKPOINT_CHANGED')
    return {'state':'NATIVE_CHAIN_ONLY_B2_NOT_INSTALLED','result':result,'view':view,
            'report_view_sha256':_b1_hash('habu-private-pdca-report-view-v2',view,budget)}


def _b1_publish(store, path, raw, budget):
    """Published source/binding is shared forever; only the temp is cleaned."""
    _guard_private_path(store, path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _guard_private_path(store, path)
    temp = identity = None
    try:
        with NamedTemporaryFile(dir=path.parent, prefix='.b1-pending-', delete=False) as stream:
            temp = Path(stream.name)
            info = os.fstat(stream.fileno())
            identity = (info.st_dev, info.st_ino)
            _guard_private_path(store, temp)
            os.chmod(temp, 0o600)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        _guard_private_path(store, path)
        budget.check()
        try:
            os.link(temp, path)
        except FileExistsError:
            pass
        _guard_private_path(store, path)
        if _b1_raw(path, B1_MAX_JSON, budget) != raw:
            raise PrivateRunError('B1_IMMUTABLE_CONFLICT')
    finally:
        _cleanup_owned_temp(store, temp, identity, sys.exception())


def _b1_history(base, budget):
    """No absent-active shortcut; no claimed B2 completion checker exists yet."""
    base = Path(base)
    _guard_private_path(base.parent, base)
    if not base.exists():
        return []
    names = []
    with os.scandir(base) as iterator:
        for entry in iterator:
            budget.check()
            if len(names) >= B1_MAX_ENTRIES:
                raise PrivateRunError('B1_HISTORY_LIMIT')
            names.append(entry.name)
    if 'active.json' in names:
        raise PrivateRunError('B1_BUSY_OR_INCOMPLETE')
    if set(names) - {'source.json', 'attempts'}:
        raise PrivateRunError('B1_UNKNOWN_SCOPE_STATE')
    if 'source.json' in names:
        _guard_private_path(base, base/'source.json')
        _b1_document(_b1_raw(base/'source.json', B1_MAX_JSON, budget), budget)
    attempts = base/'attempts'
    if not attempts.exists():
        if names:
            raise PrivateRunError('B1_INCOMPLETE_ATTEMPT')
        return []
    _guard_private_path(base, attempts)
    seen = 0
    with os.scandir(attempts) as iterator:
        for entry in iterator:
            budget.check()
            seen += 1
            if seen > B1_MAX_FILES:
                raise PrivateRunError('B1_HISTORY_LIMIT')
            if not SHA.fullmatch(entry.name):
                raise PrivateRunError('B1_UNKNOWN_ATTEMPT')
            directory = attempts/entry.name
            _guard_private_path(base, directory)
            if not entry.is_dir(follow_symlinks=False):
                raise PrivateRunError('B1_UNKNOWN_ATTEMPT')
            for name in ('binding.json', 'claim.json', 'terminal.json'):
                path = directory/name
                _guard_private_path(base, path)
                if not path.exists():
                    raise PrivateRunError('B1_INCOMPLETE_ATTEMPT')
                _b1_document(_b1_raw(path, B1_MAX_JSON, budget), budget)
            # Never accept caller-declared B2 evidence or mint a completed reuse.
            raise PrivateRunError('B1_B2_REQUIRED: terminal evidence not accepted by B1')
    if 'source.json' in names:
        raise PrivateRunError('B1_INCOMPLETE_ATTEMPT')
    return []


def _b1_claim_files(store, scope_id, attempt_id, source, binding, revision, budget):
    """Low-level reservation only; not source validation/execution/completion."""
    if not SHA.fullmatch(scope_id) or not SHA.fullmatch(attempt_id) or not re.fullmatch(r'r[1-9][0-9]{0,5}', revision):
        raise PrivateRunError('B1_CLAIM_ID')
    store = Path(store)
    base = store/'private_pdca_runs'/'v2'/'scopes'/scope_id
    _guard_private_path(store, base)
    _b1_history(base, budget)
    _b1_binding_shape(source,binding,budget)
    if binding['scope_id'] != scope_id or binding['revision'] != revision:
        raise PrivateRunError('B1_CLAIM_BINDING')
    legacy = store/'private_pdca_runs'/(hashlib.sha256((source['night']+':'+source['source_receipt_id']).encode()).hexdigest()+'.json')
    _guard_private_path(store,legacy)
    if legacy.exists():
        raise PrivateRunError('B1_LEGACY_UNBOUND')
    if revision != 'r1':
        raise PrivateRunError('B1_B2_REQUIRED: new revision requires accepted prior evidence')
    source_raw = _b1_canonical(source, budget)
    binding_raw = _b1_canonical(binding, budget)
    binding_sha = _b1_hash('habu-private-pdca-binding-v2', binding, budget)
    if scope_id != _b1_hash('habu-private-pdca-source-scope-v2', source, budget):
        raise PrivateRunError('B1_SOURCE_SCOPE_MISMATCH')
    if attempt_id != _b1_hash('habu-private-pdca-attempt-v2',
                            {'scope_id':scope_id, 'revision':revision, 'binding_sha256':binding_sha}, budget):
        raise PrivateRunError('B1_ATTEMPT_MISMATCH')
    _b1_publish(store, base/'source.json', source_raw, budget)
    directory = base/'attempts'/attempt_id
    _b1_publish(store, directory/'binding.json', binding_raw, budget)
    claim = {'schema':'habu-private-pdca-claim-v2','scope_id':scope_id,'attempt_id':attempt_id,
             'revision':revision,'binding_sha256':binding_sha,'claim_nonce':secrets.token_hex(16),
             'created_at_utc':datetime.now(timezone.utc).isoformat(),'phase':'RESERVED_PRESPAWN'}
    raw = _b1_canonical(claim, budget)
    temp = identity = None
    active_created = False
    try:
        # The only new state allowed since preflight is this call's own publication.
        def names(path):
            _guard_private_path(store,path)
            result = set()
            with os.scandir(path) as iterator:
                for entry in iterator:
                    budget.check()
                    if len(result) >= B1_MAX_ENTRIES:
                        raise PrivateRunError('B1_HISTORY_LIMIT')
                    _guard_private_path(store,path/entry.name)
                    result.add(entry.name)
            return result
        if (names(base) != {'source.json','attempts'} or names(base/'attempts') != {attempt_id}
                or names(directory) != {'binding.json'}):
            raise PrivateRunError('B1_LATE_SCOPE_STATE')
        if (_b1_raw(base/'source.json',B1_MAX_JSON,budget) != source_raw
                or _b1_raw(directory/'binding.json',B1_MAX_JSON,budget) != binding_raw):
            raise PrivateRunError('B1_LATE_BINDING_CHANGED')
        with NamedTemporaryFile(dir=directory, prefix='.b1-claim-', delete=False) as stream:
            temp = Path(stream.name)
            info = os.fstat(stream.fileno())
            identity = (info.st_dev, info.st_ino)
            os.chmod(temp, 0o600)
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        _guard_private_path(store, base/'active.json')
        budget.check()
        try:
            os.link(temp, base/'active.json')
            active_created = True
        except FileExistsError as exc:
            raise PrivateRunError('B1_CLAIM_CONFLICT') from exc
        _guard_private_path(store, directory/'claim.json')
        os.link(temp, directory/'claim.json')
        if (_b1_raw(base/'active.json', B1_MAX_JSON, budget) != raw or
                _b1_raw(directory/'claim.json', B1_MAX_JSON, budget) != raw):
            raise PrivateRunError('B1_CLAIM_READBACK')
        budget.check()
        return {'state':'RESERVED_ONLY_B2_NOT_INSTALLED','claim':claim,'base':str(base)}
    except BaseException:
        if active_created:
            _cleanup_owned_temp(store, base/'active.json', identity, sys.exception())
        raise
    finally:
        _cleanup_owned_temp(store, temp, identity, sys.exception())


def _b1_reserve(prepared, store, budget):
    """Recheck the physical preparation immediately before private reservation."""
    if type(prepared) is not dict or set(prepared) != {'source','binding','scope_id','attempt_id','state'}:
        raise PrivateRunError('B1_PREPARATION_FIELDS')
    if prepared['state'] != 'BINDING_ONLY_NO_EXECUTION':
        raise PrivateRunError('B1_PREPARATION_STATE')
    _b1_recheck(prepared['source'],prepared['binding'],store,budget)
    return _b1_claim_files(Path(store),prepared['scope_id'],prepared['attempt_id'],prepared['source'],
                           prepared['binding'],prepared['binding']['revision'],budget)


def _guard_private_path(root: Path, path: Path) -> None:
    try:
        guard_private_path(root, path)
    except IntakeError as exc:
        raise PrivateRunError(str(exc)) from exc


def _cleanup_owned_temp(root, temp, identity, primary):
    try:
        cleanup_owned_temp(root, temp, identity, primary)
    except IntakeError as exc:
        raise PrivateRunError(str(exc)) from exc


def _is_under(path: Path, base: Path) -> bool:
    return path == base or base in path.parents


def _validate_roots(code_root: Path, workspace: Path, store: Path) -> tuple[Path, Path, Path]:
    code_root = code_root.resolve(strict=True)
    workspace = workspace.resolve(strict=True)
    store = store.resolve(strict=True)
    if not (code_root / "scripts" / "run_pdca.py").is_file():
        raise PrivateRunError("Canonical PDCA script unavailable")
    for private in (workspace, store):
        if _is_under(private, code_root) or _is_under(code_root, private):
            raise PrivateRunError("Refusing a private path overlapping repository code")
        if os.name == "posix" and private.stat().st_mode & 0o077:
            raise PrivateRunError("Private directory accessible by group/other")
    if workspace == store or _is_under(workspace, store) or _is_under(store, workspace):
        raise PrivateRunError("Source store and scientific workspace must be separate")
    return code_root, workspace, store


def _sha(path: Path, budget: _ReadBudget, *, size=None) -> str:
    return _digest(path, budget, expected_size=size)[0]


def _receipt_json(path: Path, budget: _ReadBudget):
    raw = _read_bytes(path, MAX_RECEIPT_BYTES, budget)
    # Bound nesting before json's recursive decoder; escaped string delimiters do not count.
    depth = 0
    quoted = escaped = False
    for offset, value in enumerate(raw):
        if offset % 1024 == 0:
            budget.check()
        if quoted:
            if escaped:
                escaped = False
            elif value == 92:
                escaped = True
            elif value == 34:
                quoted = False
        elif value == 34:
            quoted = True
        elif value in (91, 123):
            depth += 1
            if depth > 64:
                raise PrivateRunError("Receipt nesting capacity exceeded")
        elif value in (93, 125):
            depth -= 1
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise PrivateRunError("Invalid intake receipt JSON") from exc
    budget.check()
    return result


def _receipt_sources(receipt_path: Path, store: Path, budget: _ReadBudget) -> tuple[str, list[dict]]:
    _guard_private_path(store, receipt_path)
    receipt_path = receipt_path.resolve(strict=True)
    if not _is_under(receipt_path, store):
        raise PrivateRunError("Receipt outside private source store")
    manifest = _receipt_json(receipt_path, budget)
    fields = {"schema", "receipt_id", "sources", "log_diagnostic", "pdca",
              "model_validation", "official_p0", "negative_labels"}
    if (not isinstance(manifest, dict) or set(manifest) != fields or
            manifest["schema"] != "habu-private-intake-v1" or
            not isinstance(manifest["log_diagnostic"], dict) or
            manifest["pdca"] != "NOT_RUN" or manifest["model_validation"] != "NOT_RUN" or
            manifest["official_p0"] != "NOT_CHECKED" or manifest["negative_labels"] != "NOT_CERTIFIED"):
        raise PrivateRunError("Invalid intake receipt schema")
    receipt_id = manifest.get("receipt_id")
    if not isinstance(receipt_id, str) or not SHA.fullmatch(receipt_id):
        raise PrivateRunError("Invalid receipt identifier")
    rows = manifest.get("sources")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 2:
        raise PrivateRunError("Missing original sources")
    seen = set()
    for row in rows:
        budget.check()
        if not isinstance(row, dict) or set(row) != {"type", "sha256", "size_bytes", "private_archive"}:
            raise PrivateRunError("Invalid source row schema")
        kind = row.get("type")
        digest = row.get("sha256")
        if kind not in ("log", "gpx") or not isinstance(digest, str) or not SHA.fullmatch(digest):
            raise PrivateRunError("Invalid source manifest entry")
        if kind in seen:
            raise PrivateRunError("Duplicate source kind")
        seen.add(kind)
        size, archive = row["size_bytes"], row["private_archive"]
        if type(size) is not int or not 0 < size <= MAX_RAW_BYTES:
            raise PrivateRunError("Invalid source size")
        if not isinstance(archive, str) or not archive or not Path(archive).is_absolute():
            raise PrivateRunError("Invalid source archive path")
    if source_receipt_id(rows) != receipt_id:
        raise PrivateRunError("Receipt identifier does not bind source rows")
    for row in rows:
        budget.check()
        target = Path(row["private_archive"])
        _guard_private_path(store, target)
        if target.is_symlink():
            raise PrivateRunError("Symlink source forbidden")
        target = target.resolve(strict=True)
        if not _is_under(target, store) or not target.is_file():
            raise PrivateRunError("Source outside private store")
        if _sha(target, budget, size=row["size_bytes"]) != row["sha256"]:
            raise PrivateRunError("Source integrity mismatch")
    return receipt_id, rows


def _copy_verified(source: Path, dest: Path, digest: str, allowed_root: Path,
                   budget: _ReadBudget, size: int) -> None:
    budget.check()
    _guard_private_path(allowed_root, dest)
    dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _guard_private_path(allowed_root, dest)
    real_parent = dest.parent.resolve(strict=True)
    if not _is_under(real_parent, allowed_root):
        raise PrivateRunError("Inbox escapes private workspace")
    if dest.is_symlink():
        raise PrivateRunError("Symlink destination forbidden")
    if dest.exists():
        if _sha(dest, budget, size=size) != digest:
            raise PrivateRunError("Scientific inbox collision")
        return
    tmp = None
    temp_identity = None
    try:
        with NamedTemporaryFile(dir=dest.parent, delete=False) as f:
            tmp = Path(f.name)
            opened = os.fstat(f.fileno())
            temp_identity = (opened.st_dev, opened.st_ino)
            _guard_private_path(allowed_root, tmp)
            os.chmod(tmp, 0o600)
            for part in _chunks(source, MAX_RAW_BYTES, budget, expected_size=size):
                f.write(part)
            f.flush()
            os.fsync(f.fileno())
        _guard_private_path(allowed_root, tmp)
        if _sha(tmp, budget, size=size) != digest:
            raise PrivateRunError("Copy integrity mismatch")
        try:
            _guard_private_path(allowed_root, dest)
            budget.check()
            os.link(tmp, dest)
        except FileExistsError:
            _guard_private_path(allowed_root, dest)
            if _sha(dest, budget, size=size) != digest:
                raise PrivateRunError("Concurrent inbox collision")
        if _sha(dest, budget, size=size) != digest:
            raise PrivateRunError("Published inbox conflict")
    finally:
        _cleanup_owned_temp(allowed_root, tmp, temp_identity, sys.exception())


def run_private(code_root: Path, workspace: Path, store: Path,
                receipt_path: Path, night: str, timeout_seconds: int = 330) -> dict:
    budget = _ReadBudget(timeout_seconds, maximum=330, error_type=PrivateRunError)
    if not NIGHT.fullmatch(night):
        raise PrivateRunError("Invalid operational-night identifier")
    code_root, workspace, store = _validate_roots(code_root, workspace, store)
    receipt_id, rows = _receipt_sources(receipt_path, store, budget)
    identity = hashlib.sha256(f"{night}:{receipt_id}".encode()).hexdigest()
    outdir = store / "private_pdca_runs"
    dest = outdir / f"{identity}.json"
    _guard_private_path(store, dest)
    for row in rows:
        digest = row["sha256"]
        kind = row["type"]
        extension = ".txt" if kind == "log" else ".gpx"
        _copy_verified(Path(row["private_archive"]),
                       workspace / "incoming" / "private_pdca" / (digest + extension),
                       digest, workspace, budget, row["size_bytes"])
    command = [sys.executable, str(code_root / "scripts" / "run_pdca.py"),
               "--root", str(workspace), "--night", night]
    # The engine sees a private workspace, not the public repository checkout.
    outcome = "NOT_RUN"
    overall = "BLOCKED"
    try:
        proc = subprocess.run(command, cwd=workspace, capture_output=True,
                              timeout=budget.remaining_seconds(), check=False)
        budget.check()
        output = json.loads(proc.stdout.decode("utf-8"))
        outcome = str(output.get("overall_status", "INVALID_OUTPUT"))
        if outcome not in {"PASS", "PARTIAL", "BLOCKED", "FAIL", "NOT_VALIDATED"}:
            outcome = "INVALID_OUTPUT"
        overall = "PARTIAL" if proc.returncode == 0 else "BLOCKED"
    except (subprocess.TimeoutExpired, UnicodeError, json.JSONDecodeError, OSError):
        outcome = "RUNNER_FAILURE"
        overall = "BLOCKED"
    # Private intake is not canonically admitted evidence and thus never itself proves KPI.
    record = {"schema": "habu-private-pdca-run-v1", "night": night,
              "source_receipt_id": receipt_id, "source_sha256": [r["sha256"] for r in rows],
              "backend_status": outcome, "overall_status": overall,
              "raw_inbox_only": True, "source_eligible_for_model": False,
              "p0_frozen_score": "NOT_CERTIFIED", "p1_scores": "NOT_CERTIFIED",
              "model_validation": "NOT_CERTIFIED", "champion_promotion": "FORBIDDEN",
              "next": "Complete canonical source-admission audit, then rerun existing engine"}
    _guard_private_path(store, dest)
    outdir.mkdir(mode=0o700, parents=True, exist_ok=True)
    _guard_private_path(store, dest)
    if dest.exists() and not dest.is_file():
        raise PrivateRunError("Result receipt is not a regular file")
    previous = _receipt_json(dest, budget) if dest.exists() else None
    if previous and previous != record:
        raise PrivateRunError("Non-identical scientific retry: retain old run, use versioned attempt")
    if not previous:
        data = _encoded_report(record, budget)
        tmp = None
        temp_identity = None
        try:
            with NamedTemporaryFile(dir=outdir, delete=False) as file:
                tmp = Path(file.name)
                opened = os.fstat(file.fileno())
                temp_identity = (opened.st_dev, opened.st_ino)
                _guard_private_path(store, tmp)
                os.chmod(tmp, 0o600)
                file.write(data)
                file.flush()
                os.fsync(file.fileno())
            try:
                _guard_private_path(store, dest)
                budget.check()
                os.link(tmp, dest)
            except FileExistsError:
                _guard_private_path(store, dest)
                if _read_bytes(dest, MAX_RECEIPT_BYTES, budget) != data:
                    raise PrivateRunError("Concurrent result conflict")
            if _read_bytes(dest, MAX_RECEIPT_BYTES, budget) != data:
                raise PrivateRunError("Published result conflict")
        finally:
            _cleanup_owned_temp(store, tmp, temp_identity, sys.exception())
    budget.check()
    return {"run_receipt": identity, "backend_status": outcome,
            "overall_status": overall, "p0": "NOT_CERTIFIED",
            "model_validation": "NOT_CERTIFIED"}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--code-root", type=Path, required=True)
    p.add_argument("--private-workspace", type=Path, required=True)
    p.add_argument("--private-store", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--night", required=True)
    a = p.parse_args()
    print(json.dumps(run_private(a.code_root, a.private_workspace, a.private_store,
                                 a.receipt, a.night), ensure_ascii=False))


if __name__ == "__main__":
    main()
