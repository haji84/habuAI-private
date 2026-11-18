"""Posthoc feature-coverage diagnostics on existing owner NightCount + JMA notes.

Provides actionable covariate gaps without asserting original P0 availability,
true active-search effort, spatial negatives, causal influence or model fit.
"""
from __future__ import annotations
import hashlib
import json
import math
from collections import Counter
from datetime import date

from research_nightcount_clock import compare_nightcount

VERSION = "habu-research-feature-coverage-v1"
FEATURES = {
    "JMA_KONIYA_CALENDAR_DAY_MIN_NOT_HUNT_TIME": ("station_day_min_c",),
    "JMA_KONIYA_HOURLY": ("station_15_c", "station_20_c",
                         "station_15_to_20_delta_c", "station_20_day_over_day_c"),
}


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False,
                                     sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def analyze_feature_coverage(count_source: dict, environment_source: dict) -> dict:
    """Compare only observed matching nights. All posthoc station features remain unqualified."""
    # Reuse the existing count-source validator; no new authority inference.
    compared = compare_nightcount(count_source)
    if (type(environment_source) is not dict or
            environment_source.get("schema_version") != "habu-cooling-retrospective-audit-v1"):
        raise ValueError("Expected existing cooling historical source")
    raw = environment_source.get("records")
    if type(raw) is not list or len(raw) > 1000:
        raise ValueError("Invalid or unbounded environmental rows")
    counts = {r["night"]: r for r in count_source["training_nights"]}
    seen = set()
    groups = {key: [] for values in FEATURES.values() for key in values}
    matched = []
    for row in raw:
        if type(row) is not dict or type(row.get("night")) is not str:
            raise ValueError("Invalid environmental row")
        night = row["night"]
        date.fromisoformat(night)
        if night in seen:
            raise ValueError("Repeated environment night")
        seen.add(night)
        reference = counts.get(night)
        if reference is None:
            raise ValueError("Environment night outside the declared NightCount cohort")
        if (type(row.get("owner_captures")) is not int or
                row["owner_captures"] != reference["count"] or
                type(row.get("captured_not_no_capture_negative")) is not bool or
                row["captured_not_no_capture_negative"] is not True):
            raise ValueError("Conflicting capture count or unsupported Negative claim")
        hours = row.get("session_elapsed_proxy_h")
        if (type(hours) not in (int,float) or not math.isfinite(hours) or
                abs(hours-reference["effort_hours_proxy"]) > .001):
            raise ValueError("Environmental effort is inconsistent with the stored source")
        group = row.get("temp_source")
        if group not in FEATURES:
            raise ValueError("Unknown station measurement scope")
        values = {}
        for key in FEATURES[group]:
            if key not in row:
                continue
            v = row[key]
            if type(v) not in (int,float) or not math.isfinite(v) or not -100 <= v <= 100:
                raise ValueError("Invalid observed station covariate")
            groups[key].append({"night": night, "feature": float(v),
                                "captured": row["owner_captures"]})
            values[key] = float(v)
        if not values:
            raise ValueError("No observed values for environmental row")
        matched.append(night)

    feature_status = {}
    for feature, items in groups.items():
        capture_values = [x["captured"] for x in items]
        unique = len({x["feature"] for x in items})
        reason = ("posthoc measurement; no source-bound as-of availability" if len(items) >= 6
                  else "fewer than six directly comparable nights")
        feature_status[feature] = {
            "matched_nights": len(items), "unique_observed_values": unique,
            "source_class": ("CALENDAR_DAY_MIN_NOT_HUNT_TIME" if feature=="station_day_min_c"
                             else "HOURLY_STATION_NOT_ON_ROAD"),
            "mean_recorded_captures_when_feature_present":
                (sum(capture_values)/len(capture_values) if capture_values else None),
            "research_eligibility": "DESCRIPTIVE_ONLY" if items else "NO_OBSERVATIONS",
            "forecast_ready": False, "coefficient_fitted": False,
            "reason": reason,
        }
    extreme = sorted(r["night"] for r in count_source["training_nights"]
                     if r["count"] == 0 or r["count"] >= 6)
    missing = sorted(set(counts) - set(matched))
    return {
        "schema_version": VERSION,
        "nightcount_source_json_sha256": _hash(count_source),
        "environment_source_json_sha256": _hash(environment_source),
        "count_research_folds_checked": compared["heldout_chronological_folds"],
        "count_source_nights": len(counts), "environment_matched_nights": len(matched),
        "environment_missing_nights": missing,
        "feature_coverage": feature_status,
        "extreme_count_rule": "RECORDED_CAPTURE_COUNT_EQ_0_OR_GTE_6_DESCRIPTIVE_ONLY",
        "extreme_nights": extreme,
        "extreme_nights_without_environment": sorted(set(extreme)-set(matched)),
        "distinct_feature_groups_not_poolable": True,
        "recorded_capture_count_equals_biological_abundance": False,
        "source_asof_eligibility": "NOT_ESTABLISHED",
        "actual_active_search_effort_eligibility": "NOT_ESTABLISHED",
        "formal_negative_labels_created": 0,
        "causal_weather_effect_identified": False,
        "predictive_improvement_proven": False,
        "champion_promotion_allowed": False,
        "next_action": ("Collect comparable night-specific weather, road wetness, "
                        "pre-cutoff availability, observed search effort and route exposure "
                        "without backfilling ex-ante inputs from later observations."),
    }
