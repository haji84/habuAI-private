# Task7 second slice: fixed report-only persistence

This adds transport-observed persistence to the reviewed pure proposal ledger.
It does not admit an authorized root, attest clocks/source/recipes, execute a
reservation, migrate an existing used campaign or implement backend continuation.
No workflow, permission, credential, arbitrary shell or AI- changes are allowed.

The public API constructs the existing GitTransport with fixed origin internally.
The private transport seam exists only for explicit tests. Use its existing
bridge namespace, restricted further to
`reports/pdca/{night}/bridge/science/{root_command_id}/` and deterministic
`pdca/science-{root_command_id}`. Root report source stays fixed across later
scientific code versions. Empty bootstrap requires branch and base namespace
absence; later writes add exactly one semantic event under the same origin/base.

Canonical origin/state/event envelopes bind master-root identity, night, fixed
report source, original pure proposal, prefix proposal hashes and origin record.
All authorization flags stay false. Current state, full event history, immutable
raw record bytes, paths, regular-file modes and linear one-event commit history
are validated before writes. A non-force direct-parent Git commit atomically
publishes state plus the new event. Origin and prior events cannot be replaced.

After an ambiguous push, reconcile actual remote history. An exact already
published proposal prefix can receive TRANSPORT_ACK_ONLY, returning the latest
ledger/head/tip. It never proves the old reservation is still live or permits
execution. Divergence is a conflict; no branch reset, new attempt or budget reset.

Read at most34 fixed blobs, each<=1MiB before read/decode, with<=16MiB cumulative
actual blob bytes including rereads. Git metadata/fetch traffic is not that
counter and is not hard-preemptible by this helper. Existing transport limits
remain outer ceilings. Non-force sibling conflict protection is not server-side
exact-old-SHA CAS against external administrator deletion/rewind. Bot commit text
is audit metadata, not proof of Actions or controller authentication.

TDD covers canonical records and no authority natively. Actual GitTransport
bootstrap/append/restart, two writers, prefix ACK after expiry, ambiguous push,
unchanged report base across source updates, immutable tamper, foreign paths and
preexisting base namespace use temporary bare Git repositories on real POSIX CI.
The transport's unnecessary eager scientific-engine import is replaced by a
lazy call to the same actual engine. This permits real native Windows bare-Git
tests without a fcntl facade. Scientific/master execution still requires its
real supported environment and actual POSIX integration CI.
The same transport reads its already-resolved Git blob with `cat-file`, avoiding
Windows `git show commit:path` filename disambiguation limits. Existing mode and
size preflight remain unchanged; no checkout or raw source normalization occurs.
