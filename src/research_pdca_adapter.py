"""Explicit development dispatch through both strict gates, without reveal.

Only the fixed config request enables this path. Complete diagnostic candidate
sets receive a content-addressed REPLAY after source rechecks; no confirmation
reader, selection metric, official issuer or production activation is provided.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile

import g0_forecast_contract as g0
import g0_training_source_contract as training
from master_contracts import SCHEMA_VERSION, canonical_bytes, digest, stage, validate_night
from master_inventory import local_path
import prospective_inputs as pi
import research_model_adapter as models

VERSION = 'habu-research-model-request-v1'
REQUEST_PATH = 'config/research-model-request.json'
NAMES = ('model_evaluation', 'feature_research', 'candidate_generation', 'candidate_validation')
FIELDS = {'schema_version', 'mode', 'operational_night', 'fit_cutoff', 'forecast_as_of',
          'forecast_cutoff', 'feature_definition_sha256', 'training_manifest', 'forecast_manifest', 'exposed_nights'}
MAX_REPLAY_BYTES = 64 * 1024**2


def has_research_request(root):
    """Existence only: malformed explicit requests must not fall back to legacy."""
    return local_path(Path(root), REQUEST_PATH).exists()


def _request(root, reader):
    path = local_path(root, REQUEST_PATH)
    raw = pi._bounded_bytes(path, pi._LocalByteBudget(reader.context, g0.MAX_SMALL_BYTES), reader.context.check)
    ref = dict(path=REQUEST_PATH, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    value = reader.read(ref, small=True)
    if type(value) is not dict or set(value) != FIELDS or value['schema_version'] != VERSION or value['mode'] != 'DEVELOPMENT_ONLY':
        raise ValueError('Exact development-only research request fields required')
    training._reference(value['training_manifest'], 'manifest')
    g0._input_ref(value['forecast_manifest'])
    # Transport accepts arbitrary local refs. This caller must exclude reveal
    # namespaces before either gate opens any requested payload/code source.
    for item in (value['training_manifest'], value['forecast_manifest']):
        if any(part.casefold() in {'sealed', 'confirmation'} for part in item['path'].split('/')):
            raise ValueError('Sealed confirmation reference forbidden')
    return value, ref


def _preflight_forecast(reader, ref):
    """Exclude reveal paths even in nested source/code refs before the loader."""
    manifest = reader.read(ref, small=True)
    pending = [manifest]
    while pending:
        reader.context.check()
        item = pending.pop()
        if type(item) is dict:
            path = item.get('path')
            if type(path) is str and any(part.casefold() in {'sealed', 'confirmation'} for part in path.split('/')):
                raise ValueError('Sealed confirmation reference forbidden')
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)


def _publish(root, night, content, context):
    """A single complete immutable artifact; never overwrite an existing replay."""
    content_sha = digest(content)
    relative = f'predictions/replay/{night}/research/{content_sha}.json'
    path = local_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.research-replay-', dir=path.parent)
    sha, count = hashlib.sha256(), 0
    try:
        with os.fdopen(fd, 'wb') as stream:
            for text in json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).iterencode(content):
                context.check()
                raw = text.encode('utf-8')
                count += len(raw)
                if count > MAX_REPLAY_BYTES:
                    raise pi.InputCapacityError('CAPACITY_BLOCKED: complete REPLAY bytes')
                stream.write(raw)
                sha.update(raw)
            stream.write(b'\n')
            sha.update(b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        context.check()
        local_path(root, relative)
        try:
            os.link(temporary, path)
        except FileExistsError:
            existing = g0.G0ArtifactReader(root, context)
            existing.read(dict(path=relative, sha256=sha.hexdigest(), size_bytes=count + 1), parse=False)
        context.check()
        return dict(path=relative, sha256=sha.hexdigest(), content_sha256=content_sha,
                    trust='DEVELOPMENT_REPLAY_NOT_OFFICIAL_OR_TRUSTED_SEAL')
    finally:
        os.unlink(temporary)


def evaluate_research_request(root, night, budget_seconds=300, *, _read_context=None):
    validate_night(night)
    root = Path(root).absolute()
    result = dict(schema_version=SCHEMA_VERSION, stages=[], candidates=[], folds=[], replay=[],
        implementation_blockers=['Independent confirmation selection/consumption lock and trusted runner',
            'Feature-aware retraining ablation, count/detection/activity/route/rerouting executors'],
        data_blockers=[], decision=dict(decision='NEED_MORE_DATA', reasons=[]),
        scientific_fit_authorized=False, production_activation_authorized=False,
        official_issuance_authorized=False, confirmation_labels_used=False)
    status, kind = 'BLOCKED', 'DATA_BLOCKED'
    reason = 'Required qualified TRAIN_ONLY evidence and complete strict forecast inputs'
    prepared = None
    try:
        if budget_seconds == 0:
            raise TimeoutError('Parent cumulative budget exhausted')
        context = _read_context or pi.ProspectiveReadContext(budget_seconds, g0.MAX_TOTAL_READ_BYTES)
        if not isinstance(context, pi.ProspectiveReadContext):
            raise ValueError('Shared prospective read context required')
        context.restrict(budget_seconds, g0.MAX_TOTAL_READ_BYTES)
        reader = g0.G0ArtifactReader(root, context)
        request, request_ref = _request(root, reader)
        if request['operational_night'] != night:
            raise ValueError('Research request night mismatch')
        cutoff, as_of, fit = (pi._time(request[key]) for key in ('forecast_cutoff', 'forecast_as_of', 'fit_cutoff'))
        if pi._night(cutoff) != night or fit >= cutoff or as_of < cutoff:
            raise ValueError('Research request fit/forecast boundaries inconsistent')
        expected = request['feature_definition_sha256']
        if type(expected) is not str or not pi.SHA256.fullmatch(expected):
            raise ValueError('Strict registered feature-definition digest required')
        selected = training.select_g0_training_rows(root, request['training_manifest'], night,
            request['fit_cutoff'], request['forecast_cutoff'], expected_feature_definition_sha256=expected,
            exposed_nights=request['exposed_nights'], budget_seconds=context.remaining_seconds, _read_context=context)
        _preflight_forecast(reader, request['forecast_manifest'])
        forecast = g0.load_g0_forecast_rows(root, request['forecast_manifest'], night, as_of,
            expected_feature_definition_sha256=expected, budget_seconds=context.remaining_seconds, _read_context=context)
        if pi._time(forecast['receipt']['cutoff_time']) != cutoff:
            raise ValueError('Request cutoff differs from strict forecast cutoff')
        prepared = models.prepare_research_candidates(selected['selection'], forecast['rows'],
            cutoff_time=request['forecast_cutoff'],
            joined_universe_sha256=forecast['receipt']['canonical_joined_rows_sha256'],
            budget_seconds=context.remaining_seconds)
        context.check()
        consumed = {}
        for receipt in (selected['receipt'], forecast['receipt']):
            for path, expected_sha in receipt['consumed_sha256'].items():
                context.check()
                if path in consumed and consumed[path] != expected_sha:
                    raise ValueError('Conflicting training/forecast source binding')
                consumed[path] = expected_sha
        # Recheck all earlier training and forecast sources after fitting; a
        # per-gate scan alone would miss mutations during later model calls.
        for path, expected_sha in consumed.items():
            target = local_path(root, path)
            reader.read(dict(path=path, sha256=expected_sha, size_bytes=target.stat().st_size), parse=False)
        reader.rescan()
        context.check()
        result['evidence'] = dict(request_ref=request_ref, training=selected['receipt'], forecast=forecast['receipt'],
            consumed_inputs=dict(consumed, **{REQUEST_PATH: request_ref['sha256']}),
            source_authentication='NOT_ATTESTED', actual_read_bytes=context.bytes_read)
        if prepared['status'] == 'NEED_MORE_DATA':
            reason = 'DATA_BLOCKED: ' + '; '.join(prepared['blockers'])
        else:
            content = dict(schema_version=VERSION, scope='DEVELOPMENT_ONLY', request_ref=request_ref,
                training_receipt=selected['receipt'], forecast_receipt=forecast['receipt'], prepared=prepared,
                confirmation_labels_used=False, scientific_fit_authorized=False,
                official_issuance_authorized=False, production_activation_authorized=False)
            replay = _publish(root, night, content, context)
            context.check()
            result['replay'] = [replay]
            result['candidates'] = prepared['candidates']
            status, kind = 'NOT_VALIDATED', None
            reason = 'Complete diagnostic candidates prepared; independent evaluation and promotion gates unmet'
    except (TimeoutError, models.ResearchBudgetExhausted, pi.InputCapacityError, models.ResearchCapacityBlocked) as exc:
        status, kind, reason = 'BLOCKED', 'RUNTIME_BLOCKED', str(exc)
    except (FileNotFoundError, training.G0TrainingInputBlocked, g0.ForecastCapabilityError) as exc:
        status, kind, reason = 'BLOCKED', 'DATA_BLOCKED', str(exc)
    except (ValueError, TypeError, KeyError, OSError, OverflowError) as exc:
        if type(exc) is ValueError and str(exc) == 'Missing prospective input':
            # Legacy prospective transport represents absent files as this
            # ValueError, rather than a FileNotFoundError. Preserve its API.
            status, kind, reason = 'BLOCKED', 'DATA_BLOCKED', str(exc)
        else:
            status, kind, reason = 'FAIL', None, f'INVALID_RESEARCH_EVIDENCE: {exc}'
            result['decision']['decision'] = 'REJECT_CANDIDATE'
    if status != 'NOT_VALIDATED':
        result['candidates'], result['replay'] = [], []
    result['data_blockers'] = [reason, 'Source authenticity and independent prospective confirmation remain unvalidated']
    result['decision']['reasons'] = [reason]
    for name in NAMES:
        item_status, item_kind = status, kind
        if status == 'NOT_VALIDATED':
            item_status = 'PASS' if name == 'candidate_generation' else 'BLOCKED' if name == 'candidate_validation' else 'NOT_VALIDATED'
            item_kind = 'DATA_BLOCKED' if name == 'candidate_validation' else None
        result['stages'].append(stage(name, item_status, reason, evidence=[r['path'] for r in result['replay']],
            metrics={'diagnostic_candidates': len(result['candidates'])}, blocker_kind=item_kind))
    return result
