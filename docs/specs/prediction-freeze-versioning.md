# Habu AI Prediction Freeze and Versioning Specification v1.0

Status: Normative
Timezone: Asia/Tokyo
Operational-night boundary: 07:00

## 1. Purpose

This specification preserves what Habu AI actually predicted at each point in an exploration night, prevents hindsight leakage, and separates pre-departure forecasting skill from real-time adaptation skill.

A freeze applies to one prediction version, not to the entire exploration night. New prediction versions may be created as new information becomes legitimately available, but an already frozen version must never be overwritten or rewritten.

## 2. Prediction classes

### P0: pre-exploration baseline

P0 is the official prediction created before exploration begins.

P0 measures pure pre-exploration predictive performance. No observation, capture, sighting, GPX segment, road condition, weather observation, or other information learned after P0 cutoff_time may enter P0.

### P1, P2, P3...: real-time update predictions

P1 and later versions are sequential predictions created during exploration.

Each version may use only information that was available at or before its own cutoff_time. This may include legitimate observations accumulated during the current exploration session, such as traversed roads, elapsed time, observed weather or road surface, biological reactions, captures, and other approved live inputs.

Creating Pn never modifies P0...P(n-1).

## 3. Immutable freeze rule

Every prediction version is frozen immediately when issued.

After freeze:
- prediction payload is immutable;
- cutoff_time is immutable;
- model/version identifiers are immutable;
- input-data references are immutable;
- prediction scores, rankings, routes, expected counts, and explanations are immutable;
- correction by replacement is prohibited.

If a mistake or new input requires another prediction, create the next version. Never edit history.

Each frozen payload must have a SHA-256 digest so later evaluation can prove exactly what was predicted.

## 4. Required metadata

Every prediction version must record at least:

- prediction_id
- operational_night
- prediction_version: P0, P1, P2...
- prediction_class: ORIGINAL
- created_at
- cutoff_time
- timezone
- model_name
- model_version
- model/spec hash where available
- input dataset snapshot/hash where available
- feature snapshot/reference
- forecast/weather input snapshot/reference where applicable
- live observations included, for P1+
- excluded/future information declaration
- 1 km Area prediction/ranking
- 500 m, 250 m, and 100 m Road Zone predictions when produced
- time-window prediction, including the official 100 m ±10 minute target where produced
- expected capture count when produced
- size-class prediction when produced
- candidate routes A/B/C when produced
- route assumptions and constraints
- prediction rationale/major contributing features when produced
- payload_sha256
- frozen_at

Missing optional outputs must be represented as unknown/not-produced, not fabricated.

## 5. cutoff_time and evaluation boundary

cutoff_time is the hard information boundary for a prediction version.

A prediction version may only be credited for outcomes occurring after its cutoff_time.

Example:
- P2 cutoff_time = 23:10
- a capture at 22:50 cannot count as a P2 success;
- outcomes after 23:10 may be evaluated against P2 according to the applicable KPI.

Information after cutoff_time must not be used to reconstruct or improve that frozen prediction.

## 6. ORIGINAL versus REPLAY

### ORIGINAL

ORIGINAL is a prediction actually issued during the real exploration workflow.

P0/P1/P2... ORIGINAL versions constitute the operational record and official real-world score history.

### REPLAY

REPLAY is a later re-prediction of a historical night, typically using an improved model.

REPLAY must:
- be stored separately from ORIGINAL;
- never overwrite or replace ORIGINAL;
- preserve strict historical information cutoffs;
- identify the model/version used for replay;
- identify the historical cutoff being replayed;
- be labeled REPLAY in all evaluation outputs.

REPLAY performance is model-comparison evidence, not the original operational score.

## 7. PDCA evaluation

PDCA must report at least two distinct performance families.

### A. Pre-exploration performance

Evaluate P0 separately.

This answers: how well could Habu AI predict the night before exploration-derived information was available?

### B. Real-time adaptive performance

Evaluate P1/P2/P3... as sequential forecasts using their individual cutoff_time boundaries.

This answers: how much did legitimate live observations improve predictions for the remaining future portion of the night?

P0 and P1+ scores must not be blended into a single metric without also retaining and reporting the separated results.

## 8. Negative observations

This specification does not change the repository Negative rule.

Unknown is not Negative. A Negative requires evidence that the matching road/time unit was actually searched or traversed. Prediction versions must not infer Negative labels merely from absence of a capture record.

## 9. Leakage prevention

For every ORIGINAL and REPLAY evaluation:
- features and training data must have existed before the applicable prediction cutoff;
- future captures, sightings, GPX trajectory, weather observations, labels, and derived future-only information are prohibited;
- walk-forward evaluation must preserve temporal ordering;
- any leakage finding invalidates the affected score until corrected and rerun.

## 10. Storage model

Recommended canonical structure:

predictions/
  original/
    <operational_night>/
      P0/
      P1/
      P2/
      ...
  replay/
    <operational_night>/
      <model_version>/
        P0/
        P1/
        ...

Each prediction-version directory should contain the immutable prediction payload and its integrity metadata/hash.

Actual observations and evaluation outputs remain separate from frozen prediction payloads so label reveal cannot mutate the prediction record.

## 11. Version numbering

- P0 exists once per operational night as the pre-exploration baseline.
- Subsequent live predictions increment monotonically: P1, P2, P3...
- Deleted/reused version numbers are prohibited.
- If a prediction generation fails before issuance/freeze, record the failure separately rather than creating a fake successful prediction version.

## 12. Governance

This specification is normative for Habu AI prediction storage and PDCA scoring.

Any future change that alters the meaning of P0, cutoff_time, ORIGINAL, REPLAY, or historical scoring must be versioned explicitly. Historical scores must not be silently recalculated under a changed definition.

The central principle is simple: preserve every forecast exactly as it existed when it could still be wrong.
