"""Pure locked split metadata checks; no labels, file reads, fits or authority.

Hashes bind declarations, not the authenticity/completeness of their evidence.
Referenced source selection, universe, features and outcomes still need their
existing independent validators before any scientific execution.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
import re

from codex_cycle_contract import POLICY_DIGEST, training_boundary, require_ready_before
from evidence_audit import JST, timestamp
from master_contracts import canonical_bytes, digest, validate_night

MAX_METADATA_BYTES = 4 * 1024 * 1024
MAX_GROUPS = 10_000
MAX_FOLDS = 128
PLAN_FIELDS = {'schema_version', 'cycle_sha256', 'policy_sha256', 'frozen_at',
               'exposure_history_sha256', 'training_groups', 'forecast_cohorts',
               'folds', 'registered_recipes', 'selected_recipe', 'model_sha256',
               'predictions_sha256'}
GROUP_FIELDS = {'group_id', 'operational_night', 'geography_ids',
                'corpus_selection_sha256', 'readiness'}
COHORT_FIELDS = {'cohort_id', 'operational_night', 'geography_ids', 'forecast_cutoff',
                 'universe_sha256', 'feature_snapshot_sha256', 'feature_available_at',
                 'outcome_ledger_commitment_sha256'}
FOLD_FIELDS = {'fold_id', 'purpose', 'train_group_ids', 'evaluation_cohort_ids',
               'heldout_geography_ids', 'embargo_nights'}
HISTORY_FIELDS = {'research_used_nights', 'confirmation_used_nights'}


def _fields(value, fields, reason):
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(reason)


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value):
        raise ValueError('INVALID_IDENTIFIER')
    return value


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value):
        raise ValueError('INVALID_SHA256')


def _list(value, *, empty=False):
    if not isinstance(value, list) or len(value) > MAX_GROUPS or (not empty and not value):
        raise ValueError('BOUNDED_LIST_REQUIRED')
    return value


def _ids(value, *, empty=False):
    value = _list(value, empty=empty)
    for item in value:
        _identifier(item)
    if len(set(value)) != len(value):
        raise ValueError('DUPLICATE_IDENTIFIER')
    return set(value)


def _night(value):
    if not isinstance(value, str):
        raise ValueError('INVALID_NIGHT')
    validate_night(value)
    return date.fromisoformat(value)


def _time(value):
    if not isinstance(value, str):
        raise ValueError('TIMEZONE_REQUIRED')
    return timestamp(value)


def _night_start(night):
    return datetime.combine(_night(night), time(7), JST)


def validate_locked_protocol(plan: dict, exposure_history: dict) -> dict:
    """Validate declared split consistency without authenticating any evidence.

    The exposure history is a required projection of existing protocol history.
    Its hash does not prove global coverage, truthful exposure or a trusted seal.
    No input is mutated and no path, shell, executable recipe or label is read.
    """
    _fields(plan, PLAN_FIELDS, 'PLAN_FIELDS')
    _fields(exposure_history, HISTORY_FIELDS, 'EXPOSURE_HISTORY_REQUIRED')
    if len(canonical_bytes([plan, exposure_history])) > MAX_METADATA_BYTES:
        raise ValueError('METADATA_LIMIT')
    if plan['schema_version'] != 'habu-locked-protocol-v1':
        raise ValueError('PROTOCOL_VERSION')
    for key in ('cycle_sha256', 'policy_sha256', 'exposure_history_sha256',
                'model_sha256', 'predictions_sha256'):
        _sha(plan[key])
    if plan['policy_sha256'] != POLICY_DIGEST:
        raise ValueError('SHARED_POLICY_MISMATCH')
    history_nights = set()
    for values in exposure_history.values():
        _list(values, empty=True)
        for night in values:
            _night(night)
        if len(set(values)) != len(values):
            raise ValueError('DUPLICATE_EXPOSURE_NIGHT')
        history_nights.update(values)
    if digest(exposure_history) != plan['exposure_history_sha256']:
        raise ValueError('EXPOSURE_HISTORY_HASH')
    recipes = plan['registered_recipes']
    _ids(recipes)
    if len(recipes) > 3 or recipes[0] != 'uniform':
        raise ValueError('RECIPES_REQUIRE_UNIFORM_AND_MAX_THREE')
    if plan['selected_recipe'] not in recipes:
        raise ValueError('UNREGISTERED_SELECTION')
    frozen = _time(plan['frozen_at'])

    groups, selection_hashes = {}, set()
    for group in _list(plan['training_groups']):
        _fields(group, GROUP_FIELDS, 'TRAIN_GROUP_FIELDS')
        ident = _identifier(group['group_id'])
        _night(group['operational_night'])
        _ids(group['geography_ids'])
        _sha(group['corpus_selection_sha256'])
        if ident in groups or group['corpus_selection_sha256'] in selection_hashes:
            raise ValueError('DUPLICATE_TRAIN_GROUP_OR_SELECTION')
        groups[ident] = group
        selection_hashes.add(group['corpus_selection_sha256'])

    cohorts = {}
    for cohort in _list(plan['forecast_cohorts']):
        _fields(cohort, COHORT_FIELDS, 'COHORT_FIELDS')
        ident = _identifier(cohort['cohort_id'])
        start = _night_start(cohort['operational_night'])
        _ids(cohort['geography_ids'])
        for key in ('universe_sha256', 'feature_snapshot_sha256', 'outcome_ledger_commitment_sha256'):
            _sha(cohort[key])
        cutoff = _time(cohort['forecast_cutoff'])
        if cutoff >= start + timedelta(days=1):
            raise ValueError('FORECAST_CUTOFF_AFTER_NIGHT')
        if _time(cohort['feature_available_at']) >= cutoff:
            raise ValueError('FORECAST_AVAILABILITY')
        if ident in cohorts:
            raise ValueError('DUPLICATE_COHORT')
        cohorts[ident] = cohort

    folds = _list(plan['folds'])
    if len(folds) > MAX_FOLDS:
        raise ValueError('FOLD_LIMIT')
    fold_ids, evaluated_ids, used_groups = set(), set(), set()
    night_owner, development, confirmation = {}, set(), set()
    confirmation_training = None
    geographic_holdout = False
    for fold in folds:
        _fields(fold, FOLD_FIELDS, 'FOLD_FIELDS')
        ident = _identifier(fold['fold_id'])
        if ident in fold_ids:
            raise ValueError('DUPLICATE_FOLD')
        fold_ids.add(ident)
        purpose = fold['purpose']
        if purpose not in ('DEVELOPMENT_FORECAST', 'SEALED_CONFIRMATION'):
            raise ValueError('FOLD_PURPOSE')
        train = _ids(fold['train_group_ids'])
        evaluation = _ids(fold['evaluation_cohort_ids'])
        holdout = _ids(fold['heldout_geography_ids'], empty=True)
        embargo = fold['embargo_nights']
        if isinstance(embargo, bool) or not isinstance(embargo, int) or not 0 <= embargo <= 365:
            raise ValueError('INVALID_EMBARGO')
        if not train <= groups.keys() or not evaluation <= cohorts.keys():
            raise ValueError('UNKNOWN_GROUP_OR_COHORT')
        if evaluated_ids & evaluation:
            raise ValueError('DUPLICATE_EVALUATION_COHORT')
        evaluated_ids.update(evaluation)
        used_groups.update(train)
        evaluation_geographies = {g for item in evaluation for g in cohorts[item]['geography_ids']}
        if not holdout <= evaluation_geographies:
            raise ValueError('GEOGRAPHIC_HOLDOUT_NOT_EVALUATED')
        if any(holdout & set(groups[item]['geography_ids']) for item in train):
            raise ValueError('GEOGRAPHIC_LEAKAGE')
        geographic_holdout = geographic_holdout or bool(holdout)
        if purpose == 'SEALED_CONFIRMATION':
            if confirmation_training is not None and train != confirmation_training:
                raise ValueError('CONFIRMATION_TRAINING_CHANGED')
            confirmation_training = train
        for item in evaluation:
            cohort = cohorts[item]
            night = cohort['operational_night']
            if night in night_owner and night_owner[night] != ident:
                raise ValueError('SPLIT_NIGHT_REUSED_ACROSS_FOLDS')
            night_owner[night] = ident
            (confirmation if purpose == 'SEALED_CONFIRMATION' else development).add(night)
            boundary = training_boundary(night, plan['frozen_at'], cohort['forecast_cutoff'])
            for group_id in train:
                group = groups[group_id]
                train_night, eval_night = _night(group['operational_night']), _night(night)
                if train_night == eval_night:
                    raise ValueError('SAME_NIGHT_TRAINING')
                if train_night > eval_night:
                    raise ValueError('FUTURE_TRAINING')
                if train_night >= eval_night - timedelta(days=embargo):
                    raise ValueError('EMBARGO_BOUNDARY')
                ready = require_ready_before(group['readiness'], boundary.isoformat())
                if ready < _night_start(group['operational_night']):
                    raise ValueError('TRAIN_READINESS_PRECEDES_OBSERVATION')
            if purpose == 'SEALED_CONFIRMATION':
                if frozen >= min(_night_start(night), _time(cohort['forecast_cutoff'])):
                    raise ValueError('CONFIRMATION_FREEZE')
                if _time(cohort['feature_available_at']) >= frozen:
                    raise ValueError('SEALED_PREDICTION_AVAILABILITY')
    if evaluated_ids != cohorts.keys() or used_groups != groups.keys():
        raise ValueError('COHORT_COVERAGE')
    if confirmation & history_nights:
        raise ValueError('CONFIRMATION_REUSED')
    if development and confirmation and max(development) >= min(confirmation):
        raise ValueError('SPLIT_NIGHT_ORDER')
    if any(group['operational_night'] in confirmation for group in groups.values()):
        raise ValueError('CONFIRMATION_USED_FOR_TRAINING')

    blockers = ['EXPOSURE_HISTORY_AUTHENTICITY_UNVERIFIED',
                'INDEPENDENT_COMPLETE_OUTCOME_LEDGER_UNVERIFIED',
                'SOURCE_ELIGIBILITY_AND_CANONICAL_EVENT_OVERLAP_UNVERIFIED',
                'TRUSTED_PRE_REVEAL_SELECTION_AND_PREDICTION_RECEIPTS_UNVERIFIED']
    if len(confirmation) < 5:
        blockers.append('FEWER_THAN_FIVE_CONFIRMATION_NIGHTS')
    if not geographic_holdout:
        blockers.append('GEOGRAPHIC_HOLDOUT_UNALLOCATED')
    protocol_sha = digest({'plan': plan, 'exposure_history': exposure_history})
    return dict(status='PROTOCOL_CONTRACT_VALIDATED', protocol_sha256=protocol_sha,
                cycle_sha256=plan['cycle_sha256'], policy_sha256=POLICY_DIGEST,
                fold_sha256={fold['fold_id']: digest({'protocol_sha256': protocol_sha, 'fold': fold})
                             for fold in sorted(folds, key=lambda x: x['fold_id'])},
                development_nights=sorted(development), confirmation_nights=sorted(confirmation),
                confirmation_floor='MET_NOT_SUFFICIENT' if len(confirmation) >= 5 else 'BLOCKED',
                exposure_history_authenticity='NOT_VALIDATED', denominator_gate='NOT_EVALUATED',
                metric_denominator_policy_sha256=POLICY_DIGEST, scientific_status='NOT_VALIDATED',
                fit_authorized=False, production_authorized=False, blockers=blockers)
