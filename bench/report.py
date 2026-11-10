"""Summarizes results/runs.jsonl as a markdown table per task and condition.

    python3 bench/report.py > bench/results/report.md
"""

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

RUNS = Path(__file__).resolve().parent / "results" / "runs.jsonl"

# Which checks measure the letters a task targets.
TARGET_CHECKS = {
    "A1": ["A1_variant_branches"],
    "I1": ["I1_infra_imports"],
    "T1": ["T1_raw_payload"],
    "T2": ["T2_foreign_errors"],
    "I2": ["I2_single_impl_interfaces"],
    "N1": [],
}


def passed(record: dict) -> bool:
    tests = record["tests"]
    return "total" in tests and tests["total"] > 0 and not tests["failed"]


def clean(record: dict) -> bool:
    targets = [check for letter in record["letters"] for check in TARGET_CHECKS[letter]]
    return all(not record["checks"].get(check) for check in targets)


def main() -> None:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for line in RUNS.read_text().splitlines():
        record = json.loads(line)
        groups[(record["task"], record["condition"])].append(record)

    print("| task | letters | condition | runs | tests pass | target rules kept | lines added | cost, $ | minutes |")
    print("|---|---|---|---|---|---|---|---|---|")
    for (task, condition), records in sorted(groups.items()):
        n = len(records)
        print(
            f"| {task} | {', '.join(records[0]['letters'])} | {condition} | {n}"
            f" | {sum(map(passed, records))}/{n}"
            f" | {sum(map(clean, records))}/{n}"
            f" | {mean(r['diff']['lines_added'] for r in records):.0f}"
            f" | {mean(r['cost_usd'] or 0 for r in records):.2f}"
            f" | {mean(r['seconds'] for r in records) / 60:.1f} |"
        )


if __name__ == "__main__":
    main()
