# Independent G0 full-universe score-summary review

Reviewed by the independent V lane on 2026-10-26. Result: **PASS for the complete standalone Phase2 software contract at `eb20045228189c1b3b10ea01862d088d26eb6359`**. This is separate from the earlier Phase1 scalar-seam review. No remaining blocking defect was found after the repairs below. No runtime, test, specification, source-data, policy, STATE or cycle was edited by this reviewer.

## Fixed source and scope

The final executable snapshot was materialized with raw `git cat-file --batch` blobs, using NUL-delimited `ls-tree -rz` path metadata. All 204 files / 4,213,777 bytes were compared against their Git mode, blob SHA-1, SHA-256, size and complete bytes before and after execution. Every mode was `100644`; the snapshot has no fake Git repository and imports identify the selected snapshot itself. All Python commands used the bundled Windows runtime with `-B -X utf8`.

Exactly ten scoped files differ from actual base `021de78514871a6e2aa0c3cc7070d78e93a4e21c`. Raw, incoming, policies, model schemas, historical cycles, parent dispatch and workflows have no delta. The branch contains 99 runtime closure paths; that is not a claim that the later coordinator union/freeze or Linux CI has passed.

| Native Git file | Bytes | SHA-256 |
| --- | ---: | --- |
| `src/g0_full_universe_score_summary.py` | 30174 | `4259b7f743d2747d3d5b0bfc440fa16234b0d3555efd3888b8ce7d977976e7df` |
| `src/g0_forecast_contract.py` | 55628 | `f0febc3e488f6339c42706823179dc29e10d1d497c0d33bca316146d55a0b4cd` |
| `src/research_model_adapter.py` | 29032 | `23894f677d5d3398a57ca28cd505979913514b97a15cec3a17c11a2484333d7a` |
| `src/models/occupancy_shrinkage.py` | 12598 | `8f7c024f5c6f67a9d398e4a7b0659eb60f56f4208c2fc068f4d5331383a5b8ab` |
| `src/models/hba1_feature_candidate.py` | 29922 | `0eb6a707d297a719de1f77b1e214e8be0d47eb8ebb54ca425a2f9dddad4a4032` |
| `src/models/research_selection.py` | 19454 | `4715758f97a2024c8d5be1a47755ecbab23a09c5de52f7ab0e8dc3b46d1c7bac` |
| `tests/test_g0_full_universe_score_summary.py` | 34424 | `4c464d309f41ec976106612fe74c141616470a91e23cc5057811eeac0c5b31be` |
| `docs/specs/g0-full-universe-score-summary-v1.md` | 33131 | `8bf920b37ec009c1c86fa397b1c86739cce18bcf0ccb54558db6b6cc398ca83f` |

The author record was also verified at 14,462 bytes / `312aa0755843cbfa28d689ab37e0995cf3c0c8d9d198f481bdbfb9a53a38a401`.

## Source review

The additive G0 seam admits only the fixed private `_ScoreReducer` type. Ordinary public load/validate signatures and the existing physical/DAG/validity/joined-row checks remain in charge. There is no external consumer, output row iterator, shortcut validator, full-row collection, target payload read or refit. The reducer visits every validated joined unit in the original order, including when missing models/lineage or an incomplete seven-feature schema require a whole-set NEED_MORE_DATA result.

Uniform, HB-A0 and full-mask HB-A1 reuse native scalar formulas and rounding. HB-B1 global/conditional ranks remain explicitly IMPLEMENTATION_BLOCKED; no probability conversion or chunk-rank concatenation was introduced. Nine legacy public model/adapter/G0 signatures were compared with the genuine old source. The old complete receipt `a8c59d499d8fa8d132cbb05876469596c5c365755b05397f80ae06cc808184e0` and candidate registry are retained. The authorized scalar extraction changes the historical five-body pin; the immutable old pin `8a035042...` remains recorded, unchanged four-body pin `943fc0b5743a0ea8c95cba28f04cef2c3f708403057606435109bed750af4ff5` and new seven-body pin `2a5f7540a7d98e9da6365c31adda81bdc7970125faca76a36d38c369da66a053` are checked separately.

The source/config/current-code/recipe/retained-model/TRAIN declarations are bound and rechecked within the same ProspectiveReadContext. All provided native contradictions are validated before missing-data publication. Exact all-unit means use a bounded binary64 integer accumulator and one Fraction-to-float conversion; Top10 uses all area means with lexical ties. The H/R/T stream framing binds the ordered complete row stream, model/config/feature/lineage identities and final joined-row digest. A changed config identity correctly changes framed hashes even when numerical area scores remain equal.

## Findings and repairs

Three narrowly scoped pure datetime conversions exposed a public OverflowError rather than malformed-input ValueError. These were demonstrated on fully rebound public inputs, rather than an unverified helper-only call:

| Source with defect | Public case | Final behavior |
| --- | --- | --- |
| `42c50b4...` | Lineage maximum window at UTC year 9999 / aware year 0001 | Both ValueError |
| `42c50b4...` | Serialized HB-A0 maximum window at the same two extremes, without lineage | Both ValueError |
| `89006baf...` | Profile fit cutoff `0001-01-01T00:00:00+23:00` reaching delegated JST training-boundary conversion | ValueError before loader |

HB-A1's corresponding two native cases already rejected correctly and were retained as negative controls. Final source catches only the pure conversion at the new entry boundary; caller checks and legacy model guards remain outside the catch. Four exception classes (ValueError, OverflowError, TimeoutError and KeyboardInterrupt) preserve the original caller object, including checks after the new conversion, inside the native HB-A0 guard, proof/reader paths, rescans and the final sealed encoding.

After correcting the snapshot issue described below, the old 42/890 and final eb sources were independently rebuilt from raw Git blobs and these time cases were replayed: six old-42 cases, two old-890 cases and eight final cases in 17.063 seconds. The five old overflow failures and all final ValueErrors were confirmed; no old golden or generic legacy conversion was changed.

## Executed final native controls

| Actual command/control | Result |
| --- | --- |
| Independent public/resource/numeric suite, raw-native eb snapshot | 16/16 PASS, 0 skips; unittest 42.232 s |
| New summary + A0 + selection + adapter + G0 modules | 172/172 PASS, 0 skips; unittest 73.168 s |
| Genuine old/current subprocesses: four complete prepared variants and five complete G0 cases | Whole canonical/native bytes, hashes, read ledgers and native open order equal; 2.750 s |
| Optional order uniform/A0/A1 versus uniform/A1/A0 | Same complete 18-unit area scores, model hashes and Top10; config-bound stream hashes differ correctly; 3.797 s |
| Independent native old-RED/final-GREEN timestamp replay | 16 public cases; 17.063 s |
| Phase1 and old-source raw Git re-audit | 203 files / 4,151,472 B and 202 files / 4,144,330 B exact; unaffected |

The 172-test command was `python -B -X utf8 -m unittest tests.test_g0_full_universe_score_summary tests.test_occupancy_shrinkage tests.test_research_selection tests.test_research_model_adapter tests.test_g0_forecast_contract`, run from the isolated native snapshot. These are synthetic software controls, not eligible-source model-training evidence.

The independent suite used an unequal six-shard, six-cell, three-window, four-area fixture. It independently reconstructed all native scores, exact area means, lexical Top10, framed H/R/T bytes and the final seal. There were 104 separate mean oracles including subnormal, zero, negative-zero, ULP-sensitive and seeded random controls. The old/current model subprocess also performed 165 scalar/ownership/exception controls against the actual old dependencies, including 80 seeded A1 formula/round8 comparisons; the genuine old subprocess performed 30 controls.

Shared accounting was traced through 468 actual opens: 4,653,447 bytes incurred by the summary call and 4,654,071 cumulative bytes after a prior actual 624-byte model read. No fresh budget was substituted. Controls cover remaining+1 reads, metadata/model/node/frame/state/output caps including the sealed result, missing models and partial-schema NMD with full source processing, invalid last shard/raw field, contradictory retained corpus, stale current-code recipe binding, strict readiness equality, owned caller refs, model mutation during final rescan, and final-seal expiry. A genuine Windows directory junction test rejected before external payload open (zero opens), preserved its sentinel and removed only the link. No POSIX behavior or engine availability was simulated.

## Immutable old oracle and harness corrections

The pre-extraction baseline at `f05fcc6ebc0005d3377d796c297cbaa2dc72e09a` was executed in its own actual old-source process, not through current aliases. All 425 listed artifacts / 6,074,995 bytes remain at their original hashes; its physical manifest is 68,080 bytes / `3f993da0d11f1fecf749452103e5e5f6f3e4f93e4418c99a20c8f50e0aa46224`. Five G0 controls retain complete typed/native/canonical outputs and input/read/open identities: small load/validate each 44 opens / 43,344 bytes; uneven load/shared-load/validate each 138 opens / 180,742 bytes. Current physical code-map/recipe bindings are checked separately from the controlled immutable old-code-map numerical oracle. No golden was regenerated.

An independent final native-byte assertion exposed a reviewer harness error: the earlier Phase2 `git archive` materialization obeyed core.autocrlf and transformed 203 of 204 files to CRLF. Those earlier 42/890/eb test outputs and descriptors remain immutable as CRLF-materialized software controls; their internal snapshot equality is not Git-native identity. The failed final AGENTS-byte assertion produced no final approval. Acceptance above uses only new raw cat-file snapshots and fresh reruns. The native final source hash is the 30,174-byte `4259b7...` hash shown in the table. Phase1 and the old baseline used raw `git show` originally; all their current bytes were rechecked against cat-file and were unaffected.

Earlier imported-test-class collection and stale config fixture controls were also corrected without product edits. The additional optional-order harness initially rewrote config bytes without rebinding its enclosing source profile; the real Reader correctly rejected the stale hash. That failed command is retained separately, and the corrected control binds both envelopes. Historical author 32/340 and 34/171 aggregates are not relabeled as the final 35-new/172-module run.

## Private evidence and limits

The following immutable files are in the coordinator workspace `.worktrees/`, outside the repository. The final receipt contains the complete command output and physical artifact matrix.

| Evidence | Bytes | SHA-256 |
| --- | ---: | --- |
| `g0-score-summary-phase2-independent-final-receipt-native-eb-20261026.json` | 11183 | `7e8904614c784ec424ba370d1437e7337c9bc7c16b2e46de47c2eb84e129be0c` |
| `g0-score-summary-phase2-independent-native-eb-20261026.json` | 51972 | `60edf3fda70f03a12dbdbc63daef6d3d9415310b54f7a0c7ad22e28e2dfa6721` |
| `g0-score-summary-phase2-independent-controls-native-eb-20261026.json` | 935 | `8020a36387892b055c54fc77b42893d39d71aaeac642f3f261dff36a50641caf` |
| `g0-score-summary-phase2-authored172-native-eb-20261026.json` | 1067 | `4166501c0b353bf62a598d9cd363411e0873d04233b0faca3921b9c3f80e5a88` |
| `g0-score-summary-phase2-compatibility-native-eb-20261026.json` | 7669 | `a2d9d60355abd6fff4c72e1175179a5fa73fbf519b3cb250aa949fc94aa55f4c` |
| `g0-score-summary-phase2-independent-time-red-green-native-20261026.json` | 4014 | `d933290a8544f8d1620f636d4bccd9160f11b4a83f4ff6a61e7bfe76ede8743d` |
| `g0-score-summary-phase2-native-materialization-correction-20261026.json` | 32632 | `9be1d4a2cb29060bf5cfc07c5badc6acd799ba94446093d67146191133811b35` |
| `g0-score-summary-phase1-native-reaudit-20261026.json` | 1009 | `a3f921c258abfb3dad700c924f665e2e6e18783f160b68465423deb27801a4be` |

All nine authorities remain false. Physical bytes, declared readiness and a caller-supplied label-free TRAIN sidecar are not issuer authenticity, historical availability, prereveal freeze or loaded-interpreter authentication. Sequential rescans are not an atomic filesystem snapshot or protection against hostile concurrent same-user mutation. Source geometry remains explicitly a cell-origin proxy, not measured road-point geometry.

This is a bounded internal additive foundation. No real qualified TRAIN fit, target/confirmation read, accuracy result, native HB-B1/HB-A2 integration, prediction array, Stage1/T2/parent transport, campaign authority, P0 or production admission was established. The prior OSM input-only 72-window rehearsal does not measure this new summary's full-night latency, actual byte cost or memory. Those measurements, coordinator source union/freeze and actual exact-head Ubuntu CI remain separate gates. A software PASS does not make the absent eligible data or those missing connections complete.
