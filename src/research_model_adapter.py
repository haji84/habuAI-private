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


def _uniform(selected, future, cutoff_time, joined_sha, check):
    # Exact historical uniform smoothing formula in model_evaluation._fit.
    # This is a separate research receipt, never a rewritten historical model.
    counts = selected["counts"]
    probability = (counts["positives"] + 1) / (counts["accepted_rows"] + 2)
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
