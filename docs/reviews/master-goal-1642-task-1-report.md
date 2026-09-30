# Task 1 implementation report

Status: bounded Task 1 implemented locally; independent review required. No remote writes.
Commit: `4c36075` (`Fix operational scoring integrity and prospective prediction freezing`). Base snapshot was local `c875a7c`; canonical remote baseline remains `c1acabe1e2e6f6959c0a949bd18c37f174480c5a`.

## Changes

Only allowed paths committed: `src/pdca_pipeline.py`, `scripts/freeze_prediction.py`, `tests/test_pdca_e2e.py`, `tests/test_recovered_prediction.py`, new `tests/test_master_scoring.py`.

- Integrity aggregation cannot downgrade FAIL when a later payload lacks its hash. Pipeline checks prediction class/night/version against actual storage scope before reading evidence. Loader no longer fabricates a hashed version field. Missing hashes remain PARTIAL and cannot produce official eligibility.
- Formal matching always uses 100m and ±10min, regardless of payload overrides. Targets at/before cutoff and outside the target operational night are excluded. Deterministic sorted bipartite augmenting paths find maximum-cardinality one-to-one matches, including the greedy-counterexample regression.
- `score_prediction` keeps its original positional interface and adds optional `exposure`. Only matches and unmatched targets in matching observed-negative grid/time units enter precision; other targets are UNKNOWN. Reports expose unknown, observed-negative, and excluded-nonprospective counts.
- Cell labels use the same floor(UTM52N/100) and 10-minute JST bucket for evidence and captures; sample ordering no longer changes labels. Capture parser accepts explicit capture/捕獲 only; rejects invalid counts, nonfinite/out-of-range coordinates and contradictory operational dates. Invalid target coordinates do not enter metrics.
- Historical P0 diagnostics require valid hashes and matching payload/path contracts. Current/future nights are excluded when called from the pipeline. `walk_forward` compatibility data key remains, but entries are HISTORICAL_DIAGNOSTIC and the stage is `model_evaluation: NOT_VALIDATED`. Candidate validation is NOT_VALIDATED, and overall status cannot PASS with NOT_VALIDATED stages.
- All operational scores explicitly remain `strict_official_score_eligible: false`, `provenance_status: NOT_VALIDATED`. No claim of independently verified issuance lineage or observation completeness is fabricated.
- Expected capture count/range accuracy is NOT_VALIDATED absent complete observation-window proof. Existing verified error/range-result keys remain present with null values. Existing arithmetic is available under `diagnostic_capture_count_absolute_error` and `diagnostic_actual_within_expected_range`.
- Freezing validates canonical date path, input class/night/version, contiguous version ordering and prospective target times. REPLAY, recovered/pre-frozen inputs and retrospective relabeling are rejected. Issuance timestamp is actual current time, with optional injected timezone-aware `now` for deterministic tests. Supplied cutoff/created_at must equal actual issuance time exactly; normal CLI inputs should omit those timestamps. There is no arbitrary lag allowance. Newly frozen records explicitly lack validation until Champion lineage integration.

## Verification

Read AGENTS/spec and the TDD skill plus writing-good-tests reference. Added adversarial tests first; initial 13 tests demonstrated 18 assertion failures and the expected missing optional-exposure API error. Subsequent focused red/green cycles covered count/provenance, freeze metadata/time, version gaps and invalid coordinates/targets. Existing overly permissive E2E PASS assertion was replaced with PARTIAL plus explicit NOT_VALIDATED/official-ineligible assertions; the P1 target exactly at cutoff now correctly matches zero.

Final command: `python -m unittest discover -s tests`: **74 tests passed** (53 baseline, 21 new test methods). Affected PDCA tests and new tests were run during red/green development. No baseline failures remain. Scoped `git diff --check` passed. Global diff-check showed CRLF warnings in the parent's gap-matrix CSV, outside Task1 and not included in this commit.

Historical dry-run executed in a temporary copy of data/predictions/reports: September 28 result PARTIAL / RECOVERED_ORIGINAL; 22,990 GPX points; 6 captures; 947 exposure units; count status NOT_VALIDATED; official eligibility false. SHA-256 comparison of all **45 original raw/prediction/report files** before and after confirmed byte equality. No historical raw, predictions or reports were modified.

## Remaining limits / review concerns

- Full independently validated model/source/issuance provenance is Task4. Current scores intentionally cannot become official even if callers insert self-declared lineage fields.
- Existing exposure construction still treats parsed GPX presence as observed passage; search role, quality, gap completeness and Gold eligibility need the later evidence-audit slice. Thus operational metrics remain diagnostics, not verified scientific evidence.
- Complete capture ascertainment/window coverage is unavailable; count errors are diagnostics only. No complete-observation bypass flag was introduced.
- Exact issuance timestamps intentionally reject supplied stale cutoff/created_at. To issue normally omit them; trusted upstream integrations needing an earlier information cutoff require explicit provenance in Task4 rather than a permissive lag heuristic.
- Existing output writer overwrite/stale-exposure behavior and run/checkpoint concurrency remain Task2/5. Historical malformed JSON can still propagate an exception instead of returning a structured rejection. No stale-success/recovery redesign was attempted in this bounded slice.
- Matching uses recursive augmenting paths; appropriate for existing bounded target sets, but extremely large unbounded target lists may require an iterative implementation or an input budget in later contracts.
- Local verification is not remote Actions evidence or live workflow validation. Parent must review and materialize changes onto the complete canonical remote tree.

## Independent review fix round 1

Read `/workspace/scratch/fb45a4f31791/task-1-review.md` and addressed both Important findings (no Critical findings). This correction supersedes the original report's exact-equality cutoff limitation: forecast information cutoff and actual issuance are separate.

- A supplied `cutoff_time <= issued_at` is now preserved unchanged. The issuer's current/injected clock still sets `frozen_at`, and default `created_at`; no caller cutoff establishes historical issuance. Future cutoffs, completed operational nights, elapsed targets, replay/recovered relabeling and missing full provenance remain rejected or official-ineligible as appropriate. No arbitrary lag allowance is introduced.
- Prediction load-stage labels come from known storage-directory metadata, avoiding use of unvalidated payload versions. Contract validation now explicitly rejects missing, non-string and noncanonical versions (including `P00`) through structured integrity FAIL and persisted failure report before evidence/scoring.
- Added regressions for one-second and previous-day information cutoffs with future targets, trusted freeze timestamp retention and continued provenance NOT_VALIDATED; an elapsed target cannot become prospective through an earlier cutoff. Added valid-hash missing/integer/list/P00 version regression checking returned/persisted FAIL and immutable prediction bytes. Removed the prior test expectation that a one-second-earlier cutoff must fail because that expectation contradicted the normative architecture.

TDD verification: `python -m unittest discover -s tests -p test_master_scoring.py` before fixes showed the expected earlier-cutoff rejection and missing/wrong-type-version crashes; adding the P00 case additionally showed BLOCKED instead of FAIL. After fixes, `python -m unittest discover -s tests` passed **77 tests**. Scoped `git diff --check` passed. Only the three allowed files above changed; no historical data, documentation, dependencies or remote state changed. All other provenance, completeness, evidence-quality and later-slice limitations remain as described above. Local tests are not remote Actions/live-workflow evidence.

Fix-round commit: `317c8341c508503a866c803c65b2a0344dcfeb81` (`Separate forecast cutoff from issuance and reject malformed versions`).
