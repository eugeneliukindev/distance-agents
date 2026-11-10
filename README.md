# distance-agents

[DISTANCE](https://github.com/eugeneliukindev/DISTANCE) design rules for coding agents, and a benchmark that checks whether they change what agents write.

## Use the rules

Copy [`AGENTS.md`](AGENTS.md) into your repository root. Agents that read `AGENTS.md` pick it up as is; for Claude Code, save it as `CLAUDE.md` or add `@AGENTS.md` to your `CLAUDE.md`.

The file is short on purpose: studies of context files found that long or generated instructions add cost and can lower success rates, while short human-written ones help a little. Every rule is meant to be checkable.

## Results so far

Claude Code (`sonnet`), 5 runs per cell, about 400 runs. Details, the letter ablation and limits are in [`bench/results/report.md`](bench/results/report.md).

Held-out tasks, written after the rules were fixed (rules v3):

| rule | no rules | generic "clean code" advice | DISTANCE |
|---|---|---|---|
| I1, T2: integrations in adapters (fiscal-receipt) | 0/5 | 0/5 | 5/5 |
| A3: composition over inheritance (customer-repository) | 0/5 | 0/5 | 5/5 |
| A1: a new variant is an implementation (delivery-options) | 0/5 | 0/5 | 4/5 |
| D3: no chains through other objects (delivery-zone) | 0/5 | 0/5 | 4/5 |
| E1: no magic numbers in business logic (all six tasks) | 20/30 | 20/30 | 30/30 |

On the original tasks the same rules also fix T1 (0/5 -> 5/5), C2 mocks in tests (53/70 -> 68/70) and C3 pinning tests (0/5 -> 3-4/5). All runs passed the tests. With DISTANCE a run costs about 20% more. Traps that are still too easy to tell the conditions apart: S1, S2, A2, N1, and the D4 and held-out T1 tasks.

## How the benchmark works

The question: does an agent with the DISTANCE rules keep them better than the same agent without them, without breaking functionality or costing much more?

- **The starter code is ordinary, not exemplary.** `bench/shop` is a small shop where the `Checkout` use case talks to SQLite and the acquiring API directly, with no interfaces or adapters to copy. A first pilot on a clean starter showed no difference between conditions: the agent simply mirrored the clean patterns it saw.
- **Tasks are traps.** Each task is an ordinary feature request, where the easy solution breaks a specific rule:

  | Task | Easy mistake | Rules |
  |---|---|---|
  | `payment-methods` | `if method == "cash"` inside business logic | A1 |
  | `courier` | business logic calls the HTTP client and checks status codes | I1, T2 |
  | `address` | raw request dict passed into business logic | T1 |
  | `promo-code` | interface, registry or strategy for one fixed code (reverse trap) | I2, N1 |

  14 tasks in total, one or more per rule from S1 to C3; see `bench/tasks/*/task.toml`.

- **Three conditions.** `baseline` runs the agent with no rules; `placebo` appends generic "write clean code" advice ([`bench/placebo.md`](bench/placebo.md)), to separate the effect of DISTANCE from the effect of any instructions; `distance` appends `AGENTS.md` to its system prompt. The agent runs isolated from user settings, memory and MCP servers, so the baseline really has no rules.
- **Correctness first.** Hidden tests talk to the app only through HTTP-like requests, so they accept any internal design. A run counts only if both the task tests and the regression tests pass.
- **Rules are checked statically, against the starter.** `bench/checks.py` parses the result with `ast` and counts only findings that were not in the starter already. It flags in business logic: infrastructure imports (I1), strings only an adapter or handler should know, like an API path or a raw request key (I1, T1), raw keys and dict parameters (T1), library errors and status codes (T2), methods named after a variant like `pay_by_cash` and checks like `if self._sbp is None` (A1); outside handlers: branches and dispatch tables on a variant name (A1); anywhere: interfaces with fewer than two implementations (I2).
- **Follow-up changes measure maintainability.** `payment-methods` gets a second request on top of the agent's own result: add gift cards. The report counts how many business logic files that change had to touch.
- **Cost and size.** Every run records cost, turns, time and lines added, so over-engineering shows up too.
- **Repeats.** Agent runs are noisy, so every task runs several times per condition.

## Run it

Needs Python 3.11+ and [Claude Code](https://docs.claude.com/en/docs/claude-code). No other dependencies.

```bash
python3 -m unittest discover -s bench -p "test_checks.py"            # self-check of the static checks
python3 -m unittest discover -s bench -p "test_run.py"               # self-check of the ablation conditions
python3 bench/run.py --runs 5                                         # all tasks and conditions, 5 runs each
python3 bench/validate_task.py <task>                                 # a task is a fair trap: correct and broken solutions
python3 bench/run.py --tasks courier --conditions distance minus-I    # ablation: rules without one letter
python3 bench/report.py                                               # summary tables
```

`CLAUDE_BIN` sets the path to the `claude` binary, `--model` the model. Raw results go to `bench/results/runs.jsonl`, every diff to `bench/results/patches/`.

## Add a task

Create `bench/tasks/<name>/` with:

- `task.md`: the request, written the way a user would ask, without hints about the rules;
- `test_hidden.py`: tests through `_bench.support` (`make_app`, `call`, `FakeService`);
- `task.toml`: `letters` the task targets, `variants` names for A1, `markers` (strings business logic must not contain) and optionally `followup = true` with `followup.md` and `test_followup.py`.

## Limits

- Static checks see structure, not intent; read the patches before drawing conclusions.
- A handful of tasks and one agent is a pilot, not a verdict. Results are per model and per agent version.
- Rules go in through the system prompt, not a file in the repository, so the agent cannot skip reading them.
