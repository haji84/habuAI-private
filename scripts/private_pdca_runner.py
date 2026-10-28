"""Private-source runner for the existing, single-entry Habu PDCA engine.

This adapter intentionally does not declare imported raw files eligible scientific data.
Run receipts and stdout logs remain within a private filesystem outside GitHub.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import importlib
import json
import math
import os
import re
import secrets
import selectors
import signal
import stat
import subprocess
import sys
import threading
import time
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


class _B2NativeRejected(PrivateRunError):
    """A locally established native admission contradiction, not a read error."""


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


def _b1_document(raw, budget, *, error_type=PrivateRunError):
    """Bound tokens/nesting before the decoder allocates its object graph."""
    if type(raw) is not bytes or len(raw) > B1_MAX_JSON:
        raise error_type('B1_JSON_LIMIT')
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
            raise error_type('B1_JSON_STRUCTURE_LIMIT')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise error_type('B1_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def nonfinite(_):
        raise error_type('B1_NONFINITE_JSON')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=nonfinite)
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, PrivateRunError):
            raise
        raise error_type('B1_INVALID_JSON') from exc
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


def _b1_raw(path, cap, budget, *, expected_size=None):
    """A owns positive reads; inventory empties need a genuine checked EOF."""
    path = Path(path)
    budget.check()
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise PrivateRunError('B1_NONREGULAR_FILE')
    if expected_size is not None and (type(expected_size) is not int or expected_size < 0 or info.st_size != expected_size):
        raise PrivateRunError('B1_ORIGINAL_SIZE_CHANGED')
    if info.st_size:
        if expected_size is not None:
            data = bytearray()
            for chunk in _chunks(path,cap,budget,expected_size=expected_size):
                data.extend(chunk)
            budget.check()
            return bytes(data)
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


def _b1_file_ref(path, budget, *, cap=MAX_RAW_BYTES, expected_size=None):
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise PrivateRunError('B1_NONREGULAR_FILE')
    if expected_size is not None and (type(expected_size) is not int or expected_size < 0 or info.st_size != expected_size):
        raise PrivateRunError('B1_ORIGINAL_SIZE_CHANGED')
    if info.st_size > cap:
        raise PrivateRunError('B1_FILE_LIMIT')
    h = hashlib.sha256()
    if info.st_size == 0:
        h.update(_b1_raw(path, cap, budget, expected_size=0))
    else:
        for chunk in _chunks(path, cap, budget, expected_size=info.st_size):
            h.update(chunk)
    budget.check()
    return {'sha256': h.hexdigest(), 'size_bytes': info.st_size}


def _b1_view(root, budget, *, code=False, whole=False, expected=None):
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
        if expected is not None and relative not in expected:
            raise PrivateRunError('B2_UNEXPECTED_MEMBER')
        if len(result) >= min(B1_MAX_FILES, 256 if code else B1_MAX_FILES):
            raise PrivateRunError('B1_VIEW_FILE_LIMIT')
        if len(relative.encode('utf-8')) > 1024:
            raise PrivateRunError('B1_PATH_LIMIT')
        cap = 4*1024*1024 if code else B1_MAX_JSON if path.suffix == '.json' else MAX_RAW_BYTES
        declared = path.lstat().st_size
        if expected is not None and declared != expected[relative]['size_bytes']:
            raise PrivateRunError('B2_ORIGINAL_SIZE_CHANGED')
        if code and total + declared > 16*1024*1024:
            raise PrivateRunError('B1_CODE_TOTAL_LIMIT')
        row = _b1_file_ref(path, budget, cap=cap, expected_size=declared)
        if expected is not None and row != expected[relative]:
            raise PrivateRunError('B2_ORIGINAL_MEMBER_CHANGED')
        if code and total + row['size_bytes'] > 16*1024*1024:
            raise PrivateRunError('B1_CODE_TOTAL_LIMIT')
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
    if expected is not None and set(result) != set(expected):
        raise PrivateRunError('B2_MISSING_MEMBER')
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
        ref = _b1_file_ref(path,budget,cap=B1_MAX_JSON,expected_size=size)
        if total+ref['size_bytes'] > B1_MAX_REPORT:
            raise PrivateRunError('B1_REPORT_BYTES_LIMIT')
        if name in cp['outputs'] and cp['outputs'][name] != ref['sha256']:
            raise PrivateRunError('B1_REPORT_CHANGED')
        view[name] = ref
        total += ref['size_bytes']
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
    _b1_binding_shape(source,binding,budget)
    prior_ids=set()
    if revision=='r1':
        _b1_history(base,budget)
    else:
        old=_b2_history(store,dict(source=source,binding=binding,scope_id=scope_id,attempt_id=attempt_id),budget)
        if not old:raise PrivateRunError('B2_REVISION_REQUIRES_PRIOR_TERMINAL')
        _b2_revision_guard(old,binding,attempt_id)
        prior_ids={row['claim']['attempt_id'] for row in old}
    if binding['scope_id'] != scope_id or binding['revision'] != revision:
        raise PrivateRunError('B1_CLAIM_BINDING')
    legacy = store/'private_pdca_runs'/(hashlib.sha256((source['night']+':'+source['source_receipt_id']).encode()).hexdigest()+'.json')
    _guard_private_path(store,legacy)
    if legacy.exists():
        raise PrivateRunError('B1_LEGACY_UNBOUND')
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
        if (names(base) != {'source.json','attempts'} or names(base/'attempts') != prior_ids|{attempt_id}
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
        # fsync can outlast the earlier scan. Recheck after it, admitting only
        # this still-owned claim temp; shared publications are never rolled back.
        _guard_private_path(store,temp)
        current = temp.lstat()
        if not stat.S_ISREG(current.st_mode) or (current.st_dev,current.st_ino) != identity:
            raise PrivateRunError('B1_CLAIM_TEMP_CHANGED')
        if (_b1_raw(base/'source.json',B1_MAX_JSON,budget) != source_raw
                or _b1_raw(directory/'binding.json',B1_MAX_JSON,budget) != binding_raw):
            raise PrivateRunError('B1_LATE_BINDING_CHANGED')
        if (names(base) != {'source.json','attempts'} or names(base/'attempts') != prior_ids|{attempt_id}
                or names(directory) != {'binding.json',temp.name}):
            raise PrivateRunError('B1_LATE_SCOPE_STATE')
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


B2_META_BYTES = 64*1024
B2_STDOUT_BYTES = 5*1024*1024
B2_STDERR_BYTES = 1024*1024
B2_TERM_SECONDS = 5
B2_PERSIST_SECONDS = 20
B2_FLAGS = {'source_eligible_for_model':False,'p0_certified':False,
            'model_validation_certified':False,'champion_activation':False}


def _b2_capability(budget):
    budget.check()
    if (os.name != 'posix' or any(not hasattr(os,n) for n in ('waitid','waitpid','WNOWAIT','WNOHANG','WEXITED','P_PID','getpgid','killpg','set_blocking','waitstatus_to_exitcode'))
            or threading.current_thread() is not threading.main_thread() or len(threading.enumerate()) != 1
            or signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL):
        raise PrivateRunError('B2_NOT_STARTED_CAPABILITY: genuine exclusive POSIX waiter required')


def _b2_metadata(value,budget):
    # Preflight the tighter metadata cap before the canonical owned copy.
    length=0
    for piece in json.JSONEncoder(sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).iterencode(value):
        budget.check()
        for start in range(0,len(piece),4096):
            length+=len(piece[start:start+4096].encode('utf-8'))
            if length+1>B2_META_BYTES:raise PrivateRunError('B2_METADATA_LIMIT')
    return _b1_canonical(value,budget)+b'\n'


def _b2_capture(argv,cwd,store,directory,budget,run_deadline,cleanup_deadline):
    """One genuine POSIX process; no reaping before the final group signal."""
    _b2_capability(budget)
    selector=selectors.DefaultSelector()
    process=None;pid=pgid=None;reaped=False;signals=[];streams={};opened=[]
    reason='NATIVE_EXIT';origin='NONE';spawn='SPAWNED';returncode=None
    started=datetime.now(timezone.utc).isoformat();at_spawn=budget.bytes_read
    after_capture=at_spawn;capture_bytes=0;cleanup_ok=False
    def own():
        _b2_capability(budget)
        observed=os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
        if ((observed is not None and observed.si_pid != pid) or os.getpgid(pid)!=pgid or pgid!=pid):
            raise PrivateRunError('B2_GROUP_OWNERSHIP_UNPROVEN')
        return observed
    def send(sig):
        own()
        if time.monotonic()>=cleanup_deadline:raise PrivateRunError('B2_CLEANUP_DEADLINE')
        event={'signal':int(sig),'at_monotonic_ns':time.monotonic_ns(),'result':'SENT'}
        if event['at_monotonic_ns']>=int(cleanup_deadline*10**9):raise PrivateRunError('B2_CLEANUP_DEADLINE')
        try:os.killpg(pgid,sig)
        except ProcessLookupError:event['result']='ESRCH'
        except OSError:
            event['result']='OS_ERROR';signals.append(event);raise
        signals.append(event)
        return event['result']
    def absent():
        try:os.killpg(pgid,0)
        except ProcessLookupError:return True
        except OSError:return False
        return False
    def close_process():
        nonlocal reaped,returncode
        if process is None:return
        # The unreaped leader reserves this generation through both signals.
        if send(signal.SIGTERM)!='ESRCH':
            grace=min(cleanup_deadline,time.monotonic()+1)
            while time.monotonic()<grace and not absent():
                own();time.sleep(min(.02,max(0,grace-time.monotonic())))
            if not absent():send(signal.SIGKILL)
        # Mutating group signals are permanently over before the first reap.
        while time.monotonic()<cleanup_deadline:
            budget.check()
            found,status=os.waitpid(pid,os.WNOHANG)
            if found==pid:
                reaped=True;returncode=os.waitstatus_to_exitcode(status)
                process.returncode=returncode
                break
            time.sleep(min(.02,max(0,cleanup_deadline-time.monotonic())))
        if not reaped:raise PrivateRunError('B2_CHILD_UNREAPED')
        while time.monotonic()<cleanup_deadline and not absent():
            budget.check();time.sleep(min(.02,max(0,cleanup_deadline-time.monotonic())))
        if not absent():raise PrivateRunError('B2_GROUP_ABSENCE_UNPROVEN')
    primary=None
    try:
        streamdir=directory/'streams';_guard_private_path(store,streamdir)
        streamdir.mkdir(mode=0o700,parents=True,exist_ok=True);_guard_private_path(store,streamdir)
        for name,cap in (('stdout',B2_STDOUT_BYTES),('stderr',B2_STDERR_BYTES)):
            f=NamedTemporaryFile(dir=streamdir,prefix='.capture-',delete=False)
            opened.append(f)
            info=os.fstat(f.fileno())
            streams[name]={'temp':Path(f.name),'identity':(info.st_dev,info.st_ino),'file':f,'cap':cap,
                           'observed':0,'retained':0,'hash':hashlib.sha256(),'eof':False,'overflow':False}
            os.chmod(f.name,0o600)
        budget.check();at_spawn=budget.bytes_read
        try:
            process=subprocess.Popen(argv,cwd=cwd,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                     shell=False,close_fds=True,start_new_session=True)
        except OSError:
            spawn='SPAWN_FAILED';reason='SPAWN_FAILURE';origin='OS_SPAWN_OR_EXIT'
        if process is not None:
            pid=process.pid;pgid=os.getpgid(pid)
            own()
            for name,pipe in (('stdout',process.stdout),('stderr',process.stderr)):
                os.set_blocking(pipe.fileno(),False);selector.register(pipe,selectors.EVENT_READ,name)
            turn=0
            while True:
                budget.check()
                if time.monotonic()>=run_deadline:
                    reason='OWNED_TIMEOUT';origin='CLOSED_TIMER_OBSERVATION';break
                observed=own()
                if not selector.get_map() and observed is not None:break
                events=selector.select(min(.05,max(0,run_deadline-time.monotonic())))
                if turn%2:events.reverse()
                turn+=1
                stop=False
                for key,_ in events:
                    row=streams[key.data]
                    budget.check()
                    amount=min(65536,row['cap']-row['observed'],2147483648-budget.bytes_read)+1
                    try:chunk=os.read(key.fd,max(1,amount))
                    except (BlockingIOError,InterruptedError):continue
                    budget.bytes_read+=len(chunk);capture_bytes+=len(chunk);row['observed']+=len(chunk)
                    budget.check()
                    if not chunk:
                        row['eof']=True;selector.unregister(key.fileobj);continue
                    keep=chunk[:max(0,row['cap']-row['retained'])]
                    row['file'].write(keep);row['hash'].update(keep);row['retained']+=len(keep)
                    if row['observed']>row['cap']:
                        row['overflow']=True;reason=key.data.upper()+'_CAPACITY';origin='CLOSED_PIPE_READ_OBSERVATION';stop=True;break
                if stop:break
            after_capture=budget.bytes_read
            if after_capture!=at_spawn+capture_bytes:raise PrivateRunError('B2_CAPTURE_LEDGER_DRIFT')
            close_process()
            if reason=='NATIVE_EXIT' and returncode is not None and returncode<0:
                reason='CHILD_SIGNAL';origin='OS_SPAWN_OR_EXIT'
        cleanup_ok=True
    except BaseException as exc:
        primary=exc
        if process is not None and not reaped and not signals:
            try:close_process()
            except BaseException:BaseException.add_note(primary,'B2_CLEANUP_UNVERIFIED')
    finally:
        def residual(exc,code):
            nonlocal primary
            if primary is None:primary=exc
            else:BaseException.add_note(primary,code)
        for pipe in (() if process is None else (process.stdout,process.stderr)):
            try:
                if pipe is not None:pipe.close()
            except BaseException as exc:
                residual(exc,'B2_PIPE_CLOSE_RESIDUAL')
        try:selector.close()
        except BaseException as exc:residual(exc,'B2_SELECTOR_CLOSE_RESIDUAL')
        for f in opened:
            try:
                if not f.closed:f.flush();os.fsync(f.fileno())
            except BaseException as exc:residual(exc,'B2_STREAM_FLUSH_RESIDUAL')
            try:f.close()
            except BaseException as exc:residual(exc,'B2_STREAM_CLOSE_RESIDUAL')
        if primary is not None:
            for row in streams.values():
                try:_cleanup_owned_temp(store,row['temp'],row['identity'],primary)
                except BaseException as exc:residual(exc,'B2_TEMP_CLEANUP_RESIDUAL')
    if primary is not None:raise primary
    if not cleanup_ok:raise PrivateRunError('B2_CLEANUP_UNVERIFIED')
    output={}
    try:
        for name,row in streams.items():
            target=directory/'streams'/(name+'.bin');_guard_private_path(store,target)
            budget.check();os.link(row['temp'],target)
            raw=_b1_raw(target,row['cap'],budget,expected_size=row['retained'])
            if hashlib.sha256(raw).hexdigest()!=row['hash'].hexdigest():raise PrivateRunError('B2_STREAM_CHANGED')
            complete=row['eof'] and not row['overflow']
            output[name]={'artifact_ref':dict(path=target.relative_to(store).as_posix(),sha256=row['hash'].hexdigest(),size_bytes=row['retained']),
                          'observed_read_bytes':row['observed'],'retained_size_bytes':row['retained'],'retained_sha256':row['hash'].hexdigest(),
                          'eof':row['eof'],'complete':complete,'overflow_detected':row['overflow'],
                          'full_stream_sha256':row['hash'].hexdigest() if complete else None,
                          'error_code':None if complete else reason,'raw':raw}
    finally:
        for row in streams.values():_cleanup_owned_temp(store,row['temp'],row['identity'],sys.exception())
    return {'stdout':output['stdout'],'stderr':output['stderr'],'pid':pid,'pgid':pgid,'returncode':returncode,
            'spawn_status':spawn,'stop_reason':reason,'stop_origin':origin,'started_at_utc':started,
            'finished_at_utc':datetime.now(timezone.utc).isoformat(),'capture_read_bytes':capture_bytes,
            'artifact_read_bytes_at_spawn':at_spawn,'artifact_read_bytes_after_capture':after_capture,
            'cleanup':{'direct_child':'REAPED' if process else 'NOT_SPAWNED','process_group':'ABSENT' if process else 'NOT_SPAWNED',
                       'stdout_closed':True,'stderr_closed':True,'selector_closed':True,'owned_temps_verified':True,
                       'signal_events':signals,'residual_codes':[]}}


def _b2_publish_terminal(store,path,terminal,budget):
    """P is observed before this publication tail, never a prospective cost."""
    p=budget.bytes_read
    body=dict(terminal,artifact_read_bytes=p)
    raw=_b2_metadata(body,budget)
    if budget.bytes_read+len(raw)>2147483648:raise PrivateRunError('B2_TERMINAL_READ_RESERVE')
    _guard_private_path(store,path);budget.check()
    if budget.bytes_read!=p:raise PrivateRunError('B2_PRECOMMIT_LEDGER_DRIFT')
    created=complete_write=False
    try:
        stream=None;primary=None
        try:
            stream=path.open('xb');created=True
            os.chmod(path,0o600);budget.check()
            written=stream.write(raw)
            if written!=len(raw):raise OSError('B2_TERMINAL_SHORT_WRITE')
            complete_write=True
            stream.flush();os.fsync(stream.fileno())
        except BaseException as exc:
            primary=exc
            raise
        finally:
            if stream is not None:
                try:stream.close()
                except BaseException:
                    if primary is not None:BaseException.add_note(primary,'B2_TERMINAL_CLOSE_RESIDUAL')
                    else:raise
        _guard_private_path(store,path)
        actual=_b1_raw(path,B2_META_BYTES,budget,expected_size=len(raw))
        if actual!=raw:raise PrivateRunError('B2_TERMINAL_CHANGED')
        fd=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
        budget.check()
        if budget.bytes_read!=p+len(raw):raise PrivateRunError('B2_POSTCOMMIT_LEDGER_DRIFT')
    except BaseException as exc:
        if created:
            note=('B2_COMMITTED_ACK_UNKNOWN: visible content requires fresh validation; never rerun child'
                  if complete_write else 'B2_INCOMPLETE_TERMINAL: retain partial content; never resume or rerun child')
            BaseException.add_note(exc,note)
        raise
    return body



def _b2_relative(value):
    if (type(value) is not str or not value or len(value.encode('utf-8'))>1024 or '\\' in value or ':' in value
            or any(ord(c)<32 or ord(c)==127 for c in value)
            or any(p in ('','.','..') or p.endswith(('.', ' ')) or re.search(r'~[0-9]+(?:\.|$)',p) for p in value.split('/'))):
        raise PrivateRunError('B2_UNSAFE_REFERENCE')
    return value


def _b2_ref(root,reference,budget,cap=B2_META_BYTES):
    if (type(reference) is not dict or set(reference)!={'path','sha256','size_bytes'}
            or type(reference['sha256']) is not str or not SHA.fullmatch(reference['sha256'])
            or type(reference['size_bytes']) is not int or not 0<=reference['size_bytes']<=cap):
        raise PrivateRunError('B2_REFERENCE_FIELDS')
    path=Path(root)/_b2_relative(reference['path']);_guard_private_path(Path(root),path)
    raw=_b1_raw(path,cap,budget,expected_size=reference['size_bytes'])
    if hashlib.sha256(raw).hexdigest()!=reference['sha256']:raise PrivateRunError('B2_REFERENCE_CHANGED')
    return raw


def _b2_record(path,store,value,budget):
    raw=_b2_metadata(value,budget);_b1_publish(store,path,raw,budget)
    return dict(path=path.relative_to(store).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),size_bytes=len(raw))


def _b2_names(root,budget):
    _guard_private_path(Path(root).parent,Path(root));result=[]
    if not Path(root).exists():return result
    with os.scandir(root) as entries:
        for entry in entries:
            budget.check()
            if len(result)>=B1_MAX_ENTRIES:raise PrivateRunError('B2_NAMESPACE_LIMIT')
            _guard_private_path(Path(root),Path(root)/entry.name);result.append(entry.name)
    return sorted(result)


def _b2_plan(prepared,budget):
    """Planned bytes are reserves, never charges in the live ledger."""
    s,b=prepared['source'],prepared['binding'];refs={}
    def add(root,path,row,count=1):
        key=str(root)+'/'+path
        previous=refs.get(key)
        if previous is not None and previous['size_bytes']!=row['size_bytes']:raise PrivateRunError('B2_READ_PLAN_ALIAS')
        refs[key]={'size_bytes':row['size_bytes'],'passes':(previous or {}).get('passes',0)+count}
    for row in s['sources']:add('',row['private_archive'],row)
    for row in s['verified_inbox']:add(b['workspace_root'],row['path'],row)
    # Actual B1 recheck: input/code duplicate passes and cursor rereads are explicit.
    for root,key in ((b['selected_code_root'],'tool_input_view'),(b['workspace_root'],'workspace_input_view'),(b['selected_code_root'],'complete_code_view')):
        for p,row in b[key].items():add(root,p,row)
    for key,row in b['cycle_refs'].items():add(b['selected_code_root'],row['path'],row,2 if key in ('pointer','manifest') else 1)
    source_bytes=len(_b1_canonical(s,budget));binding_bytes=len(_b1_canonical(b,budget))
    # Receipt verification reads twice; physical stores are separately guarded later.
    receipt=s['intake_receipt_ref'];add('store',receipt['path'],receipt,2)
    k=sum(row['size_bytes']*row['passes'] for row in refs.values())+source_bytes+binding_bytes+2*B2_META_BYTES
    snapshot=sum(v['size_bytes'] for v in b['workspace_input_view'].values())
    # Four native-chain passes plus one final original-ref rescan; the extra
    # passes are reserved before spawn rather than exempted after execution.
    reserve=k+2*snapshot+13*B1_MAX_REPORT+2*(B2_STDOUT_BYTES+B2_STDERR_BYTES)+1024*1024
    claim_reads=3*(source_bytes+binding_bytes)+2*B2_META_BYTES
    plan={'schema':'private-pdca-read-plan-v2','refs':refs,'snapshot_bytes':snapshot,'report_passes':13,
          'stream_passes':2,'metadata_tail_bytes':1024*1024,'claim_read_ceiling':claim_reads}
    if budget.bytes_read+claim_reads+B2_STDOUT_BYTES+B2_STDERR_BYTES+2+reserve>2147483648:
        raise PrivateRunError('B2_READ_RESERVE_UNAVAILABLE')
    return {'terminate_seconds':B2_TERM_SECONDS,'validate_persist_seconds':B2_PERSIST_SECONDS,
            'final_read_reserve_bytes':reserve,'pipe_read_ceiling_bytes':B2_STDOUT_BYTES+B2_STDERR_BYTES+2,
            'read_plan_sha256':_b1_hash('habu-private-pdca-read-plan-v2',plan,budget)}


def _b2_known_checkpoint(workspace,identity,budget):
    contracts,_=_b1_modules(budget);runid=contracts.digest(identity)
    directory=Path(workspace)/'reports'/'pdca'/identity['night']/'runs'/runid
    _guard_private_path(Path(workspace),directory)
    if not directory.exists():return None
    cp_path=directory/'checkpoint.json';_guard_private_path(Path(workspace),cp_path)
    if not cp_path.exists():raise PrivateRunError('B2_UNKNOWN_CUMULATIVE_CHECKPOINT')
    before=_b1_raw(cp_path,B1_MAX_JSON,budget);cp=_b1_document(before,budget)
    checksum=_b1_document(_b1_raw(directory/'checkpoint.sha256.json',B1_MAX_JSON,budget),budget)
    if (type(cp) is not dict or set(cp)!={'schema_version','run_id','outputs','elapsed_seconds','round_number','created_at','result_sha256','active_stage','active_since','attempt_deadline'}
            or cp['schema_version']!=contracts.SCHEMA_VERSION or cp.get('run_id')!=runid or checksum!={'sha256':contracts.digest(cp)}
            or type(cp.get('outputs')) is not dict or len(cp['outputs'])>B1_MAX_FILES
            or type(cp.get('round_number')) is not int or not 0<=cp['round_number']<=2
            or type(cp.get('elapsed_seconds')) not in (int,float) or not 0<=cp['elapsed_seconds']<=sys.float_info.max
            or not math.isfinite(cp['elapsed_seconds'])):
        raise PrivateRunError('B2_UNKNOWN_CUMULATIVE_CHECKPOINT')
    created=_b2_utc(cp['created_at'])
    if cp['result_sha256'] is not None and (type(cp['result_sha256']) is not str or not SHA.fullmatch(cp['result_sha256'])):
        raise PrivateRunError('B2_UNKNOWN_CUMULATIVE_CHECKPOINT')
    for key in ('active_since','attempt_deadline'):
        if cp[key] is not None and _b2_utc(cp[key])<created:raise PrivateRunError('B2_PARTIAL_CHECKPOINT_TIME')
    if ((cp['active_stage'] is None)!=(cp['active_since'] is None)
            or (cp['active_stage'] is not None and (type(cp['active_stage']) is not str or cp['active_stage'] not in contracts.STAGE_NAMES))):
        raise PrivateRunError('B2_PARTIAL_CHECKPOINT_STAGE')
    if cp.get('result_sha256'):
        checked=_b1_report(directory,identity,budget)
        return dict(checkpoint=cp,result=checked['result'])
    expected={};total=0
    for relative,sha in cp['outputs'].items():
        path=directory/_b2_relative(relative);_guard_private_path(Path(workspace),path)
        row=_b1_file_ref(path,budget,cap=B1_MAX_JSON)
        total+=row['size_bytes']
        if total>B1_MAX_REPORT or type(sha) is not str or row['sha256']!=sha:raise PrivateRunError('B2_PARTIAL_CHECKPOINT_CHANGED')
        expected[relative]=row
    # Match the unchanged native restore's only stage-wrapper semantic check.
    # Physical reads/checks remain outside the pure validator's narrow catch.
    for name in contracts.STAGE_NAMES:
        relative='stages/'+name+'.json'
        if relative in cp['outputs']:
            wrapper=_b1_document(_b1_raw(directory/relative,B1_MAX_JSON,budget),budget)
            if type(wrapper) is not dict or 'stage' not in wrapper:raise PrivateRunError('B2_PARTIAL_CHECKPOINT_STAGE')
            budget.check()
            try:contracts.validate_stage(wrapper['stage'],name)
            except (ValueError,TypeError,KeyError) as exc:raise PrivateRunError('B2_PARTIAL_CHECKPOINT_STAGE') from exc
            budget.check()
    expected.update({'snapshot/'+p:row for p,row in identity['inputs'].items()})
    expected['checkpoint.json']=dict(sha256=hashlib.sha256(before).hexdigest(),size_bytes=len(before))
    checksum_raw=_b1_raw(directory/'checkpoint.sha256.json',B1_MAX_JSON,budget)
    expected['checkpoint.sha256.json']=dict(sha256=hashlib.sha256(checksum_raw).hexdigest(),size_bytes=len(checksum_raw))
    _b1_view(directory,budget,whole=True,expected=expected)
    if _b1_raw(cp_path,B1_MAX_JSON,budget)!=before:raise PrivateRunError('B2_CHECKPOINT_CHANGED')
    return dict(checkpoint=cp,result=None)


def _b2_native(capture,binding,budget,grant,prior=None,*,historical=False):
    contracts,_=_b1_modules(budget)
    if (not capture['stdout']['complete'] or capture['returncode'] not in (0,2)):
        raise _B2NativeRejected('B2_INVALID_NATIVE_STREAM')
    stdout=_b1_document(capture['stdout']['raw'],budget,error_type=_B2NativeRejected)
    ident=binding['master_identity'];directory=Path(binding['workspace_root'])/'reports'/'pdca'/ident['night']/'runs'/binding['master_run_id']
    checked=_b1_report(directory,ident,budget);result=checked['result']
    if _b1_canonical(stdout,budget)!=_b1_canonical(result,budget):raise _B2NativeRejected('B2_NATIVE_STDOUT_CHANGED')
    if not historical:
        top=Path(binding['workspace_root'])/'reports'/'pdca'/ident['night']/'pdca_result.json'
        _guard_private_path(Path(binding['workspace_root']),top)
        if _b1_canonical(_b1_document(_b1_raw(top,B1_MAX_JSON,budget),budget),budget)!=_b1_canonical(result,budget):
            raise _B2NativeRejected('B2_NATIVE_TOP_POINTER_CHANGED')
    if ([s['name'] for s in result['stages']]!=list(contracts.STAGE_NAMES)
            or capture['returncode']!=(2 if result['overall_status'] in ('BLOCKED','FAIL') else 0)):
        raise _B2NativeRejected('B2_NATIVE_EXIT_STAGE_ORDER')
    native_budget=result.get('budget')
    if (type(native_budget) is not dict or type(native_budget.get('limit_seconds')) is not int
            or not 0<native_budget['limit_seconds']<=grant or type(native_budget.get('round_number')) is not int
            or not 0<=native_budget['round_number']<=2 or native_budget.get('max_rounds')!=2 or native_budget.get('max_candidates')!=3
            or type(native_budget.get('elapsed_seconds')) not in (int,float)
            or not 0<=native_budget['elapsed_seconds']<=sys.float_info.max or not math.isfinite(native_budget['elapsed_seconds'])):
        raise _B2NativeRejected('B2_NATIVE_BUDGET')
    if not historical:
        if prior is None or prior.get('result') is None:
            if native_budget['limit_seconds']!=grant:raise _B2NativeRejected('B2_FRESH_NATIVE_GRANT')
        elif _b1_canonical(prior['result'],budget)!=_b1_canonical(result,budget):
            raise _B2NativeRejected('B2_PRIOR_COMPLETE_RESULT_CHANGED')
    if prior:
        old=prior['result']['budget'] if prior.get('result') else prior['checkpoint']
        floor=old['elapsed_seconds']
        if not prior.get('result') and prior['checkpoint'].get('active_since'):
            until=datetime.fromisoformat(capture['started_at_utc'])
            if prior['checkpoint'].get('attempt_deadline'):until=min(until,datetime.fromisoformat(prior['checkpoint']['attempt_deadline']))
            floor+=max(0,(until-datetime.fromisoformat(prior['checkpoint']['active_since'])).total_seconds())
        if native_budget['elapsed_seconds']<floor or native_budget['round_number']<old['round_number']:
            raise _B2NativeRejected('B2_NATIVE_CUMULATIVE_DECREASE')
    return checked


def _b2_disposition(reason,origin,native=None):
    if native is not None:
        value=native['overall_status'];return value if value in ('BLOCKED','FAIL') else 'PARTIAL'
    if ((reason=='OWNED_TIMEOUT' and origin=='CLOSED_TIMER_OBSERVATION')
            or (reason in ('STDOUT_CAPACITY','STDERR_CAPACITY') and origin=='CLOSED_PIPE_READ_OBSERVATION')):return 'BLOCKED'
    return 'FAIL'


def _b2_fields(value,names):
    if type(value) is not dict or set(value)!=set(names.split()):raise PrivateRunError('B2_RECORD_FIELDS')


def _b2_utc(value):
    if type(value) is not str or not 1<=len(value)<=128:raise PrivateRunError('B2_UTC_TIME')
    try:parsed=datetime.fromisoformat(value)
    except ValueError as exc:raise PrivateRunError('B2_UTC_TIME') from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds()!=0:raise PrivateRunError('B2_UTC_TIME')
    return parsed


def _b2_validate_attempt(store,directory,source,budget):
    """Historical records use their recorded identity, never today's runtime."""
    def document(name):
        path=directory/name;_guard_private_path(store,path)
        return _b1_document(_b1_raw(path,B2_META_BYTES if name!='binding.json' else B1_MAX_JSON,budget),budget)
    binding=document('binding.json');claim=document('claim.json');terminal=document('terminal.json')
    if _b1_raw(directory/'terminal.json',B2_META_BYTES,budget)!=_b2_metadata(terminal,budget):
        raise PrivateRunError('B2_INCOMPLETE_TERMINAL_CONTENT')
    _b1_binding_shape(source,binding,budget)
    bh=_b1_hash('habu-private-pdca-binding-v2',binding,budget)
    scope=_b1_hash('habu-private-pdca-source-scope-v2',source,budget)
    aid=_b1_hash('habu-private-pdca-attempt-v2',{'scope_id':scope,'revision':binding['revision'],'binding_sha256':bh},budget)
    _b2_fields(claim,'schema scope_id attempt_id revision binding_sha256 claim_nonce created_at_utc phase')
    _b2_fields(terminal,'schema scope_id attempt_id binding_sha256 claim_nonce kind phase child_returncode backend_status private_status native_run_id native_completed result_ref report_view_sha256 supervisor_ref failure finished_at_utc artifact_read_bytes cleanup_verified source_eligible_for_model p0_certified model_validation_certified champion_activation')
    if (directory.name!=aid or claim['schema']!='habu-private-pdca-claim-v2' or claim['phase']!='RESERVED_PRESPAWN'
            or terminal['schema']!='habu-private-pdca-terminal-v2' or claim['revision']!=binding['revision']
            or type(claim['claim_nonce']) is not str or not re.fullmatch(r'[a-f0-9]{32}',claim['claim_nonce'])):
        raise PrivateRunError('B2_CLAIM_BINDING')
    for row in (claim,terminal):
        if (row['scope_id']!=scope or row['attempt_id']!=aid or row['binding_sha256']!=bh
                or row['claim_nonce']!=claim['claim_nonce']):raise PrivateRunError('B2_TERMINAL_BINDING')
    expected_super=(directory/'supervisor.json').relative_to(store).as_posix()
    if terminal['supervisor_ref']['path']!=expected_super:raise PrivateRunError('B2_SUPERVISOR_PATH')
    sup=_b1_document(_b2_ref(store,terminal['supervisor_ref'],budget),budget)
    _b2_fields(sup,'schema scope_id attempt_id binding_sha256 claim_nonce execution_policy argv cwd runtime pid pgid started_at_utc finished_at_utc entry_deadline_monotonic_ns run_deadline_monotonic_ns cleanup_deadline_monotonic_ns scientific_budget_seconds reserves returncode signal spawn_status stop_reason stop_origin stdout stderr capture_read_bytes artifact_read_bytes_at_spawn artifact_read_bytes_after_capture report_validation cleanup failure code_sha256')
    if (sup['schema']!='habu-private-pdca-supervisor-v2' or sup['scope_id']!=scope or sup['attempt_id']!=aid
            or sup['binding_sha256']!=bh or sup['claim_nonce']!=claim['claim_nonce'] or sup['code_sha256']!=binding['complete_code_sha256']
            or sup['execution_policy']!='private-pdca-bound-execution-v2' or sup['cwd']!=binding['workspace_root']
            or _b1_canonical(sup['runtime'],budget)!=_b1_canonical(binding['master_identity']['runtime'],budget)):
        raise PrivateRunError('B2_SUPERVISOR_BINDING')
    if not (_b2_utc(claim['created_at_utc'])<=_b2_utc(sup['started_at_utc'])<=
            _b2_utc(sup['finished_at_utc'])<=_b2_utc(terminal['finished_at_utc'])):
        raise PrivateRunError('B2_RECORD_CHRONOLOGY')
    grant=sup['scientific_budget_seconds']
    if type(grant) is not int or not 1<=grant<=300:raise PrivateRunError('B2_GRANT')
    argv=sup['argv']
    if (type(argv) is not list or len(argv)!=8 or not all(type(v) is str and len(v.encode())<=2048 for v in argv)
            or not Path(argv[0]).is_absolute() or argv[1:]!=[str(Path(binding['selected_code_root'])/'scripts'/'run_pdca.py'),'--root',binding['workspace_root'],'--night',source['night'],'--budget-seconds',str(grant)]):
        raise PrivateRunError('B2_ARGV_BINDING')
    for key in ('entry_deadline_monotonic_ns','run_deadline_monotonic_ns','cleanup_deadline_monotonic_ns','capture_read_bytes','artifact_read_bytes_at_spawn','artifact_read_bytes_after_capture'):
        if type(sup[key]) is not int or sup[key]<0:raise PrivateRunError('B2_SUPERVISOR_COUNTER')
    if (sup['run_deadline_monotonic_ns']!=sup['entry_deadline_monotonic_ns']-25*10**9
            or sup['cleanup_deadline_monotonic_ns']!=sup['entry_deadline_monotonic_ns']-20*10**9
            or sup['artifact_read_bytes_after_capture']!=sup['artifact_read_bytes_at_spawn']+sup['capture_read_bytes']):
        raise PrivateRunError('B2_SUPERVISOR_PHASE')
    _b2_fields(sup['reserves'],'terminate_seconds validate_persist_seconds final_read_reserve_bytes pipe_read_ceiling_bytes read_plan_sha256')
    if (type(sup['reserves']['terminate_seconds']) is not int or sup['reserves']['terminate_seconds']!=5
            or type(sup['reserves']['validate_persist_seconds']) is not int or sup['reserves']['validate_persist_seconds']!=20
            or type(sup['reserves']['final_read_reserve_bytes']) is not int or not 0<=sup['reserves']['final_read_reserve_bytes']<=2147483648
            or type(sup['reserves']['pipe_read_ceiling_bytes']) is not int or sup['reserves']['pipe_read_ceiling_bytes']!=B2_STDOUT_BYTES+B2_STDERR_BYTES+2
            or type(sup['reserves']['read_plan_sha256']) is not str or not SHA.fullmatch(sup['reserves']['read_plan_sha256'])):
        raise PrivateRunError('B2_RESERVES')
    captured={};observed=0
    for name,cap in (('stdout',B2_STDOUT_BYTES),('stderr',B2_STDERR_BYTES)):
        row=sup[name];_b2_fields(row,'artifact_ref observed_read_bytes retained_size_bytes retained_sha256 eof complete overflow_detected full_stream_sha256 error_code')
        if (type(row['observed_read_bytes']) is not int or not 0<=row['observed_read_bytes']<=cap+1
                or type(row['retained_size_bytes']) is not int or row['retained_size_bytes']!=min(row['observed_read_bytes'],cap)
                or any(type(row[k]) is not bool for k in ('eof','complete','overflow_detected'))
                or row['overflow_detected']!=(row['observed_read_bytes']>cap)
                or row['complete']!=(row['eof'] and not row['overflow_detected'])):
            raise PrivateRunError('B2_STREAM_COUNTER')
        if row['artifact_ref']['path']!=(directory/'streams'/(name+'.bin')).relative_to(store).as_posix():raise PrivateRunError('B2_STREAM_PATH')
        raw=_b2_ref(store,row['artifact_ref'],budget,cap)
        sha=hashlib.sha256(raw).hexdigest()
        if (len(raw)!=row['retained_size_bytes'] or sha!=row['retained_sha256']
                or row['full_stream_sha256']!=(sha if row['complete'] else None)):
            raise PrivateRunError('B2_STREAM_HASH')
        captured[name]=dict(row,raw=raw);observed+=row['observed_read_bytes']
    if observed!=sup['capture_read_bytes']:raise PrivateRunError('B2_CAPTURE_COUNTER')
    cleanup=sup['cleanup'];_b2_fields(cleanup,'direct_child process_group stdout_closed stderr_closed selector_closed owned_temps_verified signal_events residual_codes')
    if (any(cleanup[k] is not True for k in ('stdout_closed','stderr_closed','selector_closed','owned_temps_verified'))
            or cleanup['residual_codes']!=[] or type(cleanup['signal_events']) is not list or len(cleanup['signal_events'])>2):
        raise PrivateRunError('B2_CLEANUP_UNVERIFIED')
    if sup['spawn_status']!='SPAWNED' and cleanup['signal_events']:raise PrivateRunError('B2_SPAWN_FACTS')
    for event in cleanup['signal_events']:
        _b2_fields(event,'signal at_monotonic_ns result')
        if (type(event['signal']) is not int or event['signal'] not in (int(signal.SIGTERM),int(signal.SIGKILL))
                or type(event['at_monotonic_ns']) is not int or not 0<=event['at_monotonic_ns']<sup['cleanup_deadline_monotonic_ns']
                or event['result'] not in ('SENT','ESRCH')):
            raise PrivateRunError('B2_SIGNAL_FACTS')
    if sup['spawn_status']=='SPAWNED':
        if (type(sup['pid']) is not int or sup['pid']<=0 or type(sup['pgid']) is not int or sup['pgid']!=sup['pid']
                or type(sup['returncode']) is not int or not -(2**31)<=sup['returncode']<2**31
                or cleanup['direct_child']!='REAPED' or cleanup['process_group']!='ABSENT'
                or sup['signal']!=(-sup['returncode'] if sup['returncode']<0 else None)):
            raise PrivateRunError('B2_PROCESS_FACTS')
        events=cleanup['signal_events']
        if (not events or events[0]['signal']!=int(signal.SIGTERM)
                or len(events)==2 and (events[1]['signal']!=int(signal.SIGKILL)
                    or events[1]['at_monotonic_ns']<events[0]['at_monotonic_ns'])):
            raise PrivateRunError('B2_SIGNAL_ORDER')
        if sup['stop_reason']=='SPAWN_FAILURE':raise PrivateRunError('B2_PROCESS_STOP_FACTS')
    elif (sup['spawn_status']!='SPAWN_FAILED' or any(sup[k] is not None for k in ('pid','pgid','returncode','signal'))
          or cleanup['direct_child']!='NOT_SPAWNED' or cleanup['process_group']!='NOT_SPAWNED' or observed
          or cleanup['signal_events'] or sup['stop_reason']!='SPAWN_FAILURE' or sup['stop_origin']!='OS_SPAWN_OR_EXIT'):
        raise PrivateRunError('B2_SPAWN_FACTS')
    validation=sup['report_validation'];_b2_fields(validation,'status native_result_ref report_view_sha256 reason_code')
    captured.update(returncode=sup['returncode'],started_at_utc=sup['started_at_utc'])
    native=None
    if terminal['kind']=='VALIDATED_CHILD_TERMINAL':
        if (validation['status']!='VALIDATED' or not all(captured[n]['complete'] for n in ('stdout','stderr'))
                or validation['reason_code']!='NATIVE_CHAIN_VALIDATED' or sup['stop_reason']!='NATIVE_EXIT'
                or sup['stop_origin']!='NONE' or sup['failure'] is not None or terminal['failure'] is not None):
            raise PrivateRunError('B2_NATIVE_ADMISSION')
        checked=_b2_native(captured,binding,budget,grant,historical=True);native=checked['result']
        npath='reports/pdca/'+source['night']+'/runs/'+binding['master_run_id']+'/run_manifest.json'
        if validation['native_result_ref']['path']!=npath:raise PrivateRunError('B2_NATIVE_REFERENCE')
        _b2_ref(Path(binding['workspace_root']),validation['native_result_ref'],budget,B1_MAX_JSON)
        if validation['report_view_sha256']!=checked['report_view_sha256']:raise PrivateRunError('B2_NATIVE_VIEW')
    elif terminal['kind']=='SUPERVISOR_FAILURE':
        if (validation['status'] not in ('REJECTED','NOT_RUN') or any(validation[k] is not None for k in ('native_result_ref','report_view_sha256'))
                or any(terminal[k] is not None for k in ('backend_status','native_run_id','native_completed','result_ref','report_view_sha256'))):
            raise PrivateRunError('B2_FAILURE_NATIVE_FIELDS')
        failure=sup['failure'];_b2_fields(failure,'code origin phase residual')
        if any(type(v) is not str or len(v.encode('utf-8'))>512 for v in failure.values()) or terminal['failure']!=failure:
            raise PrivateRunError('B2_FAILURE_FIELDS')
        if (terminal['phase']!=sup['stop_reason'] or failure['code']!=sup['stop_reason']
                or failure['origin']!=sup['stop_origin'] or failure['phase']!='SUPERVISE_OR_NATIVE_VALIDATION'):
            raise PrivateRunError('B2_FAILURE_PHASE')
        if (validation['reason_code']!=sup['stop_reason']
                or validation['status']!=('REJECTED' if sup['stop_reason']=='INVALID_NATIVE_RESULT' else 'NOT_RUN')):
            raise PrivateRunError('B2_FAILURE_VALIDATION_PHASE')
        if sup['stop_reason']=='OWNED_TIMEOUT':
            if (sup['stop_origin']!='CLOSED_TIMER_OBSERVATION' or not cleanup['signal_events']
                    or cleanup['signal_events'][0]['at_monotonic_ns']<sup['run_deadline_monotonic_ns']):
                raise PrivateRunError('B2_UNPROVEN_TIMEOUT')
        elif sup['stop_reason'] in ('STDOUT_CAPACITY','STDERR_CAPACITY'):
            name='stdout' if sup['stop_reason']=='STDOUT_CAPACITY' else 'stderr'
            if sup['stop_origin']!='CLOSED_PIPE_READ_OBSERVATION' or not captured[name]['overflow_detected']:
                raise PrivateRunError('B2_UNPROVEN_CAPACITY')
        else:
            if (sup['stop_reason'] not in ('SPAWN_FAILURE','CHILD_SIGNAL','UNEXPLAINED_EXIT','INVALID_NATIVE_RESULT')
                    or sup['stop_origin']!=('UNVERIFIED' if sup['stop_reason']=='INVALID_NATIVE_RESULT' else 'OS_SPAWN_OR_EXIT')):
                raise PrivateRunError('B2_UNPROVEN_FAILURE')
            if (sup['stop_reason']=='CHILD_SIGNAL' and (type(sup['returncode']) is not int or sup['returncode']>=0)
                    or sup['stop_reason']=='UNEXPLAINED_EXIT' and (type(sup['returncode']) is not int or sup['returncode']<0)
                    or sup['stop_reason']=='INVALID_NATIVE_RESULT' and (sup['returncode'] not in (0,2)
                        or not all(captured[n]['complete'] for n in ('stdout','stderr')))):
                raise PrivateRunError('B2_FAILURE_EXIT_FACTS')
        _b2_known_checkpoint(Path(binding['workspace_root']),binding['master_identity'],budget)
    else:raise PrivateRunError('B2_TERMINAL_KIND')
    expected=_b2_private_result(scope,aid,bh,terminal['supervisor_ref'],sup,native)
    result_path=directory/'result.json';_guard_private_path(store,result_path)
    result_raw=_b1_raw(result_path,B2_META_BYTES,budget)
    if result_raw!=_b2_metadata(expected,budget):raise PrivateRunError('B2_PRIVATE_RESULT_CHANGED')
    status=_b2_disposition(sup['stop_reason'],sup['stop_origin'],native)
    if (terminal['private_status']!=status or terminal['child_returncode']!=sup['returncode'] or terminal['cleanup_verified'] is not True
            or type(terminal['artifact_read_bytes']) is not int
            or not sup['artifact_read_bytes_after_capture']<=terminal['artifact_read_bytes']<=2147483648
            or any(terminal[k] is not False or expected[k] is not False for k in B2_FLAGS)):
        raise PrivateRunError('B2_TERMINAL_COUNTER_OR_STATUS')
    if native is not None:
        result_ref=dict(path=result_path.relative_to(store).as_posix(),sha256=hashlib.sha256(result_raw).hexdigest(),size_bytes=len(result_raw))
        if (terminal['phase']!='CHILD_VALIDATED' or terminal['result_ref']!=result_ref or terminal['backend_status']!=native['overall_status']
                or terminal['native_run_id']!=binding['master_run_id'] or type(terminal['native_completed']) is not bool
                or terminal['native_completed']!=native['completed'] or terminal['report_view_sha256']!=validation['report_view_sha256']):
            raise PrivateRunError('B2_NATIVE_TERMINAL')
    namespace={}
    for p in ('binding.json','claim.json','supervisor.json','result.json','terminal.json'):
        raw=_b1_raw(directory/p,B1_MAX_JSON if p=='binding.json' else B2_META_BYTES,budget)
        namespace[p]=dict(sha256=hashlib.sha256(raw).hexdigest(),size_bytes=len(raw))
    for name in ('stdout','stderr'):namespace['streams/'+name+'.bin']={k:sup[name]['artifact_ref'][k] for k in ('sha256','size_bytes')}
    _b1_view(directory,budget,whole=True,expected=namespace)
    return {'binding':binding,'claim':claim,'terminal':terminal,'result':expected,'result_raw':result_raw}


def _b2_private_result(scope,attempt,binding_sha,super_ref,supervisor,native):
    validation=supervisor['report_validation']
    return dict(schema='habu-private-pdca-result-v2',scope_id=scope,attempt_id=attempt,binding_sha256=binding_sha,
                supervisor_ref=super_ref,native_result_ref=validation['native_result_ref'],report_view_sha256=validation['report_view_sha256'],
                backend_status=native['overall_status'] if native else None,
                private_status=_b2_disposition(supervisor['stop_reason'],supervisor['stop_origin'],native),
                native_run_id=native['run_id'] if native else None,native_completed=native['completed'] if native else None,
                **B2_FLAGS,next='NEED_MORE_DATA_NOT_SCIENTIFICALLY_VALIDATED')


def _b2_history(store,prepared,budget):
    base=store/'private_pdca_runs'/'v2'/'scopes'/prepared['scope_id']
    _guard_private_path(store,base)
    if not base.exists():return []
    if _b2_names(base,budget)!=['attempts','source.json']:raise PrivateRunError('B2_BUSY_OR_INCOMPLETE_SCOPE')
    raw=_b1_raw(base/'source.json',B1_MAX_JSON,budget)
    if raw!=_b1_canonical(prepared['source'],budget):raise PrivateRunError('B2_SOURCE_SCOPE_CHANGED')
    history=[]
    for name in _b2_names(base/'attempts',budget):
        if not SHA.fullmatch(name) or len(history)>=B1_MAX_FILES:raise PrivateRunError('B2_UNKNOWN_ATTEMPT')
        directory=base/'attempts'/name
        history.append(_b2_validate_attempt(store,directory,prepared['source'],budget))
    if not history:raise PrivateRunError('B2_INCOMPLETE_SCOPE')
    return history


def _b2_revision_guard(history,binding,attempt_id):
    for row in history:
        if row['claim']['attempt_id']==attempt_id:continue
        if row['binding']['revision']==binding['revision']:raise PrivateRunError('B2_REVISION_BINDING_CONFLICT')
        if (row['terminal']['kind']=='VALIDATED_CHILD_TERMINAL'
                and row['terminal']['native_run_id']==binding['master_run_id']):
            raise PrivateRunError('B2_NATIVE_NAMESPACE_ALREADY_BOUND')


def _b2_finish(prepared,store,claim,capture,budget,grant,reserves,entry_ns,run_ns,cleanup_ns,prior):
    binding=prepared['binding'];scope=prepared['scope_id'];aid=prepared['attempt_id']
    directory=Path(claim['base'])/'attempts'/aid
    native=None;checked=None;validation={'status':'NOT_RUN','native_result_ref':None,'report_view_sha256':None,'reason_code':capture['stop_reason']}
    if capture['stop_reason']=='NATIVE_EXIT' and all(capture[n]['complete'] for n in ('stdout','stderr')) and capture['returncode'] in (0,2):
        try:checked=_b2_native(capture,binding,budget,grant,prior)
        except _B2NativeRejected:
            capture['stop_reason']='INVALID_NATIVE_RESULT';capture['stop_origin']='UNVERIFIED'
            validation['status']='REJECTED';validation['reason_code']='INVALID_NATIVE_RESULT'
        else:
            native=checked['result'];path=Path(binding['workspace_root'])/'reports'/'pdca'/prepared['source']['night']/'runs'/binding['master_run_id']/'run_manifest.json'
            validation={'status':'VALIDATED','native_result_ref':dict(path=path.relative_to(binding['workspace_root']).as_posix(),**checked['view']['run_manifest.json']),
                        'report_view_sha256':checked['report_view_sha256'],'reason_code':'NATIVE_CHAIN_VALIDATED'}
    if native is None:
        if capture['stop_reason']=='NATIVE_EXIT':capture['stop_reason']='UNEXPLAINED_EXIT';capture['stop_origin']='OS_SPAWN_OR_EXIT'
        if validation['status']=='NOT_RUN':validation['reason_code']=capture['stop_reason']
        _b2_known_checkpoint(Path(binding['workspace_root']),binding['master_identity'],budget)
    failure=None if native is not None else dict(code=capture['stop_reason'],origin=capture['stop_origin'],phase='SUPERVISE_OR_NATIVE_VALIDATION',residual='')
    supervisor=dict(schema='habu-private-pdca-supervisor-v2',scope_id=scope,attempt_id=aid,binding_sha256=claim['claim']['binding_sha256'],
                    claim_nonce=claim['claim']['claim_nonce'],execution_policy='private-pdca-bound-execution-v2',
                    argv=[sys.executable,str(Path(binding['selected_code_root'])/'scripts'/'run_pdca.py'),'--root',binding['workspace_root'],'--night',prepared['source']['night'],'--budget-seconds',str(grant)],
                    cwd=binding['workspace_root'],runtime=binding['master_identity']['runtime'],pid=capture['pid'],pgid=capture['pgid'],
                    started_at_utc=capture['started_at_utc'],finished_at_utc=capture['finished_at_utc'],entry_deadline_monotonic_ns=entry_ns,
                    run_deadline_monotonic_ns=run_ns,cleanup_deadline_monotonic_ns=cleanup_ns,scientific_budget_seconds=grant,reserves=reserves,
                    returncode=capture['returncode'],signal=-capture['returncode'] if capture['returncode'] is not None and capture['returncode']<0 else None,
                    spawn_status=capture['spawn_status'],stop_reason=capture['stop_reason'],stop_origin=capture['stop_origin'],
                    stdout={k:v for k,v in capture['stdout'].items() if k!='raw'},stderr={k:v for k,v in capture['stderr'].items() if k!='raw'},
                    capture_read_bytes=capture['capture_read_bytes'],artifact_read_bytes_at_spawn=capture['artifact_read_bytes_at_spawn'],
                    artifact_read_bytes_after_capture=capture['artifact_read_bytes_after_capture'],report_validation=validation,
                    cleanup=capture['cleanup'],failure=failure,code_sha256=binding['complete_code_sha256'])
    super_ref=_b2_record(directory/'supervisor.json',store,supervisor,budget)
    result=_b2_private_result(scope,aid,claim['claim']['binding_sha256'],super_ref,supervisor,native)
    result_ref=_b2_record(directory/'result.json',store,result,budget)
    _b1_recheck(prepared['source'],binding,store,budget)
    if checked:
        expected=dict(checked['view']);expected.update({'snapshot/'+p:row for p,row in binding['master_identity']['inputs'].items()})
        reportdir=Path(binding['workspace_root'])/'reports'/'pdca'/prepared['source']['night']/'runs'/binding['master_run_id']
        _b1_view(reportdir,budget,whole=True,expected=expected)
    else:_b2_known_checkpoint(Path(binding['workspace_root']),binding['master_identity'],budget)
    expected={}
    for name in ('source.json',):
        path=Path(claim['base'])/name
        raw=_b1_raw(path,B1_MAX_JSON,budget)
        if raw!=_b1_canonical(prepared['source'],budget):raise PrivateRunError('B2_SHARED_SOURCE_CHANGED')
    for name,value in (('binding.json',binding),('claim.json',claim['claim']),('supervisor.json',supervisor),('result.json',result)):
        raw=_b1_canonical(value,budget) if name in ('binding.json','claim.json') else _b2_metadata(value,budget)
        expected[name]=dict(sha256=hashlib.sha256(raw).hexdigest(),size_bytes=len(raw))
    for name in ('stdout','stderr'):expected['streams/'+name+'.bin']={k:capture[name]['artifact_ref'][k] for k in ('sha256','size_bytes')}
    _b1_view(directory,budget,whole=True,expected=expected)
    active=Path(claim['base'])/'active.json';_guard_private_path(store,active)
    active_raw=_b1_raw(active,B2_META_BYTES,budget)
    if active_raw!=_b1_canonical(claim['claim'],budget):raise PrivateRunError('B2_ACTIVE_CHANGED')
    ainfo=active.lstat();cinfo=(directory/'claim.json').lstat()
    if (ainfo.st_dev,ainfo.st_ino)!=(cinfo.st_dev,cinfo.st_ino):raise PrivateRunError('B2_ACTIVE_IDENTITY')
    _cleanup_owned_temp(store,active,(ainfo.st_dev,ainfo.st_ino),None)
    terminal=dict(schema='habu-private-pdca-terminal-v2',scope_id=scope,attempt_id=aid,binding_sha256=claim['claim']['binding_sha256'],
                  claim_nonce=claim['claim']['claim_nonce'],kind='VALIDATED_CHILD_TERMINAL' if native else 'SUPERVISOR_FAILURE',
                  phase='CHILD_VALIDATED' if native else capture['stop_reason'],child_returncode=capture['returncode'],
                  backend_status=native['overall_status'] if native else None,private_status=result['private_status'],
                  native_run_id=native['run_id'] if native else None,native_completed=native['completed'] if native else None,
                  result_ref=result_ref if native else None,report_view_sha256=validation['report_view_sha256'],supervisor_ref=super_ref,
                  failure=failure,finished_at_utc=datetime.now(timezone.utc).isoformat(),artifact_read_bytes=0,cleanup_verified=True,**B2_FLAGS)
    _b2_publish_terminal(store,directory/'terminal.json',terminal,budget)
    return result


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
                receipt_path: Path, night: str, timeout_seconds: int = 330, *, revision: str = 'r1') -> dict:
    budget=_ReadBudget(timeout_seconds,maximum=330,error_type=PrivateRunError)
    selected=_b1_selected_root(code_root,budget)
    _b2_capability(budget)
    prepared=_b1_prepare(selected,Path(workspace),Path(store),Path(receipt_path),night,revision,budget)
    store=Path(store).resolve(strict=True)
    old_id=hashlib.sha256((night+':'+prepared['source']['source_receipt_id']).encode()).hexdigest()
    legacy=store/'private_pdca_runs'/(old_id+'.json');_guard_private_path(store,legacy)
    if legacy.exists():raise PrivateRunError('B2_LEGACY_UNBOUND')
    before_history=budget.bytes_read
    history=_b2_history(store,prepared,budget)
    history_reads=budget.bytes_read-before_history
    _b2_revision_guard(history,prepared['binding'],prepared['attempt_id'])
    for row in history:
        if row['claim']['attempt_id']==prepared['attempt_id']:
            _b1_recheck(prepared['source'],prepared['binding'],store,budget)
            before=budget.bytes_read;budget.check()
            if budget.bytes_read!=before:raise PrivateRunError('B2_REUSE_LEDGER_DRIFT')
            return row['result']
    prior=_b2_known_checkpoint(Path(prepared['binding']['workspace_root']),prepared['binding']['master_identity'],budget)
    reserves=_b2_plan(prepared,budget)
    reserves['final_read_reserve_bytes']+=2*history_reads
    reserves['read_plan_sha256']=_b1_hash('habu-private-pdca-history-read-plan-v2',
                                        {'base':reserves['read_plan_sha256'],'extra_history_passes':2,'observed_stable_pass_bytes':history_reads},budget)
    entry_ns=int(budget.deadline*10**9);run_ns=entry_ns-25*10**9;cleanup_ns=entry_ns-20*10**9
    run_deadline=run_ns/10**9;cleanup_deadline=cleanup_ns/10**9
    def ready():
        budget.check()
        value=min(300,math.floor(run_deadline-time.monotonic()))
        if value<1:raise PrivateRunError('B2_TIME_RESERVE_UNAVAILABLE')
        if budget.bytes_read+B2_STDOUT_BYTES+B2_STDERR_BYTES+2+reserves['final_read_reserve_bytes']>2147483648:
            raise PrivateRunError('B2_READ_RESERVE_UNAVAILABLE')
        if prior and prior.get('result') and prior['result']['budget']['limit_seconds']>value:
            raise PrivateRunError('B2_PRIOR_NATIVE_GRANT_EXCEEDS_REMAINING')
        return value
    ready()
    claim=_b1_reserve(prepared,store,budget)
    for row in history:
        _b2_validate_attempt(store,Path(claim['base'])/'attempts'/row['claim']['attempt_id'],prepared['source'],budget)
    base=Path(claim['base']);directory=base/'attempts'/prepared['attempt_id']
    if (_b2_names(base,budget)!=['active.json','attempts','source.json']
            or set(_b2_names(base/'attempts',budget))!={prepared['attempt_id']}|{r['claim']['attempt_id'] for r in history}
            or _b2_names(directory,budget)!=['binding.json','claim.json']):
        raise PrivateRunError('B2_PRESPAWN_NAMESPACE_CHANGED')
    active=_b1_raw(base/'active.json',B2_META_BYTES,budget)
    if active!=_b1_canonical(claim['claim'],budget):raise PrivateRunError('B2_PRESPAWN_ACTIVE_CHANGED')
    grant=ready()
    argv=[sys.executable,str(selected/'scripts'/'run_pdca.py'),'--root',prepared['binding']['workspace_root'],
          '--night',night,'--budget-seconds',str(grant)]
    capture=_b2_capture(argv,Path(workspace).resolve(),store,directory,budget,run_deadline,cleanup_deadline)
    return _b2_finish(prepared,store,claim,capture,budget,grant,reserves,entry_ns,run_ns,cleanup_ns,prior)



def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--code-root", type=Path, required=True)
    p.add_argument("--private-workspace", type=Path, required=True)
    p.add_argument("--private-store", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--night", required=True)
    p.add_argument("--revision", default="r1")
    a = p.parse_args()
    print(json.dumps(run_private(a.code_root, a.private_workspace, a.private_store,
                                 a.receipt, a.night, revision=a.revision), ensure_ascii=False))


if __name__ == "__main__":
    main()
