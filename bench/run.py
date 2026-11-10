"""Runs a coding agent on benchmark tasks with and without the DISTANCE rules.

Each run: copy the starter shop to a temp dir -> run the agent with the task -> run hidden tests
and static checks. Tasks with a follow-up get a second request on top of the agent's own result,
which measures how many business files a new variant touches. One JSON line per run goes to
results/runs.jsonl.

    python3 bench/run.py --tasks payment-methods courier --conditions baseline distance --runs 5
"""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from checks import business_files, run_checks

BENCH = Path(__file__).resolve().parent
STARTER = BENCH / "shop"
RULES = BENCH.parent / "AGENTS.md"
RESULTS = BENCH / "results"
# placebo: generic "write clean code" advice, to tell the effect of DISTANCE from the effect of any instructions.
CONDITIONS = {"baseline": None, "placebo": BENCH / "placebo.md", "distance": RULES}
AGENT_TIMEOUT_SECONDS = 1200


def agent_command(prompt: str, rules: Path | None, model: str) -> list[str]:
    """Claude Code in headless mode, isolated from user settings, memory and MCP servers."""
    command = [
        os.environ.get("CLAUDE_BIN", "claude"), "-p", prompt,
        "--setting-sources", "local",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--model", model,
        "--output-format", "json",
        "--permission-mode", "acceptEdits",
        "--allowedTools", "Read", "Edit", "Write", "Glob", "Grep", "Bash(python3:*)",
        "--disallowedTools", "WebFetch", "WebSearch",
    ]
    if rules is not None:
        command += ["--append-system-prompt-file", str(rules)]
    return command


def git(work: Path, *args: str) -> str:
    identity = ["-c", "user.name=bench", "-c", "user.email=bench@localhost"]
    return subprocess.run(["git", *identity, *args], cwd=work, capture_output=True, text=True, check=True).stdout


def commit(work: Path, message: str) -> None:
    git(work, "add", "-A")
    git(work, "commit", "-qm", message, "--allow-empty")


def prepare(work: Path) -> None:
    shutil.copytree(STARTER, work, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    (work / ".gitignore").write_text("__pycache__/\n*.db\n")
    git(work, "init", "-q")
    commit(work, "start")


def run_agent(work: Path, prompt: str, condition: str, model: str) -> dict:
    started = time.monotonic()
    try:
        done = subprocess.run(
            agent_command(prompt, CONDITIONS[condition], model),
            cwd=work, capture_output=True, text=True, timeout=AGENT_TIMEOUT_SECONDS, stdin=subprocess.DEVNULL,
        )
        agent = json.loads(done.stdout)
    except (subprocess.TimeoutExpired, ValueError) as error:
        agent = {"is_error": True, "result": repr(error)}
    return {
        "seconds": round(time.monotonic() - started),
        "agent_error": agent.get("is_error", True),
        "cost_usd": agent.get("total_cost_usd"),
        "turns": agent.get("num_turns"),
        "output_tokens": agent.get("usage", {}).get("output_tokens"),
        "agent_reply": (agent.get("result") or "")[:2000],
    }


def hidden_tests(work: Path, task_dir: Path, test_files: list[str]) -> dict:
    bench_dir = work / "_bench"
    shutil.copytree(BENCH / "harness", bench_dir, ignore=shutil.ignore_patterns("__pycache__"))
    for name in test_files:
        shutil.copy(task_dir / name, bench_dir / name)
    modules = ["_bench.test_regression", *(f"_bench.{Path(name).stem}" for name in test_files)]
    try:
        done = subprocess.run(
            ["python3", "_bench/run_tests.py", *modules], cwd=work, capture_output=True, text=True, timeout=180,
        )
        summary = json.loads(done.stdout.strip().splitlines()[-1])
    except (subprocess.TimeoutExpired, ValueError, IndexError) as error:
        summary = {"runner_error": repr(error)}
    shutil.rmtree(bench_dir)
    return summary


def diff_stats(work: Path) -> dict:
    """Changes since the last commit."""
    git(work, "add", "-A")
    stats = {"lines_added": 0, "lines_removed": 0, "test_lines_added": 0, "files": []}
    for line in git(work, "diff", "--cached", "--numstat", "HEAD").splitlines():
        plus, minus, path = line.split("\t")
        stats["files"].append(path)
        if plus == "-":
            continue
        if path.startswith("tests/"):
            stats["test_lines_added"] += int(plus)
        else:
            stats["lines_added"] += int(plus)
            stats["lines_removed"] += int(minus)
    return stats


def save_patch(work: Path, name: str) -> None:
    patches = RESULTS / "patches"
    patches.mkdir(parents=True, exist_ok=True)
    git(work, "add", "-A")
    (patches / f"{name}.patch").write_text(git(work, "diff", "--cached", "HEAD"))


def run_one(task: str, condition: str, index: int, model: str) -> dict:
    task_dir = BENCH / "tasks" / task
    config = tomllib.loads((task_dir / "task.toml").read_text())
    variants, markers = set(config["variants"]), set(config["markers"])
    run_id = f"{task}.{condition}.{index}.{int(time.time())}"
    work = Path(tempfile.mkdtemp(prefix=f"da-{task}-{condition}-"))
    prepare(work)

    record = {"run_id": run_id, "task": task, "letters": config["letters"], "condition": condition, "model": model}
    record |= run_agent(work, (task_dir / "task.md").read_text(), condition, model)
    record["tests"] = hidden_tests(work, task_dir, ["test_hidden.py"])
    record["checks"] = run_checks(work, STARTER, variants, markers)
    record["diff"] = diff_stats(work)
    record["work_dir"] = str(work)
    save_patch(work, run_id)

    if config.get("followup"):
        commit(work, "stage 1")
        business_before = business_files(work)
        followup = run_agent(work, (task_dir / "followup.md").read_text(), condition, model)
        followup["tests"] = hidden_tests(work, task_dir, ["test_hidden.py", "test_followup.py"])
        followup["checks"] = run_checks(work, STARTER, variants, markers)
        followup["diff"] = diff_stats(work)
        followup["business_files_touched"] = sorted(set(followup["diff"]["files"]) & business_before)
        save_patch(work, run_id + ".followup")
        record["followup"] = followup
    return record


def summary_line(record: dict) -> str:
    def part(stage: dict) -> str:
        tests = stage["tests"]
        failed = len(tests["failed"]) if "total" in tests else tests
        found = {k: len(v) for k, v in stage["checks"].items() if not k.startswith("_") and v}
        return f"tests failed: {failed} | new findings: {found}"

    line = f"{record['run_id']} {part(record)}"
    if "followup" in record:
        line += f" || followup {part(record['followup'])} | business files touched: {record['followup']['business_files_touched']}"
    return line


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", nargs="+", default=sorted(p.name for p in (BENCH / "tasks").iterdir()))
    parser.add_argument("--conditions", nargs="+", default=list(CONDITIONS), choices=list(CONDITIONS))
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--parallel", type=int, default=4)
    parser.add_argument("--out", default="runs.jsonl", help="results file name inside results/")
    args = parser.parse_args()

    jobs = [(t, c, i, args.model) for i in range(args.runs) for t in args.tasks for c in args.conditions]
    RESULTS.mkdir(exist_ok=True)
    with ThreadPoolExecutor(args.parallel) as pool, (RESULTS / args.out).open("a") as out:
        for record in pool.map(lambda job: run_one(*job), jobs):
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            print(summary_line(record), flush=True)


if __name__ == "__main__":
    main()
