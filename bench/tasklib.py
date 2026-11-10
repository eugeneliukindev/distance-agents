"""What a task is: its config, its starter code and its checks. Shared by run.py, regrade.py and validate_task.py.

A task directory holds:
    task.md          the request, as a user would write it
    task.toml        letters it targets; optional variants, markers, followup
    test_hidden.py   hidden tests through _bench.support
    overlay/         optional: files copied over the shared starter before the agent starts
    check.py         optional: `check(root, starter) -> list[str]`, new findings for the task's own rule
    solution/        optional: overlay of a correct solution, used only by validate_task.py
    bad/             optional: overlay of a solution that breaks the target rule, used only by validate_task.py
"""

import importlib.util
import shutil
import tempfile
import tomllib
from functools import cache
from pathlib import Path

from checks import run_checks

BENCH = Path(__file__).resolve().parent
TASKS = BENCH / "tasks"
SHARED_STARTER = BENCH / "shop"
IGNORE = shutil.ignore_patterns("__pycache__")


def config(task: str) -> dict:
    values = tomllib.loads((TASKS / task / "task.toml").read_text())
    return {"variants": [], "markers": [], "followup": False} | values


@cache
def starter(task: str) -> Path:
    """The shared starter with the task's overlay applied."""
    target = Path(tempfile.mkdtemp(prefix=f"da-starter-{task}-"))
    shutil.copytree(SHARED_STARTER, target, dirs_exist_ok=True, ignore=IGNORE)
    overlay = TASKS / task / "overlay"
    if overlay.is_dir():
        shutil.copytree(overlay, target, dirs_exist_ok=True, ignore=IGNORE)
    return target


def task_check(task: str):
    path = TASKS / task / "check.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(f"task_check_{task.replace('-', '_')}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.check


def checks(task: str, root: Path) -> dict[str, list[str]]:
    """Generic checks plus the task's own check, all as new findings against the task starter."""
    values = config(task)
    results = run_checks(root, starter(task), set(values["variants"]), set(values["markers"]))
    own = task_check(task)
    if own is not None:
        results["task_rule"] = own(root, starter(task))
    return results
