"""Re-runs the static checks on saved run directories, without running the agents again.
Use it after changing checks.py. Rewrites the results files in place.

    python3 bench/regrade.py [results file names, default runs.jsonl]
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import tasklib

BENCH = Path(__file__).resolve().parent
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
        task = record["task"]
        if "followup" in record:
            record["checks"] = tasklib.checks(task, stage_one(work))
            record["followup"]["checks"] = tasklib.checks(task, work)
        else:
            record["checks"] = tasklib.checks(task, work)
    runs.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    print(f"regraded {len(records)} runs in {runs.name}")


def main() -> None:
    for name in sys.argv[1:] or ["runs.jsonl"]:
        regrade(RESULTS / name)


if __name__ == "__main__":
    main()
