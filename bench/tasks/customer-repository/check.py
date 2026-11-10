"""A3: a class reuses behavior by inheriting from a project class instead of holding an instance.

Allowed bases: Exception, Enum, Protocol, ABC and the like, and project classes that themselves only
derive from those. Anything else in shop/ (not tests) is a finding; inheritance already in the starter is not.
"""

import ast
from collections import Counter
from pathlib import Path

import checks

ALLOWED_BASES = {
    "object", "Exception", "BaseException", "ValueError", "LookupError", "RuntimeError",
    "Enum", "IntEnum", "StrEnum", "Flag", "Protocol", "ABC", "NamedTuple", "TypedDict", "Generic",
}


def classes(root: Path) -> dict[str, tuple[str, set[str]]]:
    """Class name -> (file, base names) for every class under shop/."""
    found = {}
    for path in sorted((root / "shop").rglob("*.py")):
        tree = checks.parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                found[node.name] = (path.relative_to(root).as_posix(), checks.bases(node))
    return found


def findings(root: Path) -> list[str]:
    project = classes(root)
    allowed = set(ALLOWED_BASES)
    changed = True
    while changed:  # project classes that only derive from allowed bases are allowed bases too
        changed = False
        for name, (_, bases) in project.items():
            if name not in allowed and bases and bases <= allowed:
                allowed.add(name)
                changed = True
    return [
        f"{path}: class {name} inherits {base}"
        for name, (path, bases) in sorted(project.items())
        for base in sorted(bases)
        if base in project and base not in allowed
    ]


def check(root: Path, starter: Path) -> list[str]:
    known = Counter(findings(starter))
    new = []
    for hit in findings(root):
        if known[hit]:
            known[hit] -= 1
        else:
            new.append(hit)
    return new
