# Aug31 positive source registration — independent review

PASS for the bounded source/data registration at exact
`49e1a3dbd7ba8b96be840b0368568fcf9f195952`, tree
`d08198f5c9bb666f06d7ec32b07387254dc4c875`. This review adds only this document;
it does not change runtime, policy, registered review, source data or STATE.
The independent source audit is PARTIAL, not scientific validation or parent PDCA.

## Publication order and actual time

The software baseline is actual main
`756441d7b2c758c6c81318935a50a7524afc94b1`. The coordinator reported the preceding
exact PR121 software gate as 1504 tests, 32 skips, 402.820s. I independently read
the fresh-main GitHub job and its logs: [40219261082 / 121247055819](https://github.com/haji84/habuAI-private/actions/runs/40219261082/job/121247055819)
checked out that exact main, finished 1504 tests with 32 skips in 401.704s at
`2026-10-25T18:08:38.3418382Z`, then passed the frozen-code CLI and secret-file
step. The job API reports completed/success; its last logged timestamp is
`2026-10-25T18:08:39.0277903Z`.

The final NEW review records actual
`reviewed_at=2026-10-25T18:09:46.626604+00:00`, after that software gate, and the
registration commit time is `2026-10-25T18:10:24+00:00`. The independent successful
run used `verified_at=2026-10-25T18:15:24.871536+00:00`; this record was prepared
after the UTC clock check at `2026-10-25T18:20:32+00:00`. The review was absent at
the software baseline. No provisional fixture timestamp was reused and no
historical August receipt/usable time was inferred. The public audit's source
availability and qualification check are current-audit time, including its
existing equivalent JST serialization.

## Exact data boundary and unchanged evidence

The registration diff contains only the new
`evidence/source_reviews/2026-08-31-positive-source-review.json` and
`policies/observation_evidence.json`. The new review is 3973 native bytes, SHA256
`da5923ef406df84ad0054daffd783cc1ce179e1dab3d0f0cb7149add555cf964`.
Policy SHA changes from
`d8c702002eafcec4baee41e0c68f04068389fc459ece8345e79577d7b8bf76a7` to
`314d25ebd91b2db5d31a6a2f0cde7429d4fc8e625e432f1adead7661a2845e78`.
Removing its sole new source entry reproduces the entire old policy as canonical
typed JSON. The old Sept28 entry and all other semantic fields remain exact;
sessions and outcome_coverage remain empty.

The entry binds only the fixed 413-byte capture CSV, SHA
`137c04b5abe6713c1668633fe10afa61f601a5c0a8d5331471d71f8cbf0a972f`,
to that exact new review. All six fixed source refs, their sizes/hashes, the
116496-byte native TXT, exact original line/byte slices, original GPX and derived
378-byte occurrence CSV were verified. Unchanged source code reproduced both
crosswalks and GPX QC; typed proof SHA is
`7bc55a50110113cb3f5b2b6373966e34a9c7a71e616eaa67cabd48547f1c12c6`.
The existing source-selector and GPX facts are those of the approved Aug31 spec;
no coordinate, interpolation, new quantity or original animal ID is supplied here.

`AUG31SRC-L10110` and `AUG31SRC-L10492` each have their matching `-OCC01`
source-occurrence link and count one. They are two recorded singular capture
occurrences, not a claim of two permanently identified or distinct biological
animals. Owner August47/cumulative243 records, their historical false fields,
Raw, originals, old reviews and all other committed bytes remain unchanged.
The new review is RESEARCH_EXPOSED/outcome_label only; all eight authority fields
are false, and device authentication/permanent biological identity remain
NOT_ESTABLISHED. A future qualifying audit must execute the fixed verifier;
reading or hashing this review is not independent scientific authentication.

## Independent native execution and resources

The external harness materialized the complete fixed Git tree with NUL-safe
paths and command-local `core.autocrlf=false`: **878 files / 182154574 bytes**.
Every file matched its native Git blob identity, size and SHA; the source
worktree also matched those bytes. All files were checked unchanged before and
after the executions. Native manifest SHA is
`4d786856086f3e517cad0a825150e31d57566489dbd9b10eccd03f8fedbb9b64`.
Only the snapshot's own runtime modules were imported. No Raw normalization,
network input, fake filesystem/backend/POSIX layer or cap change was used.

Direct `reproduce_sources` passed in 0.875s and public `verify_review` passed in
0.953s. Each used its own real Audit context: **12 reads / 9749432 bytes / 17906
point charges**, with the identical complete typed proof. These are two separate
contexts and separate from the complete public audit below; their success is not
a claim that their combined work shared one deadline or budget.

The actual public `audit_evidence` for operational night2026-08-31 used one
unchanged 300s / 512MiB / 4000-read / 1000000-point context:

- PARTIAL, no FAIL checks, **16.641s / 556 reads / 361619206 actual bytes /
  325364 point charges**.
- 220 consumed paths; their hashes agree with actual read order/accounting and
  the complete native inventory. Final reference rereads and result seal passed.
- 7 qualified events / 8 recorded source occurrences / 7 positive units,
  including exactly the two new Aug31 events/occurrences; 688 requested-night
  UNKNOWN units and zero Negatives.
- Search and complete scopes remain empty; denominator NOT_ESTABLISHED,
  scientific validation NOT_VALIDATED. TRAIN credit remains zero; no training
  selector, numerical fit, parent PDCA, official issuance or production ran.

The unchanged frozen closure also passed actual `validate_cycle`: 97 code refs,
code SHA `0d694c4c29f8d7f6d12f4413a53fa10e44bc102beb3d70cfa599ee7aeb843fff`,
semantic cycle SHA
`a5675602fa647e53918e5904636f7158bd836a325c3766628e3e2cf255f8370e`.
This direct source audit does not substitute for exact data-PR CI, a full parent
run or the coordinator's later integration gate. Native execution here was
Windows; genuine Ubuntu software coverage is the earlier linked job.

## Observer correction and private receipts

The first private observer attempt stopped after the public audit because it
compared the UTC input timestamp string directly with the existing Audit's JST
output string. Those strings represent exactly the same instant. This was an
observer error, not a source/runtime finding or a passing receipt. The first
attempt's metadata directory was retained, not overwritten. The observer was
corrected to exact timezone-aware datetime equality, without tolerance or product
changes, and the entire native reproduction/verification/public-audit sequence
was rerun into a distinct `-r2` directory. Only that complete rerun is PASS.

Artifacts are private, outside Git, under
`C:\Users\qq113\OneDrive\ドキュメント\ChatGPT\ハブAI\.worktrees\aug31-registration-independent-49e1a3dbd7ba-20261026-r2`:

| Artifact | Bytes | Physical SHA256 |
| --- | ---: | --- |
| `small-summary.json` |1719|`6abd2879ea051d0414e97984387a247e7573c42ecdb7ffece19381f09657ccc4`|
| `full-independent-receipt.json` |567363|`91e185f61981919bba19292af209bcd7a0649865dc04eae5695e37b32c5c7af0`|
| `full-audit.json` |315793|`71b1a44048cd869ca9a2ebc3d006adba83a9db6019896a98ed4f06fddfd4c1b3`|
| `actual-read-ledger.json` |104149|`4b2bfcdaa173bb622b84693f84953cf7239d2bfb0d3de7f20f9d4ae99cbdbde7`|

The full private receipt includes the complete native inventory, consumed-input
hashes, full result, read ledger and both direct-call receipts. Hashes bind these
software/data observations, not the truth of every field observation or an
unmeasured biological denominator. No additional originals, source promotion,
broader August registration or new family runtime is authorized by this record.
