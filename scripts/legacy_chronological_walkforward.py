#!/usr/bin/env python3
"""Leakage-guarded chronological evaluation of the legacy 10 m dataset.

This is diagnostic evidence only. It does not implement the current official
100 m ±10 minute KPI and must never be mixed with ORIGINAL prediction scores.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


SOURCE_COMMIT = "4877c30d518bec4022041d4868e0a1c239e4b28c"
SOURCE_URL = (
    "https://raw.githubusercontent.com/haji84/habuAI/"
    f"{SOURCE_COMMIT}/data/processed/learning_10m_road.csv"
)
SOURCE_GIT_BLOB_SHA1 = "f443fd0ff997aeb4d5a68d81718c756b8fc7a067"
SOURCE_SIZE_BYTES = 30_318_569
MIGRATED_NIGHTS = [
    "2026-08-13",
    "2026-08-15",
    "2026-08-17",
    "2026-08-19",
    "2026-08-21",
    "2026-08-23",
    "2026-08-24",
    "2026-08-27",
]

FEATURE_GROUPS = {
    "time": ["sin_hour", "cos_hour"],
    "movement_exposure": [
        "mean_speed_mps",
        "elevation_m",
        "curvature_deg",
        "segment_prior_visits",
    ],
    "weather": [
        "rain_1h_mm",
        "rain_3h_mm",
        "rain_6h_mm",
        "rain_12h_mm",
        "rain_24h_mm",
        "rain_48h_mm",
        "temperature_c",
        "humidity_pct",
        "dew_point_c",
        "hours_since_rain",
    ],
    "terrain_road": [
        "slope_observed_deg",
        "local_relief_proxy_m",
        "road_class_code",
        "junction_distance_m",
        "stream_distance_m",
        "coast_distance_m",
        "forest_distance_m",
        "farmland_distance_m",
        "residential_distance_m",
    ],
}


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def download_source(url: str = SOURCE_URL) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "habuAI-private-chronological-eval/1"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def source_integrity(raw: bytes) -> dict:
    sha = git_blob_sha1(raw)
    return {
        "size_bytes": len(raw),
        "git_blob_sha1": sha,
        "size_match": len(raw) == SOURCE_SIZE_BYTES,
        "blob_match": sha == SOURCE_GIT_BLOB_SHA1,
    }


def prepare_frame(raw: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(raw), low_memory=False)
    required = {"entered_at", "habu_capture"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"legacy learning table missing required columns: {sorted(missing)}")
    entered = pd.to_datetime(df["entered_at"], utc=True, errors="coerce", format="mixed")
    if entered.isna().any():
        raise ValueError("legacy learning table has unparseable entered_at rows")
    jst = entered.dt.tz_convert("Asia/Tokyo")
    df = df.copy()
    df["entered_at_jst"] = jst
    df["operational_night"] = (jst - pd.Timedelta(hours=7)).dt.date.astype(str)
    df["habu_capture"] = pd.to_numeric(df["habu_capture"], errors="raise").astype(int)
    return df[df["operational_night"].isin(MIGRATED_NIGHTS)].copy()


def feature_columns(df: pd.DataFrame) -> tuple[list[str], dict[str, list[str]]]:
    groups = {name: [c for c in cols if c in df.columns] for name, cols in FEATURE_GROUPS.items()}
    biology = sorted(c for c in df.columns if c.startswith("bio_") and (c.endswith("_count") or c.endswith("_nearest_m")))
    groups["biology"] = biology
    ordered: list[str] = []
    for cols in groups.values():
        for col in cols:
            if col not in ordered:
                ordered.append(col)
    if not ordered:
        raise ValueError("no approved legacy feature columns found")
    return ordered, groups


def make_model() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value=0)),
        ("scale", StandardScaler()),
        ("model", LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            C=0.5,
            random_state=0,
        )),
    ])


def evaluate_fold(train: pd.DataFrame, test: pd.DataFrame, features: list[str]) -> dict:
    y_train = train["habu_capture"].astype(int)
    y_test = test["habu_capture"].astype(int)
    if y_train.nunique() < 2:
        return {"status": "INSUFFICIENT_TRAIN_CLASSES"}
    model = make_model()
    model.fit(train[features], y_train)
    prob = model.predict_proba(test[features])[:, 1]
    result = {
        "status": "OK",
        "rows": int(len(test)),
        "positives": int(y_test.sum()),
        "brier": float(brier_score_loss(y_test, prob)),
        "mean_pred_prob": float(np.mean(prob)),
    }
    if y_test.nunique() > 1:
        result["pr_auc"] = float(average_precision_score(y_test, prob))
    coef = model.named_steps["model"].coef_[0]
    result["coefficients"] = {
        feature: float(value) for feature, value in zip(features, coef)
    }
    return result


def run_walk_forward(df: pd.DataFrame, min_train_nights: int = 2) -> dict:
    features, groups = feature_columns(df)
    available_nights = [n for n in MIGRATED_NIGHTS if n in set(df["operational_night"])]
    folds = []
    ablation_rows = []

    for index, test_night in enumerate(available_nights):
        train_nights = available_nights[:index]
        if len(train_nights) < min_train_nights:
            continue
        train = df[df["operational_night"].isin(train_nights)].copy()
        test = df[df["operational_night"] == test_night].copy()
        full = evaluate_fold(train, test, features)
        fold = {
            "test_night": test_night,
            "train_nights": train_nights,
            "future_nights_used": [],
            **full,
        }
        folds.append(fold)

        for group_name, group_cols in groups.items():
            reduced = [c for c in features if c not in set(group_cols)]
            if not reduced:
                continue
            score = evaluate_fold(train, test, reduced)
            ablation_rows.append({
                "test_night": test_night,
                "omitted_group": group_name,
                "feature_count": len(reduced),
                **{k: v for k, v in score.items() if k != "coefficients"},
            })

    ok_folds = [f for f in folds if f["status"] == "OK"]
    all_no_future = all(
        all(train_night < fold["test_night"] for train_night in fold["train_nights"])
        and not fold["future_nights_used"]
        for fold in folds
    )

    briers = [f["brier"] for f in ok_folds]
    pr_aucs = [f["pr_auc"] for f in ok_folds if "pr_auc" in f]

    coefficient_abs: dict[str, list[float]] = {}
    for fold in ok_folds:
        for feature, value in fold.get("coefficients", {}).items():
            coefficient_abs.setdefault(feature, []).append(abs(value))
    top_coefficients = sorted(
        (
            {
                "feature": feature,
                "mean_abs_standardized_coefficient": float(np.mean(values)),
                "folds": len(values),
            }
            for feature, values in coefficient_abs.items()
        ),
        key=lambda row: row["mean_abs_standardized_coefficient"],
        reverse=True,
    )[:30]

    full_brier_by_night = {f["test_night"]: f.get("brier") for f in ok_folds}
    group_summary = []
    for group_name in groups:
        rows = [
            r for r in ablation_rows
            if r["omitted_group"] == group_name and r["status"] == "OK"
        ]
        deltas = []
        for row in rows:
            baseline = full_brier_by_night.get(row["test_night"])
            if baseline is not None and "brier" in row:
                deltas.append(float(row["brier"] - baseline))
        group_summary.append({
            "omitted_group": group_name,
            "folds": len(deltas),
            "mean_brier_delta_vs_full": float(np.mean(deltas)) if deltas else None,
            "interpretation": (
                "positive means worse without group; negative means better without group"
            ),
        })

    return {
        "evaluation_class": "LEGACY_10M_CHRONOLOGICAL_DIAGNOSTIC",
        "official_100m_10min_kpi": False,
        "future_leakage_guard": all_no_future,
        "minimum_training_nights": min_train_nights,
        "available_nights": available_nights,
        "feature_count": len(features),
        "feature_groups": groups,
        "folds": folds,
        "summary": {
            "completed_folds": len(ok_folds),
            "mean_brier": float(np.mean(briers)) if briers else None,
            "mean_pr_auc_on_mixed_label_folds": float(np.mean(pr_aucs)) if pr_aucs else None,
        },
        "group_ablation": group_summary,
        "top_standardized_coefficients": top_coefficients,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/legacy_chronological_walkforward.json"),
    )
    args = parser.parse_args()

    raw = download_source()
    integrity = source_integrity(raw)
    if not integrity["size_match"] or not integrity["blob_match"]:
        raise ValueError(f"legacy source integrity mismatch: {integrity}")

    df = prepare_frame(raw)
    report = run_walk_forward(df)
    report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["source"] = {
        "repository": "haji84/habuAI",
        "commit": SOURCE_COMMIT,
        "path": "data/processed/learning_10m_road.csv",
        "expected_git_blob_sha1": SOURCE_GIT_BLOB_SHA1,
        "expected_size_bytes": SOURCE_SIZE_BYTES,
        "integrity": integrity,
    }
    report["warning"] = (
        "This re-evaluates a legacy 10 m derived table with chronological night splits. "
        "It is diagnostic evidence only and does not replace the current 100 m ±10 minute KPI."
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
