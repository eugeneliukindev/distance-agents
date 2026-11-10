# Results

Agent: Claude Code 2.1.321, model `sonnet`, headless, isolated from user settings and memory. Rules: the current `AGENTS.md` (v2). 5 runs per task and condition, 245 valid runs, about $45. Date: 2026-11-10.

Conditions:
- **no rules**: the agent gets only the task;
- **placebo**: generic advice, "write clean, maintainable code" ([`placebo.md`](../placebo.md));
- **DISTANCE**: `AGENTS.md` appended to the system prompt;
- **without a letter**: `AGENTS.md` with all rules of one letter removed.

Runs where the agent itself failed (a usage limit hit once) are dropped; the report script skips them.

## Target rule kept, per task

Runs where the static checks found no new violation of the rule the task targets. All runs passed the hidden and regression tests in every condition.

| task | rules | no rules | placebo | DISTANCE |
|---|---|---|---|---|
| courier | I1, T2 | 0/5 | 0/5 | 5/5 |
| payment-email | I2, I1 | 0/5 | 0/5 | 5/5 |
| payment-methods | A1 | 0/5 | 0/5 | 5/5 |
| order-details | T1 | 0/5 | 0/5 | 5/5 |
| delivery-legacy | C3 | 0/5 | 5/5 | 4/5 |
| gold-discount | D3 | 0/5 | 0/5 | 2/5 |
| warehouse-reservation | A3 | 0/5 | 0/5 | 0/5 |
| revenue-report | D4 | 5/5 | 5/5 | 0/5 |
| address | T1 | 5/5 | 5/5 | 5/5 |
| free-shipping | S1 | 5/5 | 5/5 | 5/5 |
| cancel-order | S2 | 5/5 | 5/5 | 5/5 |
| refunds | A2 | 5/5 | 5/5 | 5/5 |
| promo-code | I2, N1 | 5/5 | 5/5 | 5/5 |
| order-export | N1, I2 | 5/5 | 5/5 | 5/5 |

## Which letter does the work

| task | letter removed | DISTANCE | DISTANCE without the letter |
|---|---|---|---|
| payment-methods | A | 5/5 | 0/5 |
| delivery-legacy | C | 4/5 | 0/5 |
| order-details | T | 5/5 | 2/5 |
| courier | I | 5/5 | 4/5 |
| payment-email | I | 5/5 | 5/5 |

## Checked on every task

| condition | runs | tests pass | mocks in tests (C2) | magic numbers (E1) | mean cost, $ | mean lines added |
|---|---|---|---|---|---|---|
| no rules | 70 | 70/70 | 17/70 | 32/70 | 0.16 | 54 |
| placebo | 70 | 70/70 | 17/70 | 25/70 | 0.16 | 55 |
| DISTANCE | 70 | 70/70 | 2/70 | 4/70 | 0.19 | 70 |

## Follow-up on payment-methods: add gift cards on top of the agent's own result

| condition | rule kept | business files touched |
|---|---|---|
| no rules | 0/5 | 2.0 |
| placebo | 0/5 | 2.0 |
| DISTANCE | 5/5 | 1.4 |

## What this shows

**Work, and generic advice does not:**
- **I1, T2** (courier, payment-email): new integrations go into adapters instead of `Checkout`.
- **A1** (payment-methods): one `pay(order_id, method)` and an implementation per method instead of `pay_by_cash`, `pay_by_sbp`. Without the A rules: 0/5.
- **T1** (order-details): the handler parses the request; without the T rules: 2/5.
- **C2**: mocks in tests drop from 17/70 to 2/70.
- **E1**: magic numbers in business logic drop from 32/70 to 4/70.

**Work, but so does generic advice:** C3 (delivery-legacy). The placebo also says "add tests", which is enough; without the C rules DISTANCE drops to 0/5.

**Partly:** D3 (gold-discount), 2/5. The agent adds a method but still reaches it through `customer.profile.loyalty`.

**Do not work:** A3 (warehouse-reservation), 0/5 everywhere. The starter already has a client that inherits from `JsonApiClient`, and the agent copies it, as it did with A1 before rules v2.

**Hurts:** D4 (revenue-report). With rules the agent extracts the report into its own class, which is good, but gives it the whole 7-method `OrderStore`. Without rules it adds a method to `Checkout`, which this check cannot see as a violation, so this row compares unlike things; still, D4 as written does not lead to a narrow interface.

**Redundant in the rules:** removing the I letter barely changes courier and payment-email: the definition of "adapter" in the terms section and T2 carry the same idea.

**Traps too weak:** S1, S2, A2, N1, and T1 in `address`: the agent does not make the mistake even without rules.

**Cost:** with DISTANCE about 20% more per run and 30% more lines.

## Rules v3 and held-out tasks

Rules v3 rewrote D3, D4 and A3 after the results above (commit before any held-out result was seen). Then six new tasks the rules had never been tuned on were written and run in all three conditions.

**Rules v3 on the tasks above** (DISTANCE column, v2 -> v3): gold-discount D3 2/5 -> 5/5, warehouse-reservation A3 0/5 -> 5/5, revenue-report D4 0/5 -> 3/5, delivery-legacy C3 4/5 -> 3/5, every other task unchanged at 5/5. 70/70 runs passed the tests.

**Held-out tasks** (rules v3):

| task | rules | no rules | placebo | DISTANCE |
|---|---|---|---|---|
| fiscal-receipt | I1, T2 | 0/5 | 0/5 | 5/5 |
| customer-repository | A3 | 0/5 | 0/5 | 5/5 |
| delivery-options | A1 | 0/5 | 0/5 | 4/5 |
| delivery-zone | D3 | 0/5 | 0/5 | 4/5 |
| customer-profile | T1 | 3/5 | 4/5 | 4/5 |
| customer-stats | D4 | 5/5 | 5/5 | 4/5 |

Magic numbers in business logic (E1): 10/30 runs without rules, 10/30 with the placebo, 0/30 with DISTANCE. Tests passed in all runs except 2 baseline runs of delivery-zone.

**What this adds:** A1, A3, D3, I1 and T2 carry over to tasks the rules were not tuned on. The held-out T1 and D4 traps are too easy to tell the conditions apart, and the D4 check cannot see a report added as a method of `Checkout`.

## Not covered yet

- Letters without a task: D1, D2, I3, I4, E2, E3. Some need an LLM judge rather than a static check.
- A second model or agent.

## Limits

- One agent, one model, five runs per cell: a pilot, not a verdict.
- Static checks see structure, not intent. False positives found by reading patches were fixed and covered by `bench/test_checks.py`; every task was validated against a correct and a broken solution with `bench/validate_task.py`.
- The first pilot, on a starter that already followed the rules, showed no difference between conditions: the agent mirrored the clean code.
