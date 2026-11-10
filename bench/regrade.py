"""Re-runs the static checks on saved run directories, without running the agents again.
Use it after changing checks.py. Rewrites the results files in place.

    python3 bench/regrade.py [results file names, default runs.jsonl]
"""

import json
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from checks import run_checks

BENCH = Path(__file__).resolve().parent
STARTER = BENCH / "shop"
RESULTS = BENCH / "results"


def stage_one(work: Path) -> Path:
    """The tree as it was after the first request (commit "stage 1")."""
    commit = subprocess.run(
        ["git", "log", "--format=%H", "--grep", "^stage 1$"], cwd=work, capture_output=True, text=True, check=True
    ).stdout.split()[0]
    target = Path(tempfile.mkdtemp(prefix="da-stage1-"))
    archive = subprocess.run(["git", "archive", commit], cwd=work, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(target)], input=archive, check=True)
    return target


def regrade(runs: Path) -> None:
    records = [json.loads(line) for line in runs.read_text().splitlines()]
    for record in records:
        work = Path(record["work_dir"])
        config = tomllib.loads((BENCH / "tasks" / record["task"] / "task.toml").read_text())
        variants, markers = set(config["variants"]), set(config["markers"])
        if "followup" in record:
            record["checks"] = run_checks(stage_one(work), STARTER, variants, markers)
            record["followup"]["checks"] = run_checks(work, STARTER, variants, markers)
        else:
            record["checks"] = run_checks(work, STARTER, variants, markers)
    runs.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    print(f"regraded {len(records)} runs in {runs.name}")


def main() -> None:
    for name in sys.argv[1:] or ["runs.jsonl"]:
        regrade(RESULTS / name)


if __name__ == "__main__":
    main()
