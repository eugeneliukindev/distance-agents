"""Summarizes results files (default results/runs.jsonl) as markdown tables per task and condition.

    python3 bench/report.py > bench/results/report.md
    python3 bench/report.py rules-v2.jsonl
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

RESULTS = Path(__file__).resolve().parent / "results"

# Generic checks that measure the letters a task targets. `markers` and the task's own `task_rule` check
# are always targets; letters without a generic check rely on `task_rule`.
TARGET_CHECKS = {
    "A1": ["A1_variant_branches", "A1_variant_api"],
    "I1": ["I1_infra_imports"],
    "T1": ["T1_raw_payload"],
    "T2": ["T2_foreign_errors"],
    "I2": ["I2_single_impl_interfaces"],
}
# Checked on every run, whatever the task.
SECONDARY_CHECKS = ["C1_undocumented", "C2_mocks", "E1_magic_numbers"]


def passed(stage: dict) -> bool:
    tests = stage["tests"]
    return "total" in tests and tests["total"] > 0 and not tests["failed"]


def clean(stage: dict, letters: list[str]) -> bool:
    targets = ["markers", "task_rule", *(check for letter in letters for check in TARGET_CHECKS.get(letter, []))]
    return all(not stage["checks"].get(check) for check in targets)


def main() -> None:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    lines = [line for name in sys.argv[1:] or ["runs.jsonl"] for line in (RESULTS / name).read_text().splitlines()]
    failed_agents = []
    for record in map(json.loads, lines):
        if record["agent_error"] or record.get("followup", {}).get("agent_error"):
            failed_agents.append(record["run_id"])  # e.g. a usage limit: the agent never worked on the task
            continue
        groups[(record["task"], record["condition"])].append(record)
    if failed_agents:
        print(f"Skipped {len(failed_agents)} runs where the agent itself failed: {', '.join(failed_agents)}\n")

    print("| task | letters | condition | runs | tests pass | target rules kept | lines added | cost, $ | minutes |")
    print("|---|---|---|---|---|---|---|---|---|")
    for (task, condition), records in sorted(groups.items()):
        n, letters = len(records), records[0]["letters"]
        print(
            f"| {task} | {', '.join(letters)} | {condition} | {n}"
            f" | {sum(map(passed, records))}/{n}"
            f" | {sum(clean(r, letters) for r in records)}/{n}"
            f" | {mean(r['diff']['lines_added'] for r in records):.0f}"
            f" | {mean(r['cost_usd'] or 0 for r in records):.2f}"
            f" | {mean(r['seconds'] for r in records) / 60:.1f} |"
        )

    by_condition: dict[str, list[dict]] = defaultdict(list)
    for (_, condition), records in groups.items():
        by_condition[condition] += records
    print("\nChecked on every task: share of runs with new findings (lower is better).\n")
    print("| condition | runs | " + " | ".join(SECONDARY_CHECKS) + " |")
    print("|---|---|" + "---|" * len(SECONDARY_CHECKS))
    for condition, records in sorted(by_condition.items()):
        cells = [f"{sum(bool(r['checks'].get(check)) for r in records)}/{len(records)}" for check in SECONDARY_CHECKS]
        print(f"| {condition} | {len(records)} | " + " | ".join(cells) + " |")

    followups = {key: [r["followup"] for r in records if "followup" in r] for key, records in groups.items()}
    if any(followups.values()):
        print("\nFollow-up: a new variant on top of the agent's own result.\n")
        print("| task | condition | runs | tests pass | rules kept | business files touched | lines added |")
        print("|---|---|---|---|---|---|---|")
        for (task, condition), stages in sorted(followups.items()):
            if not stages:
                continue
            n, letters = len(stages), groups[(task, condition)][0]["letters"]
            print(
                f"| {task} | {condition} | {n}"
                f" | {sum(map(passed, stages))}/{n}"
                f" | {sum(clean(s, letters) for s in stages)}/{n}"
                f" | {mean(len(s['business_files_touched']) for s in stages):.1f}"
                f" | {mean(s['diff']['lines_added'] for s in stages):.0f} |"
            )


if __name__ == "__main__":
    main()
