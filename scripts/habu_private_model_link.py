#!/usr/bin/env python3
"""Verified private handoff between a post-search PDCA and a research model.

Does not issue P0/P1, create negatives, train an official model, or promote a Champion.
Works only with explicitly supplied private files; never writes their bytes into Git.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
import tempfile

if __package__:
    from .backfill_historical_environment import assert_private_directory
    from .private_pdca_intake import guard_private_path, _ReadBudget, _read_bytes
else:
    from backfill_historical_environment import assert_private_directory
    from private_pdca_intake import guard_private_path, _ReadBudget, _read_bytes

SCHEMA = 'habu-private-model-learning-link-v1'
RESEARCH_MODEL_SCHEMA = 'habu-exploratory-night-count-mle-v1'
RESEARCH_STATUS = 'EXPLORATORY_FIT_COMPLETED_NOT_ELIGIBLE_FOR_HABU_SCIENTIFIC_TRAINING'
RESEARCH_MODEL_SCHEMA_V11 = 'habu-research-nightcount-poisson-v1.1'
RESEARCH_STATUS_V11 = 'RETROSPECTIVE_FIT_REPRODUCED_RESEARCH_ONLY_NOT_SCIENTIFIC_TRAINING'
HEX64 = re.compile(r'^[0-9a-f]{64}$')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canon(data: object) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def read_json(path: Path, max_bytes: int = 2_000_000) -> tuple[dict, str]:
    path = Path(path).absolute()
    guard_private_path(Path(path.anchor), path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Private artifact must be an existing regular file')
    with path.open('rb') as fp:
        content = fp.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValueError('Private artifact too large')
    def no_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    value = json.loads(content, object_pairs_hook=no_duplicates)
    if not isinstance(value, dict):
        raise ValueError('JSON object expected')
    return value, digest(content)



def research_metadata(model: dict, gpx_sha: str, night: str) -> tuple[str, str, float | None]:
    """Verify a known research-only format without granting scientific authority."""
    schema = model.get('schema_version')
    if schema == RESEARCH_MODEL_SCHEMA:
        if model.get('status') != RESEARCH_STATUS:
            raise ValueError('Unsupported or falsely promoted research model')
        flags = model.get('authorities')
        if not isinstance(flags, dict) or not all(flags.get(k) is False for k in (
                'official_p0', 'scientific_training_qualified',
                'champion_promotion', 'production_active')):
            raise ValueError('Research-only authorities required')
        field = 'artifact_sha256'
        rate = model.get('fit_summary', {}).get('fitted_capture_rate_per_session_hour_proxy')
    elif schema == RESEARCH_MODEL_SCHEMA_V11:
        if model.get('status') != RESEARCH_STATUS_V11:
            raise ValueError('Unsupported or falsely promoted research model')
        flags = model.get('authorized_for_prediction_chat')
        if (not isinstance(flags, dict) or flags.get('reference_only') is not True or
                flags.get('official_prediction') is not False or flags.get('champion') is not False or
                model.get('100m_10min_prediction_model') is not False or
                model.get('official_selector_fit') is not False or
                model.get('negative_labels_created') != 0 or
                model.get('privacy') != 'PRIVATE_LIBRARY_ONLY' or
                model.get('permissions') != {'main_merge': False, 'deploy': False,
                                              'champion_promotion': False}):
            raise ValueError('Research-only authorities required')
        lineage = model.get('source_lineage')
        if not isinstance(lineage, dict) or not isinstance(lineage.get('private_original_gpx_sha256'), dict):
            raise ValueError('Research source lineage missing')
        if any(n.get('night') == night for n in model.get('training_nights', [])):
            if lineage['private_original_gpx_sha256'].get(night) != gpx_sha:
                raise ValueError('Research GPX source lineage mismatch')
        field = 'model_payload_sha256'
        rate = model.get('poisson_rate_per_hour_proxy')
    else:
        raise ValueError('Unsupported or falsely promoted research model')
    embedded = model.get(field)
    if (not isinstance(embedded, str) or not HEX64.fullmatch(embedded) or
            digest(canon({k: v for k, v in model.items() if k != field})) != embedded):
        raise ValueError('Model internal content hash mismatch')
    if rate is not None and (type(rate) not in (int, float) or not 0 <= rate < 1e6):
        raise ValueError('Invalid research rate')
    return schema, embedded, rate


def build_handoff(pdca_path: Path, model_path: Path, gpx_path: Path | None = None, *,
                  route_evidence=None, route_evidence_sha256=None,
                  route_receipt=None, route_receipt_sha256=None,
                  qualified_fit_report=None, qualified_fit_report_sha256=None,
                  candidate_model=None, candidate_model_sha256=None, _reader=None) -> dict:
    pdca, pdca_sha = read_json(pdca_path)
    model, model_sha = read_json(model_path)
    night = pdca.get('night_jst')
    if not isinstance(night, str) or not re.fullmatch(r'20\d\d-\d\d-\d\d', night):
        raise ValueError('Operational night not verified')
    actual = pdca.get('actual', {})
    if not isinstance(actual, dict) or type(actual.get('captured_habu')) is not int or actual['captured_habu'] < 0:
        raise ValueError('Capture count missing')
    gp = pdca.get('input_data', {}).get('gpx_sha256')
    if not isinstance(gp, str) or not HEX64.fullmatch(gp):
        raise ValueError('Missing GPX source digest')
    if gpx_path is not None:
        if gpx_path.is_symlink() or not gpx_path.is_file() or digest(gpx_path.read_bytes()) != gp:
            raise ValueError('Raw GPX source mismatch')
    research_schema, embedded, rate = research_metadata(model, gp, night)
    pauses = pdca.get('gpx_analysis', {}).get('gap', None)
    approx = actual.get('intentional_pause_minutes_approx', 0)
    if type(approx) not in (int, float) or not 0 <= approx < 720:
        raise ValueError('Invalid pause duration')
    if pauses:
        if (not isinstance(pauses, dict) or
                pauses.get('classification') != 'user_confirmed_intentional_search_pause' or
                pauses.get('excluded_from_search_effort') is not True or
                pauses.get('gps_failure') is not False or approx <= 0):
            raise ValueError('Unknown GPS gap cannot become measured search effort')
        pause_kind = 'OWNER_CONFIRMED_INTENTIONAL_SEARCH_PAUSE'
    else:
        if approx != 0:
            raise ValueError('Unmatched pause duration')
        pause_kind = 'NO_CONFIRMED_PAUSE'
    if not isinstance(model.get('training_nights'), list):
        raise ValueError('Missing research model training nights')
    captures = [x for x in model['training_nights'] if x.get('night') == night]
    if len(captures) > 1:
        raise ValueError('Duplicated model training night')
    if captures and (captures[0].get('count') != actual['captured_habu'] or
                     captures[0].get('pause_minutes_approx', 0) != approx):
        raise ValueError('Model and PDCA outcomes/pause differ')
    result = {
        'schema_version': SCHEMA, 'operational_night': night,
        'status': 'PRIVATE_RESEARCH_HANDOFF_LINKED',
        'source_sha256': {'pdca': pdca_sha, 'research_model': model_sha, 'gpx': gp},
        'captured_habu': actual['captured_habu'],
        'pause': {'kind': pause_kind, 'approx_minutes': approx,
                  'excluded_from_search_effort': bool(pauses)},
        'research_model': {'schema_version': research_schema,
                           'artifact_sha256': embedded,
                           'fitted_captures_per_session_hour_proxy': rate,
                           'scope': 'NIGHT_COUNT_RESEARCH_ONLY'},
        'next_training': {'status': 'ALREADY_IN_RESEARCH_MODEL' if captures else 'STAGED_FOR_PRIVATE_EVIDENCE_REVIEW',
                          'research_model_already_contains_night': bool(captures),
                          'source_qualified': False,
                          'eligible_for_automatic_scientific_fit': False,
                          'why': 'Audited scoped active search, complete outcomes and historical as-of features not qualified'},
        'next_prediction': {'status': 'PROVISIONAL_NOT_FREEZABLE',
                            'automatic_champion_use': False,
                            'why': 'No approved production model and required ex-ante feature/universe evidence'},
        'forbidden': ['NO_PUBLIC_COORDINATES', 'NO_NEGATIVE_FROM_PAUSE', 'NO_RETROACTIVE_P0',
                      'NO_AUTOMATIC_MODEL_PROMOTION']
    }
    diagnostics = _diagnostic_refs(gp, route_evidence, route_evidence_sha256,
        route_receipt, route_receipt_sha256, qualified_fit_report,
        qualified_fit_report_sha256, candidate_model, candidate_model_sha256, _reader)
    if diagnostics:
        result['diagnostic_refs'] = diagnostics
    result['link_sha256'] = digest(canon(result))
    return result


def _aware(value):
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError('Aware diagnostic time required')
    return stamp


def _document(raw, check):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate diagnostic JSON key')
            value[key] = item
        return value
    def nonfinite(_):
        raise ValueError('Nonfinite diagnostic JSON')
    # Reject deep containers before decoding, including inside large artifacts.
    depth, quoted, escaped = 0, False, False
    for index, char in enumerate(raw.decode('utf-8')):
        if index % 4096 == 0:
            check()
        if quoted:
            if escaped: escaped = False
            elif char == '\\': escaped = True
            elif char == '"': quoted = False
        elif char == '"': quoted = True
        elif char in '[{':
            depth += 1
            if depth > 48: raise ValueError('Diagnostic JSON depth limit')
        elif char in ']}': depth -= 1
    value = json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)
    pending, count = [value], 0
    while pending:
        check(); item = pending.pop(); count += 1
        if count > 2_000_000: raise ValueError('Diagnostic JSON node limit')
        if isinstance(item, (dict, list)):
            if len(pending)+count+len(item) > 2_000_000:
                raise ValueError('Diagnostic JSON width limit')
            pending.extend(item.values() if isinstance(item, dict) else item)
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError('Nonfinite diagnostic JSON')
    if type(value) is not dict: raise ValueError('Diagnostic JSON object required')
    return value


class _DiagnosticReader:
    """One bounded read/rescan ledger; hashes attest bytes, not source identity."""
    def __init__(self):
        self.budget = _ReadBudget(30)
        self.refs = {}

    def read(self, path, checksum, limit):
        if type(checksum) is not str or not HEX64.fullmatch(checksum):
            raise ValueError('Explicit diagnostic SHA256 required')
        path = assert_private_directory(Path(path).absolute())
        guard_private_path(Path(path.anchor), path)
        raw = _read_bytes(path, limit, self.budget)
        if digest(raw) != checksum:
            raise ValueError('Diagnostic bytes do not match SHA256')
        row = (checksum, len(raw))
        if path in self.refs and self.refs[path] != row:
            raise ValueError('Diagnostic source changed')
        self.refs[path] = row
        return raw

    def document(self, path, checksum, limit=2_000_000):
        raw = self.read(path, checksum, limit)
        return _document(raw, self.budget.check), raw

    def rescan(self):
        for path, (checksum, size) in list(self.refs.items()):
            self.read(path, checksum, size)


def _route_authority(value):
    flags = {'candidate_database_updated', 'model_created_or_updated',
             'formal_positive_qualified', 'formal_negative_qualified',
             'p0_authorized', 'champion_promoted'}
    if (type(value) is not dict or set(value) != flags | {'canonical_capture_tally_delta'}
            or any(value[key] is not False for key in flags)
            or type(value['canonical_capture_tally_delta']) is not int
            or value['canonical_capture_tally_delta'] != 0):
        raise ValueError('Route evidence authority must remain false')


def _route_diagnostic_refs(reader, artifact, artifact_sha, receipt, receipt_sha, gpx_sha):
    route, raw = reader.document(artifact, artifact_sha, 160*1024*1024)
    proof, proof_raw = reader.document(receipt, receipt_sha)
    route_fields = {'schema_version', 'phase', 'source_manifest_sha256', 'source_records', 'routes',
        'capture_evidence', 'authority', 'runtime_code_sha256', 'python_version', 'limitations'}
    proof_fields = {'schema_version', 'source_manifest_sha256', 'artifact_sha256', 'artifact_size_bytes',
        'sources_rechecked_before_commit', 'authority', 'runtime_code_sha256', 'python_version',
        'reading_started_at_utc', 'artifact_readback_at_utc', 'receipt_prepared_at_utc', 'receipt_payload_sha256'}
    if (set(route) != route_fields or set(proof) != proof_fields
            or route.get('schema_version') != 'habu-private-recovered-route-evidence-v1'
            or route.get('phase') != 'POST_SEARCH_RESEARCH_ONLY'
            or proof.get('schema_version') != 'habu-route-recovery-completion-v1'):
        raise ValueError('Canonical research route and completion receipt required')
    _route_authority(route.get('authority')); _route_authority(proof.get('authority'))
    without_seal = {k:v for k,v in proof.items() if k != 'receipt_payload_sha256'}
    if (proof.get('receipt_payload_sha256') != digest(canon(without_seal)+b'\n')
            or proof_raw != canon(proof)+b'\n'
            or proof.get('artifact_sha256') != artifact_sha
            or type(proof.get('artifact_size_bytes')) is not int
            or proof['artifact_size_bytes'] != len(raw)
            or proof.get('sources_rechecked_before_commit') is not True):
        raise ValueError('Route completion seal/bytes mismatch')
    manifest_sha = route.get('source_manifest_sha256')
    codes = route.get('runtime_code_sha256')
    if (type(manifest_sha) is not str or not HEX64.fullmatch(manifest_sha)
            or proof.get('source_manifest_sha256') != manifest_sha
            or type(codes) is not dict or not 1 <= len(codes) <= 64
            or any(type(v) is not str or not HEX64.fullmatch(v) for v in codes.values())
            or proof.get('runtime_code_sha256') != codes
            or proof.get('python_version') != route.get('python_version')):
        raise ValueError('Route completion lineage mismatch')
    started, readback, prepared = (_aware(proof[key]) for key in
        ('reading_started_at_utc', 'artifact_readback_at_utc', 'receipt_prepared_at_utc'))
    if not started <= readback <= prepared <= datetime.now(timezone.utc):
        raise ValueError('Route completion chronology invalid')
    records, routes = route.get('source_records'), route.get('routes')
    if type(records) is not list or not 1 <= len(records) <= 32 or type(routes) is not list:
        raise ValueError('Bounded canonical route source records required')
    members = set()
    for record in records:
        if _aware(record['received_at']) > started:
            raise ValueError('Route receipt predates source receipt')
        if record.get('kind') in {'gpx', 'field-session', 'jsonl'} and record.get('sha256') == gpx_sha:
            members.add(record['source_id'])
    if not members or not any(r.get('source_sha256') == gpx_sha and r.get('source_id') in members for r in routes):
        raise ValueError('PDCA GPX is not a member of recovered route evidence')
    return dict(artifact_sha256=artifact_sha, artifact_size_bytes=len(raw),
        receipt_sha256=receipt_sha, receipt_size_bytes=len(proof_raw),
        source_manifest_sha256=manifest_sha, phase=route['phase'],
        verification_scope='BYTE_BOUND_REFERENCE_NOT_SOURCE_QUALIFICATION')


def _qualified_fit_diagnostic_refs(reader, path, checksum, candidate, candidate_sha):
    report, raw = reader.document(path, checksum)
    if (report.get('schema_version') != 'habu-private-qualified-fit-cycle-v1'
            or report.get('official_prediction_authorized') is not False
            or report.get('production_model_activated') is not False):
        raise ValueError('Existing research-only qualified-fit report required')
    night = report.get('heldout_night')
    if type(night) is not str or datetime.fromisoformat(night).date().isoformat() != night:
        raise ValueError('Qualified-fit heldout night required')
    base = dict(report_sha256=checksum, report_size_bytes=len(raw), status=report.get('status'),
        heldout_night=night, verification_scope='BYTE_BOUND_REFERENCE_NOT_SOURCE_QUALIFICATION')
    if report.get('status') == 'BLOCKED':
        required = {'schema_version', 'status', 'reason', 'heldout_night', 'eligible_training_units',
                    'model_sha256', 'official_prediction_authorized', 'production_model_activated'}
        reasons = {'MISSING_SOURCE_QUALIFIED_G0_MANIFEST', 'QUALIFIED_MANIFEST_SOURCE_NOT_AVAILABLE',
                   'G0_TRAINING_SOURCE_GATE_BLOCKED', 'INSUFFICIENT_SOURCE_QUALIFIED_TRAINING_UNITS'}
        units = report.get('eligible_training_units')
        if (not required <= set(report) or set(report)-required-{'detail','counts','blockers','source_receipt_sha256'}
                or report['reason'] not in reasons or report['model_sha256'] is not None
                or candidate is not None or candidate_sha is not None
                or units is not None and (type(units) is not int or not 0 <= units <= 100_000)):
            raise ValueError('Blocked qualified-fit report cannot declare a candidate')
        if 'counts' in report and (type(report['counts']) is not dict
                or report['counts'].get('accepted_rows') != units
                or any(type(v) is not int or not 0 <= v <= 100_000 for v in report['counts'].values())):
            raise ValueError('Blocked fit count mismatch')
        return dict(base, eligible_training_units=units, model_sha256=None)
    fields = {'schema_version', 'status', 'heldout_night', 'input_manifest_sha256', 'source_receipt_sha256',
        'training_selection_sha256', 'model_sha256', 'model_internal_sha256', 'model_relative_path',
        'fit_counts', 'stage1_top10_recall', 'formal_100m_10min', 'future_independent_validation',
        'official_prediction_authorized', 'production_model_activated', 'champion_promotion', 'report_sha256'}
    if (report.get('status') != 'RESEARCH_CANDIDATE_FITTED' or set(report) != fields
            or report['report_sha256'] != digest(canon({k:v for k,v in report.items() if k!='report_sha256'}))
            or report['model_sha256'] != candidate_sha
            or report['model_relative_path'] != 'candidates/'+str(candidate_sha)+'.json'
            or report['stage1_top10_recall'] != 'NOT_EVALUATED' or report['formal_100m_10min'] != 'NOT_EVALUATED'
            or report['future_independent_validation'] != 'NOT_PERFORMED' or report['champion_promotion'] != 'BLOCKED'):
        raise ValueError('Bound unvalidated qualified-fit report required')
    for key in ('input_manifest_sha256', 'source_receipt_sha256', 'training_selection_sha256'):
        if type(report[key]) is not str or not HEX64.fullmatch(report[key]):
            raise ValueError('Qualified-fit source SHA256 required')
    # The existing registered reader remains authoritative for candidate shape.
    # Its namespace is models/candidates, so validate an identical temporary copy.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
    from prospective_spacetime import _read_candidate_model, MAX_MODEL_BYTES
    model_raw = reader.read(candidate, candidate_sha, MAX_MODEL_BYTES)
    _document(model_raw, reader.budget.check)
    with tempfile.TemporaryDirectory(prefix='habu-candidate-readback-') as temp:
        root = assert_private_directory(Path(temp)); target = root/'models/candidates/validated.json'
        target.parent.mkdir(parents=True); target.write_bytes(model_raw)
        byte_budget = [0]
        model = _read_candidate_model(root, 'models/candidates/validated.json', candidate_sha,
            budget=byte_budget, check=reader.budget.check)
        reader.budget.bytes_read += byte_budget[0]; reader.budget.check()
    rows = report['fit_counts'].get('rows')
    if (type(rows) is not int or not 1 <= rows <= 100_000
            or report['model_internal_sha256'] != model['model_sha256']
            or report['training_selection_sha256'] != model['training_data_sha256']):
        raise ValueError('Qualified-fit report and candidate differ')
    return dict(base, eligible_training_units=rows, model_sha256=candidate_sha,
                qualification=model['qualification'])


def _diagnostic_refs(gpx_sha, artifact, artifact_sha, receipt, receipt_sha,
                     report, report_sha, candidate, candidate_sha, reader):
    route = (artifact, artifact_sha, receipt, receipt_sha)
    if any(v is not None for v in route) and any(v is None for v in route):
        raise ValueError('All four route diagnostic arguments required')
    if (report is None) != (report_sha is None) or (candidate is None) != (candidate_sha is None):
        raise ValueError('Diagnostic path and explicit SHA256 required together')
    if report is None and candidate is not None:
        raise ValueError('Candidate requires a qualified-fit report')
    result = {}; reader = reader or _DiagnosticReader()
    if artifact is not None:
        result['route_recovery'] = _route_diagnostic_refs(reader, *route, gpx_sha)
    if report is not None:
        result['qualified_fit'] = _qualified_fit_diagnostic_refs(reader, report, report_sha, candidate, candidate_sha)
    reader.rescan()
    return result


def _private_output_path(path: Path, sources: tuple[Path, ...]) -> Path:
    # Inspect the original lexical path before resolve can hide a link/junction.
    path = assert_private_directory(path)
    guard_private_path(Path(path.anchor), path)
    for source in sources:
        source = Path(source).absolute()
        guard_private_path(Path(source.anchor), source)
        if (path == source or source in path.parents or path in source.parents or
                path.exists() and source.exists() and path.samefile(source)):
            raise ValueError('PRIVATE_OUTPUT_SOURCE_CONFLICT')
    return path


def save_append_only(path: Path, result: dict, *, sources: tuple[Path, ...] = ()) -> str:
    path = _private_output_path(path, sources)
    payload = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    path.parent.mkdir(parents=True, exist_ok=True)
    _private_output_path(path, sources)
    try:
        with path.open('xb') as fp:
            fp.write(payload)
    except FileExistsError:
        _private_output_path(path, sources)
        try:
            identical = _read_bytes(path, len(payload), _ReadBudget(30)) == payload
        except (OSError, ValueError):
            identical = False
        if not identical:
            raise ValueError('Conflicting handoff: append a new revision; never overwrite')
    _private_output_path(path, sources)
    if _read_bytes(path, len(payload), _ReadBudget(30)) != payload:
        raise ValueError('Handoff verification failed')
    return digest(payload)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pdca', type=Path, required=True)
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--gpx', type=Path)
    diagnostic_paths = ('route_evidence', 'route_receipt', 'qualified_fit_report', 'candidate_model')
    for name in diagnostic_paths:
        ap.add_argument('--'+name.replace('_', '-'), type=Path)
        ap.add_argument('--'+name.replace('_', '-')+'-sha256')
    ap.add_argument('--private-output', type=Path, required=True)
    args = ap.parse_args()
    try:
        sources = tuple(p for p in (args.pdca, args.model, args.gpx,
                        *(getattr(args, name) for name in diagnostic_paths)) if p is not None)
        _private_output_path(args.private_output, sources)
        reader = _DiagnosticReader()
        options = {key: getattr(args, key) for name in diagnostic_paths for key in (name, name+'_sha256')}
        result = build_handoff(args.pdca, args.model, args.gpx, _reader=reader, **options)
        saved = save_append_only(args.private_output, result, sources=sources)
        reader.rescan()
        _private_output_path(args.private_output, sources)
        if digest(_read_bytes(args.private_output, 2_000_000, reader.budget)) != saved:
            raise ValueError('Handoff changed at completion')
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError, ImportError) as exc:
        print(json.dumps({'status': 'BLOCKED', 'reason_code': 'PRIVATE_HANDOFF_VALIDATION_FAILED',
                          'error_type': type(exc).__name__, 'completion_report_validated': False,
                          'official_prediction_authorized': False, 'production_model_activated': False}))
        return 2
    print(json.dumps({'status': result['status'], 'night': result['operational_night'],
                      'next_training': result['next_training']['status'],
                      'next_prediction': result['next_prediction']['status'],
                      'link_sha256': result['link_sha256'], 'saved_sha256': saved}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
