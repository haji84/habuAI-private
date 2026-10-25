# Development job accounting implementation evidence

Independent design review approved a focused pure module followed by a separate
fixed Git report module. It required stable root+capability accounting, paused
CI without an active worker lease, explicit late overrun and preserved original
scientific/request semantics. Root implements the slice inline.

TDD began with11 new tests failing on the missing module/API. The first pure
implementation passed11/11 in0.201s. A further declared request-window test
failed before the START observation/expiry guard was added;12/12 then passed.
Additional tests cover terminal incidents while another attempt waits for CI,
extreme-year lease arithmetic and strict false-versus-zero authority fields.
The15 new pure tests plus32 original handoff tests pass47/47 in0.258s without
skips. Original request/science/transport source files are unmodified.

This phase has no Git publisher or durable job completion claim yet. It is
replayable unauthenticated accounting only. Full runtime/worker hard-stop/root
admission/result verification/controller/continuation remain unimplemented.
Known overrun is stored at its full bounded value and blocks the job; it does
not permit extra science or implementation. Actual scientific fit rows remain0.

Independent exact-source review is required before the fixed report layer.
