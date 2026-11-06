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

from g0_training_source_contract import G0TrainingInputBlocked, select_g0_training_rows, training_boundary
from master_contracts import canonical_bytes, digest, validate_night
from prospective_inputs import ProspectiveReadContext, _LocalByteBudget
from prospective_spacetime import _read_candidate_model, MAX_MODEL_BYTES
from train_spacetime_candidate import fit_candidate
from training_corpus import _read_bytes as _context_read_bytes, _unique_json_object
from master_contracts import safe_path
import g0_forecast_contract as g0
if __package__:
    from .backfill_historical_environment import assert_private_directory
    from .private_pdca_intake import (guard_private_path, _ReadBudget, _read_bytes,
                                      _temp_owner, cleanup_owned_temp)
else:
    from backfill_historical_environment import assert_private_directory
    from private_pdca_intake import (guard_private_path, _ReadBudget, _read_bytes,
                                     _temp_owner, cleanup_owned_temp)

HEX = re.compile(r'[0-9a-f]{64}\Z')
VERSION = 'habu-private-qualified-fit-cycle-v1'
PREPARATION_VERSION = 'habu-private-g0-source-preparation-v1'
MAX_PREPARATION_FILES = 256
MAX_PREPARATION_FILE_BYTES = 64 * 1024**2
MAX_PREPARATION_UNIQUE_BYTES = 512 * 1024**2
MAX_PREPARATION_LIST_BYTES = 256 * 1024


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


def _preparation_ref(value):
    """Own a portable private diagnostic reference; this is not G0 admission."""
    if type(value) is not dict or set(value) != {'path', 'sha256', 'size_bytes'}:
        raise ValueError('Exact private preparation reference required')
    value = dict(value)
    path = value['path']
    if (type(path) is not str or not path or len(path) > 512 or
            any(ord(c) < 32 or ord(c) == 127 or c in '\\:<>"|?*' for c in path) or
            any(part in ('', '.', '..') or part[-1:] in (' ', '.') or
                part.casefold() in {'.git', 'sealed', 'confirmation'} or
                re.fullmatch(r'(?i:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part)
                for part in path.split('/')) or
            type(value['sha256']) is not str or not HEX.fullmatch(value['sha256']) or
            type(value['size_bytes']) is not int or
            not 0 <= value['size_bytes'] <= MAX_PREPARATION_FILE_BYTES):
        raise ValueError('Invalid bounded private preparation reference')
    return value


def _preparation_path(root, relative):
    path = safe_path(root, relative)
    guard_private_path(root, path)
    return path


def _preparation_read(root, ref, context):
    context.check()
    path = _preparation_path(root, ref['path'])
    raw = _context_read_bytes(path, ref['size_bytes'], context)
    guard_private_path(root, path)
    if len(raw) != ref['size_bytes'] or hashlib.sha256(raw).hexdigest() != ref['sha256']:
        raise ValueError('Private preparation source integrity mismatch')
    context.check()
    return raw


def _preparation_write(path, raw, context, *, _created=None):
    """Never replace bytes; integrity reads use the caller's existing ledger."""
    context.check()
    path = _private_output(ROOT, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _private_output(ROOT, path)
    try:
        with path.open('xb') as stream:
            if _created is not None:
                _created.append((path, _temp_owner(stream)))
            if stream.write(raw) != len(raw):
                raise OSError('Incomplete private preparation write')
    except FileExistsError:
        pass
    context.check()
    _private_output(ROOT, path)
    actual = _context_read_bytes(path, len(raw), context)
    if actual != raw:
        raise ValueError('Conflicting immutable preparation artifact')
    _private_output(ROOT, path)
    context.check()
    return hashlib.sha256(raw).hexdigest()


def _preparation_save(output, relative, value, context, *, _created=None):
    raw = canonical_bytes(value) + b'\n'
    if len(raw) > MAX_PREPARATION_FILE_BYTES:
        raise ValueError('Preparation receipt capacity exceeded')
    sha = _preparation_write(output / relative, raw, context, _created=_created)
    return dict(path=relative, sha256=sha, size_bytes=len(raw))


def _preparation_union(refs):
    """Reject alias/prefix collisions and excessive unique inputs before writes."""
    by_path, portable, total = {}, {}, 0
    for ref in refs:
        ref = _preparation_ref(ref)
        path = ref['path']
        if path in by_path and by_path[path] != ref:
            raise ValueError('Conflicting preparation source references')
        folded = path.casefold()
        if folded in portable and portable[folded] != path:
            raise ValueError('Nonportable preparation source alias')
        if path not in by_path:
            if (len(by_path) >= MAX_PREPARATION_FILES or
                    total + ref['size_bytes'] > MAX_PREPARATION_UNIQUE_BYTES):
                raise ValueError('Preparation input capacity exceeded')
            total += ref['size_bytes']
        by_path[path], portable[folded] = ref, path
    paths = set(portable)
    for path in paths:
        parts = path.split('/')
        if any('/'.join(parts[:i]) in paths for i in range(1, len(parts))):
            raise ValueError('Preparation file/directory prefix conflict')
    if (len(by_path) > MAX_PREPARATION_FILES or
            sum(ref['size_bytes'] for ref in by_path.values()) > MAX_PREPARATION_UNIQUE_BYTES):
        raise ValueError('Preparation input capacity exceeded')
    return [by_path[path] for path in sorted(by_path)]


def _check_preparation_gate(result):
    child = result['receipt']
    if (child['source_authentication'] != 'NOT_ATTESTED' or
            child['scientific_fit_authorized'] is not False or
            child['production_authorized'] is not False or
            result['selection']['official_issuance_authorized'] is not False):
        raise ValueError('Unexpected preparation source authority state')


def prepare_source(root, output, *, heldout_night, fit_cutoff, forecast_cutoff,
                   research_refs=(), manifest_path=None, manifest_sha256=None,
                   feature_sha256=None, exposed_nights=(), budget_seconds=30,
                   _read_context=None):
    """Prepare existing private bytes, never infer audited rows or fit a model.

    A supplied v1 declaration is rechecked by the actual source selector on both
    sides. That validates caller declarations, not biological source truth.
    Research inputs alone preserve an exact existing BLOCKED fit report.
    """
    if _read_context is not None and not isinstance(_read_context, ProspectiveReadContext):
        raise ValueError('Expected shared prospective read context')
    context = _read_context or ProspectiveReadContext(budget_seconds, g0.MAX_TOTAL_READ_BYTES)
    context.restrict(budget_seconds, g0.MAX_TOTAL_READ_BYTES)
    root = _private_output(ROOT, Path(root)).resolve()
    if not root.is_dir():
        raise ValueError('Existing private input workspace required')
    output = _private_output(root, Path(output))
    validate_night(heldout_night)
    training_boundary(heldout_night, fit_cutoff, forecast_cutoff)
    for night in exposed_nights:
        validate_night(night)
    if len(set(exposed_nights)) != len(exposed_nights):
        raise ValueError('Duplicate exposed night')
    if type(research_refs) not in (list, tuple) or len(research_refs) > MAX_PREPARATION_FILES:
        raise ValueError('Bounded explicit research reference list required')
    research = [_preparation_ref(ref) for ref in research_refs]
    if len({ref['path'] for ref in research}) != len(research):
        raise ValueError('Duplicated research source reference')
    research = _preparation_union(research)
    for ref in research:
        _preparation_path(root, ref['path'])
    source_result = prepared_result = None
    manifest_ref = None
    blocked = None
    if manifest_path is None:
        # The existing no-manifest report has an exact downstream envelope.
        blocked = run_cycle(root, output, manifest_path=None,
            manifest_sha256=manifest_sha256, feature_sha256=feature_sha256,
            heldout_night=heldout_night, fit_cutoff=fit_cutoff,
            forecast_cutoff=forecast_cutoff, exposed_nights=tuple(exposed_nights))
    else:
        if (type(manifest_path) is not str or
                not manifest_path.startswith('protocols/development/') or
                not manifest_path.endswith('.json') or
                type(manifest_sha256) is not str or not HEX.fullmatch(manifest_sha256) or
                type(feature_sha256) is not str or not HEX.fullmatch(feature_sha256)):
            raise ValueError('Explicit existing G0 declaration binding required')
        candidate = _preparation_path(root, _preparation_ref(dict(
            path=manifest_path, sha256=manifest_sha256, size_bytes=0))['path'])
        if not candidate.is_file():
            blocked = dict(schema_version=VERSION, status='BLOCKED',
                reason='QUALIFIED_MANIFEST_SOURCE_NOT_AVAILABLE', heldout_night=heldout_night,
                eligible_training_units=None, model_sha256=None,
                official_prediction_authorized=False, production_model_activated=False)
        else:
            manifest_ref = _preparation_ref(dict(path=manifest_path,
                sha256=manifest_sha256, size_bytes=candidate.stat().st_size))
            try:
                source_result = select_g0_training_rows(root, manifest_ref,
                    heldout_night, fit_cutoff, forecast_cutoff,
                    expected_feature_definition_sha256=feature_sha256,
                    exposed_nights=tuple(exposed_nights), budget_seconds=context.remaining_seconds,
                    _read_context=context)
            except G0TrainingInputBlocked as exc:
                blocked = dict(schema_version=VERSION, status='BLOCKED',
                    reason='G0_TRAINING_SOURCE_GATE_BLOCKED', detail=str(exc)[:300],
                    heldout_night=heldout_night, eligible_training_units=None,
                    model_sha256=None, official_prediction_authorized=False,
                    production_model_activated=False)
            if source_result is not None:
                _check_preparation_gate(source_result)
    refs = list(research)
    if manifest_ref is not None:
        refs.append(manifest_ref)
    if source_result is not None:
        for path, sha in source_result['receipt']['consumed_sha256'].items():
            target = _preparation_path(root, path)
            refs.append(_preparation_ref(dict(path=path, sha256=sha, size_bytes=target.stat().st_size)))
    refs = _preparation_union(refs)
    # Preflight every reference and size/hash before creating any output.
    for ref in refs:
        _preparation_read(root, ref, context)
    identity = dict(research_refs=research, input_refs=refs,
        manifest_ref=manifest_ref, requested_manifest_path=manifest_path,
        requested_manifest_sha256=manifest_sha256, feature_sha256=feature_sha256,
        heldout_night=heldout_night, fit_cutoff=fit_cutoff, forecast_cutoff=forecast_cutoff,
        exposed_nights=sorted(exposed_nights))
    preparation_id = digest(identity)
    relative_workspace = 'inputs/' + preparation_id
    workspace = output / relative_workspace
    for ref in refs:
        context.check()
        raw = _preparation_read(root, ref, context)
        _preparation_write(workspace / ref['path'], raw, context)
    if source_result is not None:
        prepared_result = select_g0_training_rows(workspace, manifest_ref,
            heldout_night, fit_cutoff, forecast_cutoff,
            expected_feature_definition_sha256=feature_sha256,
            exposed_nights=tuple(exposed_nights), budget_seconds=context.remaining_seconds,
            _read_context=context)
        _check_preparation_gate(prepared_result)
        if prepared_result['selection'] != source_result['selection']:
            raise ValueError('Prepared source selection differs from original')
    # No success marker before both sides have survived their final rescan.
    for ref in refs:
        _preparation_read(root, ref, context)
        _preparation_read(workspace, ref, context)
    context.check()
    if source_result is not None and source_result['selection']['status'] != 'DEVELOPMENT_TRAINING_ELIGIBLE':
        selection, child = source_result['selection'], source_result['receipt']
        blocked = dict(schema_version=VERSION, status='BLOCKED',
            reason='INSUFFICIENT_SOURCE_QUALIFIED_TRAINING_UNITS', heldout_night=heldout_night,
            eligible_training_units=selection['counts']['accepted_rows'], counts=selection['counts'],
            blockers=selection['blockers'], source_receipt_sha256=child['receipt_sha256'],
            model_sha256=None, official_prediction_authorized=False, production_model_activated=False)
    fit_ref = None
    if blocked is not None:
        fit_ref = _preparation_save(output, 'fit-reports/' + digest(blocked) + '.json', blocked, context)
    selection = source_result['selection'] if source_result is not None else None
    receipt = dict(schema_version=PREPARATION_VERSION, preparation_id=preparation_id,
        status='DECLARATION_PREPARED' if selection is not None else 'BLOCKED',
        reason=blocked['reason'] if blocked is not None else None,
        research_refs=research, input_refs=refs, prepared_workspace=relative_workspace,
        prepared_manifest_ref=manifest_ref if selection is not None else None,
        declared_training_units=selection['counts']['accepted_rows'] if selection is not None else None,
        declared_training_status=selection['status'] if selection is not None else None,
        training_selection_sha256=selection['selection_sha256'] if selection is not None else None,
        heldout_night=heldout_night, fit_cutoff=fit_cutoff, forecast_cutoff=forecast_cutoff,
        exposed_nights=sorted(exposed_nights), source_authentication='NOT_ATTESTED',
        scientific_fit_authorized=False, production_authorized=False,
        new_qualified_rows=0, new_negatives=0, new_real_fits=0, model_sha256=None)
    relative_receipt = 'preparations/' + preparation_id + '.json'
    receipt_raw = canonical_bytes(receipt) + b'\n'
    receipt_ref = dict(path=relative_receipt, sha256=hashlib.sha256(receipt_raw).hexdigest(),
                       size_bytes=len(receipt_raw))
    execution = dict(source_gate_receipt=source_result['receipt'] if source_result is not None else None,
        prepared_gate_receipt=prepared_result['receipt'] if prepared_result is not None else None,
        blocked_fit_report_ref=fit_ref, preparation_receipt_ref=receipt_ref,
        actual_read_bytes_before_audit=context.bytes_read)
    execution_ref = _preparation_save(output, 'checks/' + digest(execution) + '.json', execution, context)
    context.check()
    # The completion record is last. Failed new generations are removed only
    # with the existing descriptor/FileID ownership token; prior/foreign files stay.
    created = []
    try:
        saved_ref = _preparation_save(output, relative_receipt, receipt, context, _created=created)
        if saved_ref != receipt_ref:
            raise ValueError('Preparation completion identity changed')
        context.check()
        # The last cooperative validation guard must retain live generation
        # ownership. Descriptor release below performs no more input work.
        for _, owner in created:
            owner.close()
    except BaseException as primary:
        for path, owner in created:
            cleanup_owned_temp(output, path, owner, primary)
        raise
    return dict(receipt=receipt, receipt_ref=receipt_ref, execution=execution,
                execution_ref=execution_ref, actual_read_bytes=context.bytes_read)


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
    parser.add_argument('--prepare-only', action='store_true',
                        help='Prepare private source bytes without fitting')
    parser.add_argument('--research-sources-path', help='Private relative JSON array of source references')
    parser.add_argument('--research-sources-sha256')
    parser.add_argument('--prepare-budget-seconds', type=float)
    args = parser.parse_args()
    try:
        if args.prepare_only:
            seconds = args.prepare_budget_seconds if args.prepare_budget_seconds is not None else 30
            context = ProspectiveReadContext(seconds, g0.MAX_TOTAL_READ_BYTES)
            refs = []
            if args.research_sources_path is not None or args.research_sources_sha256 is not None:
                if args.research_sources_path is None or args.research_sources_sha256 is None:
                    raise ValueError('Complete research reference-list binding required')
                root = _private_output(ROOT, args.root).resolve()
                candidate = _preparation_ref(dict(path=args.research_sources_path,
                    sha256=args.research_sources_sha256, size_bytes=0))
                path = _preparation_path(root, candidate['path'])
                size = path.stat().st_size
                if size > MAX_PREPARATION_LIST_BYTES:
                    raise ValueError('Preparation reference-list capacity exceeded')
                inventory = _preparation_ref(dict(candidate, size_bytes=size))
                raw = _preparation_read(root, inventory, context)
                context.check()
                refs = json.loads(raw, object_pairs_hook=lambda pairs: _unique_json_object(pairs, context))
                context.check()
                if type(refs) is not list:
                    raise ValueError('Research references must be a JSON array')
                # Preserve the binding list as a separate research-only input.
                refs.append(inventory)
            result = prepare_source(args.root, args.private_output,
                heldout_night=args.heldout_night, fit_cutoff=args.fit_cutoff,
                forecast_cutoff=args.forecast_cutoff, research_refs=refs,
                manifest_path=args.manifest_path, manifest_sha256=args.manifest_sha256,
                feature_sha256=args.feature_sha256, exposed_nights=tuple(args.exposed_night),
                budget_seconds=seconds, _read_context=context)
            receipt = result['receipt']
            console = {key: receipt[key] for key in ('schema_version', 'status', 'reason',
                'preparation_id', 'declared_training_units', 'declared_training_status',
                'source_authentication', 'scientific_fit_authorized', 'production_authorized',
                'new_qualified_rows', 'new_negatives', 'new_real_fits', 'model_sha256')}
            console['actual_read_bytes'] = result['actual_read_bytes']
            print(json.dumps(console, ensure_ascii=False, sort_keys=True))
            return 0 if receipt['status'] == 'DECLARATION_PREPARED' else 2
        if (args.research_sources_path is not None or args.research_sources_sha256 is not None or
                args.prepare_budget_seconds is not None):
            raise ValueError('Preparation arguments require explicit preparation mode')
        result = run_cycle(args.root, args.private_output,
            manifest_path=args.manifest_path, manifest_sha256=args.manifest_sha256,
            feature_sha256=args.feature_sha256, heldout_night=args.heldout_night,
            fit_cutoff=args.fit_cutoff, forecast_cutoff=args.forecast_cutoff,
            exposed_nights=tuple(args.exposed_night))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        print(json.dumps({'status': 'BLOCKED', 'reason_code':
                          'PRIVATE_SOURCE_PREPARATION_VALIDATION_FAILED' if args.prepare_only else 'PRIVATE_FIT_VALIDATION_FAILED',
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
