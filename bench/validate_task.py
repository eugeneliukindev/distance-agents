"""Checks that a task is a fair trap before spending agent runs on it.

    python3 bench/validate_task.py <task> [<task> ...]

1. On the task starter: regression tests pass, some hidden tests fail, checks find nothing new.
2. With solution/ applied: all tests pass, the target rules are kept.
3. With bad/ applied: the target rules are broken (bad/ is the easy solution the trap is about).
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import tasklib
from report import clean

BENCH = Path(__file__).resolve().parent


def tree_with(task: str, overlay: str | None) -> Path:
    work = Path(tempfile.mkdtemp(prefix=f"da-validate-{task}-"))
    shutil.copytree(tasklib.starter(task), work, dirs_exist_ok=True, ignore=tasklib.IGNORE)
    if overlay:
        shutil.copytree(tasklib.TASKS / task / overlay, work, dirs_exist_ok=True, ignore=tasklib.IGNORE)
    return work


def tests(task: str, work: Path) -> dict:
    bench_dir = work / "_bench"
    shutil.copytree(BENCH / "harness", bench_dir, ignore=tasklib.IGNORE)
    shutil.copy(tasklib.TASKS / task / "test_hidden.py", bench_dir)
    done = subprocess.run(
        ["python3", "_bench/run_tests.py", "_bench.test_regression", "_bench.test_hidden"],
        cwd=work, capture_output=True, text=True, timeout=180,
    )
    shutil.rmtree(bench_dir)
    return json.loads(done.stdout.strip().splitlines()[-1])


def findings(checks: dict) -> dict:
    return {k: v for k, v in checks.items() if not k.startswith("_") and v}


def validate(task: str) -> list[str]:
    letters = tasklib.config(task)["letters"]
    problems = []

    start = tree_with(task, None)
    result = tests(task, start)
    if "total" not in result:
        problems.append(f"starter: tests do not load: {result}")
    else:
        if any("test_regression" in name for name in result["failed"]):
            problems.append(f"starter: regression fails: {result['failed']}")
        if not any("test_hidden" in name for name in result["failed"]):
            problems.append("starter: no hidden test fails, the task asks for nothing")
    if findings(tasklib.checks(task, start)):
        problems.append(f"starter: checks find something: {findings(tasklib.checks(task, start))}")

    if (tasklib.TASKS / task / "solution").is_dir():
        good = tree_with(task, "solution")
        result = tests(task, good)
        if "total" not in result or result["failed"]:
            problems.append(f"solution: tests fail: {result}")
        if not clean({"checks": tasklib.checks(task, good)}, letters):
            problems.append(f"solution: breaks target rules: {findings(tasklib.checks(task, good))}")
    else:
        problems.append("no solution/: tests and checks are not validated against a correct solution")

    if (tasklib.TASKS / task / "bad").is_dir():
        if clean({"checks": tasklib.checks(task, tree_with(task, "bad"))}, letters):
            problems.append("bad: target rules look kept, the checks miss the trap")
    else:
        problems.append("no bad/: the checks are not shown to catch the trap")
    return problems


def main() -> None:
    failed = False
    for task in sys.argv[1:]:
        problems = validate(task)
        failed |= bool(problems)
        print(f"{task}: {'OK' if not problems else 'PROBLEMS'}")
        for problem in problems:
            print(f"  - {problem}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
