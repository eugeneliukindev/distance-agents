"""C3 for delivery-legacy: the old delivery rule changed, but no test pins the delivery logic.

A pinning test is a test file under tests/, new or changed against the starter, that calls the delivery logic:
it imports shop.delivery, names delivery_date, or requests the /delivery-date route.
"""

import ast
from pathlib import Path

from checks import parse

LOGIC = "shop/delivery.py"


def source(root: Path, relative: str) -> str | None:
    path = root / relative
    return path.read_text(encoding="utf-8") if path.is_file() else None


def touches_delivery(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("shop.delivery"):
            return True
        if isinstance(node, ast.Import) and any(alias.name.startswith("shop.delivery") for alias in node.names):
            return True
        if isinstance(node, ast.Name) and node.id == "delivery_date":
            return True
        if isinstance(node, ast.Attribute) and node.attr == "delivery_date":
            return True
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "/delivery-date" in node.value:
            return True
    return False


def check(root: Path, starter: Path) -> list[str]:
    if source(root, LOGIC) == source(starter, LOGIC):
        return []
    for path in sorted((root / "tests").rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        if source(root, relative) == source(starter, relative):
            continue
        tree = parse(path)
        if tree is not None and touches_delivery(tree):
            return []
    return ["delivery rule changed without a test that pins the delivery logic"]
