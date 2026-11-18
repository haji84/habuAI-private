"""Bounded, retrospective comparison of existing private NightCount/EventClock models.

No GPX, coordinates, official labels, P0 issuance or Champion authority here.
Chronological predictions use only preceding *rows*. Historical availability
of a row to the owner at the time is not asserted by a retrospective source.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from datetime import date

VERSION = "habu-count-clock-retrospective-comparison-v1"
MAX_NIGHTS = 1000
MAX_EVENTS = 100000
FIVE_HOUR_ASSUMPTION = 5.0
MIN_PRIOR_NIGHTS = 5
BOOTSTRAP_DRAWS = 2000


def _finite(value, name):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Nonfinite or invalid " + name)
    return float(value)


def _identity(source):
    raw = json.dumps(source, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _poisson_nll(mean, count):
    if mean <= 0:
        return 0.0 if count == 0 and mean == 0 else None
    return mean - count * math.log(mean) + math.lgamma(count + 1)


def _metrics(rows, key):
    ae = [abs(row[key] - row["count"]) for row in rows]
    se = [(row[key] - row["count"]) ** 2 for row in rows]
    nll = [_poisson_nll(row[key], row["count"]) for row in rows]
    return {
        "n_evaluated_nights": len(rows),
        "mae_captures": sum(ae) / len(ae),
        "rmse_captures": math.sqrt(sum(se) / len(se)),
        "mean_poisson_nll": sum(nll) / len(nll) if all(x is not None for x in nll) else None,
    }


def _paired_uncertainty(rows, key, criterion="absolute"):
    if criterion == "absolute":
        differences = [abs(row[key] - row["count"]) -
                       abs(row["historical_night_mean"] - row["count"])
                       for row in rows]
    else:
        nll_candidate = [_poisson_nll(row[key], row["count"]) for row in rows]
        nll_base = [_poisson_nll(row["historical_night_mean"], row["count"]) for row in rows]
        if any(x is None for x in nll_candidate + nll_base):
            return None
        differences = [a - b for a, b in zip(nll_candidate, nll_base)]
    rng = random.Random(1642)
    samples = sorted(sum(rng.choices(differences, k=len(differences))) / len(differences)
                     for _ in range(BOOTSTRAP_DRAWS))
    return [samples[49], samples[1949]]


def compare_nightcount(source, *, minimum_prior=MIN_PRIOR_NIGHTS,
                       assumed_hours=FIVE_HOUR_ASSUMPTION):
    if type(source) is not dict or source.get("schema_version") != "habu-research-nightcount-poisson-v1.2":
        raise ValueError("Existing NightCount v1.2 research source required")
    if type(minimum_prior) is not int or not 3 <= minimum_prior <= 50:
        raise ValueError("Invalid historical training minimum")
    assumed_hours = _finite(assumed_hours, "assumed hours")
    if not 0 < assumed_hours <= 12:
        raise ValueError("Fixed research duration must be in (0,12]")
    training = source.get("training_nights")
    if type(training) is not list or not minimum_prior < len(training) <= MAX_NIGHTS:
        raise ValueError("Insufficient bounded historical nights")
    rows = []
    for row in training:
        if type(row) is not dict or type(row.get("night")) is not str:
            raise ValueError("Malformed historical row")
        date.fromisoformat(row["night"])
        count = row.get("count")
        if type(count) is not int or not 0 <= count <= MAX_EVENTS:
            raise ValueError("Invalid count, including bool")
        hours = _finite(row.get("effort_hours_proxy"), "elapsed session proxy")
        if not 0 < hours <= 24:
            raise ValueError("Invalid elapsed session proxy")
        if rows and row["night"] <= rows[-1]["night"]:
            raise ValueError("Duplicate/out-of-order operational nights")
        rows.append({"night": row["night"], "count": count, "proxy_hours": hours})
    if (type(source.get("nights")) is not int or source["nights"] != len(rows) or
            type(source.get("owner_captures")) is not int or
            sum(x["count"] for x in rows) != source["owner_captures"] or
            abs(sum(x["proxy_hours"] for x in rows) -
                _finite(source.get("elapsed_session_hours_proxy"), "model total hours")) > 0.0001):
        raise ValueError("Model summary and historical rows disagree")
    folds = []
    for i in range(minimum_prior, len(rows)):
        prior, target = rows[:i], rows[i]
        total = sum(item["count"] for item in prior)
        hours_total = sum(item["proxy_hours"] for item in prior)
        forecasts = {
            "historical_night_mean": total / len(prior),
            "assumed_5h_exposure_rate": total / hours_total * assumed_hours,
            "recent_5_night_mean": sum(item["count"] for item in prior[-5:]) / 5,
        }
        folds.append({"count": target["count"], **forecasts})
    names = ["historical_night_mean", "assumed_5h_exposure_rate", "recent_5_night_mean"]
    metrics = {name: _metrics(folds, name) for name in names}
    baseline = metrics[names[0]]
    comparisons = []
    for name in names[1:]:
        candidate = metrics[name]
        delta_mae = candidate["mae_captures"] - baseline["mae_captures"]
        delta_nll = (candidate["mean_poisson_nll"] - baseline["mean_poisson_nll"]
                     if candidate["mean_poisson_nll"] is not None and
                     baseline["mean_poisson_nll"] is not None else None)
        both_better = delta_mae < 0 and delta_nll is not None and delta_nll < 0
        comparisons.append({
            "candidate": name,
            "delta_mae_vs_historical_night_mean": delta_mae,
            "delta_poisson_nll_vs_historical_night_mean": delta_nll,
            "delta_mae_bootstrap_95_interval": _paired_uncertainty(folds, name),
            "delta_nll_bootstrap_95_interval": _paired_uncertainty(folds, name, "nll"),
            "decision": "RESEARCH_HYPOTHESIS_ONLY" if both_better else "REJECT_EXPLORATORY_CHANGE",
            "formal_promotion_eligible": False,
        })
    return {
        "schema_version": VERSION, "component": "nightcount",
        "source_schema_version": source["schema_version"], "parsed_source_sha256": _identity(source),
        "sample_nights": len(rows), "sample_owner_captures": sum(x["count"] for x in rows),
        "heldout_chronological_folds": len(folds), "minimum_prior_nights": minimum_prior,
        "assumed_ex_ante_duration_hours": assumed_hours,
        "holdout_actual_proxy_effort_used_as_predictor": False,
        "scores": metrics, "paired_comparisons": comparisons,
        "evaluation_class": "RETROSPECTIVE_CHRONOLOGICAL_REPLAY",
        "historical_source_availability_verified": False,
        "formal_100m_10min": "NOT_EVALUATED", "champion_promotion_allowed": False,
    }


def compare_eventclock(source):
    if type(source) is not dict or source.get("schema_version") != "habu-positive-event-clock-research-v1.2":
        raise ValueError("Existing EventClock v1.2 research source required")
    prior, holdout, combined = (source.get(k) for k in
                                ("prior_histogram", "nov_increment_histogram", "new_histogram"))
    if (any(type(x) is not list or len(x) != 6 for x in (prior, holdout, combined)) or
            any(type(v) is not int or not 0 <= v <= MAX_EVENTS for a in
                (prior, holdout, combined) for v in a)):
        raise ValueError("Invalid six-bin histograms")
    if any(a + b != c for a, b, c in zip(prior, holdout, combined)):
        raise ValueError("Historical and evaluation histogram overlap/inconsistency")
    if (sum(holdout) < 1 or type(source.get("total_owner_recorded_capture_events_both_years")) is not int or
            sum(combined) != source["total_owner_recorded_capture_events_both_years"]):
        raise ValueError("Histogram totals disagree")
    alpha = _finite(source.get("alpha_per_bin"), "smoothing alpha")
    if not 0 < alpha <= 10:
        raise ValueError("Invalid recorded Laplace smoothing parameter")
    prior_total = sum(prior)
    historical_probs = [(n + alpha) / (prior_total + alpha * 6) for n in prior]
    uniform = [1 / 6] * 6
    # Deliberately fixed half-shrink research counterfactual; chosen after seeing
    # the stored holdout and therefore *never* independent candidate validation.
    half_shrink = [(p + 1 / 6) / 2 for p in historical_probs]
    def nll(p):
        return -sum(k * math.log(prob) for k, prob in zip(holdout, p)) / sum(holdout)
    scores = {"uniform_six_bins": nll(uniform),
              "historical_laplace": nll(historical_probs),
              "half_shrink_to_uniform": nll(half_shrink)}
    return {
        "schema_version": VERSION, "component": "eventclock",
        "source_schema_version": source["schema_version"], "parsed_source_sha256": _identity(source),
        "historical_events": prior_total, "evaluation_events": sum(holdout),
        "mean_negative_log_likelihood_per_event": scores,
        "half_shrink_delta_vs_uniform": scores["half_shrink_to_uniform"] - scores["uniform_six_bins"],
        "half_shrink_delta_vs_historical": scores["half_shrink_to_uniform"] - scores["historical_laplace"],
        "decision": ("RESEARCH_HYPOTHESIS_ONLY" if scores["half_shrink_to_uniform"] <
                     min(scores["historical_laplace"], scores["uniform_six_bins"])
                     else "REJECT_EXPLORATORY_CHANGE"),
        "selection_was_posthoc": True,
        "evaluation_class": "RETROSPECTIVE_RECENT_EVENTS_DIAGNOSTIC",
        "rate_per_active_search_time": "NOT_ESTIMATED",
        "formal_100m_10min": "NOT_EVALUATED", "champion_promotion_allowed": False,
    }
