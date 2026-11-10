"""A2: an implementation does not fulfill its interface, or callers check which implementation they hold.

Flags in shop/ (not tests): `raise NotImplementedError`, `except NotImplementedError`, `isinstance` against a
project class, `hasattr` probes, and methods of non-interface classes whose body only raises.
"""

import ast
from collections import Counter
from pathlib import Path

import checks


def project_classes(root: Path) -> set[str]:
    return {
        node.name
        for path in (root / "shop").rglob("*.py")
        if (tree := checks.parse(path)) is not None
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    }


def class_names(node: ast.AST) -> list[str]:
    targets = node.elts if isinstance(node, ast.Tuple) else [node]
    return [ast.unparse(target).split(".")[-1] for target in targets]


def only_raises(function: ast.FunctionDef) -> bool:
    body = function.body[1:] if ast.get_docstring(function) else function.body
    return len(body) == 1 and isinstance(body[0], ast.Raise)


def findings(root: Path) -> list[str]:
    classes = project_classes(root)
    hits = []
    for path in sorted((root / "shop").rglob("*.py")):
        tree = checks.parse(path)
        if tree is None:
            continue
        relative = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise) and node.exc is not None and "NotImplementedError" in ast.unparse(node.exc):
                hits.append(f"{relative}: raises NotImplementedError")
            elif isinstance(node, ast.ExceptHandler) and node.type is not None and "NotImplementedError" in ast.unparse(node.type):
                hits.append(f"{relative}: catches NotImplementedError")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "isinstance" and len(node.args) == 2:
                    for name in class_names(node.args[1]):
                        if name in classes:
                            hits.append(f"{relative}: isinstance check against {name}")
                elif node.func.id == "hasattr":
                    hits.append(f"{relative}: hasattr probe {ast.unparse(node)}")
            elif isinstance(node, ast.ClassDef) and not checks.bases(node) & checks.INTERFACE_BASES:
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and only_raises(method):
                        hits.append(f"{relative}: {node.name}.{method.name} only raises")
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
