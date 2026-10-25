# PR46 integration verification, 2026-10-25

This updates the existing Draft PR46, preserving its history and original head
`daf09612f4ffd2cd389b0011cb7c615eb49fef3d`. The branch clean-merged current main
`f1e8d2df8e11d20a0b71feff3366c8dd6eb482fc` at
`53472b7ed8b990a06a3133f4b9411a70384b5ff1`. Its base can now be main because the
strict PR32 API dependency is merged. PR33's producer and actual source evidence
remain separate work; source hashes/declarations do not become authenticated.

Reviewed source changes already existed before this integration:

- `c224d7f4d17fabf825fb582a6e2bd52a1a868ec2`: duplicate JSON and reparse-path
  refusal plus the common selection gate before legacy numeric fitting.
- `38ddc8f19e54153f58dcbaae1a2a35cd45da6245`: the selector optionally shares
  actual read/rescan bytes and an absolute deadline with the prospective reader.
- `9f4facb7ac12ee2fa7497a556b8504c0a0cc50da`: deadline checks before JSON parsing,
  during object-pair handling and around canonical work, following independent
  reproduction of a hash-to-parse expiry gap. No-context results are preserved.
- `a8392d39d9d281d5593a2362edd212310ee432f1`: existing candidate fitting requires
  a source-selected history with full accepted-row correspondence and strict
  cutoff binding. GPX passage alone cannot supply training labels. Numeric fitting
  remains research/development computation and does not confer official status.

The prior scoped search/complete-outcome gates are retained: UNKNOWN is not a
Negative; every Negative needs independent scoped source-bound receipts with
actual time/cell coverage, distinct basis byte identities and valid readiness.
Post-outcome predictor names and malformed source bindings fail closed. Direct
fitting cannot bypass the repaired selector by supplying its old history flags.

On the integrated source, 186 relevant native tests completed in 22.809 seconds:
184 PASS, two explicit POSIX-only symlink skips. Actual Windows junction tests ran.
Patterns: training corpus, development walk-forward, prospective spacetime,
legacy candidate, prospective inputs, G0 cycle contract/cursor/prewalk. The full
Windows suite was not rerun at coordinator direction; its previously named
environment failures remain in the source review/specification records. The new
exact-head Ubuntu run is required before merge, with all failures actionable.

Earlier main fb06f767 separately has fresh Ubuntu CI PASS: 688 tests, 16 platform
skips, current-cycle CLI and secret-file guard all successful in
[run40162267001](https://github.com/haji84/habuAI-private/actions/runs/40162267001).
This is base evidence, not the final PR46 result.

New immutable `20261025-pr46-02` freezes all 72 runtime Python/schema/dependency
references from Git index bytes. A separate native snapshot built exclusively
from those bytes passed the actual current-cycle CLI:

- cycle semantic SHA256: `e7c1851039c990aeccbd725643f6be8c5996cf3e1490dbe1e520cffb4ec6c1be`
- code SHA256: `c7d621ea000fd47f7083599c2bd63a2aa04f0adcc9910eab7223cc4728d82fa2`
- fit/production authority false; original G0 and all previous cycles unchanged.

The integration itself changes checkpoint/cycle/review metadata only. Raw,
ORIGINAL, Champion, existing policy, workflow permissions and dependencies are
unchanged. No actual qualified real-data rows or nights were fitted (0/0), no
sealed outcome was opened, and no official Stage1/100m performance is asserted.
Strict training-source contracts, mandatory parent request dispatch, source-bound
full-night materialization, independent confirmation and production authorization
remain separate obligations. Parent/coordinator owns final main merge.

PR100 was integrated first to preserve its independent full-ledger source. Its
exact head passed716Linux tests with16platform skips in run40162577266. Main
f1e8d2df fresh run40162945237 was still running when this checkpoint was written.
No PR46 runtime source changed after the186-test run; the merge adds the reviewed
full-ledger module and its tests. New source membership was re-frozen as72refs.
After that merge,57 full-ledger/G0 contract/cursor/prewalk tests passed in1.747s.
