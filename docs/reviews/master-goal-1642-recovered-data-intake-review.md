# Independent recovered-data intake review

## Verdict

**Approve bounded append-only archival of the selected saved read-response artifacts as `RAW_CONNECTOR_RESPONSE`, with the representation and eligibility limits below. Do not admit canonical positive/negative labels or individual counts yet.** This can preserve useful recovered field evidence and support event reconciliation without manufacturing historical provenance. No repository edits, source imports, subagents, or code execution from recovered artifacts were performed by this review.

The recovered field logs materially improve the evidence available for inspection. Workbook summaries, model-generated classifications and archive counts do not become ground truth merely because their response bytes are now hashed.

## Verified identity and safe archival contract

I independently rehashed all 18 entries in `library-habu-audit/inventory.json`: every saved byte size and SHA-256 matches. These identities establish the exact **saved response/extracted/analysis artifact bytes** only.

Important distinction: `read-first.json` is a serialized structured result and `read-pages.json` is a collection of such results; other read files contain the tool response envelope. They are not necessarily the original network transport serialization. `RAW_CONNECTOR_RESPONSE` must therefore carry a representation such as `saved_structured_result_json` or `saved_response_collection_json`, rather than claiming original transport bytes, original TXT bytes, or original XLSX bytes. Equal extracted/advertised TXT sizes do not establish original-byte identity.

Archive the already saved selected files byte-for-byte through the normal incoming/receipt path, using content-addressed or collision-refusing destinations. Verify copied SHA and size before promotion. Never overwrite existing Raw or ORIGINAL. A future successful original-binary recovery is a new linked artifact, not a replacement for this response history.

The receipt should record:

- Artifact kind/representation, saved-response SHA and actual size, provider/Library identity, original filename as metadata, each original file ID, and returned version ID exactly as observed. Keep absent versions null. The 89-night derivative read has version `1`; do not flatten that known value to null.
- The actual current intake/verification timestamp and its meaning. Preserve any separately recorded original read time; if unavailable, leave it unknown. Do not invent the original retrieval instant or use Library created/modified time as verified historical access.
- `original_binary_verified=false`, `original_file_sha256=null`, and advertised original size in a separately named metadata field. Record materialization HTTP502 as a recovery limitation, not a verified original-file hash.
- Source/model-generated flags as provider assertions, exact returned page/line ranges, incomplete ranges, serialization/extraction method, and references to each batch member. A container with multiple source results needs a member list, not one misleading source ID.
- Permitted use `recovered_source_review`/`diagnostic_only`, canonical-label eligibility false, and unresolved quantity/ownership/time/provenance checks. Source-event time, label availability and predictor availability remain separate.

### Selected artifacts and coverage

| Saved artifacts | Permitted archival interpretation |
|---|---|
| `rawRead.json` + `rawPages.json` | Primary May–July log response coverage 1–14470. Initial response also contains the first 1000 lines of a duplicate-copy candidate; preserve that member explicitly and do not count it as independent evidence. |
| `augRead.json` + `augPages.json` | Primary August log response coverage 1–4653. Suitable for source-local event-candidate review. |
| `read-first.json` + `read-pages.json` | Model-generated capture workbook responses through returned line 9000, plus 89-night derivative and unreadable ZIP members in the initial batch. Final attempted workbook tail returned an empty 1–0/0 result, not successful coverage of advertised lines 9001–9073. Preserve the mismatch. |
| `may-july-extracted.txt`, `august-extracted.txt`, `capture-read.txt` | Derived extracted representations linked to the saved responses and extraction method. Do not call their hashes original-file hashes. |
| `parsed-sheets.json`, `candidate-blocks.json` | Reproducible analysis/review-queue artifacts only; keep parser limitations and source locators. Not canonical events or source Raw. |

Exclude search/discovery responses and `analyze.py` from a blanket “raw field-log intake.” Search results are unnecessary broader metadata; the script is analysis code, despite the inventory's generic kind label. If the mixed initial read container is archived intact, its derivative workbook/failed-ZIP members must remain non-ground-truth metadata. Selecting or sanitizing members into a new file creates a derived selection with its own hash; do not claim it preserves the whole original saved response byte-for-byte.

## What can be parsed and linked now

Safe immediate work is a **source-local candidate ledger** preserving exact raw blocks, line/page/member locators, native date/time strings, species/event wording, coordinate text, quantity wording/bounds, ownership wording, source IDs and unresolved conflicts. Stable candidate IDs should bind source-response identity plus locator; a later canonical event ID must reconcile aliases rather than counting every copy as another event.

The two field logs contain real capture statements, not just forecast narratives. They can be classified as explicit capture mentions pending subject/species, completed-event meaning, ownership, quantity and duplicate resolution. Blank quantity remains null/unknown; a capture mention or workbook default `1` is not evidence of exactly one individual. Event occurrence and individual count must remain separate concepts.

I independently checked the supplied candidate blocks against the 13 actual legacy GPX files. Interpreting native local timestamps provisionally as Asia/Tokyo and applying the canonical 07:00 boundary produced these useful correspondences:

| Operational night | August-log candidate line starts | Candidate mention blocks |
|---|---|---:|
| 2026-08-12 | 2631, 2770, 2994, 3030 | 4 |
| 2026-08-13 | 3176, 3470 | 2 |
| 2026-08-15 | 3833, 4156, 4186 | 3 |
| 2026-08-17 | 4279, 4609 | 2 |

All 11 blocks have explicit coordinate pairs. A read-only proximity probe found recorded GPX points within approximately 1.5 metres and 52 seconds of each block's timestamp/location under that provisional timezone interpretation. This is strong **source-alignment evidence**, not proof of ownership, completed capture, quantity, independent corroboration, complete search effort or complete outcome ascertainment. Every one of these 11 blocks lacked an explicit numeric `匹`/`頭` quantity token. None may silently become `capture_count=1`.

The May–July log has no date overlap with those 13 August/September GPX nights. It can still preserve earlier candidate outcomes for later reconciliation; lack of a matching GPX does not erase a genuine capture statement. Conversely, a GPX match is not permission to invent missing coordinates for an event. For example, the May7 22:58 capture block must not borrow the next 23:02 roadkill position.

The workbook supplies additional candidate mentions overlapping GPX nights, including August19/23/24/27/28/29, but those require the unresolved underlying August source and row-level reconciliation. Workbook-only linkage is weaker derivative evidence. Absence of candidates on other GPX nights does not establish zero captures.

For a durable link artifact, preserve the GPX SHA, track/segment/point locator, time and distance residual, raw-log source locator, timezone interpretation and conflict status. The probe used geographic-distance proximity for intake review; it is not a formal prediction KPI computation. Full source/point hashes and locators should be persisted by the bounded intake implementation rather than copied from this narrative alone.

## Quarantine and resolution requirements

1. **Workbook role conflict.** Independently confirmed 206 capture-labeled rows with inherited counts 204×1 and 2×2, and roles 本命95 / 対象58 / 反応53. Neither 206 records, 208 individuals nor a 本命/対象-only filter is a verified eligible total. Preserve all 53 conflicts and resolve against source blocks, event semantics and ownership. Inherited `high`/`source_confirmed` fields are assertions, not independent quality certification.
2. **Ownership.** Independently confirmed normalized row index209 (May15 22:50) explicitly marked other-person capture. Keep it as separately scoped reaction/other-person evidence, not the user's target-capture outcome. Lack of an other-person flag is not sufficient proof of own capture; the role ontology must be explicit.
3. **Quantity.** Never default blank to one. Retain explicit integers, lower/upper bounds and lower-bound flags separately; conflicting/approximate quantities remain quarantined for individual-count metrics. A confirmed binary event occurrence may later have a different eligibility decision from an unresolved individual count, but this review authorizes no canonical label admission.
4. **Time.** Canonical night remains 07:00 JST despite the workbook summary's explicit 05:00 rule. Recompute only from verified native calendar timestamp plus timezone; keep supplied night and discrepancy. Approximate `夜`/`頃`/`前後` or context-inferred time cannot be promoted to exact ten-minute eligibility. Some workbook night cells are extracted Excel serials: a provisional 1900-epoch interpretation produced many disagreements with naive calendar-date recomputation, so do not assume those serials or the `日付` field's semantics are already trustworthy. Resolve against native log blocks/original date-system evidence before treating any disagreement as a corrected fact.
5. **Duplicates and source completeness.** The similarly named TXT copy matches only the inspected prefix; equal advertised size is not full hash equality. Cumulative logs, workbook quoted blocks and duplicate copies are alias candidates. Empty duplicate keys or unique keys do not prove semantic uniqueness. The workbook tail and one malformed normalized row remain unresolved extraction limitations.
6. **Species/event separation.** Roadkill, sightings, other species, “capturing” ambiguity, reaction records and unknown event kinds remain separate. “No decisive capture” and uncertain partial-session no-capture wording cannot create negative cells. Neither a daily summary nor an empty capture file establishes exhaustive observation.
7. **Derived reconstruction and other workbooks.** The 89-night workbook's recovery categories/event-GPS anchors are hypotheses, not 89 measured nights, 21 actual reconstructed trajectories or complete labels. The model-generated literature workbook is not personal capture truth; unreadable ZIP content is unverified. Do not convert 10m derivative claims into the formal 100m exposure contract.

## Metadata and secret screening

I screened the six selected JSON read artifacts recursively, including decoded string content, without printing secret values. No URLs, email-pattern matches, sensitive credential/download/owner-ID metadata keys or common bearer/private-key/token markers were detected in those selected files. All inventoried artifacts were also checked for signed-URL/query and common credential patterns; none were detected. The broad `search.json` contains URLs and remains outside the proposed selected archival set.

This is a bounded metadata/pattern screen, not exhaustive personal-data certification. Relevant field locations are deliberately part of the authorized private Habu evidence scope. Do not archive unrelated discovery metadata, authenticated materialization URLs, signed URLs, cookies, headers or credentials if later recovery returns them. If an exact response contains such material, withhold that raw response from Git and create an explicitly sanitized derivative with distinct provenance; never silently redact a file while retaining its old hash or “exact response” claim.

## Effect on real-data gaps

The safe next step is append-only evidence preservation plus a typed reconciliation queue, especially the 11 tightly aligned August candidates and workbook/source role conflicts. This can replace “no source content recovered” with actual reviewable source statements for four GPX nights. It cannot yet establish 11 individuals, complete nightly totals, negative units, Gold exposure, a complete Stage1 outcome denominator or a valid learning snapshot.

Current verified intake and completed validation may support **future** training availability. Library creation dates, event dates, filenames, reconstructed text and workbook summaries do not establish past model access, ex-ante feature/universe availability, historical ORIGINAL issuance or untouched confirmation. Keep the receipt and all derived eligibility changes additive, and do not retroactively upgrade previously revealed nights into independent confirmation evidence.

No full test suite was run. Verification here was read-only saved-artifact hash/coverage/schema inspection, selected metadata screening, source-count/role checks and the explicitly scoped GPX proximity probe. Original binary integrity and transport-byte fidelity remain unverified.
