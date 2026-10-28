# PR146 limited F1–F3 independent review

Source checkpoint `7402e429cd911ed9d6a003fb962bfecf46ba7a70`, parent `a0a0d8b4ac0c93e67eb14ad5c8308bfcc8d07645`. Root read the intake, runner and ownership delta plus author evidence, and independently executed the real synthetic-temp test files: 37 total, 30 actual PASS, seven Windows symlink privilege skips, zero failures/errors, 1.417 seconds. Actual junction cases executed. These skips require genuine POSIX CI; no facade or elevated privilege was used.

The original independent RED probe on a0a demonstrated deletion of an unowned regular temporary-path replacement. A separate immutable GREEN probe on7402 confirms original archive bytes retained, replacement marker retained and explicit TEMP_CLEANUP_RESIDUAL. The repair checks opened-handle dev/inode ownership before deleting a temporary and retains the first exception object. All four temporary cleanup sites have replacement/primary regression controls and normal-owned cleanup controls. No claim of atomic protection against hostile filesystem races is made.

Fixture text is explicitly synthetic; no conclusion is drawn that the prior literal was a proven disclosure. Receipt validation recomputes the existing records-only source identity, rejects extra/type/size/duplicate errors, and preserves correct original receipt compatibility. Descendant symlink/junction checks tighten the existing cooperative path guard.

**PASS_SCOPED_F1_F3_ONLY.** This is not acceptance of the complete runner or PR146. F4 bounded resource use, F5 read/parse/copy identity, F6 pre-engine idempotency with code/protocol identity and F7 child-failure evidence remain open. New composed freeze, exact Ubuntu CI and safe integration remain required. No actual private engine, source payload, GPX acquisition, network, fit or source qualification was exercised. Science remains NOT_VALIDATED; formal TRAIN/negative/search/fit are zero.

Independent probe artifacts: `pr146-root-temp-ownership-red-20261028.json`, `pr146-root-temp-ownership-green-20261028.json`. No PR146 push or main integration is authorized by this limited verdict alone.
