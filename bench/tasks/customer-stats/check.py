"""D4: code depends on a wide interface (4+ methods) but uses at most two of its methods.

A function counts what it calls on a parameter annotated with such an interface. A class counts what it
calls on `self.<attr>` assigned from such a parameter in `__init__`. Scans all of shop/, handlers included.
"""

import ast
import re
from collections import Counter
from pathlib import Path

import checks

WIDE = 4
NARROW_USE = 2


def wide_interfaces(trees: list[ast.Module]) -> dict[str, int]:
    found = {}
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and checks.bases(node) & checks.INTERFACE_BASES:
                methods = [f for f in node.body if isinstance(f, ast.FunctionDef) and not f.name.startswith("__")]
                if len(methods) >= WIDE:
                    found[node.name] = len(methods)
    return found


def interface_of(arg: ast.arg, wide: dict[str, int]) -> str | None:
    if arg.annotation is None:
        return None
    names = set(re.findall(r"\w+", ast.unparse(arg.annotation)))
    return next((name for name in sorted(names) if name in wide), None)


def findings(root: Path) -> list[str]:
    paths = sorted((root / "shop").rglob("*.py"))
    trees = {path: tree for path in paths if (tree := checks.parse(path)) is not None}
    wide = wide_interfaces(list(trees.values()))
    hits = []
    for path, tree in trees.items():
        relative = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                init = next((f for f in node.body if isinstance(f, ast.FunctionDef) and f.name == "__init__"), None)
                if init is None:
                    continue
                for arg in init.args.args:
                    interface = interface_of(arg, wide)
                    if interface is None:
                        continue
                    fields = {
                        target.attr
                        for statement in ast.walk(init)
                        if isinstance(statement, ast.Assign)
                        and isinstance(statement.value, ast.Name)
                        and statement.value.id == arg.arg
                        for target in statement.targets
                        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self"
                    }
                    used = {
                        sub.attr
                        for sub in ast.walk(node)
                        if isinstance(sub, ast.Attribute)
                        and isinstance(sub.value, ast.Attribute)
                        and isinstance(sub.value.value, ast.Name)
                        and sub.value.value.id == "self"
                        and sub.value.attr in fields
                    }
                    if len(used) <= NARROW_USE:
                        hits.append(f"{relative}: {node.name} takes {interface} ({wide[interface]} methods) but uses {sorted(used)}")
            elif isinstance(node, ast.FunctionDef) and node.name != "__init__":
                for arg in node.args.args + node.args.kwonlyargs:
                    interface = interface_of(arg, wide)
                    if interface is None:
                        continue
                    used = {
                        sub.attr
                        for sub in ast.walk(node)
                        if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id == arg.arg
                    }
                    if len(used) <= NARROW_USE:
                        hits.append(f"{relative}: {node.name}() takes {interface} ({wide[interface]} methods) but uses {sorted(used)}")
    return hits


def check(root: Path, starter: Path) -> list[str]:
    known = Counter(findings(starter))
    new = []
    for hit in findings(root):
        if known[hit]:
            known[hit] -= 1
        else:
            new.append(hit)
    return new
