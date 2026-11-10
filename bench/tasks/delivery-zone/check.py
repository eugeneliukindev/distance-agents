"""D3: business logic does not reach through other objects' internals.

Flags, in business modules, attribute chains three or more hops deep through objects other than `self`:
`customer.address.city.zone` (3 hops from `customer`), `self._customers.get(x).address.city.zone`
(4 hops after the field `self._customers`). Calls in a chain count as part of it; only the outermost
attribute of a chain is reported.
"""

import ast
from pathlib import Path

import checks

MAX_HOPS = 2


def hops(node: ast.AST) -> tuple[int, ast.AST]:
    """Attribute hops in a chain, and the chain's base."""
    count = 0
    while isinstance(node, (ast.Attribute, ast.Call, ast.Subscript)):
        if isinstance(node, ast.Attribute):
            count += 1
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        else:
            node = node.value
    return count, node


def findings(root: Path) -> list[str]:
    hits = []
    for name, tree in checks.business_modules(root).items():
        inner = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                child = node.value.func if isinstance(node.value, ast.Call) else node.value
                if isinstance(child, ast.Attribute):
                    inner.add(id(child))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute) or id(node) in inner:
                continue
            count, base = hops(node)
            if isinstance(base, ast.Name) and base.id == "self":
                count -= 1  # the first hop from self is the object's own field
            if count > MAX_HOPS:
                hits.append(f"{name} chain {ast.unparse(node)}")
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
