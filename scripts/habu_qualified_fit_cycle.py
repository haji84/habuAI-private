#!/usr/bin/env python3
"""One private, evidence-gated G0 TRAIN_ONLY -> research candidate fit cycle.

Wraps the existing G0 source selector, fit_candidate, and registered candidate
reader. No raw data are embedded in output; no official P0 or Champion write.
Requires an isolated private data workspace and private output outside it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from g0_training_source_contract import G0TrainingInputBlocked, select_g0_training_rows
from master_contracts import canonical_bytes, digest, validate_night
from prospective_inputs import ProspectiveReadContext, _LocalByteBudget
from prospective_spacetime import _read_candidate_model, MAX_MODEL_BYTES
from train_spacetime_candidate import fit_candidate
if __package__:
    from .backfill_historical_environment import assert_private_directory
    from .private_pdca_intake import guard_private_path, _ReadBudget, _read_bytes
else:
    from backfill_historical_environment import assert_private_directory
    from private_pdca_intake import guard_private_path, _ReadBudget, _read_bytes

HEX = re.compile(r'[0-9a-f]{64}\Z')
VERSION = 'habu-private-qualified-fit-cycle-v1'


def _hash_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def _private_output(root: Path, target: Path) -> Path:
    target = assert_private_directory(target)
    guard_private_path(Path(target.anchor), target)
    root = root.resolve()
    # Reject even a separate output folder nested in the code/data checkout.
    if target == root or root in target.parents or target in root.parents:
        raise ValueError('Private output must be outside the code/data workspace')
    return target


def _save_new_or_identical(path: Path, value: dict) -> str:
    path = _private_output(ROOT, path)
    raw = canonical_bytes(value) + b'\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    _private_output(ROOT, path)
    try:
        with path.open('xb') as stream:
            stream.write(raw)
    except FileExistsError:
        _private_output(ROOT, path)
        try:
            identical = _read_bytes(path, len(raw), _ReadBudget(30)) == raw
        except (OSError, ValueError):
            identical = False
        if not identical:
            raise ValueError('Conflicting immutable candidate artifact')
    _private_output(ROOT, path)
    if _read_bytes(path, len(raw), _ReadBudget(30)) != raw:
        raise ValueError('Written artifact integrity mismatch')
    return hashlib.sha256(raw).hexdigest()


def run_cycle(root: Path, output: Path, *, manifest_path: str | None,
              manifest_sha256: str | None, feature_sha256: str | None,
              heldout_night: str, fit_cutoff: str, forecast_cutoff: str,
              exposed_nights: tuple[str, ...] = ()) -> dict:
    """Return a gate report, persisting only a verifiable *development* model.

    Missing qualified source is BLOCKED, not a request to fabricate training
    labels from GPX. Ill-formed or tampered sources fail instead of bypassing.
    """
    root = Path(root).resolve()
    output = _private_output(root, Path(output))
    validate_night(heldout_night)
    for night in exposed_nights:
        validate_night(night)
    for name, value in (('manifest_sha256', manifest_sha256), ('feature_sha256', feature_sha256)):
        if value is not None and (not isinstance(value, str) or not HEX.fullmatch(value)):
            raise ValueError('Invalid ' + name)
    if manifest_path is None:
        if manifest_sha256 is not None or feature_sha256 is not None:
            raise ValueError('Incomplete manifest binding')
        return {
            'schema_version': VERSION, 'status': 'BLOCKED',
            'reason': 'MISSING_SOURCE_QUALIFIED_G0_MANIFEST',
            'heldout_night': heldout_night, 'eligible_training_units': None,
            'model_sha256': None, 'official_prediction_authorized': False,
            'production_model_activated': False,
        }
    if (not manifest_sha256 or not feature_sha256 or
            not isinstance(manifest_path, str) or
            not manifest_path.startswith('protocols/development/') or
            not manifest_path.endswith('.json') or
            any(part in ('', '.', '..', 'sealed', 'confirmation') for part in manifest_path.split('/'))):
        raise ValueError('Source-bound G0 manifest path and hashes required')
    source = root / manifest_path
    if source.is_symlink() or not source.is_file():
        return {
            'schema_version': VERSION, 'status': 'BLOCKED',
            'reason': 'QUALIFIED_MANIFEST_SOURCE_NOT_AVAILABLE',
            'heldout_night': heldout_night, 'eligible_training_units': None,
            'model_sha256': None, 'official_prediction_authorized': False,
            'production_model_activated': False,
        }
    raw_size = source.stat().st_size
    binding = {'path': manifest_path, 'sha256': manifest_sha256, 'size_bytes': raw_size}
    # This is the actual existing source/readiness/feature binding gate.
    try:
        result = select_g0_training_rows(
            root, binding, heldout_night, fit_cutoff, forecast_cutoff,
            expected_feature_definition_sha256=feature_sha256,
            exposed_nights=exposed_nights)
    except G0TrainingInputBlocked as exc:
        return {
            'schema_version': VERSION, 'status': 'BLOCKED',
            'reason': 'G0_TRAINING_SOURCE_GATE_BLOCKED', 'detail': str(exc)[:300],
            'heldout_night': heldout_night, 'eligible_training_units': None,
            'model_sha256': None, 'official_prediction_authorized': False,
            'production_model_activated': False,
        }
    selection, receipt = result['selection'], result['receipt']
    if (receipt['production_authorized'] is not False or
            receipt['scientific_fit_authorized'] is not False or
            receipt['source_authentication'] != 'NOT_ATTESTED' or
            selection['official_issuance_authorized'] is not False):
        raise ValueError('Unexpected source selector authorization escalation')
    if selection['status'] != 'DEVELOPMENT_TRAINING_ELIGIBLE':
        return {
            'schema_version': VERSION, 'status': 'BLOCKED',
            'reason': 'INSUFFICIENT_SOURCE_QUALIFIED_TRAINING_UNITS',
            'heldout_night': heldout_night, 'eligible_training_units': selection['counts']['accepted_rows'],
            'counts': selection['counts'], 'blockers': selection['blockers'],
            'source_receipt_sha256': receipt['receipt_sha256'],
            'model_sha256': None, 'official_prediction_authorized': False,
            'production_model_activated': False,
        }
    fit = fit_candidate(selection)
    model = fit['model']
    if (fit['status'] != 'DEVELOPMENT_FIT_ONLY' or
            fit['official_issuance_authorized'] is not False or
            fit['independent_confirmation'] != 'NOT_PERFORMED' or
            model['qualification'] != 'UNVALIDATED_CANDIDATE' or
            model['training_data_sha256'] != selection['selection_sha256']):
        raise ValueError('Illegal candidate fit authority state')
    model_raw = canonical_bytes(model) + b'\n'
    model_blob_sha = hashlib.sha256(model_raw).hexdigest()
    # Verify compatibility using the *existing* prospective candidate reader.
    with tempfile.TemporaryDirectory() as tmp:
        fake_root = Path(tmp)
        candidate_path = fake_root / 'models' / 'candidates' / 'new.json'
        candidate_path.parent.mkdir(parents=True)
        candidate_path.write_bytes(model_raw)
        budget = ProspectiveReadContext(30, 16 * 1024 * 1024)
        decoded = _read_candidate_model(
            fake_root, 'models/candidates/new.json', model_blob_sha,
            budget=_LocalByteBudget(budget, source_limit=MAX_MODEL_BYTES),
            check=budget.check)
        if decoded != model:
            raise ValueError('Prospective model reader changed the candidate')
    # Only AFTER all checks may any candidate bytes be written.
    saved_model_path = output / 'candidates' / (model_blob_sha + '.json')
    saved_model_sha = _save_new_or_identical(saved_model_path, model)
    report = {
        'schema_version': VERSION, 'status': 'RESEARCH_CANDIDATE_FITTED',
        'heldout_night': heldout_night,
        'input_manifest_sha256': manifest_sha256,
        'source_receipt_sha256': receipt['receipt_sha256'],
        'training_selection_sha256': selection['selection_sha256'],
        'model_sha256': model_blob_sha,
        'model_internal_sha256': model['model_sha256'],
        'model_relative_path': 'candidates/' + model_blob_sha + '.json',
        'fit_counts': dict(fit['fit_evidence'], limitations=fit['fit_evidence']['limitations']),
        'stage1_top10_recall': 'NOT_EVALUATED',
        'formal_100m_10min': 'NOT_EVALUATED',
        'future_independent_validation': 'NOT_PERFORMED',
        'official_prediction_authorized': False,
        'production_model_activated': False,
        'champion_promotion': 'BLOCKED',
    }
    # Seal same-content reruns with a deterministic receipt name.
    report_path = output / 'receipts' / (model_blob_sha + '.json')
    report['report_sha256'] = digest(report)
    _save_new_or_identical(report_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--private-output', type=Path, required=True)
    parser.add_argument('--manifest-path')
    parser.add_argument('--manifest-sha256')
    parser.add_argument('--feature-sha256')
    parser.add_argument('--heldout-night', required=True)
    parser.add_argument('--fit-cutoff', required=True)
    parser.add_argument('--forecast-cutoff', required=True)
    parser.add_argument('--exposed-night', action='append', default=[])
    args = parser.parse_args()
    try:
        result = run_cycle(args.root, args.private_output,
            manifest_path=args.manifest_path, manifest_sha256=args.manifest_sha256,
            feature_sha256=args.feature_sha256, heldout_night=args.heldout_night,
            fit_cutoff=args.fit_cutoff, forecast_cutoff=args.forecast_cutoff,
            exposed_nights=tuple(args.exposed_night))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        print(json.dumps({'status': 'BLOCKED', 'reason_code': 'PRIVATE_FIT_VALIDATION_FAILED',
                          'error_type': type(exc).__name__, 'completion_report_validated': False,
                          'official_prediction_authorized': False, 'production_model_activated': False}))
        return 2
    # Selector diagnostics may include private row IDs or source paths.
    console = result if result['status'] == 'RESEARCH_CANDIDATE_FITTED' else {
        key: result[key] for key in ('schema_version', 'status', 'reason', 'heldout_night',
            'eligible_training_units', 'model_sha256', 'official_prediction_authorized',
            'production_model_activated')}
    print(json.dumps(console, ensure_ascii=False, sort_keys=True))
    return 0 if result['status'] == 'RESEARCH_CANDIDATE_FITTED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
