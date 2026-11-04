# Task8 pure production trust foundations, 2026-11-04 JST

This bounded change implements two prerequisites of the existing Task8 design. It does not complete Task8 or the Master Goal, and it does not enable any production model. Actual approved PR136 integration/fresh-main evidence is recorded separately in `main-9ad62594-verification-20261104.md`.

## Supplied exact-fact consistency

`production_verification.verify_exact_facts(facts, *, intent, policy, max_seconds=1.0)` validates bounded built-in JSON and compares repository/task/PR revisions, commit/tree/closure mappings, complete relevant collections, exact workflow definition/run/attempt/event, actual required job checkouts/steps and effective independent reviews. Merge, squash and rebase content mapping are distinct. The direct-run contract does not require an unrelated exhaustive Actions-history scan.

Returns CONSISTENT_NOT_AUTHENTICATED, BLOCKED or FAIL. Every result retains source authentication NOT_ATTESTED_BY_PURE_VALIDATOR, scientific reproduction NOT_REPRODUCED, production_authorized=false and official_issuance_authorized=false. A coherent invented document can pass consistency; this function cannot authenticate that document, attest a clock or reproduce science. Fresh authenticated connector acquisition/normalization belongs to the fixed authorized controller and remains unimplemented.

Initial local source commit `ee2dfce964e9d2cc8054de36c7836d2c87a416aa`:42 author tests and42 independent tests passed. Independent external controls made1,183 scalar replacements:1,033 FAIL,147 BLOCKED, and3 unchanged-value replacements CONSISTENT_NOT_AUTHENTICATED. All retained false authority. Custom metaclass probes executed zero callbacks; oversized strings were rejected before secondary large encoding allocations. Both defects were reproduced and repaired before acceptance.

| Evidence | SHA256 |
|---|---|
| Exact-facts source | `ff291efeeb391f1c9c8b18de4d8209b502d6ab2652505d1fa57b3aa349d97ad4` |
| Exact-facts tests | `534fff9b59d1bc930f801061467d804b6244f61130a29b89de0ad16128be0e6a` |
| Initial author execution receipt (historical) | `2249a76fbaf9ff21f959235e1ca7cfe7a40d44dccfb42e68e455efe16762450d` |
| Initial independent scoped review (before subsequent finding) | `8f5dacf3cedea4918b622e30c2e11bbd38934265159eac853940c0a08e90bc07` |
| Optional-job repair execution receipt | `2930c043c53e8a780fd9c4b698d871d4fa442da72ea6df3cde6112c785094333` |
| Optional-job exact repair independent review | `295de4808bded7c27a86dfa5608b0c7509642343fc7c741dcba3b7ade82ea9c8` |

A subsequent independent review reproduced malformed optional-job facts passing the initial checker. Local repair commit `d93c36950690e77862cc7cb98c84663367d0db5a` validates all supplied job/step/checkout shapes while requiring success only for policy-required jobs/steps. Ten RED failures were observed before46 tests passed. A different reviewer independently ran46 tests plus63 controls, including valid optional failure/skipped/cancelled/neutral and distinct valid optional checkout. No important finding remained; the earlier review is preserved as historical evidence, not inherited approval for the repair.

Whole-branch review then reproduced two terminal hierarchy contradictions: a completed run could contain a nonterminal optional job, and a completed job could contain an extra nonterminal step. Local commit `367f8ac5b1de55bfcb3f5935c8f585c24077f468` adds four guard lines. Six RED cases were observed before48 tests passed; independent48 tests and36 external controls passed with valid optional terminal outcomes preserved. Writer receipt `679db5fe5fe694b8b86d139246a50c268c708a4ecb380d85d6b67b3c1eee665d`; final source review `368948dd8e9fcc68e205268d590d5bf1783530686a84b0b32582f3fdfb06b865`. The preliminary131-test/cycle124-01 checkpoint and HOLD review remain historical; current acceptance uses133 tests/cycle124-02.

## Unpublished transition construction

`production_registry.prepare_transition_proposal(predecessor, intent, *, policy, expected_ref_sha, expected_previous_event_sha256, max_seconds=1.0)` constructs an inert canonical proposal-record addition and pointer-update descriptor. The addition explicitly requires the path to be absent. Its commit specification has exactly the observed existing predecessor as sole parent. Missing predecessor/pointer prerequisites BLOCK; supplied contradictions FAIL. No genesis/ref selection, active-model pointer bytes, trusted ActivationEvent/time, transport, local/remote write or production context is provided.

The policy and predecessor inventory are supplied declarations, not authenticated or independently complete facts. Collision checks apply to that supplied inventory. A future authorized writer must fetch/validate actual complete state and enforce all preconditions. Sibling specifications illustrate the required direct-parent construction; no remote CAS or race acceptance is claimed by this pure library.

Local source commit `94cf8cd9eec18e7290a847bc460213d76b1c5320`:19 new +32 related tests passed. Independent reviews ran19 tests/437 external invocations (including350 scalar mutations and28 custom-type placements) and51 tests/245 scalar mutations. All retained false authority; callback probes ran zero custom callbacks.

| Registry evidence | SHA256 |
|---|---|
| Source | `817b67755514723df1d8ed78e28c121899626b2e804f878379ca34ab8a3398eb` |
| Tests | `8358d89d59563aac79542738e1e40b318dd1c2d51443b194db909c1993ea1c2e` |
| Author receipt | `2261f3477595f930389c7658407dacee0a82a54332da3bc55dbecf03aa90d49b` |
| Independent review1 | `25b8bf1879356e68d6e8d7623c51460d8e2a03a0ed2e9a31c340d2f04c1a1512` |
| Independent review2 | `d1df2d349a50e546a8477645e25440ceba592b9d51aac03a559a7f5bbb2b2542` |

## Integrated source and Freeze

The combined reviewed source at local commit `a5d1df9` passed133 targeted tests with0 skips/failures/errors. This includes67 new tests; it is not a full-suite claim. Actual verbose log SHA `79b4dccf04a4d128dc0307514fb608d1c7614932d058b5f32a2faa25d8565eb9`; execution receipt `90f55f6bbcfaac49d46c850a33eefc37854e52fc92b76042e42ef86f9a33d98d`.

New immutable development cycle124-02 covers124 code +1 policy=125 inputs: code `7758aaeabc36630ceed21f6b39bee4ff0ed0e9d4b7e36a79b7b7ca8b109c1803`, canonical cycle `aa5dcf071470adc6e538e05aaa1781fbf4b024c236448ec6d2c49b3d38c09208`, manifest bytes `e7da580a87076b47dd69dd7b36b3ae213034c28fc73ce66c7097224259e7f816`, cursor bytes `70b11352f06e7d7c3a6e4dd43bffd8703fbc785b58ca3a2939257d1220dfeed0`. Its validation grants no scientific fit or production authority. Source and protected-history audit must be finalized before publication.

All13 existing open PRs were checked by changed-file scope (299 filenames, every page shorter than100); no overlap with the new production paths was found. This is a path audit, not a semantic equivalence proof. Receipt `579137a3e7f07accc553d7603ceab3a56fc9b643a040f1f015565fc75d78e303`. One distinct foundation Draft PR is appropriate; no existing source/data PR is co-merged.

## Remaining completion gates

- IMPLEMENTATION_BLOCKED: authenticated controller fact acquisition/normalization, substantive raw-evidence scientific reproduction, remote state publication/CAS/ambiguous-ack handling, compatible model loading, registered composite/output/route executors and formal P0 publication remain unimplemented.
- DATA_BLOCKED / NOT_VALIDATED: genuine qualified corpus/manifests, independent search and complete outcome scopes, ex-ante input/universe availability, untouched confirmation/cross-year evaluation and formal KPI evidence remain insufficient. Retained environmental backfill is available with its stated support/unknowns; source processing alone does not qualify training labels.
- AUTHORITY_BLOCKED: actual registry genesis/enabling, production activation/Champion and later main integration require their applicable explicit authority. PR136-specific approval did not grant those actions.
- FIELD_E2E_NOT_COMPLETED: no trusted future formal P0 followed by actual exploration, GPX/log reconciliation, 1km Top10/100m±10min formal scoring and future Champion acceptance was demonstrated. No departure time or earlier ORIGINAL is reconstructed.

Actual fitted rows0, new models0, full qualified total null, improvement NOT_EVALUATED. No new GPS originals, precise capture locations or private logs are included. Raw/ORIGINAL/model/tally bytes and older development cycles must remain unchanged.

This is a dated source/test checkpoint. The eventual feature PR's exact-head CI must be read from the [Master's current verification record](https://github.com/haji84/AI-/issues/1642#issuecomment-6618423329); successful main9ad CI is not inherited by new code.
