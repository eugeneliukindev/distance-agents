"""S1: the shipping rule (5000 threshold, 300 fee) must live in one place.

Flags, anywhere under shop/ (handlers included), when there are more than one:
- literals equal to the threshold or the fee (5000, Decimal("5000"), 300, ...);
- comparisons against the threshold, as a literal or through a module-level name bound to it.
"""

import ast
from pathlib import Path

import checks

THRESHOLD, FEE = 5000, 300


def numeric(node) -> float | None:
    if not isinstance(node, ast.Constant) or isinstance(node.value, bool):
        return None
    if isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node.value, str):
        try:
            return float(node.value)
        except ValueError:
            return None
    return None


def findings(root: Path) -> list[str]:
    trees = {
        path.relative_to(root).as_posix(): tree
        for path in sorted((root / "shop").rglob("*.py"))
        if (tree := checks.parse(path)) is not None
    }
    literals = {THRESHOLD: [], FEE: []}
    threshold_names: set[str] = set()
    for relative, tree in trees.items():
        for node in ast.walk(tree):
            value = numeric(node)
            if value in literals:
                literals[value].append(f"{relative} literal {value:g}")
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and any(numeric(c) == THRESHOLD for c in ast.walk(node)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                threshold_names |= {t.id for t in targets if isinstance(t, ast.Name)}

    comparisons = []
    for relative, tree in trees.items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            parts = [node.left, *node.comparators]
            if any(
                numeric(c) == THRESHOLD
                or isinstance(c, ast.Name) and c.id in threshold_names
                or isinstance(c, ast.Attribute) and c.attr in threshold_names
                for part in parts
                for c in ast.walk(part)
            ):
                comparisons.append(f"{relative} compares with the threshold")

    hits = []
    for value, places in literals.items():
        if len(places) > 1:
            hits += [f"{place} (the value appears {len(places)} times)" for place in places]
    if len(comparisons) > 1:
        hits += [f"{place} ({len(comparisons)} threshold comparisons)" for place in comparisons]
    return hits


def check(root: Path, starter: Path) -> list[str]:
    known = set(findings(starter))
    return [hit for hit in findings(root) if hit not in known]
