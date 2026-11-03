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

SCHEMA = 'habu-private-model-learning-link-v1'
RESEARCH_MODEL_SCHEMA = 'habu-exploratory-night-count-mle-v1'
RESEARCH_STATUS = 'EXPLORATORY_FIT_COMPLETED_NOT_ELIGIBLE_FOR_HABU_SCIENTIFIC_TRAINING'
HEX64 = re.compile(r'^[0-9a-f]{64}$')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canon(data: object) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def read_json(path: Path, max_bytes: int = 2_000_000) -> tuple[dict, str]:
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


def build_handoff(pdca_path: Path, model_path: Path, gpx_path: Path | None = None) -> dict:
    pdca, pdca_sha = read_json(pdca_path)
    model, model_sha = read_json(model_path)
    night = pdca.get('night_jst')
    if not isinstance(night, str) or not re.fullmatch(r'20\d\d-\d\d-\d\d', night):
        raise ValueError('Operational night not verified')
    if model.get('schema_version') != RESEARCH_MODEL_SCHEMA or model.get('status') != RESEARCH_STATUS:
        raise ValueError('Unsupported or falsely promoted research model')
    authorities = model.get('authorities')
    if not isinstance(authorities, dict) or not all(authorities.get(k) is False for k in (
            'official_p0', 'scientific_training_qualified', 'champion_promotion', 'production_active')):
        raise ValueError('Research-only authorities required')
    embedded = model.get('artifact_sha256')
    if not isinstance(embedded, str) or digest(canon({k: v for k,v in model.items() if k != 'artifact_sha256'})) != embedded:
        raise ValueError('Model internal content hash mismatch')
    actual = pdca.get('actual', {})
    if not isinstance(actual, dict) or type(actual.get('captured_habu')) is not int or actual['captured_habu'] < 0:
        raise ValueError('Capture count missing')
    gp = pdca.get('input_data', {}).get('gpx_sha256')
    if not isinstance(gp, str) or not HEX64.fullmatch(gp):
        raise ValueError('Missing GPX source digest')
    if gpx_path is not None:
        if gpx_path.is_symlink() or not gpx_path.is_file() or digest(gpx_path.read_bytes()) != gp:
            raise ValueError('Raw GPX source mismatch')
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
        'research_model': {'schema_version': RESEARCH_MODEL_SCHEMA,
                           'artifact_sha256': embedded,
                           'fitted_captures_per_session_hour_proxy': model.get('fit_summary', {}).get('fitted_capture_rate_per_session_hour_proxy'),
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


def save_append_only(path: Path, result: dict) -> str:
    payload = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('xb') as fp:
            fp.write(payload)
    except FileExistsError:
        if path.read_bytes() != payload:
            raise ValueError('Conflicting handoff: append a new revision; never overwrite')
    if path.read_bytes() != payload:
        raise ValueError('Handoff verification failed')
    return digest(payload)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pdca', type=Path, required=True)
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--gpx', type=Path)
    ap.add_argument('--private-output', type=Path, required=True)
    args = ap.parse_args()
    result = build_handoff(args.pdca, args.model, args.gpx)
    saved = save_append_only(args.private_output, result)
    print(json.dumps({'status': result['status'], 'night': result['operational_night'],
                      'next_training': result['next_training']['status'],
                      'next_prediction': result['next_prediction']['status'],
                      'link_sha256': result['link_sha256'], 'saved_sha256': saved}, ensure_ascii=False))


if __name__ == '__main__':
    main()
