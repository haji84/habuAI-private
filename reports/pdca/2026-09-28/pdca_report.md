# Habu AI PDCA 2026-09-28

Overall: PARTIAL

## Stages
- load_frozen_predictions: PARTIAL Using retrospectively recovered prediction history; strict official score ineligible
- verify_prediction_integrity: PASS
- load_actual_evidence: PASS 22990 GPX points; 6 captures
- build_exposure: PASS 947 observed 100m x 10min units
- score_p0: PARTIAL P0 has no recoverable 100m ±10min targets; count forecast only
- score_realtime: PARTIAL No P1+ predictions
- error_analysis: PASS
- feature_analysis: PASS Observed exposure by time-of-night
- diagnostic_ablation: PASS Space/time dimensions evaluated separately
- walk_forward: PARTIAL No scorable historical P0
- candidate_validation: PASS No replay/candidate requested; ORIGINAL history preserved
- act_decision: PASS NEED_MORE_DATA

## P0
- formal 100m ±10min: NOT_PRODUCED
- targets: 0
- captures after cutoff: 6
- matches: 0
- precision: None
- recall: None
- expected capture count: 4.0
- count absolute error: 2.0
- actual within expected range: True
