"""Guarded, bounded GPX transport phase; no writes or source-role authority."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import lzma
import os
from pathlib import Path
import re
import stat

from master_inventory import local_path

ANCHOR = 'data/raw/attachment_archives/gpx'
MAX_BYTES = 100 * 1024 * 1024
MAX_DECODED_BYTES = 100 * 1024 * 1024
MAX_DISCOVERY_ENTRIES = 4000
XZ_MEMORY_LIMIT = 128 * 1024 * 1024
STEP_BYTES = 65536
FIELDS = frozenset(('schema_version', 'original_filename', 'kind', 'source',
                    'source_ref', 'raw_size_bytes', 'raw_sha256', 'compression',
                    'compressed_size_bytes', 'compressed_sha256', 'transfer_encoding',
                    'encoded_chars', 'part_chars', 'part_count', 'part_glob'))


class GpxAttachmentError(ValueError):
    """Known malformed transport/path; never a caller callback exception."""


def _capacity(reason):
    # Runtime import avoids adding a module-import cycle to the legacy auditor.
    from evidence_audit import AuditBudgetExceeded
    raise AuditBudgetExceeded(reason)


def _path(root, relative):
    try:
        return local_path(root, relative)
    except (ValueError, OSError) as exc:
        raise GpxAttachmentError('ATTACHMENT_PATH: ' + str(exc)) from exc


def _metadata(root, relative, *, check, missing=False):
    check()
    path = _path(root, relative)
    try:
        info = path.lstat()
    except FileNotFoundError:
        if missing:
            return None
        raise GpxAttachmentError('ATTACHMENT_MEMBER_MISSING') from None
    except OSError as exc:
        raise GpxAttachmentError('ATTACHMENT_METADATA') from exc
    check()
    return info


def _entries(root, relative, *, check, counter):
    check()
    directory = _path(root, relative)
    try:
        entries = os.scandir(directory)
    except OSError as exc:
        raise GpxAttachmentError('ATTACHMENT_DIRECTORY') from exc
    names = []
    with entries:
        while True:
            check()
            try:
                entry = next(entries)
            except StopIteration:
                break
            except OSError as exc:
                raise GpxAttachmentError('ATTACHMENT_DIRECTORY') from exc
            counter[0] += 1
            if counter[0] > MAX_DISCOVERY_ENTRIES:
                _capacity('ATTACHMENT_DISCOVERY_LIMIT')
            # Guard the spelling before even requesting entry metadata.
            _path(root, relative + '/' + entry.name)
            names.append(entry.name)
    check()
    return sorted(names)


def _members(root, directory, *, check, counter):
    info = _metadata(root, directory, check=check)
    if not stat.S_ISDIR(info.st_mode):
        raise GpxAttachmentError('ATTACHMENT_DIRECTORY_TYPE')
    names = _entries(root, directory, check=check, counter=counter)
    for name in names:
        if name != 'manifest.json' and not re.fullmatch(r'part_[0-9]{3,4}\.b64', name):
            raise GpxAttachmentError('ATTACHMENT_MEMBER_NAME')
        info = _metadata(root, directory + '/' + name, check=check)
        if not stat.S_ISREG(info.st_mode):
            raise GpxAttachmentError('ATTACHMENT_MEMBER_TYPE')
    if 'manifest.json' not in names:
        raise GpxAttachmentError('ATTACHMENT_MANIFEST_MISSING')
    return tuple(names)


def discover_gpx_attachment_archives(root, *, check):
    """Return bounded paths/membership; no payload reads, links, or recursion."""
    root = Path(root)
    info = _metadata(root, ANCHOR, check=check, missing=True)
    if info is None:
        return (), (False, ())
    if not stat.S_ISDIR(info.st_mode):
        raise GpxAttachmentError('ATTACHMENT_ANCHOR_TYPE')
    counter = [0]
    records = []
    for name in _entries(root, ANCHOR, check=check, counter=counter):
        if not re.fullmatch('[0-9a-f]{64}', name):
            raise GpxAttachmentError('ATTACHMENT_DIRECTORY_NAME')
        directory = ANCHOR + '/' + name
        records.append((name, _members(root, directory, check=check, counter=counter)))
    check()
    return tuple(ANCHOR + '/' + name + '/manifest.json' for name, _ in records), (True, tuple(records))


def _json_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise GpxAttachmentError('ATTACHMENT_DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def _constant(_):
    raise GpxAttachmentError('ATTACHMENT_NONFINITE_JSON')


def _manifest(raw, raw_sha):
    try:
        m = json.loads(raw.decode('utf-8'), object_pairs_hook=_json_pairs,
                       parse_constant=_constant)
    except GpxAttachmentError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise GpxAttachmentError('ATTACHMENT_MANIFEST_JSON') from exc
    if type(m) is not dict or set(m) != FIELDS:
        raise GpxAttachmentError('ATTACHMENT_MANIFEST_FIELDS')
    fixed = dict(schema_version='habu-text-safe-byte-archive-v1', kind='gpx',
                 compression='xz', transfer_encoding='base64', part_glob='part_*.b64')
    if any(m[key] != value for key, value in fixed.items()):
        raise GpxAttachmentError('ATTACHMENT_MANIFEST_FORMAT')
    for key in ('raw_sha256', 'compressed_sha256'):
        if type(m[key]) is not str or not re.fullmatch('[0-9a-f]{64}', m[key]):
            raise GpxAttachmentError('ATTACHMENT_MANIFEST_SHA')
    if m['raw_sha256'] != raw_sha:
        raise GpxAttachmentError('ATTACHMENT_DIRECTORY_SHA')
    for key, cap in (('raw_size_bytes', MAX_BYTES), ('compressed_size_bytes', MAX_BYTES),
                     ('part_chars', 1024 * 1024), ('part_count', 4000),
                     ('encoded_chars', 4 * ((MAX_BYTES + 2) // 3))):
        if type(m[key]) is not int or not 0 < m[key] <= cap:
            raise GpxAttachmentError('ATTACHMENT_MANIFEST_BOUND')
    if (m['part_chars'] % 4 or m['encoded_chars'] != 4 * ((m['compressed_size_bytes'] + 2) // 3)
            or m['part_count'] != (m['encoded_chars'] + m['part_chars'] - 1) // m['part_chars']):
        raise GpxAttachmentError('ATTACHMENT_MANIFEST_LENGTH')
    for key, limit in (('original_filename', 1024), ('source', 4096), ('source_ref', 4096)):
        value = m[key]
        if key == 'source_ref' and value is None:
            continue
        if type(value) is not str or not 0 < len(value) <= limit or '\0' in value:
            raise GpxAttachmentError('ATTACHMENT_MANIFEST_TEXT')
        try:
            value.encode('utf-8')
        except UnicodeError as exc:
            raise GpxAttachmentError('ATTACHMENT_MANIFEST_TEXT') from exc
    return m


def _read(root, relative, limit, *, read, check):
    info = _metadata(root, relative, check=check)
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise GpxAttachmentError('ATTACHMENT_MEMBER_SIZE_OR_TYPE')
    check()
    _path(root, relative)
    raw = read(relative, max_bytes=limit)
    check()
    if type(raw) is not bytes or len(raw) > limit:
        raise GpxAttachmentError('ATTACHMENT_READ_SIZE_OR_TYPE')
    return raw


def _ref(path, raw, *, check):
    check()
    ref = dict(path=path, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    check()
    return ref


def read_gpx_attachment_archive(root, manifest_path, *, read, check, consume_decoded_bytes):
    """Return verified phase bytes/crosswalk; caller must finalize source closure."""
    if type(manifest_path) is not str:
        raise GpxAttachmentError('ATTACHMENT_MANIFEST_PATH')
    match = re.fullmatch(re.escape(ANCHOR) + r'/([0-9a-f]{64})/manifest\.json', manifest_path)
    if match is None:
        raise GpxAttachmentError('ATTACHMENT_MANIFEST_PATH')
    directory = manifest_path.rsplit('/', 1)[0]
    members = _members(root, directory, check=check, counter=[0])
    mb = _read(root, manifest_path, 65536, read=read, check=check)
    check()
    m = _manifest(mb, match[1])
    check()
    part_names = tuple(f'part_{i:03d}.b64' for i in range(m['part_count']))
    if set(members) != {'manifest.json', *part_names}:
        raise GpxAttachmentError('ATTACHMENT_PART_MEMBERSHIP')
    parts = []
    compressed = bytearray()
    for index, name in enumerate(part_names):
        check()
        expected = min(m['part_chars'], m['encoded_chars'] - index * m['part_chars'])
        path = directory + '/' + name
        encoded = _read(root, path, expected, read=read, check=check)
        if len(encoded) != expected:
            raise GpxAttachmentError('ATTACHMENT_PART_LENGTH')
        if index < m['part_count'] - 1 and b'=' in encoded:
            raise GpxAttachmentError('ATTACHMENT_PREMATURE_BASE64_PADDING')
        try:
            chunk = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise GpxAttachmentError('ATTACHMENT_BASE64') from exc
        check()
        if len(compressed) + len(chunk) > m['compressed_size_bytes']:
            raise GpxAttachmentError('ATTACHMENT_COMPRESSED_SIZE')
        compressed.extend(chunk)
        parts.append(_ref(path, encoded, check=check))
    check()
    compressed_sha = hashlib.sha256(compressed).hexdigest()
    check()
    if len(compressed) != m['compressed_size_bytes'] or compressed_sha != m['compressed_sha256']:
        raise GpxAttachmentError('ATTACHMENT_COMPRESSED_IDENTITY')
    check()
    try:
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ, memlimit=XZ_MEMORY_LIMIT)
    except lzma.LZMAError as exc:
        raise GpxAttachmentError('ATTACHMENT_XZ') from exc
    check()
    output = []
    produced = 0
    position = 0
    while not decoder.eof:
        check()
        remaining = consume_decoded_bytes(0)
        if type(remaining) is not int or remaining < 0:
            raise ValueError('Invalid caller decoded allowance')
        if decoder.needs_input:
            if position == len(compressed):
                break
            data = compressed[position:position + STEP_BYTES]
            position += len(data)
        else:
            data = b''
        limit = min(STEP_BYTES, m['raw_size_bytes'] - produced + 1, remaining + 1)
        try:
            chunk = decoder.decompress(data, max_length=limit)
        except lzma.LZMAError as exc:
            if 'Memory usage limit' in str(exc):
                _capacity('ATTACHMENT_XZ_MEMORY_LIMIT')
            raise GpxAttachmentError('ATTACHMENT_XZ') from exc
        consume_decoded_bytes(len(chunk))
        check()
        produced += len(chunk)
        if produced > m['raw_size_bytes']:
            raise GpxAttachmentError('ATTACHMENT_RAW_SIZE')
        output.append(chunk)
    check()
    if not decoder.eof or decoder.unused_data or position != len(compressed):
        raise GpxAttachmentError('ATTACHMENT_XZ_CLOSURE')
    raw = b''.join(output)
    check()
    raw_sha = hashlib.sha256(raw).hexdigest()
    check()
    if len(raw) != m['raw_size_bytes'] or raw_sha != m['raw_sha256']:
        raise GpxAttachmentError('ATTACHMENT_RAW_IDENTITY')
    crosswalk = dict(schema_version='habu-gpx-attachment-transport-v1',
                     manifest_ref=_ref(manifest_path, mb, check=check), parts=parts,
                     compressed=dict(sha256=compressed_sha, size_bytes=len(compressed)),
                     reconstructed=dict(sha256=raw_sha, size_bytes=len(raw)),
                     declared_original_filename=m['original_filename'], declared_source=m['source'],
                     declared_source_ref=m['source_ref'], integrity='BYTE_EXACT_VERIFIED')
    check()
    return raw, crosswalk
