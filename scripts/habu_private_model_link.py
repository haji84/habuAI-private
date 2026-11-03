#!/usr/bin/env python3
"""Verified private handoff between a post-search PDCA and a research model.

Does not issue P0/P1, create negatives, train an official model, or promote a Champion.
Works only with explicitly supplied private files; never writes their bytes into Git.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

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


def build_handoff(pdca_path: Path, model_path: Path, gpx_path: Path | None = None) -> dict:
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
    result['link_sha256'] = digest(canon(result))
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
    ap.add_argument('--private-output', type=Path, required=True)
    args = ap.parse_args()
    try:
        sources = tuple(p for p in (args.pdca, args.model, args.gpx) if p is not None)
        _private_output_path(args.private_output, sources)
        result = build_handoff(args.pdca, args.model, args.gpx)
        saved = save_append_only(args.private_output, result, sources=sources)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
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
