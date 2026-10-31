# Independent P0 read-only preflight review

Reviewed implementation927d6febea9774d398475139d5ee9ae384b07580 against accepted
main386dfd52cd0b4d80e87897f8e5ccf544fff7e135. No critical or important findings;
approved for bounded software scope, conditional on its own native Ubuntu CI.

The reviewer independently compared the extracted constants to baseline via
AST: values unchanged. Checker changes only its import. Registry retains
fcntl, live sandbox contexts, locks and production rejection; importing it
without POSIX locking still fails. No fabricated lock implementation or new
activation authority was introduced.

Fresh independent tests on native Windows: readiness6 PASS/0.146s;
observer31 PASS/1 actual symlink-privilege skip/10.032s; policy parity and
registry fail-closed controls PASS; diff-check PASS. Root's separate runs were
readiness6 PASS, observer31 PASS/1 skip, and official-request contracts3 PASS.
The new subprocess regression first failed with actual fcntl import/exit1,
then passed with the real read-only JSON/exit2 and an unchanged empty root.

The complete Git-native code closure111 plus policy was checked by the actual
check_codex_cycle CLI in a fresh code-only capsule. Code SHA256:
`5975433435726177b2c343c31d603efa66c8ba80326475f83012dbb222f7057a`;
cycle SHA256:
`d2e9fc5d5520468f4bb68aa0105b9ef32aa41b2ee37a00bb9d2655e7931ec717`.
Original cycles,109 prior execution records and source qualification hash
`0431de596af6ee96e3f2edf32d02ff24318ef9ca4938e3a2c4c60885292a1057`
remain preserved. A separate applied-state reviewer independently verified all
111 Git references plus policy, exactly114 code-only capsule files, raw cursor
identity, complete canonical CLI receipt equality, all109 historical execution
entries and other prior typed state fields. Both original PR151 failed-CI
receipt hashes/sizes match. No important findings; own CI/fresh remain pending.
This metadata review grants no science or production authority.

These results establish diagnostic portability and contract consistency.
Production/scientific readiness, real fits, eligible denominators, genuine
prospective P0 and field E2E remain BLOCKED/NOT_VALIDATED. Windows tests do
not substitute for genuine POSIX/full Ubuntu execution.
