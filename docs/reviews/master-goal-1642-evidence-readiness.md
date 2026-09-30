# Follow-on 6: evidence audit and learning snapshot readiness

Update: the missing local OSM bytes were recovered and independently hash-verified from the pinned repository archive. See master-goal-1642-osm-recovery.md and evidence/master-goal-1642/osm-recovery-inventory.json. This supersedes byte-absence findings below; historical prediction access, time-universe, search eligibility and outcome completeness remain unverified.

Read-only independent audit of the current local habuAI-private tree for #1642. AGENTS.md read. Task3 model evaluator was not edited. No external requests, credentials, repository writes or test-suite executions. Findings below include actual read-only SHA/CSV/XML checks, not merely document claims.

## Concrete present evidence

| Source | Actually present and checked | Available fields / provenance | Missing or not justified |
|---|---|---|---|
| data/raw/gpx/*__legacy.gpx and evidence/raw_intake/<sha>.json | 13 GPX; all 13 receipt SHA and byte sizes match; all 13 join historical QC by SHA and point count; total 243747 trackpoints | Byte hash, raw/incoming paths, source=chat-archive, source_ref, received_at_utc, duplicate/promotion status; all receipt dates 2026-09-30 | August model availability; search vs transport intervals; complete night coverage; road matching; capture outcomes for these 13 nights; audited Gold status |
| evidence/legacy/habuAI-public/v2_actual_gpx_13night_qc.csv | 13 per-night rows joining actual bytes | operational_night, source filename, gps_points,start/end,duration,distance,median/p95/max gap,gaps_gt_300s,sha256 | QC is not outcome completeness or field search-role certification; no acquisition timestamp |
| data/raw/gpx_archives/2026-09-28-探索.gpx.lines | 24 parts reconstruct to declared 6068111 bytes and SHA 2e9fde7aa459fc100abf8014d95635e697a638679cc9df731f4e0f6a80fb62f3; 22990 trackpoints | Manifest source, original filename, part layout, exact hash/size/count; actual first trackpoint 2026-09-28T09:47:12.000Z, last 2026-09-28T16:11:01.999Z | No ingestion receipt timestamp in archive manifest; recording interval is not evidence that all interval is searched |
| data/raw/habu_logs/2026/2026-09-28.json | 5 capture events /6 individuals declared; one sighting 22:36 and exploration_end 01:11 | Times, place names, type, counts, size/sex/behavior notes, declared 07:00 boundary | No source received_at; no event IDs/coordinates for direct unambiguous machine lineage; no search-start entry; no full reaction/survey completeness |
| data/processed/capture_events/2026/2026-09-28.csv | 5 unique event IDs, counts sum6; all individual links match | event_id,operational_date,event_time_local,event_place,event_type,event_count,latitude,longitude,surface,source_note | No source-row references/hash or derivation record; coordinate method/uncertainty absent; no label_available_at or logging completeness |
| data/processed/individuals/2026/2026-09-28.csv | 6 individuals, 2 correctly linked to midnight event | individual_id,event_id,index,time/place,size,sex,behavior,microhabitat | Same timestamp/provenance limitations; must not count as 6 additional events |
| evidence/osm/* manifests/audit | Metadata present; no local OSM payload under data found | Acquisition retrieval times/hash/size, auxiliary role, tile IDs, claimed 16990 candidate cells in processing audit | Manifest paths point to a prior absolute scratch workspace; referenced roads/grid/boundary bytes unresolved. DATA_BLOCKED for hash resolution, not usable forecast features/universe |
| predictions/recovered_original/2026-09-28/P0/prediction.json | Retrospectively recovered count/range/text ranking, no formal targets | source_message_timestamp, cutoff, recovery date, self-contained SHA, explicit permanent strict-ineligibility | Original frozen model/features/universe, exact spatial targets, pre-reveal freeze; cannot repair retrospectively |
| model_learning.json / explicit forecast universe | Absent in current inspected tree | None | Cannot feed strict evaluator yet; no invented synthetic rows for real report |

The GPX XML read-only check found **one zero-time-delta transition**, data/raw/gpx/2026-08-27__legacy.gpx trackpoint index20156 (zero-based). This must be reported, segmented or policy-excluded; blanket continuity PASS from an old summary is insufficient. No missing/naive timestamps were encountered in the 13 raw GPX probe. This was a narrow schema/time probe, not road/search eligibility validation.

No raw capture_db CSV exists locally. Only September28 has the canonical processed capture CSV. Therefore absence of capture CSV for the 13 legacy GPX nights is **missing outcome evidence**, not zero captures.

## Existing implementation and exact seams

- src/master_orchestrator.py:_evidence currently records all fields availability/quality/recovery/search_role as UNKNOWN/null and emits a permanently NOT_VALIDATED evidence_audit. Replace this with executed per-check audit results while retaining conservative eligibility aggregation.
- src/pdca_pipeline.py:load_captures now checks exact capture type, finite positive integral count, coordinates and 07:00 date consistency. It still silently drops invalid rows, deduplicates equal event IDs without conflict checks, and discards useful provenance/surface/quality. A provenance-preserving audited loader should be shared rather than a second incompatible parser.
- load_gpx_points verifies archive bytes/deduplicates raw hashes but discards segment flags, role, quality and record-level refs. build_exposure still marks every valid GPX point cell/time as eligible absence/negative without audited search and outcome completeness. Existing outputs are diagnostics until audit facts are attached.
- src/gpx_audit.py:parse_gpx silently skips no-time points, permits naive datetime conversion, loses trkseg identity; build_gpx_audit assigns night from first point and classifies complete-vs-nonsearch by filename. Do not promote this legacy classifier into the new eligibility authority.
- docs/specs/master-goal-1642.md gives EvidenceManifest/LearningSnapshot/ForecastUniverse requirements. Current Gold criterion explicitly needs real time/location/search coverage; five recovery classes are epistemic labels, not an algorithm that can invent missing lineage.
- Source five-class summary is working/not-final: ACTUAL_GPX13 / HIGH21 / PARTIAL18 / SPATIAL_ONLY36 / UNRECONSTRUCTABLE0. Only 13 SHA-bound raw trajectories are present; do not create 88 nightly records with inferred identities from aggregate counts.

## Minimum auditable source contract

Keep source identity and timestamps separate:
- source_id = stable content identity; relative path, bytes SHA256/size, artifact type, source system/class, ingestion receipt ref+hash.
- event_time_range = observation/recording times; source_created_at/source_published_at only when explicitly supported.
- first_verified_received_at (or known_available_by) = actual verified ingestion receipt time; historical_available_at nullable with evidence basis and confidence. Never equate GPX event time, old filename, Git commit timestamp, source message timestamp or filesystem mtime with model access.
- effective_available_at for **prospective** use = max(verified receipt, required dependent source receipts, validated transformation/audit completion). Record its basis. Derived row availability cannot precede inputs and required interpretation.
- use_role enum/set: outcome_label, observed_exposure, static_predictor, forecast_predictor, live_predictor, universe, provenance_only, diagnostic_only. Source role and search_role differ.
- search_role = SEARCH / PASSAGE / NONSEARCH / UNKNOWN with interval(s), issuer/method and supporting source_ref; point-level audit retains source track/segment/index.
- recovery_class = COMPLETE_REAL_GPX / HIGH_QUALITY_GPS_RECONSTRUCTION / PARTIAL_RECONSTRUCTION / SPATIAL_ONLY / UNRECOVERABLE, nullable/unresolved if evidence lacks a defensible assignment. Keep ACTUAL_GPX provenance separate from completeness. Byte-exact line archive is a transport encoding of real GPX, not biological trajectory reconstruction.
- quality = GOLD / SILVER / UNKNOWN / REJECTED plus executed quality checks. Silver permits only explicitly bounded diagnostic/partial uses; it is not permission to generate temporal negatives.
- source_refs should reference manifest source IDs **and typed selectors** (CSV row/event ID, JSON pointer, GPX track/segment/point interval), include role, expected hash, availability proof ref and transformation version. All paths confined to snapshot; reject path escapes and hash mismatches.

The September30 receipts establish a conservative known availability starting at documented ingestion for future use, subject to trusting/verifying the existing receipt and independently validating labels/role. They do not prove August availability. Raw trajectories with observation time in August can be valid inputs to a model trained after September30 if their use is justified; no reason to demand impossible old availability for prospective operation.

For receipt-less existing captures/logs, a new actual audit can record **new current verified availability** prospectively; it cannot fabricate old receipt dates. A current timestamp honestly means “verified present now,” not “available on observation date.”

## Minimum real audit execution

Proposed bounded module src/evidence_audit.py, shared pure validation helpers, run-scoped output through master_orchestrator; tests/test_evidence_audit.py. Read only snapshot inputs. No raw/prediction mutation.

1. Rehash every source; verify receipt path/hash/size and archive parts, counts, raw digest; compare source IDs/aliases. Fail integrity mismatch; unresolved external references produce DATA_BLOCKED requirements. Do not silently traverse old absolute OSM paths or fetch replacements.
2. Parse CSV/JSON/XML with strict finite coordinates, explicit timezone, count and event semantics; report every rejected record plus reason, never just disappear it. Recompute operational night per record.
3. Preserve GPX segment identity; report missing/backward/duplicate timestamps, bounds, outlier/gap intervals, count/time-range discrepancy. Compare legacy QC by SHA; keep report claims separate from recomputed measurements.
4. Resolve declared recovery provenance and interval-specific search eligibility from evidence. Missing search declaration -> UNKNOWN; coverage missing -> not complete. Existing class summaries serve provenance hypotheses, not certification.
5. Reconcile event layer, individual layer and raw log. Exact same ID+same content -> one canonical event with multiple source_refs; same ID+different count/time/location -> conflict FAIL/quarantine. Different IDs with same/near coordinates/time are duplicate **candidates**, not automatic merges; legitimate multiple individuals/events remain possible. Link midnight count2 to its two individual IDs.
6. Build per-unit observation provenance only for explicit eligible intervals. Positive capture can be real even with no GPX; missing GPX blocks effort/exposure-based interpretation rather than deleting outcome. Negative requires observed matching unit AND appropriate outcome completeness; an unlogged 13-night corpus is not 13 zero nights. No interpolation over breaks to manufacture searches.
7. Audit each feature/universe/label source role and availability independently. Current-night GPX/exposure is ex-post label/eligibility evidence, never P0 feature or universe. Surface reports at capture time are post-outcome covariates, not weather forecasts.
8. Output per-check statuses, eligibility by use and explicit requirements. Executed byte/schema/dedup checks can PASS while full evidence gate remains PARTIAL/BLOCKED; unavailable science stays NOT_VALIDATED. Do not make entire audit “PASS” merely because missingness was correctly catalogued.

Output artifact suggestion: evidence_audit.json contains check results, source_manifest, capture_audit, trajectory_audit, eligibility decisions, duplicate_candidates/conflicts, input_requirements[], summary counts, code/input hashes. input_requirements each has code,kind(DATA_BLOCKED/IMPLEMENTATION_BLOCKED/SCIENTIFIC_LIMITATION),source IDs,criterion,required_fields,evidence_needed,permitted_next_action and whether retrospective recovery is possible. This is materially useful even when no training rows are eligible.

## Safe learning snapshot builder

Proposed src/learning_snapshot.py, tests/test_learning_snapshot.py, invoked from master with a typed audited manifest and explicit frozen ForecastUniverse artifact. Do not generate strict model_learning.json from observed GPX cells.

Minimum preconditions: verified universe bytes/domain/cell-time coordinates and availability; versioned label/effort policy; audited source-role/quality/availability; eligible capture/log coverage; explicit fold cutoffs and research/confirmation partition. Missing prerequisite -> emit a build report and requirements, no pretend usable learning snapshot.

For each declared ex-ante universe row:
- retain exact coordinates, cell IDs, window and universe row ID/hash;
- join observed evidence via bounded validated intervals; unknown label remains null;
- label0 requires matching observed search/passage and outcome completeness; label1 requires valid capture evidence; preserve capture_count and canonical event IDs;
- attach feature values only from permitted sources known available before cutoff, with per-feature availability and refs;
- label_available_at stays distinct from feature availability; historical held-out labels may arrive after cutoff, but historical **training labels** must predate evaluated night/cutoff;
- preserve measured duration_seconds/distance_m only where defensible; duplicate sample timestamps cannot inflate effort; unknown effort remains null;
- do not let count2 event produce duplicate IDs across grid rows; reject collision/conflicting labels;
- compute deterministic content hashes, transformation version and source hashes; immutable run output can be promoted to canonical pointer only under existing flow, never edit raw or ORIGINAL.

Prospective path is attainable: resolve/hash actual allowed static roads/domain now; freeze future universe and features at new cutoff; issue future prediction; collect actual search/label receipts; build post-night labels and evidence. These steps cannot turn previously revealed nights into untouched confirmation nights. Current historical source limitation must not prevent legitimate future issuance infrastructure.

## Immediate input requirement report from current data

1. GPX 13 nights: raw integrity proven; missing capture/reaction completeness and interval search-role evidence. Current receipt dates permit only future use after receipt/validation, not August ex-ante reconstruction.
2. September28 log/captures: provide auditable coordinate derivation, row-source mapping and receipt/availability proof (or prospectively timestamp new verification); search interval declaration and outcome completeness are absent. The sighting has no coordinates, so it cannot be silently cell-labelled.
3. OSM references: recover exact referenced payloads from an already-authorized source or declare absent; verify matching hashes. Metadata-only auxiliary candidate-grid claim is DATA_BLOCKED. No external retrieval authorized in this audit.
4. ForecastUniverse: supply/create an independently defined **future** domain/grid/time artifact before new issuance. Historical GPX cannot fill this gap.
5. Historical features/weather: archived forecast snapshots with issuance/access times required for strict historical use. Capture-time surface labels cannot substitute.
6. Independent validation: September28 labels already revealed and legacy nights already analyzed. Need prospective unseen confirmation and cross-year evidence for full-scope claim; no amount of new hashing creates those.
7. ORIGINAL September28: permanent recovered-only status. Do not reconstruct absent 100m targets, rewrite cutoff or assert pre-reveal freeze.

## Small acceptance matrix for follow-on6

Meaningful tests: correct-hash receipt + actual GPX passes byte check; tampered raw/part fails; receipt later than historical cutoff prevents predictor use yet permits later prospective training; missing receipt stays unknown; labels may be after held-out cutoff but not training cutoff; zero-delta/gap/segment boundaries retained; per-point 07:00 boundary; hash-alias dedup; conflicting event ID rejected; two individuals preserved as one event/count2; different-ID same-time candidates flagged not merged; no capture file never zero-labels a night; nonsearch/spatial-only never negatives; OSM unresolved paths blocked; universe absent blocks build; known-good explicit universe and validated synthetic provenance produce deterministic snapshot; raw/ORIGINAL hashes unchanged.

Synthetic fixtures validate machinery, not Habu scientific eligibility. On actual local data expect executed integrity/schema checks with concrete passes and remaining DATA_BLOCKED/scientific limitations, not a fabricated fully validated snapshot.

