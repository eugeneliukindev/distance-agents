"""T1: raw request keys or raw dicts reach code outside the handlers.

Scope: every module under shop/ except the handlers (shop/web, shop/main.py) and the starter's
infrastructure helpers (shop/db.py, shop/http_client.py). Findings already in the starter do not count.
"""

import re
from collections import Counter
from pathlib import Path

import checks

MARKERS = {"name", "phone", "birth_date"}
INFRASTRUCTURE = {"shop/db.py", "shop/http_client.py"}


def modules(root: Path) -> dict:
    found = {}
    for path in sorted((root / "shop").rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        tree = checks.parse(path)
        if tree is not None and not checks.is_edge(relative) and relative not in INFRASTRUCTURE:
            found[checks.module_name(root, path)] = tree
    return found


def findings(root: Path) -> list[str]:
    scope = modules(root)
    return checks.check_markers(scope, MARKERS) + checks.check_raw_payload(scope)


def check(root: Path, starter: Path) -> list[str]:
    known = Counter(re.sub(r":\d+", "", hit) for hit in findings(starter))
    new = []
    for hit in findings(root):
        key = re.sub(r":\d+", "", hit)
        if known[key]:
            known[key] -= 1
        else:
            new.append(hit)
    return new
