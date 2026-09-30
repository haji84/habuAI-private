# Bounded prediction PDF source-gap audit

Read-only input audit, 2026-09-30. No repository, raw file, historical prediction, score, or Freeze was changed. Scope: existing Sept28 P0 and Sept29/30 candidates in the explicitly resolved PDF only.

## Evidence and bounds

Source: `今日の捕獲予想9.30まで.pdf`; Library `libfile_4935527416908191aa59b5de1f11b81f`; file `file_0000000032188209868da12d4c164662`; version **null**; advertised size 13,415,073 bytes; created/modified 2026-09-30T15:31:14.849445Z. Text service reports 1,982 pages / 68,679 lines. Read initial 80 lines, pp1757–1759 and pp1976–1982. Date/weekday find over entire extracted text returned 23 matches for corrected bounded-date regex, all inspected. No unrelated Library sources accessed. This is not an exhaustive visual inspection of 1,982 pages and absence claims are bounded by extracted text/search terms.

`prediction-pdf-read-evidence.json` beside this report preserves complete structured read responses for pp1757–1759, pp1976–1982 and corrected date-find response. It is a current retrieval representation, **not original PDF bytes**. PDF byte hash remains unavailable. Metadata creation time and printed export footer `2026/10/01 0:28` are not prediction issuance timestamps. Existing PDF text can reorder user/assistant blocks, so exact turn boundaries need original conversation export for stronger proof.

Representation integrity: 70,438 bytes; SHA-256 `5083773359946044a0abeae6cc77d7f819e050bb0d6ee96974c924e9b7f77886`.

## Available predictions within scope

| Operational night | Recoverable content and version | Cutoff / proof limit |
|---|---|---|
| 2026-09-28 | Existing repo `recovered-chat-2026-09-28-P0`, RECOVERED_ORIGINAL. PDF pp1757–1759 independently corroborate 4; central 3–5, broad 2–6; ranked 節子〜嘉徳 / 久根津 / 伊須〜勝浦・阿室釜; 19:00–21:30 and 22:30–00:00; activity burst 100–500m. | Repo timestamp 2026-09-28T09:26:08Z / cutoff18:26:08+09:00 is existing provenance, not verified to second precision by PDF. PDF shows 月曜日18:25 before prediction; may be prompt timestamp. Keep both distinct. Existing strict eligibility false and retrospective recovery status remain. PDF central range3–5 could be appended as supplemental source evidence without altering historical payload. |
| 2026-09-29 | No Sept29-night prediction located by bounded date/weekday search or inspected tail. Date hits pp1961–1973 concern Sept28-night post-midnight capture outcomes and implementation discussion. | Do not infer Sept29 forecast from Sept29 civil-date captures. Under07:00 JST boundary those after-midnight outcomes belong to Sept28. No version/cutoff established; keep missing. |
| 2026-09-30 | Substantive forecast pp1979–1980. Starts `今日9/30は、再構成予測で「4匹」本命`; count4, range3–5, upside6; windows18:50–21:20 and22:50–00:40; route 節子・嘉徳 → 勝浦・阿室釜側 → 久根津・県道79号; large-size probability35–45%. Following response explicitly calls this 今夜のP0予測 and Freeze; future new information assigned P1+. | Exact issuance time/cutoff unavailable in inspected PDF text. Narrative Freeze is not cryptographic ex-ante Freeze. Explicit 再構成予測 means preserve source wording and do not silently classify strict ORIGINAL. Candidate P0 recovery with provenance uncertainty; strict eligibility false. No actual P1+ update found in inspected ending. |

Sept30 finer route timing recoverable: A節子→嘉徳18:50–21:15; B勝浦・阿室釜・612方面21:15–22:45; C久根津〜県道79号around23:00. Conditional Wet/light-rain adjustment4→5 is a conditional rule inside the forecast, not evidence an actual P1 was issued. No explicit 100m×10-minute target IDs, probabilities, ex-ante candidate universe or frozen input snapshot occur in these forecast blocks. Do not invent them from the route text.

## Practical append-only recovery path

1. Preserve current PDF response evidence with IDs, null version, exact page coverage and retrieval time; label its hash as response-representation integrity only. If original PDF bytes are later materialized, intake separately through incoming, actual byte-size/SHA audit and provenance linkage; retain both forms.
2. Append Sept30 as a source recovery candidate with literal forecast/confirmation blocks, `source_claimed_version=P0`, claimed date2026-09-30, unknown exact issuance/cutoff, `source_prediction_wording=再構成予測`, missing formal targets and `strict_official_score_eligible=false`. Do not fill mandatory timestamps with export/retrieval times. If current recovered-original schema requires exact dated issuance, keep this in candidate evidence pending a timestamp-bearing conversation export rather than weakening validation.
3. Attach PDF corroboration and central3–5 range to a supplemental Sept28 provenance record. Keep existing immutable Sept28 P0 payload/hash and its broader2–6 range untouched. Record18:25 display versus existing18:26:08 timestamp as different provenance precision, not an automatic correction.
4. Keep Sept29 input explicitly unavailable in this bounded source. A future timestamp-bearing source may append a candidate; no interpolation from Sept28/30 and no backdated Freeze.
5. Any future accepted recovery gets a current recovery-time immutable hash. Source dates, narrative Freeze assertions and PDF archive timing cannot establish historical feature access, pre-label cryptographic freeze or strict official scoring eligibility. Historical count/route diagnostics must remain separate from strict ORIGINAL scoring.

No tests were run because no repository implementation changed. Content findings above are source audit results, not scientific validation or verified historical model execution.
