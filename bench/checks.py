"""Static checks for DISTANCE rules. They parse the agent's code with ast and never run it.

Business logic = every non-edge module under shop/ that defines `Checkout` or `Order`,
plus every shop module those import at runtime.
Edges = shop/web/** and shop/main.py: there, choosing a variant and reading raw keys is allowed.

The starter code already breaks some rules on purpose. A run is judged only by NEW findings:
findings in the run minus findings in the starter, compared without line numbers.
"""

import ast
import re
import sys
from collections import Counter
from pathlib import Path

ROOT_CLASSES = {"Checkout", "Order"}
INFRA_IMPORTS = ("sqlite3", "urllib", "http", "socket", "json", "requests", "httpx")
FOREIGN_ERRORS = {"NetworkError", "HTTPError", "URLError", "HttpResult", "OperationalError", "DatabaseError"}
STATUS_ATTRS = {"status", "status_code", "code"}
INTERFACE_BASES = {"Protocol", "ABC"}


def parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return None


def is_edge(relative: str) -> bool:
    return relative.startswith("shop/web/") or relative == "shop/main.py"


def module_name(root: Path, path: Path) -> str:
    return ".".join(path.relative_to(root).with_suffix("").parts).removesuffix(".__init__")


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


def defines_root(tree: ast.Module) -> bool:
    return any(isinstance(n, ast.ClassDef) and n.name in ROOT_CLASSES for n in ast.walk(tree))


def imports_any(tree: ast.Module, name: str, targets: tuple[str, ...] | set[str]) -> bool:
    return any(
        imported == bad or imported.startswith(bad + ".") for imported in runtime_imports(tree, name) for bad in targets
    )


def infra_modules(root: Path) -> set[str]:
    """Shop modules that talk to infrastructure, directly or through another such module, and define no
    Checkout or Order: adapters and infrastructure helpers."""
    modules = {}
    for path in sorted((root / "shop").rglob("*.py")):
        tree = parse(path)
        if tree and not is_edge(path.relative_to(root).as_posix()) and not defines_root(tree):
            modules[module_name(root, path)] = tree
    infra = {name for name, tree in modules.items() if imports_any(tree, name, INFRA_IMPORTS)}
    while True:
        more = {name for name, tree in modules.items() if name not in infra and imports_any(tree, name, infra)}
        if not more:
            return infra
        infra |= more


def business_modules(root: Path) -> dict[str, ast.Module]:
    """Modules defining Checkout or Order, plus what they import. Adapters and infrastructure helpers are not
    business logic: business logic may import them (I2 allows depending on the adapter class directly), so the
    walk stops there; what leaks from them into business code is caught by markers and foreign errors."""
    infra = infra_modules(root)
    queue = []
    for path in sorted((root / "shop").rglob("*.py")):
        tree = parse(path)
        if tree and not is_edge(path.relative_to(root).as_posix()) and defines_root(tree):
            queue.append(module_name(root, path))
    found: dict[str, ast.Module] = {}
    while queue:
        name = queue.pop()
        path = module_file(root, name)
        if name in found or name in infra or path is None or is_edge(path.relative_to(root).as_posix()):
            continue
        tree = parse(path)
        if tree is None:
            continue
        found[name] = tree
        queue.extend(n for n in runtime_imports(tree, name) if n.startswith("shop."))
    return found


def business_files(root: Path) -> set[str]:
    """Relative paths of business logic modules."""
    return {module_file(root, name).relative_to(root).as_posix() for name in business_modules(root)}


def check_infra_imports(modules: dict[str, ast.Module]) -> list[str]:
    """I1: business logic imports infrastructure."""
    return [
        f"{name} imports {imported}"
        for name, tree in modules.items()
        for imported in sorted(runtime_imports(tree, name))
        if any(imported == bad or imported.startswith(bad + ".") for bad in INFRA_IMPORTS)
    ]


def check_markers(modules: dict[str, ast.Module], markers: set[str]) -> list[str]:
    """I1/T1: business logic contains strings only an adapter or handler should know (paths, raw keys).
    Attribute names given to setattr/getattr (as in a frozen value object) are not raw keys."""
    hits = []
    for name, tree in modules.items():
        attribute_names = {
            id(arg)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and ast.unparse(node.func).split(".")[-1] in {"setattr", "getattr", "__setattr__"}
            for arg in node.args
        }
        hits += [
            f"{name}:{node.lineno} knows {node.value!r}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and node.value in markers and id(node) not in attribute_names
        ]
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


def check_variant_api(modules: dict[str, ast.Module], variants: set[str]) -> list[str]:
    """A1: a variant leaks into the use case API as its own method (`Checkout.pay_by_cash`).
    Entity methods are not checked: a status transition like `Order.mark_awaiting_cash` is a closed set (A1 exception)."""
    words = {variant.replace("_", "") for variant in variants}
    return [
        f"{name}:{method.lineno} method {cls.name}.{method.name}"
        for name, tree in modules.items()
        for cls in ast.walk(tree)
        if isinstance(cls, ast.ClassDef) and cls.name == "Checkout"
        for method in cls.body
        if isinstance(method, ast.FunctionDef)
        and not method.name.startswith("_")
        and words & set(re.split(r"_+", method.name.lower()))
    ]


def check_optional_dependencies(modules: dict[str, ast.Module]) -> list[str]:
    """A1/I1 smell: business logic checks whether a collaborator is configured (`if self._sbp is None`)."""
    return [
        f"{name}:{node.lineno} checks {ast.unparse(node.left)} is None"
        for name, tree in modules.items()
        for node in ast.walk(tree)
        if isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Attribute)
        and isinstance(node.left.value, ast.Name)
        and node.left.value.id == "self"
        and any(isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops)
        and any(isinstance(c, ast.Constant) and c.value is None for c in node.comparators)
    ]


def trees(root: Path) -> list[ast.Module]:
    paths = [*(root / "shop").rglob("*.py"), *(root / "tests").rglob("*.py")]
    return [tree for tree in map(parse, sorted(paths)) if tree is not None]


def bases(node: ast.ClassDef) -> set[str]:
    return {ast.unparse(b).split(".")[-1].split("[")[0] for b in node.bases}


def check_single_impl_interfaces(root: Path) -> list[str]:
    """I2: an interface that has fewer than two implementations."""
    classes = [node for tree in trees(root) for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    hits = []
    for interface in (c for c in classes if bases(c) & INTERFACE_BASES):
        methods = {f.name for f in interface.body if isinstance(f, ast.FunctionDef) and not f.name.startswith("__")}
        implementations = [
            cls.name
            for cls in classes
            if not bases(cls) & INTERFACE_BASES
            and (interface.name in bases(cls) or methods and methods <= {f.name for f in cls.body if isinstance(f, ast.FunctionDef)})
        ]
        if len(implementations) < 2:
            hits.append(f"interface {interface.name} has {len(implementations)} implementation(s)")
    return hits


def findings(root: Path, variants: set[str], markers: set[str]) -> dict[str, list[str]]:
    modules = business_modules(root)
    results = {
        "I1_infra_imports": check_infra_imports(modules),
        "markers": check_markers(modules, markers),
        "T1_raw_payload": check_raw_payload(modules),
        "T2_foreign_errors": check_foreign_errors(modules),
        "I2_single_impl_interfaces": check_single_impl_interfaces(root),
        "optional_dependencies": check_optional_dependencies(modules),
    }
    if variants:
        results["A1_variant_branches"] = check_variant_branches(root, variants)
        results["A1_variant_api"] = check_variant_api(modules, variants)
    return results


def without_line(finding: str) -> str:
    return re.sub(r":\d+", "", finding)


def run_checks(root: Path, starter: Path, variants: set[str], markers: set[str] = frozenset()) -> dict[str, list[str]]:
    """NEW findings in root compared with the starter."""
    before = findings(starter, variants, markers)
    after = findings(root, variants, markers)
    results = {}
    for check, hits in after.items():
        known = Counter(without_line(hit) for hit in before[check])
        new = []
        for hit in hits:
            if known[without_line(hit)]:
                known[without_line(hit)] -= 1
            else:
                new.append(hit)
        results[check] = new
    results["_business_modules"] = sorted(business_modules(root))
    return results


if __name__ == "__main__":
    import json

    run_dir, starter_dir = Path(sys.argv[1]), Path(sys.argv[2])
    variants = set(sys.argv[3].split(",")) if len(sys.argv) > 3 and sys.argv[3] else set()
    markers = set(sys.argv[4].split(",")) if len(sys.argv) > 4 else set()
    print(json.dumps(run_checks(run_dir, starter_dir, variants, markers), indent=2))
