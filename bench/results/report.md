# Results

Agent: Claude Code 2.1.321, model `sonnet`, headless, isolated from user settings and memory. 5 runs per task and condition. Date: 2026-11-10.

- **rules v1**: the first `AGENTS.md`.
- **rules v2**: the current `AGENTS.md`. Two sentences were added after v1 was measured: I1 says existing infrastructure calls in business code are not a pattern to copy, and A1 forbids a method per variant in a use case.

## Rules kept

Runs where the static checks found no new violation of the rules the task targets.

| task | rules | baseline | placebo | distance (rules v1) | distance (rules v2) |
|---|---|---|---|---|---|
| courier | I1, T2 | 0/5 | 0/5 | 5/5 | 5/5 |
| payment-methods | A1 | 0/5 | 0/5 | 1/5 | 5/5 |
| address | T1 | 5/5 | 5/5 | 5/5 | 5/5 |
| promo-code | I2, N1 | 5/5 | 5/5 | 5/5 | 5/5 |

## Follow-up: add gift cards on top of the agent's own payment-methods result

| condition | rules kept | business files touched |
|---|---|---|
| baseline | 0/5 | 2.0 |
| placebo | 0/5 | 2.0 |
| distance (rules v1) | 1/5 | 2.0 |
| distance (rules v2) | 5/5 | 1.4 |

## Correctness and cost, all four tasks

| condition | tests pass | mean cost, $ | mean lines added |
|---|---|---|---|
| baseline | 20/20 | 0.18 | 61 |
| placebo | 20/20 | 0.18 | 63 |
| distance (rules v1) | 20/20 | 0.19 | 82 |
| distance (rules v2) | 20/20 | 0.20 | 89 |

## What this shows

- **The rules change the design where the easy path breaks them.** Without rules the agent copies the starter: it calls the courier and SBP APIs from `Checkout` and adds `pay_by_cash` and `pay_by_sbp`. With rules v2 it puts each integration in its own adapter and adds one `pay(order_id, method)` with an implementation per method.
- **Generic advice does nothing.** The placebo ("write clean, maintainable code") matches the baseline on every task.
- **Wording matters.** Rules v1 already fixed the courier task but not payment methods: the agent followed the surrounding code. Saying explicitly that existing infrastructure calls are not a pattern, and naming the "method per variant" mistake, moved payment methods from 1/5 to 5/5.
- **No correctness cost.** Every run passed the hidden and regression tests.
- **Some size cost.** Runs with rules add about 45% more lines and cost about 10% more. Part of it is moving existing card code into an implementation.
- **Two traps are too weak.** `address` and `promo-code` show no difference: the agent does not pass raw dicts inward or over-engineer one promo code even without rules. They need harder versions.

## Limits

- One agent, one model, five runs per cell: a pilot, not a verdict.
- Rules v2 was written after looking at v1 results on the same task, and then measured on the same tasks. A held-out set of tasks is needed to rule out fitting the rules to the benchmark.
- Static checks see structure, not intent. Two false positives were found by reading patches and fixed (`bench/test_checks.py` covers them); results were regraded with `bench/regrade.py`.
- The first pilot, on a starter that already followed the rules, showed no difference between conditions: the agent mirrored the clean code.
