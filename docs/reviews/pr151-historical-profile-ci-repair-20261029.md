# PR151 historical-profile CI repair

Scope: software verification only; no source qualification, training, P0 issuance,
production activation, or private-data publication.

Exact original head: `1ce29e86a870a2771d13bc4774fcd10f720fec86`.
The Ubuntu [failed run](https://github.com/haji84/habuAI-private/actions/runs/40725267479)
executed 2050 tests: 2011 passed, 38 skipped, one failed. The sole failure was
`test_reviewed_v4_profile_never_reopens_implemented_capability`: it loaded the
moving HEAD (v5) while asserting the immutable reviewed v4 identity.

Repair the existing PR by loading the accepted v4 source as a readable code
fixture, following the existing v3 and Stage1 fixture pattern. The native LF
fixture is exactly the accepted main `386dfd52cd0b4d80e87897f8e5ccf544fff7e135`
`src/research_pdca_adapter.py`: 31947 bytes, SHA-256
`1892440621057125b40adfef09a583395a744e505a3cc5fff657fa0f2db2fcc9`.
Retain the hash guard and add a size guard. Do not replace the production v4
allowlist with v5, admit an unknown revision, or weaken the assertion that the
reviewed v4 capability is already implemented.

The local pre-edit suite reproduced one failure (16 tests, 2 platform skips,
86.164 seconds). After the fixture repair the same suite passed (16 tests,
14 actual passes, 2 platform skips, 87.954 seconds). A separate reviewer
verified the complete fixture against the accepted Git blob and ran the
repaired case successfully. These local results do not replace Ubuntu full
CI; exact-head CI and fresh-main checks remain required before acceptance.

A fresh independent whole-branch review found no critical/important issue and
approved software-only merge conditional on repaired exact-head CI. The reviewer
ran calibration36 PASS/76.401s, backend14 PASS/2 genuine POSIX skips/79.004s,
and the final size-guarded v4 case1 PASS/2.707s. It also verified all111
native current-cycle code/policy references against Git blobs. This is separate
from the root author's results above and grants no scientific authority.

The runtime code and current development-cycle manifest are unchanged by
this test repair. Historical failed CI remains linked above. Scientific
status remains NOT_VALIDATED and Master Goal #1642 remains NOT_COMPLETE.
