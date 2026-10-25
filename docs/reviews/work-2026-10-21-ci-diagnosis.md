## Work audit: confirmed hosted-runner billing block (2026-10-21 work date)

Authenticated GitHub UI now provides the missing account-visible evidence.

1. Exact job annotation on run [39575012103](https://github.com/haji84/habuAI-private/actions/runs/39575012103/job/119138261078), head `415837c3713a167794149770f1228190fa158fe6`:
   > The job was not started because recent account payments have failed or your spending limit needs to be increased. Please check the 'Billing & plans' section in your settings

2. [Account billing overview](https://github.com/settings/billing): GitHub Free; Actions minutes **2,000 min used / 2,000 min included**. Actions billable usage **$0** after included discounts. Storage 0.1 GB / 0.5 GB. The page reports included limits reset in 11 days.
3. [Budgets and alerts](https://github.com/settings/billing/budgets): account-wide **Actions budget $0.00 / $0.00, Usage blocked**.

**Confirmed diagnosis:** included hosted-runner allowance is exhausted and the account's zero-dollar Actions budget blocks additional usage. The generic annotation mentions payment failure as an alternative; payment failure itself was NOT established and is NOT needed to explain this observed block.

**No changes made** to budgets, payment methods, plan, runner permissions, workflows or repository visibility. No repeated reruns while the confirmed account gate is unchanged. Issue remains OPEN, CI is NOT restored, and pending PRs must not merge.

Human Gate is now concrete: waiting for included allowance reset needs no budget change; enabling paid hosted-runner use requires the owner's explicit cost/budget authorization. Read-only diagnosis and local implementation/review/data audit continue independently. After the gate is cleared, rerun exact final PR heads and a separate real poller/bridge smoke test; unit-test success alone does not establish poller recovery.

