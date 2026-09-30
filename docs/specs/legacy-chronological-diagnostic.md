# Legacy 10 m Chronological Diagnostic Policy

Status: Auxiliary diagnostic evidence
Official KPI: No

## Purpose

The historical public Habu AI pipeline produced a derived 10 m road-learning table. This repository may use that fixed legacy table to diagnose model behavior, but it must not be presented as the current official 100 m ±10 minute prediction score.

## Source lock

The diagnostic source is fixed to:
- repository: haji84/habuAI
- commit: 4877c30d518bec4022041d4868e0a1c239e4b28c
- path: data/processed/learning_10m_road.csv
- Git blob SHA-1: f443fd0ff997aeb4d5a68d81718c756b8fc7a067
- byte size: 30318569

Execution must fail if the source size or Git blob identity changes.

## Chronological split

Only the eight nights represented by the locked legacy learning table are used:
2026-08-13, 08-15, 08-17, 08-19, 08-21, 08-23, 08-24, 08-27.

For each test night:
- training nights must be strictly earlier;
- future nights are prohibited;
- the report records train_nights and an empty future_nights_used list;
- the future_leakage_guard must be true.

The first two nights are warm-up training history. This yields six evaluated chronological folds.

## Interpretation limits

Brier score, PR-AUC, coefficients, and group ablation are diagnostic only.

A group whose omission improves legacy Brier is a candidate for re-specification or regularization, not proof that the underlying ecological factor is irrelevant.

A group whose omission worsens legacy Brier is a candidate to retain and retest, not proof of causality.

Movement/exposure variables may describe search or observation process as well as animal behavior. Their coefficients must not be interpreted as biological causal effects.

## PDCA integration

The single-entry PDCA pipeline may read this report and generate HYPOTHESIS_ONLY candidates.

No legacy diagnostic may:
- alter ORIGINAL predictions;
- replace current 100 m ±10 minute scoring;
- automatically promote a feature or model;
- bypass REPLAY/current-framework validation.
