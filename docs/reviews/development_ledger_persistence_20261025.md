# Fixed scientific-ledger report persistence

Coordinator implementation; independent exact-source review and Ubuntu CI are
required separately. This is transport-observed persistence only, never trusted
root admission, live reservation permission or automatic backend continuation.

The approved fixed branch and bridge/science paths reuse the existing report
transport without widening its allowlist, changing credentials/permissions or
touching Raw/ORIGINAL. Bootstrap rejects an existing branch or base namespace;
updates require the same origin/fixed report base and one appended semantic event.
Whole semantic history, exact immutable canonical bytes, regular-file modes,
paths and each linear commit's state/event delta are checked. Later scientific
source commits do not change the report branch's base.

Actual already-published prefixes receive only TRANSPORT_ACK_ONLY with the latest
ledger/head/tip; this includes an expired latest reservation and cannot authorize
the stale caller to execute. Divergent history never creates another attempt or
resets allowance. Individual blobs are sized before materialization, with1MiB
perblob and16MiB cumulative actual blob bytes, including rereads. Git metadata,
network and subprocess work are explicitly outside that byte/deadline guarantee.
Nonforce direct-parent writes reject competing append-only siblings; this is not
server-side exact-head CAS against external administrator ref deletion/rewind.
Commit author text is not controller/Actions authentication.

TDD first produced four missing-builder failures and six explicitly unexecuted
Windows transport skips. A separate import regression then demonstrated that
the existing pure Git transport unnecessarily imported the scientific locking
engine. Its same-name lazy wrapper now calls the actual original engine only
for scientific operations; no fcntl facade or locking change was made. Native
Git tests were enabled, and four exposed Windows git-show commit:path length
errors. Reading the already-resolved immutable blob using cat-file fixed that
specific transport issue without changing prior mode/size checks or raw bytes.

Final native Windows command ran35tests successfully in61.350seconds with no
skips: original17accounting tests,15publisher tests including ten real temporary
bare-Git scenarios, and three existing connector-handoff tests. Real scenarios
cover bootstrap/append/restart, stale writers, a native sibling push interleaved
after preparation, lost response after an actual successful push, prefix retry
after EXPIRE, immutable whitespace tamper, foreign report changes, blob-size
rejection before payload access, preserved report base across actual source
updates and rejection of preexisting base campaign data. Each repository is
synthetic and local; no GitHub root campaign or genuine scientific fit was made.
A subsequent metadata-path bound has its own pre-payload regression and targeted
recheck. Independent review/final exact Linux/fresh-main receipts remain pending.

Actual owner/command/repository/root admission, authentic source/recipe/clock
history, existing-campaign migration, trusted overrun enforcement, implementation
job budgets, typed development results, supervised continuation and automatic
wake-up remain unimplemented. All execution/science/selection/production flags
remain false. A persisted zero-event record is not permission to initialize an
existing already-consumed scientific campaign at zero.

## Independent review

Independent source and actual native-Git review: **PASS**, with no blocking
finding, for exact source commit `b97e4b5ace0680973323ba1e0dfe87b26b827070`.
This covers fixed report persistence mechanics, not authenticated root admission,
scientific execution, live lease permission or backend continuation.

Canonical Git blobs were extracted with `core.autocrlf=false`; the corresponding
working files differ only by Windows newline conversion. Both source modules
and the new test parse successfully. SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `src/development_handoff.py` | `2f7b539fb58ad9595a4ae0a7f83c82be272d717ac77f8dee82dbdb23d2ebd524` |
| `src/pdca_bridge.py` | `d589d22ed6afc8ebc8adc2eade4bd44d55ead53aa048d17dc11b3e86af1693c1` |
| `tests/test_development_ledger_persistence.py` | `a9cca46107b3803509579c8070f34b3315f430b8770a2fe754aeb5abd610cfd9` |

The reviewer reran all 16 committed publisher tests: 16/16 pass in 62.924s,
including ten actual temporary bare-Git cases. The original pure accounting
and existing connector handoff suites also pass: 20/20 in 0.070s. No skips or
`fcntl` facade were used. The reviewer additionally wrote an independent
public-API harness using one real temporary bare origin and two separate real
checkouts. Its twelve native-Git cases passed in two fresh-process commands:
10/10 in 69.270s, then two additional mode/history controls in 6.736s.
These local repositories contain only synthetic data; nothing was published
to GitHub, no actual root campaign was initialized and no model was fitted.

Independent controls cover bootstrap, RESERVE/SETTLE, restart from the second
checkout, and exact actual-blob counters and hashes. A sibling writer was
interleaved immediately before the losing writer's real push; its commit won
and the losing call did not merge, reset or silently append another event.
A successful native push followed by a synthetic lost response was reconciled
without another commit. Retrying an old reserved prefix after EXPIRE returns
the latest expired proposal and tip, with execution authority still false.
Wrong expected tips are rejected.

A distinct adversarial history has a completely canonical current state and
correct immutable current event files, but its earlier Git commit contains a
different valid proposal state. The publisher rejects that historical mismatch.
It also rejects two valid semantic events placed in one Git commit, a whitespace
rewrite of immutable origin bytes, a foreign campaign path and an executable
file mode. The executable-mode and oversized-blob controls assert that no
offending payload is materialized before rejection. Divergent remote branches
remain unchanged rather than being repaired or reset.

An actual source-code commit update can appear in a new reservation's source
field without changing the report origin's pinned base. Attempting to advance
that report base is rejected. A base already containing the campaign namespace
cannot bootstrap another zero-event report. The public signature rejects
remote, transport, trusted-facts and execution-authority switches; the factory
constructs the real fixed-origin transport.

Source review confirms regular nonexecutable modes, the exact fixed path set,
full semantic replay and every direct-parent bootstrap/event delta. Canonical
origin-record digest, semantic event/tip/proposal hashes and physical blob
hashes are distinct identities. In particular, `origin_record_sha256` is the
canonical record digest without its trailing LF; `blob_reads` records the
physical committed-byte SHA. Immutable raw bytes are compared separately.
The limit is 34 distinct campaign paths, not 34 total historical reads. All
materialized blob reads, including historical prefix states, are preflighted
at 1 MiB per blob and charged against the shared 16 MiB read allowance.
Git metadata, fetch traffic and subprocess work are outside that byte guarantee.

The `pdca_bridge` diff preserves the same-name scientific identity function
through a lazy call to the actual engine. It does not replace locks or emulate
POSIX behavior. The actual Git transport imports and runs on Windows; the
scientific engine still needs its real supported environment. The existing
resolved-blob mode/size checks precede `cat-file blob`; committed payload bytes
remain unnormalized. Exact-head Ubuntu regression CI remains required for
the real POSIX scientific/master paths affected by import timing.

All stored pure proposals remain `UNPUBLISHED_PROPOSAL` with false execution,
science, selection and production flags. Receipts are only transport
observations. Non-force direct-parent writes protect competing append-only
siblings; they are not server-side exact-old-SHA CAS against administrator
ref deletion/rewind. Bot author text is not authenticated Actions/controller
identity. Existing campaign migration, owner/command/repository/source admission,
trusted clocks/runtime accounting, job control and unattended wake-up remain
unimplemented. None is inferred from a successful report push.

The external harness `science-publisher-independent-probes-20261025.py` has SHA
`713429a2b0f66e51cc8c0be71c46258a59dc4865f63ccafea8fe957d84b83da2`.
The reviewer changed only this Independent review section. Source, tests,
workflow, permissions, credentials, Raw, ORIGINAL and shared state were not
edited. Coordinator-owned plan wording remains outside this review commit.
