"""N1/I2 for order-export: one CSV format needs no registry of formats and no abstract exporter."""

import ast
from collections import Counter
from pathlib import Path

from checks import parse


def defined_names(trees: list[ast.Module]) -> set[str]:
    return {node.name for tree in trees for node in ast.walk(tree) if isinstance(node, (ast.ClassDef, ast.FunctionDef))}


def is_abstract_method(method: ast.FunctionDef) -> bool:
    body = [node for node in method.body if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str))]
    if any(ast.unparse(d).split(".")[-1] == "abstractmethod" for d in method.decorator_list):
        return True
    if not body:
        return True
    only = body[0] if len(body) == 1 else None
    return only is not None and (
        isinstance(only, ast.Pass)
        or isinstance(only, ast.Expr) and isinstance(only.value, ast.Constant) and only.value.value is Ellipsis
        or isinstance(only, ast.Raise) and "NotImplementedError" in ast.unparse(only)
    )


def findings(root: Path) -> list[str]:
    files = {path.relative_to(root).as_posix(): parse(path) for path in sorted((root / "shop").rglob("*.py"))}
    trees = [tree for tree in files.values() if tree is not None]
    names = defined_names(trees)
    hits = []
    for relative, tree in files.items():
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict) and node.keys and all(isinstance(k, ast.Constant) and isinstance(k.value, str) for k in node.keys):
                targets = [v.id if isinstance(v, ast.Name) else v.attr if isinstance(v, ast.Attribute) else None for v in node.values]
                if all(target in names for target in targets):
                    keys = ",".join(sorted(k.value for k in node.keys))
                    hits.append(f"{relative} registry of {keys}")
            elif isinstance(node, ast.ClassDef):
                abstract = [m.name for m in node.body if isinstance(m, ast.FunctionDef) and is_abstract_method(m)]
                if abstract:
                    hits.append(f"{relative} abstract class {node.name} ({', '.join(abstract)})")
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
