# HABU candidate-feature ablation, research only (2026-11-15)

**Scope:** evaluate three separate feature hypotheses using only previously reviewed November reference-PDCA evidence in a private executor. No source files, detailed capture locations, individual event times, original GPX or private keys are committed to this public repository.

The code at `tools/habu_pdca_research/feature_candidates.py` is a pure, synthetic-testable evaluator. It does not ingest owner data, train G0, issue P0, create Negative labels or promote Champion.

## 1. Intended search time (forecast-time input only)

- Frozen prior research diagnostic through 2026-11-09: 0.477747 owner captures per **elapsed session hour proxy** (16 nights, 38 captures), not measured active search.
- Chronological research comparison on the next three nights with available planned hours: fixed 5-hour baseline MAE **1.1296** vs planned-hours exposure-proxy MAE **1.0500**. Average Poisson log score -1.6474 vs -1.6028. Only **one of the three** original references was issued before the actual search began. Other two were issued during search before first capture.
- **Not a validated improvement.** The entire difference arises from one night with a plan other than 5 hours. Never substitute *actual* elapsed hours learned after the outcome as a forecast feature.

## 2. Prioritized forecast region

- Six recovered reference nights offer 10 captured records with an identifiable settlement label and 3 generic/unassigned capture records. Conditional settlement-name overlap: A=4, B=1, C=4. A/C membership may overlap and is not exposure-adjusted.
- No verified area-specific search minutes, road-grid denominator, forecast-time region polygons, or complete noncaptures were available. Therefore Area Top10 Recall is **null**. Never label unvisited roads or regions as zero.

## 3. Local field versus Koniya station temperature

- Owner notes contain six field-temperature records on three nights. Koniya JMA historical hourly observations are reference station observations, not route microclimate and not historical issued weather forecast snapshots.
- A retrospective night-ordered calibration simulation on the **four** later readings from **two** nights reduced field-temperature reconstruction MAE from **1.95 °C** (unadjusted station) to **0.6775 °C** (prior-night mean residual only). Source availability at the historic prediction cutoff is not independently proven; field-device uncertainty is unknown.
- This is **not a demonstration of better Habu activity prediction**. The candidate must be validated prospectively with device ID, location/height metadata, previous-night source readiness, and separately frozen weather forecast receipts.
- On 4 of 15 capture records, the locally recorded surface was WET/SOAKED despite 0 mm at the station's most recent completed hourly rainfall support. This is not evidence of a higher risk without wet/dry route effort denominators.

## Next bounded gates

1. Capture **forecast-time** planned search duration, allowed road set, region A/B/C scores and input hash in a real immutable P0 before exploration; updates create fresh P1 etc.
2. Confirm real active search per traversed segment, GPS gaps, session starts/stops, and completeness of owner capture outcomes. Unknown exposure remains UNKNOWN.
3. Record field temperature calibration metadata and separate true local readings, historical JMA station observations, and the *previously available* forecast source at issuance.
4. Conduct fixed chronological/held-out comparisons of count MAE/log score, area effort-conditioned ranking and actual 100m ±10min predictions, with uncertainty and a fixed baseline. Changes to official Champion require separate evidence and owner approval.

**Source custody:** Detailed November 2026 calculations and originals stay in owner-only Drive. Public GitHub carries only generic code, synthetic tests and the above aggregate results. This PR does not change production prediction authority, public dashboard release data or active weather collector.
