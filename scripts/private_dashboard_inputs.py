"""Bounded, private diagnostics; reuse the existing log and XML validators."""
from __future__ import annotations
import base64
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import tempfile
from xml.etree import ElementTree as ET

from scripts.build_capture_dashboard import operational_night
from scripts.private_pdca_intake import _ReadBudget, _validate_gpx

MAX_FILE = 12 * 1024 * 1024
MAX_TOTAL = 48 * 1024 * 1024
MAX_REQUEST = 66 * 1024 * 1024

class SyncError(ValueError):
    """Messages are fixed, non-sensitive reason codes suitable for the UI."""

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def decode_files(files):
    if not isinstance(files, list) or not 1 <= len(files) <= 12:
        raise SyncError('INVALID_FILE_LIST')
    result = {}; total = 0
    for item in files:
        if not isinstance(item, dict) or set(item) != {'kind', 'content_b64'}:
            raise SyncError('INVALID_FILE_FIELDS')
        kind, text = item['kind'], item['content_b64']
        if kind not in ('log', 'gpx') or not isinstance(text, str) or len(text) > (MAX_FILE + 2) // 3 * 4:
            raise SyncError('INVALID_FILE_SIZE_OR_KIND')
        try:
            raw = base64.b64decode(text, validate=True)
        except (ValueError, TypeError):
            raise SyncError('INVALID_BASE64') from None
        total += len(raw)
        if not 0 < len(raw) <= MAX_FILE or total > MAX_TOTAL:
            raise SyncError('UPLOAD_TOO_LARGE')
        sha = digest(raw)
        if sha in result and result[sha]['kind'] != kind:
            raise SyncError('SOURCE_TYPE_CONFLICT')
        result[sha] = {'sha': sha, 'kind': kind, 'body': raw}
    return [result[key] for key in sorted(result)]

def inspect_sources(sources, root: Path, code_root: Path):
    reasons = []; logs = []; gps = []
    for source in sources:
        raw = source['body']
        if source['kind'] == 'log':
            try:
                logs.append(raw.decode('utf-8-sig'))
            except UnicodeError:
                reasons.append('LOG_UTF8_REQUIRED')
            continue
        try:
            with tempfile.TemporaryDirectory(dir=root) as directory:
                path = Path(directory) / 'source.gpx'; path.write_bytes(raw)
                _validate_gpx(path, len(raw), source['sha'], _ReadBudget(20))
            # Structural/time checks are diagnostics, NOT GPS-to-capture matching
            # or a certificate of full-night search effort.
            document = ET.fromstring(raw)
            if document.tag.rsplit('}', 1)[-1] != 'gpx':
                raise ValueError('root')
            ns = document.tag[:-3] if document.tag.endswith('gpx') else ''
            times = []; nights = set(); previous = None
            for track in document.findall(ns + 'trk'):
                for segment in track.findall(ns + 'trkseg'):
                    previous = None
                    for point in segment.findall(ns + 'trkpt'):
                        lat, lon = float(point.attrib['lat']), float(point.attrib['lon'])
                        if not math.isfinite(lat + lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
                            raise ValueError('coordinate')
                        stamp = point.findtext(ns + 'time')
                        if not stamp: raise ValueError('time')
                        from datetime import datetime
                        dt = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
                        if dt.tzinfo is None or (previous is not None and dt < previous):
                            raise ValueError('clock')
                        previous = dt; nights.add(operational_night(stamp)); times.append(dt)
            if not times: raise ValueError('empty')
            gps.append({'sha256': source['sha'], 'points': len(times), 'nights': sorted(nights),
                        'first': min(times).isoformat(), 'last': max(times).isoformat(),
                        'coverage': 'SAMPLED_TIMES_ONLY_NOT_COMPLETE_SEARCH'})
        except (ValueError, KeyError, TypeError, ET.ParseError):
            reasons.append('GPX_INVALID_OR_UNTIMED')
    parsed = {'nights': [], 'problems': 0, 'exactRepeats': 0}
    if not logs:
        reasons.append('LOG_REQUIRED_FOR_TALLY')
    elif sum(len(x.encode('utf-8')) for x in logs) > MAX_FILE:
        reasons.append('COMBINED_LOG_TOO_LARGE')
    else:
        script = """const fs=require('fs'),core=require(process.argv[1]);
const p=core.parse(JSON.parse(fs.readFileSync(0,'utf8')).join('\\n'));
console.log(JSON.stringify({nights:p.nights.map(n=>({night:n.night,captureHints:n.captureHints,starts:n.starts,ends:n.ends,ambiguousTimes:n.ambiguousTimes})),problems:p.problems.length,exactRepeats:p.exactRepeats}));"""
        try:
            p = subprocess.run(['node', '--max-old-space-size=192', '-e', script,
                                str(code_root / 'dashboard/intake-core.js')],
                               input=canonical(logs).encode(), capture_output=True, timeout=20, check=False)
            if p.returncode or len(p.stdout) > 256 * 1024: raise ValueError('parser')
            parsed = json.loads(p.stdout)
            if not 1 <= len(parsed['nights']) <= 128: raise ValueError('nights')
            if parsed['problems'] or any(n['ambiguousTimes'] for n in parsed['nights']):
                reasons.append('LOG_PARSE_REVIEW_REQUIRED')
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
            raise SyncError('LOG_PARSER_UNAVAILABLE') from None
    log_nights = {n['night'] for n in parsed['nights']}
    if any(set(g['nights']) - log_nights for g in gps) and logs:
        reasons.append('GPX_LOG_NIGHT_CONFLICT')
    return {'nights': parsed['nights'], 'gpx': gps, 'exact_repeats': parsed['exactRepeats'],
            'reasons': sorted(set(reasons)), 'scientific_training_eligible': False}
