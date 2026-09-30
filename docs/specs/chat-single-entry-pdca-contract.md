# Chat Single-Entry PDCA Contract v1.0

Status: Normative operational contract

## Separation

Prediction issuance is separate from PDCA.

The prediction surface creates and freezes ORIGINAL P0/P1/P2... versions.
The PDCA surface never rewrites or retroactively recreates ORIGINAL predictions.

## Owner command

An instruction equivalent to:

- "今日のPDCA全部回して"
- "<date>のPDCA全部回して"
- "PDCA開始"

is sufficient to start the full post-exploration workflow for the resolved operational night.

The owner does not need to separately instruct model-evaluation, feature-analysis, or development surfaces.

## Full workflow

The PDCA coordinator performs, in order:

1. Resolve operational night with the 07:00 JST boundary.
2. Locate frozen ORIGINAL P0/P1/P2... predictions.
3. Verify prediction integrity and cutoff times.
4. Locate or ingest available exploration evidence.
5. Verify/reconstruct byte-exact archived GPX where applicable.
6. Load capture events and expand event_count to individual captures.
7. Audit GPX points and exclude supported GPS anomalies.
8. Generate observed 100m x 10-minute exposure units.
9. Generate Negative observations only from evidenced search/passage.
10. Score P0 independently.
11. Score each P1+ independently using only outcomes after its cutoff_time.
12. Run error decomposition.
13. Run observed-exposure feature analysis.
14. Run space/time diagnostic ablation.
15. Run historical ORIGINAL P0 chronological evaluation.
16. Evaluate available REPLAY/candidate evidence without modifying ORIGINAL.
17. Produce an Act decision.
18. Persist machine-readable and human-readable reports.
19. When code/model improvement is justified, prepare the bounded change through a branch/PR with tests and evidence. Do not rewrite historical prediction records.

## Truthfulness rule

A single command means all stages are attempted automatically. It does not authorize fabrication.

If required evidence is unavailable:
- report the affected stage as BLOCKED or PARTIAL;
- identify the concrete missing dependency;
- continue independent stages when safe;
- never manufacture GPX, captures, weather, predictions, model results, or evaluation metrics.

## Prediction updates during exploration

P1/P2/P3... are valid and expected when new live information becomes available.
Each version is immutable after issuance. Creating a new version is allowed; editing an old version is not.

A prediction can only receive credit for outcomes after its own cutoff_time.

## ORIGINAL and REPLAY

ORIGINAL is the operational record.
REPLAY is retrospective model evaluation.

REPLAY can inform future model changes but can never replace, edit, or improve the recorded ORIGINAL score.

## Official reporting separation

Always keep separate:
- P0 pre-exploration performance;
- P1+ real-time adaptive performance;
- REPLAY/candidate performance;
- diagnostic analyses that are not official KPI scores.

The formal 100m ±10-minute evaluation remains identifiable as its own metric and must not be blended with broader spatial or temporal diagnostics.
