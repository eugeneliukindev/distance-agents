# distance-agents

[DISTANCE](https://github.com/eugeneliukindev/DISTANCE) design rules for coding agents, and a benchmark that checks whether they change what agents write.

## Use the rules

Copy [`AGENTS.md`](AGENTS.md) into your repository root. Agents that read `AGENTS.md` pick it up as is; for Claude Code, save it as `CLAUDE.md` or add `@AGENTS.md` to your `CLAUDE.md`.

The file is short on purpose: studies of context files found that long or generated instructions add cost and can lower success rates, while short human-written ones help a little. Every rule is meant to be checkable.

## How the benchmark works

The question: does an agent with the DISTANCE rules keep them better than the same agent without them, without breaking functionality or costing much more?

- **Tasks are traps.** Each task is an ordinary feature request on a small shop codebase (`bench/shop`), where the easy solution breaks a specific rule:

  | Task | Easy mistake | Rules |
  |---|---|---|
  | `payment-methods` | `if method == "cash"` inside business logic | A1 |
  | `courier` | business logic calls the HTTP client and checks status codes | I1, T2 |
  | `address` | raw request dict passed into business logic | T1 |
  | `promo-code` | interface, registry or strategy for one fixed code (reverse trap) | I2, N1 |

- **Three conditions.** `baseline` runs the agent with no rules; `placebo` appends generic "write clean code" advice ([`bench/placebo.md`](bench/placebo.md)), to separate the effect of DISTANCE from the effect of any instructions; `distance` appends `AGENTS.md` to its system prompt. The agent runs isolated from user settings, memory and MCP servers, so the baseline really has no rules.
- **Correctness first.** Hidden tests talk to the app only through HTTP-like requests, so they accept any internal design. A run counts only if both the task tests and the regression tests pass.
- **Rules are checked statically.** `bench/checks.py` parses the result with `ast` and flags: infrastructure imports in business logic (I1), raw keys and dict parameters in business logic (T1), library errors and status codes in business logic (T2), branches and dispatch tables on a variant name outside handlers (A1), new interfaces with fewer than two implementations (I2).
- **Cost and size.** Every run records cost, turns, time and lines added, so over-engineering shows up too.
- **Repeats.** Agent runs are noisy, so every task runs several times per condition.

## Run it

Needs Python 3.11+ and [Claude Code](https://docs.claude.com/en/docs/claude-code). No other dependencies.

```bash
python3 -m unittest discover -s bench -p "test_checks.py"            # self-check of the static checks
python3 bench/run.py --runs 5                                         # all tasks and conditions, 5 runs each
python3 bench/report.py > bench/results/report.md                     # summary table
```

`CLAUDE_BIN` sets the path to the `claude` binary, `--model` the model. Raw results go to `bench/results/runs.jsonl`, every diff to `bench/results/patches/`.

## Add a task

Create `bench/tasks/<name>/` with:

- `task.md`: the request, written the way a user would ask, without hints about the rules;
- `test_hidden.py`: tests through `_bench.support` (`make_app`, `call`, `FakeService`);
- `task.toml`: `letters` the task targets and, for A1, the `variants` names.

## Limits

- Static checks see structure, not intent; read the patches before drawing conclusions.
- A handful of tasks and one agent is a pilot, not a verdict. Results are per model and per agent version.
- Rules go in through the system prompt, not a file in the repository, so the agent cannot skip reading them.
