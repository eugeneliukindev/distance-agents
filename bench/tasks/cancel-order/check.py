"""S2: only Order changes its own status.

Flags, anywhere under shop/ (handlers included), assignments to a `.status` attribute
(`x.status = ...`, `x.status += ...`, `setattr(x, "status", ...)`) outside the body of class Order.
"""

import ast
from pathlib import Path

import checks


def outside_order(tree: ast.Module) -> list[ast.AST]:
    inside = {
        id(node)
        for cls in ast.walk(tree)
        if isinstance(cls, ast.ClassDef) and cls.name == "Order"
        for node in ast.walk(cls)
    }
    return [node for node in ast.walk(tree) if id(node) not in inside]


def status_writes(node: ast.AST) -> bool:
    if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        return any(isinstance(t, ast.Attribute) and t.attr == "status" for target in targets for t in ast.walk(target))
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "setattr"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value == "status"
    )


def findings(root: Path) -> list[str]:
    hits = []
    for path in sorted((root / "shop").rglob("*.py")):
        tree = checks.parse(path)
        if tree is None:
            continue
        relative = path.relative_to(root).as_posix()
        hits += [f"{relative} writes .status outside Order" for node in outside_order(tree) if status_writes(node)]
    return hits


def check(root: Path, starter: Path) -> list[str]:
    known = findings(starter)
    new = []
    for hit in findings(root):
        if hit in known:
            known.remove(hit)
        else:
            new.append(hit)
    return new
