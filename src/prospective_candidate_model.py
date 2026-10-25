"""Prospective feature-aware candidate model, never production-issued ORIGINAL.

Learns only from explicitly GPS-observed exposure units with source hashes and
ex-ante feature availability. Source attestations remain independently auditable;
a JSON claim alone cannot authorize a real P0 or formal KPI.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
FEATURES = ("temperature_c", "humidity_pct", "precipitation_mm",
            "slope_deg", "tpi_m", "road_length_m",
            "wind_cross_road_proxy")


class CandidateInputError(ValueError):
    pass


def _time(text):
    if not isinstance(text, str):
        raise CandidateInputError("ISO timestamp string required")
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CandidateInputError("Invalid ISO timestamp") from exc
    if dt.utcoffset() is None:
        raise CandidateInputError("Timezone required")
    return dt.astimezone(JST)


def _night(dt):
    local = dt.astimezone(JST)
    if local.hour < 7:
        local -= timedelta(days=1)
    return local.date().isoformat()


def _sha(value):
    return isinstance(value, str) and bool(re.fullmatch("[a-f0-9]{64}", value))


def _coords(cell_id):
    found = re.fullmatch(r"utm52n_100m_([0-9]+)_([0-9]+)", str(cell_id))
    if not found:
        raise CandidateInputError("Expected UTM52N 100m road cell identifier")
    x, y = int(found[1]), int(found[2])
    if not (1000 <= x < 9000 and 0 <= y < 100000):
        raise CandidateInputError("100m cell outside projected UTM domain")
    return x, y


def _features(row):
    values = []
    for name in FEATURES:
        v = row.get(name)
        if type(v) not in (int, float) or not math.isfinite(v):
            raise CandidateInputError("Missing/non-finite predictor: " + name)
        values.append(float(v))
    if not (0 <= values[1] <= 100 and 0 <= values[2] <= 300
            and 0 <= values[3] < 90 and values[5] > 0
            and 0 <= values[6] <= 1):
        raise CandidateInputError("Predictor outside physically allowed limits")
    return values


def _validate_row(row, *, training=False):
    if not isinstance(row, dict):
        raise CandidateInputError("Prediction row must be object")
    x, y = _coords(row.get("cell_id"))
    when = _time(row["window_start_jst"])
    cutoff = _time(row["forecast_cutoff"])
    available = _time(row["features_available_at"])
    if _night(when) != row.get("operational_night") or when <= cutoff:
        raise CandidateInputError("Window must be future of cutoff in matching operational night")
    if when.minute % 10 or when.second or when.microsecond:
        raise CandidateInputError("Window start must be aligned to 10 minutes")
    if available > cutoff:
        raise CandidateInputError("Predictors unavailable at historical forecast cutoff")
    if row.get("weather_source_role") != "EX_ANTE_FORECAST":
        raise CandidateInputError("Observed later weather is not a valid ex-ante feature")
    if not _sha(row.get("features_source_sha256")):
        raise CandidateInputError("Feature snapshot hash required")
    values = _features(row)
    if training:
        if (row.get("exposure_proof") != "GPX_PASSAGE_VALIDATED"
                or not _sha(row.get("outcome_source_sha256"))):
            raise CandidateInputError("Unknown/unvisited grid cannot become a Negative")
        count = row.get("owner_capture_count")
        if type(count) is not int or count < 0 or count > 25:
            raise CandidateInputError("Invalid distinct personal Habu capture count")
        outcome_ready = _time(row["outcome_available_at"])
        if outcome_ready < when:
            raise CandidateInputError("Outcome cannot exist before its observed window")
    return values


def _sigmoid(z):
    return 1.0 / (1.0 + math.exp(-max(-35, min(35, z))))


def _score(x, coef, means, scales):
    return _sigmoid(coef[0] + sum(
        c * ((v - mu) / std) for c, v, mu, std in
        zip(coef[1:], x, means, scales)))


def train_candidate(history, *, training_cutoff: str, holdout_nights: int = 2):
    """Deterministic penalized logistic baseline; not a validated Champion."""
    cutoff = _time(training_cutoff)
    if not isinstance(history, list) or not (20 <= len(history) <= 100_000):
        raise CandidateInputError("Minimum 20 actual observed exposure units required")
    items, keys = [], set()
    for row in history:
        values = _validate_row(row, training=True)
        w = _time(row["window_start_jst"])
        if _time(row["outcome_available_at"]) >= cutoff or w >= cutoff:
            raise CandidateInputError("Training would consume unavailable or future labels")
        key = (row["operational_night"], row["cell_id"], row["window_start_jst"])
        if key in keys:
            raise CandidateInputError("Duplicate road-time observation")
        keys.add(key)
        items.append((row["operational_night"], values, 1 if row["owner_capture_count"] > 0 else 0))
    nights = sorted({row[0] for row in items})
    if len(nights) < holdout_nights + 5 or holdout_nights < 2:
        raise CandidateInputError("At least five train and two chronological holdout nights required")
    training = [t for t in items if t[0] < nights[-holdout_nights]]
    holdout = [t for t in items if t[0] >= nights[-holdout_nights]]
    positives = sum(t[2] for t in training)
    if positives < 2 or positives == len(training):
        raise CandidateInputError("Insufficient verified positive/negative training contrast")
    means = [mean(t[1][i] for t in training) for i in range(len(FEATURES))]
    scales = [max(1e-9, math.sqrt(mean((t[1][i] - means[i])**2 for t in training)))
              for i in range(len(FEATURES))]
    coef = [0.0] * (len(FEATURES) + 1)
    # L2 penalty and fixed epochs, with deterministic bounded step size.
    n = len(training)
    for epoch in range(320):
        gradient = [0.0] * len(coef)
        for _, x, y in training:
            norm = [(v - u) / s for v, u, s in zip(x, means, scales)]
            error = _score(x, coef, means, scales) - y
            for j, value in enumerate([1.0, *norm]):
                gradient[j] += error * value
        for j in range(len(coef)):
            penalty = (0.04 * coef[j]) if j else 0.0
            coef[j] -= 0.15 * (gradient[j] / n + penalty)
    brier = mean((_score(x, coef, means, scales) - y)**2 for _, x, y in holdout)
    model = {
        "schema_version": "habu-prospective-candidate-v1",
        "status": "DIAGNOSTIC_WALK_FORWARD_CANDIDATE_ONLY",
        "training_cutoff": cutoff.isoformat(), "train_nights": nights[:-holdout_nights],
        "untouched_holdout_nights": nights[-holdout_nights:],
        "train_units": len(training), "holdout_units": len(holdout),
        "train_positive_units": positives,
        "holdout_brier_diagnostic": round(brier, 8),
        "feature_names": list(FEATURES),
        "means": means, "scales": scales, "coefficients": coef,
        "production_activation_authorized": False,
        "official_stage1_recall_computed": False,
        "official_100m_10min_kpi_computed": False,
        "immutable_original_issued": False,
        "training_source_review": "INPUT_CONTRACT_ONLY_NOT_INDEPENDENTLY_ATTESTED",
    }
    raw = json.dumps(model, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False).encode()
    model["model_sha256"] = hashlib.sha256(raw).hexdigest()
    return model


def rank_future(model, rows, *, issued_at: str, operational_night: str):
    """Produce prospective 1km→100m×10min candidate scores (no P0 Freeze)."""
    now = _time(issued_at)
    if model.get("status") != "DIAGNOSTIC_WALK_FORWARD_CANDIDATE_ONLY":
        raise CandidateInputError("Unrecognized candidate model")
    if _time(model["training_cutoff"]) > now:
        raise CandidateInputError("Model training ended after issuance")
    if not isinstance(rows, list) or not (1 <= len(rows) <= 50000):
        raise CandidateInputError("Prospective forecast universe rows required")
    seen, targets, by_area = set(), [], defaultdict(list)
    for row in rows:
        x = _validate_row(row)
        start = _time(row["window_start_jst"])
        if (row["operational_night"] != operational_night or
                start <= now or _time(row["features_available_at"]) > now):
            raise CandidateInputError("Future row night or issuance cutoff violated")
        key = (row["cell_id"], start.isoformat())
        if key in seen:
            raise CandidateInputError("Duplicate prospective unit")
        seen.add(key)
        cx, cy = _coords(row["cell_id"])
        p = _score(x, model["coefficients"], model["means"], model["scales"])
        area = f"utm52n_1km_{cx//10}_{cy//10}"
        zone500 = f"utm52n_500m_{cx//5}_{cy//5}"
        zone250 = f"utm52n_250m_{int((cx*100+50)//250)}_{int((cy*100+50)//250)}"
        item = {"cell_id": row["cell_id"], "window_start_jst": start.isoformat(),
                "area_1km": area, "zone_500m": zone500,
                "zone_250m": zone250,
                "probability_diagnostic": round(p, 8)}
        targets.append(item)
        by_area[area].append(p)
    # Scores summarize the observed candidate universe only, not complete unseen terrain.
    area_rows = sorted(({"area_1km": k, "rank_score": round(max(v), 8),
                         "candidate_units": len(v)} for k, v in by_area.items()),
                       key=lambda x: (-x["rank_score"], x["area_1km"]))
    return {
        "status": "UNVALIDATED_PROSPECTIVE_MODEL_OUTPUT_NOT_ORIGINAL",
        "operational_night": operational_night, "issued_at": now.isoformat(),
        "model_sha256": model["model_sha256"],
        "area_rank_top10": area_rows[:10],
        "area_ranking_full_candidate_universe": area_rows,
        "targets_100m_10min": targets,
        "forecast_universe_coverage_verified": False,
        "stage1_recall_eligible": False,
        "formal_100m_10min_eligible": False,
        "production_p0_freeze_allowed": False,
        "route_candidates_A_B_C": "NOT_PRODUCED",
    }
