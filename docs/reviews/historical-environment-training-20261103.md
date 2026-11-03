# Historical environment backfill and training assessment, 2026-11-03

Status: **PARTIAL_BLOCKED**. Existing PR [#136](https://github.com/haji84/habuAI-private/pull/136), owner handoff `docs/handoff/CODEX_HISTORICAL_ENV_TRAINING_20261103.md`, Master Goal [#1642](https://github.com/haji84/AI-/issues/1642), repository Issues [#64](https://github.com/haji84/habuAI-private/issues/64)/[#86](https://github.com/haji84/habuAI-private/issues/86).

The following are actual development/source-processing results. Real fitted training rows are **0**; the eligible count remains **unverified**, rather than a measured zero. No model, independent confirmation score, improvement, production authorization or genuine field P0→PDCA success is asserted.

## Audited repository and access

- PR #136 source: `c7276d2044f9d64ee26586940a106922820aaf26`. Audited main: `1bc6f357fc2e3e51c056b4669c34e645a454edf1`; their original shared ancestor was `8aec1dc40bad6c2b79469088a8e974a339547fb6`.
- Latest main was merged into the **local feature branch**, preserving its mobile/GPS changes. No change was made to remote main. Reuse PR #136; do not co-merge duplicate #92 or publish the raw-source payload from #147.
- The repository is public. New raw sources, private candidate rows, GPS/log originals and full private derivatives are kept outside all Git worktrees. The owner's existing explicit approval covers public code and non-sensitive verification results; this PR publication uses that restricted scope. Main integration requires the separately requested approval.
- Current exposed connectors could not read the private Library `/ハブAI/{Raw,Derived,Evidence,PDCA}`. A private reference ledger could be read, but its Library file references did not expose the required original bytes. Bounded unsuccessful searches do not prove that files do not exist.
- The corrected September-51 workbook was available inside an existing encoded source capsule and inspected in RAM. Decoded ZIP SHA: `ee803478c0a1ec574591fc219fa585afad101539b5ddfaebae966e41c5b60aee`; workbook SHA: `ead12df59799d607a93814d91e5ed719bbc955cda3a8cf2410f22d42214d7054`. Neither was modified or newly published.
- Existing event CSV: **3,853 rows**, calendar dates through October 21 / operational nights through October 20. **3,833 exact JST timestamps, 20 quarantined ambiguous timestamps**, no removed/auto-merged rows. All original field strings and row order were retained. The 101 old 07:00-night discrepancies are in a separate 314-row historical capture display table; the all-period CSV has zero derived-night disagreements.
- The two named November 3 private CSVs and October 22 onward/November 1 original event-GPX evidence were not accessible. The reported **4,094 rows / zero qualified units** were not reverified. No missing November 1 species correction or October 29 captured/escaped identity was invented from aggregate descriptions.

## Weather and rainfall actually processed

JMA Koniya AMeDAS **88901**, historical archive block **0980**, is reference-station support. Target **2025-01-01–2026-11-01: 670/670 days**. Retained context covers December 29, 2024–November 2, 2026: **674 days / 16,176 hourly rows**.

| Field | Known | Unknown |
| --- | ---: | ---: |
| Precipitation | 16,165 | 11 |
| Temperature | 16,003 | 173 |
| Relative humidity | 16,032 | 144 |
| Wind speed | 16,170 | 6 |
| Published 16-point wind direction | 16,170 | 6 |
| Derived sector-centre bearing | 16,107 | 69 |

Unsupported quality markers remain null. Calm does not become a measured zero-degree bearing. Rain is the preceding-hour accumulation; wind is its documented averaging support, rather than a ten-minute road observation. Station sunshine was not imported as measured solar radiation.

24/48/72h rainfall requires complete contiguous prior-hour intervals; gaps/unknowns never become dry weather. Fixed exploratory decay horizons 12/24/48h are labelled **unvalidated rainfall-memory hypotheses**, with complete 72h support required. They are neither measured surface wetness nor independently preregistered ecological effects. Candidate joins use only the last completed reference hour, without interpolation to ten-minute road values.

Sources: [JMA hourly archive](https://www.data.jma.go.jp/stats/etrn/view/hourly_a1.php?prec_no=88&block_no=0980&year=2026&month=11&day=1&view=), [station metadata](https://www.data.jma.go.jp/stats/data/mdrr/chiten/meta/amdmaster.index4), [quality symbols](https://www.data.jma.go.jp/risk/obsdl/top/help4.html), [wind definitions](https://www.jma.go.jp/jma/kishou/know/faq/faq2.html), [use terms](https://www.jma.go.jp/jma/kishou/info/coment.html). Original URL, station, period, bytes/SHA, raw cell and actual retrieval are retained in private receipts.

## Tide sources remain distinct

- **JMA O9, 奄美（名瀬小湊）**, is distinct from Koniya. Finalized January 2025–September 2026: 21 months, 87,406 original bytes, **15,312 hourly slots / 14,576 numeric / 736 unknown**. October and November use separately typed provisional observations. Across the requested 670 days, independently counted **16,080 unique hourly slots / 15,344 numeric / 736 unknown**. November 2 context and future monthly blank slots are excluded from that target count.
- **JCG 4632 Koniya**, November 1: 24 astronomical predictions retrieved retrospectively, explicitly **PREDICTED**, not tide observations or proof of an old as-issued forecast. JCG terms verification remains unresolved; its output is `TERMS_NOT_VERIFIED`.
- Keep local vertical datums separate. No cross-station substitution, subtraction, datum conversion or ecological causal inference is performed. Finalized 136-column records preserve the unevaluated extrema tail; the 80-column provisional parser cannot silently accept them.

Sources: [JMA finalized archive](https://www.data.jma.go.jp/kaiyou/db/tide/genbo/index.php), [136-column format](https://www.data.jma.go.jp/kaiyou/db/tide/genbo/format.html), [provisional format](https://www.data.jma.go.jp/kaiyou/db/tide/sokuho/format.html), [JCG Koniya prediction](https://www1.kaiho.mlit.go.jp/TIDE/pred2/cgi-bin/TidePredCgi.cgi?area=4632&back=6&year=2026&month=11&day=1).

## Lunar age and actual terrain complement

NAOJ's numeric calculation table was acquired in **23 monthly requests / 157,073 original bytes**, covering **670 exact 12:00 JST points**, with zero unknown ages in those returned tables. The location is the official public Setouchi municipal reference, unrelated to private capture locations. Output is `ASTRONOMICAL_CALCULATION`, never a measured value. The candidate join retains the last noon sample within strictly less than 24h: **3,833 joined / 20 unknown timestamps**. It does not interpolate age to the event, infer illumination fraction, or infer measured road moonlight. Date, location, timezone, heading and visible numeric table are bound to the request. Hidden/inert HTML cannot supply source identity. [NAOJ calculator](https://eco.mtk.nao.ac.jp/cgi-bin/koyomi/koyomix.cgi), [definition](https://www.nao.ac.jp/faq/a0204.html), [terms](https://eco.mtk.nao.ac.jp/koyomi/site/).

For terrain, existing public OSM road archive, inverse UTM, GSI PNG decoding and `road_dem_join` are reused. **221 actual GSI tiles / 17,014,093 bytes** support 91,258 requested raster nodes; **86,366 sampled / 4,892 source nodata**. At the existing **16,990 auxiliary road cells**, **15,020 have supported elevation/slope/aspect/TPI (88.4%) / 1,970 remain UNKNOWN**. This does not establish coverage of all official/drivable roads or map private event GPX onto them.

Conversion explicitly uses nearest GSI pixels onto a 50m EPSG:32652 target grid; slope uses a 100m central-difference baseline and TPI uses eight neighbours at 50m spacing. Unrequested areas and source nodata remain distinct unknown support. GSI source height is retained without vertical datum conversion; source measurement epoch is not established. Road orientation is available; terrain wind shelter and actual road wind/wetness remain unvalidated. [GSI tile specification](https://maps.gsi.go.jp/development/demtile.html), [layer/terms information](https://maps.gsi.go.jp/development/ichiran.html), [independent PROJ coordinate control](https://proj.org/en/stable/operations/projections/utm.html).

The converter's initial completion-rescan defect was reproduced with four mutation controls and repaired before acceptance. A fresh run reused cached tiles without more requests. Its final current-native-code report is **81,373 bytes**, SHA `fd01c1c05d3f5853dda94df889826995d779fa405f6c36c5cd2a69e0a23a9d90`; ASCII SHA `c7c88088404230f15a6bb16e9a6faaebeddbe620e194b9aac570f5024fa80e7c`; node-map SHA `9da83ae609df5c3307b09a3218fcfc7301887d8d9d59e293995f1088965731c9`; final join SHA `3c60f5cf09aa1d3130db792dc784e9f4a99de4275f8b73b8b353177d2aa08d4c`. An independent agent verified all raw/receipt/artifact/readiness and current code bindings. Status remains **SOURCE_JOIN_PARTIAL / TRAIN NOT_ASSESSED**.

## Retained independently verified milestones

All artifacts below remain private, outside Git. SHA values identify exact files; their payloads are not included in this public-safe assessment.

| Milestone | Actual evidence |
| --- | --- |
| v2 weather/tide execution | 677 source/payload/readiness bundles, all recomputed by an independent agent; report 523,679 bytes, SHA `31e0fc4e1aef3e7e19da76607dbf91a5db42c494f57704a6e212b48c983d9897` |
| v2 independent audit | SHA `3406a42bc68c23da95c2b219cc8526acb74091eef57df6e7b69dbcda9b2b1076`; 3,853 originals/order and 3,833 lagged-hour bindings, 11,499 rainfall sums and 11,253 proxy scalars independently checked |
| v3 finalized-tide extension | 698 sources; report 541,487 bytes, SHA `f3e13974d13a787d449496022b3affcd4629a3c46b381ab70dfd8970d507e6d0`; code-bundle SHA `1832566a80e680c053754c7e72f7282a57e8dfb170478fd26a0dc27873eba806` |
| v3 independent audit | SHA `f62245425072d89870d0ae4ca6536fe08458d5865ec693b690af212aee857a97`; all 698 bindings, new 21 payloads from original bodies, target O9 coverage and retained v2 bytes verified |
| Final v8, Git-native code | **721 sources**, report 557,640 bytes, SHA `8f88012fb101bee6d1bab98b3056d4a92364a1c68811bd238425b504b333ec26`; four-file runtime code SHA `c1384bc475b7d2e18c7f27cc87552eaf3462a84de61d81771628999b07b7c5ab` |
| Final private candidate | 3,853 original rows, 19,443,964 derived bytes; SHA `045c7dd7b58c496b36261106a1d503ddfffc49124a7a535f7914e3de721ba768`; actual usable time `2026-11-03T09:51:16.405494+00:00` |
| Final v8 independent audit | 2,611 bytes, SHA `da59bdc47a98cbd1533cb5e9744de8263a3a5fa45b3dbc22c47429420a4a3780`; all 721 bindings, 670 noon calculations and 3,833 candidate selections checked, old generations unchanged |

The first prototype's pre-write readiness was rejected and superseded. Current derived payloads have no standalone `usable_at`: a separate post-write/readback receipt binds their exact SHA and actual materialization/audit times. Failed relative-path and unsupported acquisition-metadata attempts are retained in local logs. Native filesystem sub-microsecond timestamp representation is documented in the independent audit; clocks are not backdated. Code bytes for retained executions are separately preserved by the report's exact hashes.

Final guards also reject ordinary same-size changes to normalized payloads, readiness receipts, joined candidates and their private source before completion. Invalid/non-object/duplicate/deep receipt JSON returns non-sensitive `BLOCKED` JSON and exit 2, without private paths or source text. Code-only CRLF/LF differences were aligned to Git-native bytes; prior runtime code archives remain exact, and raw input bytes are unchanged.

## Software verification and development Freeze

- **92** historical-source/CLI tests and **31** terrain/existing DEM-probe tests independently passed. The reviews cover source normalization, malformed/hidden HTML, unknowns, source/type/date identity, strict as-of support, physical readiness, mutation checks and actual private joins. They do not certify labels or ecological predictive performance.
- New cycle: `protocols/development/cycles/20261103-historical-environment-source-117-01.json`; **117 code paths / 118 inputs including policy**. Actual CLI `CONTRACT_VALIDATED`; science `NOT_VALIDATED`, fit/production authority false. All 117 working bytes match Git index native bytes and the manifest. Old **64 cycles and policy** remain byte/OID identical.
- Cursor file SHA: `84ed68a8ac7583caa33e648be83bfc81896154de5ed577c50944c93ec33659d5`; canonical cycle SHA: `0e7dd046fd53ced5bde1af9f39b24af2494a23141f93c1d7758c903eb50e212a`; conservative code closure SHA: `f52fcf38820dd2b68d043ef36f5cf82bb656c687894c117ad5655efa7ee4d0b7`. Cursor-file and canonical hashes serve different purposes.
- An isolated local validation environment contains the pinned analysis requirements. The complete Windows run was stopped after platform limitations were confirmed, and is **not a full-suite PASS**. Independently replaying 53 selected tests at both current source and exact main `1bc6f35` gave identical **31 PASS / 22 ERROR**: 18 errors require genuine POSIX `fcntl`, four require unavailable Bash. No lock facade, skip or weakened assertion was introduced. Logs and the baseline comparison remain private. New-head Ubuntu CI is the required full-suite check; fresh-main CI requires later authorized integration.
- Existing `data-intake-tests` now explicitly checks out `github.event.pull_request.head.sha` (or `github.sha` on push) and asserts that the actual Git HEAD equals it before tests. This provides exact source-head evidence instead of treating a synthetic merge checkout as the source SHA. Workflow permissions remain `contents: read` and no deployment is enabled.
- Read-only Cloudflare API preflight found the existing `hub-natural-private` Git integration points to `haji84/habuAI-private`, production branch `main`, with preview deployment setting **`none`** and production auto-deployment enabled. The GitHub dashboard deployment job remains disabled. No Cloudflare settings, permissions or deployments were changed. Recheck these settings before a later authorized release; main integration may trigger the existing production integration and requires separate approval.

Executable entrypoints: `scripts/backfill_historical_environment.py --help`, `scripts/build_gsi_road_dem.py --help`, `scripts/check_codex_cycle.py`, `scripts/check_codex_parallel_handoff.py`. Use authorized **absolute paths outside Git** for raw evidence and output, pin the candidate CSV SHA, and use fresh append-only generations. The existing selector/fitter still requires an explicit qualified corpus, heldout night, cutoff and feature contract. Machine-readable non-sensitive results: `reports/historical-environment-20261103-summary.json`.

## Training, evaluation and remaining gates

The CLI reuses the existing `training_corpus.select_training_rows` and `train_spacetime_candidate.fit_candidate`. Its real `--run-fit` invocation returned **BLOCKED** (`MISSING_AUDITED_TRAIN_ONLY_CORPUS_AND_SOURCE_PROOFS`), selector/fitter not run, fitted rows **0**, eligible count **unverified**, model SHA **null**. Synthetic eligible fixtures exercise the real selector/fitter only as software controls; they are not field training evidence.

The recovered candidate CSV lacks source-qualified observation/label, active-search role, scoped complete capture outcomes, eligible GPX segment, individual capture IDs, source/outcome selectors, label/audit readiness and feature-source contracts. Weather enrichment does not supply these proofs. All rows remain `RESEARCH_EXPOSED` / `NOT_ASSESSED`; GPS passage generates **zero** qualified negatives.

New sources were actually retrieved November 3. They may support later qualified development fits, but cannot be inputs available before the historical nights. Historical strict walk-forward is therefore blocked for these new features. The existing M0–M3 definitions, ORIGINAL predictions and confirmation gates are preserved.

**1km Top10 Recall, formal 100m±10min, Brier/calibration, Champion comparison and model improvement: NOT_VALIDATED / NOT_EVALUATED.** No numerical success or failure is inferred from absent scores. Real P0 issuance, future-only Champion activation and actual exploration/return scoring remain separate unmet gates.

Prior remote PR #136 had an associated successful intake run [41600371973](https://github.com/haji84/habuAI-private/actions/runs/41600371973), dashboard [41600371900](https://github.com/haji84/habuAI-private/actions/runs/41600371900), and handoff [41600371909](https://github.com/haji84/habuAI-private/actions/runs/41600371909). An experimental Qwen holdout run failed and other experimental jobs were skipped. These existing runs are not CI evidence for the new local code; no exact new-head or fresh-main CI is claimed. Whole-PR feature acceptance, device E2E and production deployment are outside these source-processing reviews.

Next evidence required for real training: authorized access to newer original logs/GPX/DB and the two named private CSVs; independent search/outcome/source audit; qualifying TRAIN_ONLY cohort and unused confirmation protocol. Code, synthetic tests and this aggregate assessment use the owner's existing explicit public-code/non-sensitive-result approval. Main integration requires its separate approval and checks. No sensitive source payload or model promotion is included in that code publication.
