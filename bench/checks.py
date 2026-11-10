"""Static checks for DISTANCE rules. They parse the agent's code with ast and never run it.

Business logic = shop/orders/checkout.py, shop/orders/order.py and every shop module they import at runtime.
Edges = shop/web/** and shop/main.py: there, choosing a variant and reading raw keys is allowed.
"""

import ast
import sys
from pathlib import Path

BUSINESS_ROOTS = ("shop/orders/checkout.py", "shop/orders/order.py")
INFRA_IMPORTS = ("sqlite3", "urllib", "http", "socket", "json", "requests", "httpx", "shop.infra", "shop.adapters")
FOREIGN_ERRORS = {"NetworkError", "HTTPError", "URLError", "HttpResult", "OperationalError", "DatabaseError"}
STATUS_ATTRS = {"status", "status_code", "code"}
INTERFACE_BASES = {"Protocol", "ABC"}


def parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return None


def runtime_imports(tree: ast.Module, module: str) -> set[str]:
    """Imported module names, skipping `if TYPE_CHECKING:` blocks."""
    names: set[str] = set()
    package = module.rsplit(".", 1)[0]

    def visit(node: ast.AST) -> None:
        if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(node.test):
            for child in node.orelse:
                visit(child)
            return
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = package.split(".")
                base = ".".join(parts[: len(parts) - node.level + 1] + ([base] if base else []))
            names.add(base)
            names.update(f"{base}.{alias.name}" for alias in node.names)
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(tree)
    return names


def module_file(root: Path, name: str) -> Path | None:
    path = root / Path(*name.split("."))
    for candidate in (path.with_suffix(".py"), path / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def business_modules(root: Path) -> dict[str, ast.Module]:
    found: dict[str, ast.Module] = {}
    queue = [path[:-3].replace("/", ".") for path in BUSINESS_ROOTS]
    while queue:
        name = queue.pop()
        path = module_file(root, name)
        if name in found or path is None or path.name == "__init__.py" and name != "shop":
            continue
        tree = parse(path)
        if tree is None:
            continue
        found[name] = tree
        queue.extend(n for n in runtime_imports(tree, name) if n.startswith("shop."))
    return found


def check_infra_imports(modules: dict[str, ast.Module]) -> list[str]:
    """I1: business logic imports infrastructure."""
    hits = []
    for name, tree in modules.items():
        for imported in sorted(runtime_imports(tree, name)):
            if any(imported == bad or imported.startswith(bad + ".") for bad in INFRA_IMPORTS):
                hits.append(f"{name} imports {imported}")
    return hits


def check_raw_payload(modules: dict[str, ast.Module]) -> list[str]:
    """T1: business logic reads raw keys or accepts raw dicts."""
    hits = []
    for name, tree in modules.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                hits.append(f"{name}:{node.lineno} reads key {node.slice.value!r}")
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                hits.append(f"{name}:{node.lineno} reads key {node.args[0].value!r}")
            elif isinstance(node, ast.arg) and node.annotation is not None:
                annotation = ast.unparse(node.annotation)
                if annotation.split("[")[0] in {"dict", "Dict", "Mapping", "Any"}:
                    hits.append(f"{name}:{node.lineno} parameter {node.arg}: {annotation}")
    return hits


def check_foreign_errors(modules: dict[str, ast.Module]) -> list[str]:
    """T2: business logic sees library errors or status codes."""
    hits = []
    for name, tree in modules.items():
        for node in ast.walk(tree):
            label = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else None
            if label in FOREIGN_ERRORS:
                hits.append(f"{name}:{node.lineno} uses {label}")
            if isinstance(node, ast.Compare):
                sides = [node.left, *node.comparators]
                if any(isinstance(s, ast.Attribute) and s.attr in STATUS_ATTRS for s in sides) and any(
                    isinstance(s, ast.Constant) and isinstance(s.value, int) for s in sides
                ):
                    hits.append(f"{name}:{node.lineno} checks a status code")
    return hits


def is_edge(relative: str) -> bool:
    return relative.startswith("shop/web/") or relative == "shop/main.py"


def mentions_variant(node: ast.AST, variants: set[str]) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str) and child.value.lower() in variants:
            return True
        if isinstance(child, ast.Attribute) and child.attr.lower() in variants:
            return True
        if isinstance(child, ast.Name) and child.id.lower() in variants:
            return True
    return False


def check_variant_branches(root: Path, variants: set[str]) -> list[str]:
    """A1: outside the edges, code branches on a variant name or keeps a dispatch table."""
    hits = []
    for path in sorted((root / "shop").rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        tree = parse(path)
        if is_edge(relative) or tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and mentions_variant(node, variants):
                hits.append(f"{relative}:{node.lineno} compares with a variant")
            elif isinstance(node, ast.match_case) and mentions_variant(node.pattern, variants):
                hits.append(f"{relative}:{node.pattern.lineno} matches on a variant")
            elif isinstance(node, ast.Dict) and any(k is not None and mentions_variant(k, variants) for k in node.keys):
                hits.append(f"{relative}:{node.lineno} dispatch table keyed by variant")
    return hits


def interfaces(root: Path) -> dict[str, set[str]]:
    """Interface name -> its method names, over shop/ and tests/."""
    found = {}
    for tree in trees(root):
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and {ast.unparse(b).split(".")[-1] for b in node.bases} & INTERFACE_BASES:
                found[node.name] = {f.name for f in node.body if isinstance(f, ast.FunctionDef) and not f.name.startswith("__")}
    return found


def trees(root: Path) -> list[ast.Module]:
    paths = [*(root / "shop").rglob("*.py"), *(root / "tests").rglob("*.py")]
    return [tree for tree in map(parse, sorted(paths)) if tree is not None]


def check_single_impl_interfaces(root: Path, starter: Path) -> list[str]:
    """I2: a new interface that has fewer than two implementations."""
    known = interfaces(starter)
    classes = [
        node
        for tree in trees(root)
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and not {ast.unparse(b).split(".")[-1] for b in node.bases} & INTERFACE_BASES
    ]
    hits = []
    for name, methods in interfaces(root).items():
        if name in known:
            continue
        implementations = [
            cls.name
            for cls in classes
            if name in {ast.unparse(b).split(".")[-1] for b in cls.bases}
            or methods and methods <= {f.name for f in cls.body if isinstance(f, ast.FunctionDef)}
        ]
        if len(implementations) < 2:
            hits.append(f"interface {name} has {len(implementations)} implementation(s): {implementations}")
    return hits


def run_checks(root: Path, starter: Path, variants: set[str]) -> dict[str, list[str]]:
    modules = business_modules(root)
    results = {
        "I1_infra_imports": check_infra_imports(modules),
        "T1_raw_payload": check_raw_payload(modules),
        "T2_foreign_errors": check_foreign_errors(modules),
        "I2_single_impl_interfaces": check_single_impl_interfaces(root, starter),
    }
    if variants:
        results["A1_variant_branches"] = check_variant_branches(root, variants)
    results["_business_modules"] = sorted(modules)
    return results


if __name__ == "__main__":
    import json

    run_dir, starter_dir = Path(sys.argv[1]), Path(sys.argv[2])
    variants = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else set()
    print(json.dumps(run_checks(run_dir, starter_dir, variants), indent=2))
