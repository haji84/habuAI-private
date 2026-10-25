# Independent review: closed August positive-source family

Review date: 2026-10-26 Asia/Tokyo. Verdict: **PASS for the bounded source/code
contract after two repairs**. This approves neither family registration nor
scientific/production use.

## Fixed scope and source identity

The reviewed runtime/test commit is
`48d06f628f0981bf256f19dffe8c988b5e8cff26`; the released author-document HEAD is
`d60f669c7b13736c707151b5bac7a0b55acda493`. Their only difference is the author
review append. The initial failing source was
`c6f99025a3c193ff8f4a64107a23e0362a7f9d06` (runtime `cef75b3f...`).
The base is `119af0665dc3d505e14366f30cbb31b0dd764e0e`, before extraction.

Native Git bytes, checked against the current checkout after LF normalization:

| Runtime path | Bytes | SHA-256 |
| --- | ---: | --- |
| `src/_owner_capture_occurrence_core.py` | 14740 | `297b2bb4301a0234b61e63abaf92076390095957be054bce008e7d49c5b1a914` |
| `src/aug31_positive_source_review.py` | 5895 | `26e72df7ce45ba21fd23ec84dd14e902ee4bd5e29205daf77a07f20fd12f3397` |
| `src/august_positive_source_review.py` | 12084 | `7501ce6ad1e32de9d886c61503096e7bc1f90d6631197f0625bda45a49620e9a` |
| `src/evidence_audit.py` | 48013 | `4fc0648e35d623bb29c43eff73ec832731722efcdd71bc9a896eb27302211e56` |

The closed admission is only the pinned Aug29 line9654 descriptor. There is no
mutable family registry or per-night matcher clone. The extracted core and old
Aug31 facade are unchanged by the repair. Native fixture programs equal the
pre-extraction Git programs, rather than regenerated expectations.

## Independent primary-source check

The actual 116496-byte August text has SHA-256
`130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c`.
Lines9654–9663, byte slice[107486,107604), record Aug29 23:58, one singular Habu
capture description and the exact coordinate decimals. The 118-byte slice SHA
is `5ccb0b1454360fe58a638f3eea54b86922aab3d7ffe78d87bd19d164b09b33d4`.
The literal size note `130~150` is neither a count nor a measured biological
identity. The new event/occurrence selectors are derived source selectors,
not permanent animal IDs.

The two one-row CSVs preserve the source decimals and one-to-one links:
capture254B/SHA`84c7d546bca0eab9a3bf440d0709deade0ec51175cf1a24a8315317b87e0c71a`;
individual237B/SHA`6fe0e4b0f414860f1432b91e741a16d7f04ee61154ef1fdde4ec41c05773c4d1`.
The real Aug29 GPX is3576827B/SHA
`23686f0561ffc72e7310943f98f2953afdfa1908b683fdd101e9f7cfa28b6efe`.
Independent reuse of the existing parser/QC/matcher gives13565points,
selected index3222/sequence28616,0.5732971626350619m and47.999s residuals,
HDOP4.687, neighboring gaps1s/1s. The existing break1/maxgap148.999s is retained;
there is no interpolation or invented clock correction.

The descriptor is2424B/SHA
`0582d7b6150d6dcc9cbffcd568172fdb23feab5d4b47ba3f32e0331eb693f32c`.
Its code pin and all source selectors are checked, not merely an outcome-role
flag. Other27 frontier records,11 workbook aliases, deferred Aug19 and the
14 missing-GPX cases are outside this admission. Owner47/243 history is unchanged.

## Findings and repaired counterexamples

1. At c6, the two valid ISO extremes `9999-12-31T23:59:00+00:00` and
   `0001-01-01T00:00:00+23:00` leaked OverflowError at zero reads. The new-family
   pure conversion now raises ValueError(`AUGUST_TIME_RANGE`). It does not catch
   caller tick/read/point exceptions or alter the old facade.
2. A wrapper which performed the real Audit.ref read and then mutated its
   borrowed review-ref dictionary corrupted returned/saved lineage at c6:
   direct preflight's second review read and parent's third read retained an
   all-zero SHA while the consumed real SHA was different. Separate outbound
   copies and saved-lineage copies now preserve path/SHA/size in all six
   independent post-read mutation controls. Actual returned bytes were unchanged
   in this counterexample.

The old RED receipt is1965B/SHA
`dfe1fff9ef4a742f2d8c93c6511e04a312e50eed8cd16652b7b4678e25ffeebd`.
The author recorded the dedicated RED cases, then4/4 GREEN in4.161s and
102methods=100PASS/2 existing POSIX skips in137.524s. Those are author runs,
distinct from the independent runs below.

## Fresh independent execution and compatibility

The private harness ran the fixed48d runtime: **12methods PASS,0errors,
0failures,0skips; runner51.864s/outer51.875s**. Controls cover strict typed
proofs including bool/float distinctions, code-pinned descriptors, unknown
profiles/roles and aliases, duplicate/bad-last permutations before admission,
every supplied-file tamper, final descriptor mutation, shared byte/point/time
limits, no-policy behavior, and fifteen exact caller-exception identity cases.
Three genuine Windows junction fixtures reject before outside payload opens
or scans (both zero); link-only removal preserves target sentinels. No POSIX
result was fabricated.

All three old Aug31 whole artifacts match actual current-runtime results,
including typed values, self-hashes, source hashes, all read/open order and
interleaving, counters and point charges. The two pure artifacts are each
11198B/SHA`c100f0eae864bd0aa0159b1e46f8dc2419a46d064488262fa17171a97e90bab3`,
12reads/9749432B/17906points. The complete old public artifact is
739667B/SHA`1b26e797f385ae8f5906d584cda2680e6880383cb1ca282d8bb9e122e9929755`,
556reads/361619206B/325364points. Old inputs cause zero extra descriptor reads
or new proof fields.

The Sept28 complete whole artifact remains566151B/SHA
`e1e16caac9986c8d0441dbf1ab4f167aa1907f1d3534dfe61f12efe1fa304904`,
517reads/350684542B/289727points. Its historical362-file catalog is preserved;
the separate387-file complete input catalog SHA
`e8443ac0a2eb8d7b187e58a34feb17f190cdbf3cfe3fb990bc0412e952da9470`
does not relabel the old omission history.

The initial independent receipt's *summary only* mistakenly hashed these old
canonical values with an extra LF. Its runtime whole-equality assertions
already passed. The original2144B receipt is retained unchanged, and a separate
5784B artifact receipt records corrected physical lengths/hashes without a new
source-audit run. This is a harness measurement correction, not a product fix
or a rewritten oracle.

## Native source audit and limits

Independent artifact validation passed28 checks in2.594s: all890 native
48d Git files/182321627B, all891 temporary-input files, all224 consumed-source
hashes, the581 actual reads and their size/hash sum, old immutable artifacts,
and protected paths were checked against physical bytes and Git objects.

The actual repaired48d private provisional audit at
2026-10-25T19:41:45.999853Z completed in18.250s:
PARTIAL/no FAIL,581reads/369038838B/338929point charges/581opens/224hashes;
8events/9source occurrences/8positive units/619UNKNOWN/0Negative/0TRAIN credit.
Its audit SHA is
`d92ccf8f22df73bd98c5bc412437fcbc0df61606df0eed73c7dddcc12ad377cd`.
The preceding preparation was a separate context,14reads/7400394B/13565points;
it is not presented as one cumulative bounded run. The earlier cef provisional
17.063s run remains a separate historical execution.

The private input changes are exactly one temporary policy append and one
temporary family review. The tracked family final review is absent and the
tracked policy remains unchanged. **8/9 is not main registration.** This review
runs no TRAIN selector, fit or parent pipeline; it does not resolve real
software NEED_MORE_DATA blockers or establish a complete search denominator.
Unknown remains Unknown. Source availability is verified-now, never backdated;
research exposure does not become confirmation or prereveal authority.

The pure API requires a trusted read_ref postcondition: path, size and SHA
verify the actual returned bytes. Audit.ref provides that production boundary.
An arbitrary wrapper transforming returned bytes violates that dependency;
dictionary ownership neither authenticates a reader nor the source issuer.
Source/device/biological authentication, full completeness, science, selection,
fit, confirmation and production authority remain unestablished/false.

The current native890 snapshot is historical proof for48d, not the total at a
future merged HEAD. Existing97-ref code closure is not a validation of the new
code; subsequent merged closure (including the eventual100-ref union), frozen
cycle, exact Ubuntu/POSIX CI and registration are coordinator gates still ahead.
Generic other legacy namespaces and active filesystem races are not newly
certified by this closed-family review.

## Retained private receipts

Paths below are workspace-private under `.worktrees/`; none is committed here.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `august-family-independent-receipt-48d-20261026.json` | 2144 | `7000c831ecc383f453916c35467da4a592a05cf77204226165395c5450e6ecb6` |
| `august-family-independent-artifact-receipt-48d-20261026.json` | 5784 | `ed6a0dd602286d9201ea785efd9bc01b158945131e666a30002aa489b4601c61` |
| `august-family-independent-final-receipt-d60f669-20261026.json` | 6195 | `7f5525cc520bf3836c653f55f1a3c4821f77c23ec6a1ef1aa13a928a65b25c9b` |
| `august-family-repair-final-receipt-d60f669-20261026.json` | 4971 | `41ea1f9af55a9cf9688aee9b4d7bd211879e665952c26fbb7e78f64bfa303aa2` |
| `august-family-native-verification-48d06f628f09-20261026/full-verification-receipt.json` | 1026845 | `08dc15022f51780aa58a68383370b7e3cb1fe8a78e937140dc4a549a49b094f2` |
| `august-family-native-verification-48d06f628f09-20261026/summary.json` | 2992 | `3cb67308c42ea459a63c76fcf338a7fc8c516542471f686855272290533a1f74` |

The independent harness is17818B/SHA
`4b1279bb6eaa4601ae0477908348e156072ed73f95238ca7229b2b89f2a3221e`;
the artifact checker8871B/SHA
`93c2bd59855d8213a6149dd34a93ac6488e40f7e6cf0f62bf63688f900aeca67`.
The only authorized tracked independent change is this new review document.
