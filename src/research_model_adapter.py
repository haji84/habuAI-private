"""Prepare three diagnostic recipes on one TRAIN_ONLY selection and future set.

This pure calculation does not discover/read evidence, authenticate source
qualification, publish immutable REPLAY, consume held-out outcomes, evaluate
accuracy or select a winner. The source-bound selector and strict forecast
loader remain caller prerequisites. Historical M0--M3 are unchanged.
"""
from __future__ import annotations

import math
import time
from datetime import datetime

from master_contracts import digest
from models.hierarchy_shrinkage import fit_hierarchy, rank_hierarchy
from models.occupancy_shrinkage import fit_shrinkage, predict_shrinkage
from models.research_selection import (
    MAX_FORECAST_ROWS, ResearchInputCapacity, _json_copy, area_id,
    validate_future_rows, validate_selection,
)

VERSION = "habu-research-candidates-prepared-v1"
CANDIDATES = ("uniform", "HB-A0", "HB-B1")
MAX_BUDGET_SECONDS = 300


class ResearchBudgetExhausted(ValueError):
    """No partial candidate set is released when the shared deadline expires."""


class ResearchCapacityBlocked(ValueError):
    """Explicit capacity block; never sample or silently truncate the universe."""


def _seal(value, field):
    value[field] = digest(value)
    return value


def _uniform_probability(counts):
    """Existing uniform Beta(1,1) scalar, with no fitting or input discovery."""
    return (counts["positives"] + 1) / (counts["accepted_rows"] + 2)


def _validate_uniform_model(model, check):
    """Exact native uniform admission; hashes are consistency, not authority."""
    from models.research_selection import canonical_digest, _aware, _hash, _finite
    value = _json_copy(model, check=check)
    fields = {'schema_version','candidate_id','recipe','training_selection_sha256',
        'training_cutoff','counts','probability','scientific_status',
        'production_activation_authorized','model_sha256'}
    if type(value) is not dict or set(value) != fields:
        raise ValueError('Exact diagnostic uniform model required')
    if (value['schema_version'] != VERSION or value['candidate_id'] != 'uniform' or
            value['recipe'] != 'HISTORICAL_UNIFORM_BETA_1_1_FORMULA' or
            value['scientific_status'] != 'NOT_VALIDATED' or
            value['production_activation_authorized'] is not False):
        raise ValueError('Unregistered or privileged uniform model')
    _hash(value['training_selection_sha256'])
    _aware(value['training_cutoff'])
    if value['model_sha256'] != canonical_digest({k:v for k,v in value.items() if k!='model_sha256'},check=check):
        raise ValueError('Uniform native model content digest mismatch')
    counts = value['counts']
    if (type(counts) is not dict or set(counts) != {'accepted_rows','rejected_rows','nights','positives','negatives'} or
            any(type(n) is not int or not 0 <= n <= 20000 for n in counts.values()) or
            not 4 <= counts['accepted_rows'] or not 3 <= counts['nights'] <= counts['accepted_rows'] or
            min(counts['positives'],counts['negatives']) < 2 or
            counts['positives']+counts['negatives'] != counts['accepted_rows'] or
            counts['accepted_rows']+counts['rejected_rows'] > 20000):
        raise ValueError('Uniform training support contradicts qualified preparation')
    if _finite(value['probability']) != _uniform_probability(counts):
        raise ValueError('Uniform probability contradicts its fixed support')
    check()
    return value


def _uniform(selected, future, cutoff_time, joined_sha, check):
    # Exact historical uniform smoothing formula in model_evaluation._fit.
    # This is a separate research receipt, never a rewritten historical model.
    counts = selected["counts"]
    probability = _uniform_probability(counts)
    model = _seal({
        "schema_version": VERSION, "candidate_id": "uniform",
        "recipe": "HISTORICAL_UNIFORM_BETA_1_1_FORMULA",
        "training_selection_sha256": selected["selection_sha256"],
        "training_cutoff": selected["fit_cutoff"], "counts": counts,
        "probability": probability, "scientific_status": "NOT_VALIDATED",
        "production_activation_authorized": False,
    }, "model_sha256")
    predictions = []
    for row in future:
        check()
        predictions.append({
            "row_id": row["row_id"], "operational_night": row["operational_night"],
            "window_start_jst": row["window_start_jst"],
            "cell_x": row["cell_x"], "cell_y": row["cell_y"],
            "area_id_1km": area_id(row["cell_x"], row["cell_y"]),
            "probability": probability, "spatial_score": probability,
            "probability_status": "NOT_VALIDATED",
        })
    prediction = _seal({
        "candidate_id": "uniform", "model_sha256": model["model_sha256"],
        "universe_sha256": joined_sha, "cutoff_time": cutoff_time,
        "scientific_status": "NOT_VALIDATED", "unit_predictions": predictions,
        "target_semantics": "OWNER_CAPTURE_BINARY_GIVEN_QUALIFIED_OBSERVED_100M_10MIN_UNIT",
        "formal_100m_10min_status": "NOT_PRODUCED",
        "production_activation_authorized": False,
    }, "prediction_sha256")
    return model, prediction


def _instant(value):
    if not isinstance(value, str):
        raise ValueError("Candidate output timestamp required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("Candidate output timestamp must have timezone")
    return result


def _candidate(candidate_id, model, prediction, joined_sha, expected, selected, cutoff_time, check):
    """Bind complete candidate output without changing its native score meaning."""
    check()
    for value, field in ((model, "model_sha256"), (prediction, "prediction_sha256")):
        if not isinstance(value, dict) or value.get(field) != digest({
                k: v for k, v in value.items() if k != field}):
            raise ValueError("Candidate content digest mismatch")
    if (prediction.get("model_sha256") != model["model_sha256"] or
            prediction.get("universe_sha256") != joined_sha or
            _instant(prediction.get("cutoff_time")) != _instant(cutoff_time)):
        raise ValueError("Candidate model or joined-universe binding mismatch")
    selection_field = "selection_sha256" if candidate_id == "HB-A0" else "training_selection_sha256"
    if (model.get("candidate_id") != candidate_id or
            model.get(selection_field) != selected["selection_sha256"]):
        raise ValueError("Candidate training selection binding mismatch")
    units = prediction.get("unit_scores" if candidate_id == "HB-B1" else "unit_predictions")
    if not isinstance(units, list) or len(units) != len(expected):
        raise ValueError("Candidate must predict every supplied future unit")
    identities = []
    for unit in units:
        check()
        identity = unit["row_id"]
        identities.append(identity)
        original = expected.get(identity)
        if (original is None or unit.get("operational_night") != original["operational_night"] or
                _instant(unit.get("window_start_jst")) != _instant(original["window_start_jst"])):
            raise ValueError("Candidate night/window identity mismatch")
        cx, cy = original["cell_x"], original["cell_y"]
        if candidate_id == "HB-B1":
            if unit.get("cell_id") != f"utm52n_100m_{cx}_{cy}":
                raise ValueError("Candidate hierarchy physical cell mismatch")
        elif (type(unit.get("cell_x")) is not int or type(unit.get("cell_y")) is not int or
                unit["cell_x"] != cx or unit["cell_y"] != cy or unit.get("area_id_1km") != area_id(cx, cy)):
            raise ValueError("Candidate physical cell mismatch")
    if len(set(identities)) != len(identities) or set(identities) != set(expected):
        raise ValueError("Candidate future row coverage mismatch")
    return {
        "candidate_id": candidate_id, "model_sha256": model["model_sha256"],
        "prediction_sha256": prediction["prediction_sha256"],
        "joined_universe_sha256": joined_sha,
        "forecast_row_ids": sorted(identities), "forecast_units": len(units),
        "model": model, "prediction": prediction,
    }


def prepare_research_candidates(selection, forecast_rows, *, cutoff_time,
                                joined_universe_sha256, budget_seconds=30):
    """Return a complete prepared diagnostic set, or raise without partial output.

    Caller must establish actual source qualification, four readiness times,
    strict forecast validity and full declared-domain coverage separately.
    A valid insufficient selection returns NEED_MORE_DATA with no models. Bad
    input raises ValueError; capacity/time blocks have dedicated subclasses.
    The bounded pure model calls are checked before and after execution; this
    cooperative deadline is not an OS process-preemption guarantee.
    """
    if (type(budget_seconds) not in (int, float) or not math.isfinite(budget_seconds)
            or not 0 < budget_seconds <= MAX_BUDGET_SECONDS):
        raise ValueError("Budget must be finite, positive and at most 300 seconds")
    deadline = time.monotonic() + budget_seconds

    def check():
        if time.monotonic() >= deadline:
            raise ResearchBudgetExhausted("RUNTIME_BLOCKED: shared candidate deadline expired")

    check()
    selected = validate_selection(selection)
    check()
    if isinstance(forecast_rows, list) and len(forecast_rows) > MAX_FORECAST_ROWS:
        raise ResearchCapacityBlocked("CAPACITY_BLOCKED: use complete bounded forecast shards")
    # Own an independent JSON value before any model runs. Keep the original
    # joined digest: normalization adds cell fields and changes that digest.
    try:
        rows = _json_copy(forecast_rows)
    except ResearchInputCapacity as exc:
        raise ResearchCapacityBlocked("CAPACITY_BLOCKED: " + str(exc)) from exc
    future = validate_future_rows(rows, cutoff_time=cutoff_time,
        universe_sha256=joined_universe_sha256, heldout_night=selected["heldout_night"],
        feature_names=selected["feature_names"])
    check()
    common = {
        "schema_version": VERSION, "scientific_status": "NOT_VALIDATED",
        "source_authentication": "CALLER_DEPENDENCY_REQUIRED",
        "official_issuance_authorized": False, "production_activation_authorized": False,
        "training_selection_sha256": selected["selection_sha256"],
        "joined_universe_sha256": joined_universe_sha256,
        "joined_digest_semantics": "CANONICAL_SUPPLIED_JOINED_ROWS_NOT_SOURCE_UNIVERSE_FILE",
        "cutoff_time": cutoff_time, "forecast_units": len(future),
        "validation_status": "NOT_VALIDATED",
        "replay_status": "PREPARED_NOT_PUBLISHED_OR_TRUSTED_SEALED",
        "limitations": [
            "Source qualification/readiness and ex-ante domain completeness require upstream verification",
            "No held-out outcomes, accuracy metrics, model selection or promotion decision consumed",
            "No independent confirmation, calibrated island-wide probabilities or formal 100m +/-10min targets",
            "Pure preparation only; parent PDCA dispatch and immutable REPLAY publication are separate",
        ],
    }
    if selected["status"] == "NEED_MORE_DATA":
        result = _seal(dict(common, status="NEED_MORE_DATA", candidates=[],
            blockers=list(selected["blockers"])), "receipt_sha256")
        check()
        return result
    expected = {row["row_id"]: row for row in future}
    prepared = []
    model, prediction = _uniform(selected, future, cutoff_time, joined_universe_sha256, check)
    prepared.append(_candidate("uniform", model, prediction, joined_universe_sha256, expected, selected, cutoff_time, check))
    check()
    area_fit = fit_shrinkage(selected)
    check()
    if area_fit.get("status") != "DEVELOPMENT_FIT_ONLY" or not isinstance(area_fit.get("model"), dict):
        raise ValueError("Expected a fitted HB-A0 research model")
    model = area_fit["model"]
    prediction = predict_shrinkage(model, rows, cutoff_time=cutoff_time,
        universe_sha256=joined_universe_sha256)
    prepared.append(_candidate("HB-A0", model, prediction, joined_universe_sha256, expected, selected, cutoff_time, check))
    check()
    # HB-B1 returns the serialized model itself; it is not the HB-A0 wrapper.
    model = fit_hierarchy(selected)
    check()
    if model.get("status") != "DEVELOPMENT_CANDIDATE_FITTED":
        raise ValueError("Expected a fitted HB-B1 research model")
    prediction = rank_hierarchy(model, rows, cutoff_time=cutoff_time,
        universe_sha256=joined_universe_sha256)
    prepared.append(_candidate("HB-B1", model, prediction, joined_universe_sha256, expected, selected, cutoff_time, check))
    check()
    result = _seal(dict(common, status="DIAGNOSTIC_CANDIDATES_PREPARED",
        candidates=prepared, blockers=[]), "receipt_sha256")
    check()
    return result


# Additive v2: all v1 functions/constants above remain byte-for-byte unchanged.
import hashlib
import json
from models import hba1_feature_candidate as _hba1

VERSION_V2 = 'habu-research-candidates-prepared-v2'
CONFIG_VERSION_V2 = 'habu-research-candidate-config-v2'
V2_MAX_JSON_BYTES = 16 * 1024**2
V2_MAX_JSON_NODES = 2_000_000
V2_MAX_TRAIN_ROWS = 20_000
V2_CONFIG_FIELDS = {'schema_version', 'mode', 'candidate_ids', 'hba1_recipe', 'feature_definition_sha256'}
V2_OPTIONAL_IDS = {'HB-A0', 'HB-B1', 'HB-A1'}
V2_RAW_FEATURE_BOUNDS = {
    'humidity_pct': (0, 100, True, True),
    'precipitation_mm': (0, 300, True, True),
    'slope_deg': (0, 90, True, False),
    'road_length_m': (0, None, False, True),
    'wind_cross_road_proxy': (0, 1, True, True),
}


def _v2_encode(value, check):
    count = 0
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    for chunk in encoder.iterencode(value):
        check()
        raw = chunk.encode('utf-8')
        count += len(raw)
        if count > V2_MAX_JSON_BYTES:
            raise ResearchCapacityBlocked('CAPACITY_BLOCKED: combined v2 canonical JSON bytes')
        yield raw
    check()


def _v2_digest(value, check):
    sha = hashlib.sha256()
    for raw in _v2_encode(value, check):
        sha.update(raw)
    check()
    return sha.hexdigest()


def _v2_copy(values, check):
    pending, count = [(values, 0)], 0
    while pending:
        check()
        item, depth = pending.pop()
        count += 1
        if count > V2_MAX_JSON_NODES or depth > 12:
            raise ResearchCapacityBlocked('CAPACITY_BLOCKED: combined v2 JSON complexity')
        kind = type(item)
        if kind in (dict, list):
            if count + len(pending) + len(item) > V2_MAX_JSON_NODES:
                raise ResearchCapacityBlocked('CAPACITY_BLOCKED: combined v2 JSON nodes')
            if kind is dict:
                for key in item:
                    check()
                    if type(key) is not str or len(key) > 512:
                        raise ValueError('Bounded string v2 JSON keys required')
            for child in (item.values() if kind is dict else item):
                check()
                pending.append((child, depth+1))
        elif kind is str:
            if len(item) > 4096:
                raise ResearchCapacityBlocked('CAPACITY_BLOCKED: v2 JSON string')
        elif kind is int:
            if item.bit_length() > 1024:
                raise ResearchCapacityBlocked('CAPACITY_BLOCKED: v2 JSON integer size')
        elif kind is float:
            if not math.isfinite(item):
                raise ValueError('Nonfinite v2 JSON number')
        elif kind not in (bool, type(None)):
            raise ValueError('JSON-only v2 preparation inputs required')
    raw = bytearray()
    for chunk in _v2_encode(values, check):
        raw.extend(chunk)
    check()
    owned = json.loads(raw)
    check()
    return owned


def _v2_config(config, expected, definitions_sha, check):
    _hba1._fields(config, V2_CONFIG_FIELDS)
    if config['schema_version'] != CONFIG_VERSION_V2 or config['mode'] != 'DEVELOPMENT_ONLY':
        raise ValueError('Only explicit development candidate-config v2 is supported')
    if _v2_digest(config, check) != _hba1._hash(expected):
        raise ValueError('Candidate config content digest mismatch')
    if _hba1._hash(config['feature_definition_sha256']) != _hba1._hash(definitions_sha):
        raise ValueError('Candidate config strict feature-definition digest mismatch')
    choices = config['candidate_ids']
    if (type(choices) is not list or len(choices) != 3 or
            any(type(name) is not str for name in choices) or choices[0] != 'uniform' or
            len(set(choices)) != 3 or any(name not in V2_OPTIONAL_IDS for name in choices[1:])):
        raise ValueError('Uniform first plus exactly two unique fixed known candidate IDs required')
    if 'HB-A1' in choices:
        recipe = config['hba1_recipe']
        _hba1._recipe(recipe, _v2_digest(recipe, check), check)
        if recipe['feature_mask'] != [True]*7:
            raise ValueError('Candidate-slot HB-A1 requires the full seven-feature recipe; no ablation recipe')
    elif config['hba1_recipe'] is not None:
        raise ValueError('HB-A1 recipe must be null when HB-A1 is not selected')
    check()
    return choices


def _v2_hba1_fit(value, selected, recipe, training_rows_sha, row_ids_sha, raw_features_sha, check):
    check()
    if type(value) is not dict or value.get('receipt_sha256') != _v2_digest({
            k:v for k,v in value.items() if k != 'receipt_sha256'}, check):
        raise ValueError('HB-A1 fit receipt content digest mismatch')
    if (value.get('schema_version') != _hba1.FIT_VERSION or
            value.get('training_selection_sha256') != selected['selection_sha256'] or
            value.get('recipe_sha256') != _v2_digest(recipe, check) or value.get('counts') != selected['counts']):
        raise ValueError('HB-A1 fit receipt differs from configured training/recipe identity')
    if value.get('status') == 'NEED_MORE_DATA':
        if value.get('model') is not None or type(value.get('blockers')) is not list or not value['blockers']:
            raise ValueError('HB-A1 insufficiency receipt conflicts with returned model/blockers')
        return None
    model = value.get('model')
    if value.get('status') != 'DEVELOPMENT_FIT_ONLY' or type(model) is not dict or value.get('blockers') != []:
        raise ValueError('Expected a complete standalone HB-A1 software fit')
    if (model.get('recipe') != recipe or model.get('recipe_sha256') != _v2_digest(recipe, check) or
            model.get('training_rows_sha256') != training_rows_sha or
            model.get('training_row_ids_sha256') != row_ids_sha or
            model.get('raw_feature_rows_sha256') != raw_features_sha):
        raise ValueError('HB-A1 model declared code/recipe/TRAIN snapshot differs from candidate config')
    return model


def _v2_supplied_hba1_raw_fields(rows, check):
    """Check known supplied values using the legacy raw-feature bounds.

    This validates existing fields only, including a partial schema. Missing
    fields are neither created nor imputed; they still block the whole fit.
    """
    for row in rows:
        check()
        features = row['features']
        for name in _hba1.FEATURES:
            check()
            if name not in features:
                continue
            number = _hba1._finite(features[name])
            bounds = V2_RAW_FEATURE_BOUNDS.get(name)
            if bounds is None:
                continue
            lower, upper, include_lower, include_upper = bounds
            below = number < lower if include_lower else number <= lower
            above = upper is not None and (number > upper if include_upper else number >= upper)
            if below or above:
                raise ValueError('Known supplied HB-A1 raw feature outside physical range: '+name)


def prepare_research_candidates_v2(selection, forecast_rows, *, candidate_config,
        expected_config_sha256, cutoff_time, joined_universe_sha256,
        feature_definition_sha256, budget_seconds=30, check=None):
    """Prepare one explicit three-slot development set, never select a winner.

    Hashes prove declared consistency only. File authentication, a trusted
    campaign slot/cumulative-budget ledger and pre-reveal freeze/consumption
    lock remain caller dependencies; changing config IDs cannot establish them.
    """
    if type(budget_seconds) not in (int, float) or not 0 < budget_seconds <= MAX_BUDGET_SECONDS or not math.isfinite(budget_seconds):
        raise ValueError('Budget must be finite, positive and at most 300 seconds')
    if check is not None and not callable(check):
        raise ValueError('Parent check must be callable')
    deadline, parent_check = time.monotonic()+budget_seconds, check

    def guard():
        if parent_check is not None:
            parent_check()
        if time.monotonic() >= deadline:
            raise ResearchBudgetExhausted('RUNTIME_BLOCKED: shared v2 candidate deadline expired')

    def remaining():
        guard()
        left = deadline-time.monotonic()
        if left <= 0:
            raise ResearchBudgetExhausted('RUNTIME_BLOCKED: no remaining v2 fit budget')
        return left

    def finish(value):
        value['receipt_sha256'] = _v2_digest(value, guard)
        guard()
        return value

    guard()
    expected = _hba1._hash(expected_config_sha256)
    if type(forecast_rows) is not list:
        raise ValueError('Explicit complete future row list required')
    if len(forecast_rows) > MAX_FORECAST_ROWS:
        raise ResearchCapacityBlocked('CAPACITY_BLOCKED: complete v2 forecast rows')
    if type(selection) is dict:
        count = sum(len(selection[name]) for name in ('accepted', 'rejected') if type(selection.get(name)) is list)
        if count > V2_MAX_TRAIN_ROWS:
            raise ResearchCapacityBlocked('CAPACITY_BLOCKED: v2 training selection rows')
    config, selected_input, rows = _v2_copy([candidate_config, selection, forecast_rows], guard)
    try:
        choices = _v2_config(config, expected, feature_definition_sha256, guard)
        selected = validate_selection(selected_input)
        guard()
        future = validate_future_rows(rows, cutoff_time=cutoff_time,
            universe_sha256=joined_universe_sha256, heldout_night=selected['heldout_night'],
            feature_names=selected['feature_names'])
        guard()
        reasons = list(selected['blockers']) if selected['status'] == 'NEED_MORE_DATA' else []
        if 'HB-A1' in choices:
            # Known contradictions must not become data gaps just because a
            # different required raw field is absent from the whole schema.
            _v2_supplied_hba1_raw_fields(selected['accepted'], guard)
            _v2_supplied_hba1_raw_fields(future, guard)
            if selected['feature_names'] != sorted(_hba1.FEATURES):
                reasons.append('HB_A1_REQUIRES_EXACT_SEVEN_RAW_FEATURE_SCHEMA')
            else:
                _, _, _, missing = _hba1._training(selected, guard)
                # Recheck physical ranges even when the training floor is unmet.
                _hba1._future(rows, cutoff_time, joined_universe_sha256, selected['heldout_night'], guard)
                reasons.extend(missing)
        row_ids, feature_rows = [], []
        for row in selected['accepted']:
            guard()
            row_ids.append(row['row_id'])
            feature_rows.append(dict(row_id=row['row_id'], features=row['features']))
        training_rows_sha = _v2_digest(selected['accepted'], guard)
        row_ids_sha, features_sha = _v2_digest(row_ids, guard), _v2_digest(feature_rows, guard)
        common = dict(schema_version=VERSION_V2, candidate_config_sha256=expected,
            candidate_ids=list(choices), feature_definition_sha256=feature_definition_sha256,
            training_selection_sha256=selected['selection_sha256'], training_rows_sha256=training_rows_sha,
            training_row_ids_sha256=row_ids_sha, raw_feature_rows_sha256=features_sha,
            heldout_night=selected['heldout_night'], fit_cutoff=selected['fit_cutoff'], cutoff_time=cutoff_time,
            joined_universe_sha256=joined_universe_sha256, forecast_units=len(future),
            joined_digest_semantics='CANONICAL_SUPPLIED_JOINED_ROWS_NOT_SOURCE_UNIVERSE_FILE',
            validation_status='NOT_VALIDATED', replay_status='PREPARED_NOT_PUBLISHED_OR_TRUSTED_SEALED',
            preregistration='CALLER_DEPENDENCY_REQUIRED',
            implementation_blockers=['CONFIGURED_STAGE1_SOURCE_PARENT_NOT_CONNECTED',
                'TRUSTED_CUMULATIVE_CAMPAIGN_LEDGER_NOT_IMPLEMENTED',
                'TRUSTED_PRE_REVEAL_FREEZE_AND_CONSUMPTION_LEDGER_NOT_IMPLEMENTED',
                'MODEL_COMPARISON_AND_WINNER_SELECTION_NOT_IMPLEMENTED'],
            limitations=['DECLARED_CONFIG_MODEL_RECIPE_CODE_HASHES_NOT_FILE_AUTHENTICATION',
                'NO_HELD_OUT_OUTCOMES_METRICS_WINNER_OR_CONFIRMATION_CONSUMED',
                'SAME_CAMPAIGN_CANDIDATE_LIMIT_AND_CUMULATIVE_BUDGET_REQUIRE_TRUSTED_CALLER',
                'CHANGED_CONFIG_HASH_DOES_NOT_RESET_RESEARCH_EXPOSURE_OR_CONFIRMATION_CONSUMPTION'],
            **_hba1._flags())
        if reasons:
            return finish(dict(common, status='NEED_MORE_DATA', candidates=[], blockers=reasons))
        expected_rows = {row['row_id']: row for row in future}
        prepared = []
        for candidate_id in choices:
            guard()
            if candidate_id == 'uniform':
                model, prediction = _uniform(selected, future, cutoff_time, joined_universe_sha256, guard)
            elif candidate_id == 'HB-A0':
                fitted = fit_shrinkage(selected)
                guard()
                if fitted.get('status') != 'DEVELOPMENT_FIT_ONLY' or type(fitted.get('model')) is not dict:
                    raise ValueError('Expected complete HB-A0 fit on common selected training rows')
                model = fitted['model']
                prediction = predict_shrinkage(model, rows, cutoff_time=cutoff_time, universe_sha256=joined_universe_sha256)
            elif candidate_id == 'HB-B1':
                model = fit_hierarchy(selected)
                guard()
                if model.get('status') != 'DEVELOPMENT_CANDIDATE_FITTED':
                    raise ValueError('Expected complete HB-B1 fit on common selected training rows')
                prediction = rank_hierarchy(model, rows, cutoff_time=cutoff_time, universe_sha256=joined_universe_sha256)
            else:
                recipe = config['hba1_recipe']
                fitted = _hba1.fit_hba1(selected, recipe=recipe, expected_recipe_sha256=_v2_digest(recipe, guard),
                    budget_seconds=remaining(), check=guard)
                guard()
                model = _v2_hba1_fit(fitted, selected, recipe, training_rows_sha, row_ids_sha, features_sha, guard)
                if model is None:
                    return finish(dict(common, status='NEED_MORE_DATA', candidates=[], blockers=list(fitted['blockers'])))
                prediction = _hba1.predict_hba1(model, rows, cutoff_time=cutoff_time,
                    joined_universe_sha256=joined_universe_sha256, budget_seconds=remaining(), check=guard)
                guard()
                if (prediction.get('training_selection_sha256') != selected['selection_sha256'] or
                        prediction.get('recipe_sha256') != _v2_digest(recipe, guard)):
                    raise ValueError('HB-A1 prediction differs from configured TRAIN/recipe identity')
            guard()
            if ('candidate_id' in prediction and prediction['candidate_id'] != candidate_id or
                    'training_selection_sha256' in prediction and
                    prediction['training_selection_sha256'] != selected['selection_sha256']):
                raise ValueError('Native prediction candidate/TRAIN assertion contradicts configured identity')
            candidate = _candidate(candidate_id, model, prediction, joined_universe_sha256,
                expected_rows, selected, cutoff_time, guard)
            guard()
            candidate.update(candidate_config_sha256=expected, feature_definition_sha256=feature_definition_sha256,
                training_selection_sha256=selected['selection_sha256'], training_rows_sha256=training_rows_sha,
                training_row_ids_sha256=row_ids_sha, raw_feature_rows_sha256=features_sha)
            prepared.append(candidate)
        return finish(dict(common, status='DIAGNOSTIC_CANDIDATES_PREPARED', candidates=prepared, blockers=[]))
    except (ResearchInputCapacity, _hba1.HBA1CapacityBlocked) as exc:
        raise ResearchCapacityBlocked('CAPACITY_BLOCKED: '+str(exc)) from exc
    except (KeyError, TypeError, IndexError, OverflowError) as exc:
        raise ValueError('Malformed v2 candidate contract/output: '+str(exc)) from exc
