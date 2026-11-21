"""Static import contracts without loading application modules or their clients."""

import ast
import re
import sys
import tomllib
from importlib.util import resolve_name
from pathlib import Path

LAYERS = {"domain", "application", "ai", "adapters", "presentation", "bootstrap"}
ALLOWED = {
    "domain": {"domain"},
    "application": {"application", "domain"},
    "ai": {"ai", "application", "domain"},
    "adapters": {"adapters", "application", "domain"},
    "presentation": {"presentation", "application", "domain"},
    "bootstrap": LAYERS,
}
# Deprecated `python -m` shims (removed in the contract phase, after vps-ops runs the
# console scripts) plus the ASGI module `app.main`. Process entry points live under
# `app.bootstrap.entrypoints`.
ENTRY_POINTS = {
    "app.main",
    "app.migrate",
    "app.retention",
    "app.knowledge_sync",
    "app.knowledge_watch",
}
CLOCK_MODULE = "app.adapters.clock"
WALL_CLOCK_READS = {
    "datetime.datetime.now",
    "datetime.datetime.utcnow",
    "datetime.datetime.today",
    "datetime.date.today",
    "time.time",
    "time.time_ns",
    # Without a timestamp argument these read the wall clock; app/ has no use for them.
    "time.gmtime",
    "time.localtime",
    "time.ctime",
    "time.strftime",
}


def wall_clock_errors(module: str, source: str) -> list[str]:
    """Ban wall-clock reads (calls, references and aliases) outside the clock adapter."""
    if module == CLOCK_MODULE:
        return []
    tree = ast.parse(source)
    qualified: dict[str, str] = {}
    errors = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    qualified[alias.asname] = alias.name
                else:
                    root = alias.name.split(".")[0]
                    qualified[root] = root
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                full = f"{node.module}.{alias.name}"
                qualified[alias.asname or alias.name] = full
                if full in WALL_CLOCK_READS:
                    errors.append(f"{module}: wall-clock import {full}; inject Clock")

    def resolve(node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return qualified.get(node.id)
        if isinstance(node, ast.Attribute):
            base = resolve(node.value)
            return f"{base}.{node.attr}" if base else None
        return None

    errors.extend(
        f"{module}: wall-clock read {resolve(node)}; inject Clock"
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and resolve(node) in WALL_CLOCK_READS
    )
    return errors


def dependencies(module: str, source: str, *, package: bool = False) -> set[str]:
    result = set()
    parent = module if package else module.rpartition(".")[0]
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            name = node.module or ""
            if node.level:
                name = resolve_name("." * node.level + name, parent)
            if not (package and name == module):
                result.add(name)
            result.update(f"{name}.{alias.name}" for alias in node.names)
    return result


def dependency_errors(module: str, source: str, *, package: bool = False) -> list[str]:
    layer = "bootstrap" if module in ENTRY_POINTS else module.split(".")[1]
    if layer not in ALLOWED:
        return [f"unclassified application module: {module}"]
    errors = []
    for dependency in sorted(dependencies(module, source, package=package)):
        parts = dependency.split(".")
        if parts[0] == "app":
            if len(parts) > 1 and parts[1] in ALLOWED[layer]:
                continue
            # The parent package alone adds no dependency; imported children are checked separately.
            if dependency == "app":
                continue
            errors.append(f"{module}: forbidden dependency {dependency}")
        elif layer in ("domain", "application"):
            if parts[0] not in sys.stdlib_module_names:
                errors.append(f"{module}: third-party dependency {dependency}")
            if parts[0] in {
                "os",
                "socket",
                "subprocess",
                "sqlite3",
                "http",
            } or dependency.startswith("urllib.request"):
                errors.append(f"{module}: platform I/O dependency {dependency}")
    tree = ast.parse(source)
    loaders = {"__import__", "eval", "exec"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "importlib":
            loaders.update(
                alias.asname or alias.name for alias in node.names if alias.name == "import_module"
            )
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and (
            isinstance(node.func, ast.Name)
            and node.func.id in loaders
            or isinstance(node.func, ast.Attribute)
            and node.func.attr == "import_module"
        ):
            errors.append(f"{module}: dynamic code/import bypass")
    return errors + wall_clock_errors(module, source)


def cycle_errors(graph: dict[str, set[str]]) -> list[str]:
    visited: set[str] = set()
    active: set[str] = set()
    errors = []

    def visit(module: str) -> None:
        if module in active:
            errors.append(f"import cycle: {module}")
            return
        if module in visited:
            return
        active.add(module)
        for child in sorted(graph.get(module, ())):
            if child in graph:
                visit(child)
        active.remove(module)
        visited.add(module)

    for module in sorted(graph):
        visit(module)
    return errors


# Modules allowed to keep a `__main__` block outside app/bootstrap/entrypoints, with the reason.
MAIN_BLOCK_ALLOWED = {
    "app.bootstrap.evaluation_export": "documented opt-in operator command (python -m)",
}
CONSOLE_SCRIPT = re.compile(r"app\.bootstrap\.entrypoints\.[a-z_]+:main")


def _is_main_guard(test: ast.expr) -> bool:
    if not (isinstance(test, ast.Compare) and len(test.comparators) == 1):
        return False
    sides = (test.left, test.comparators[0])
    return any(isinstance(side, ast.Name) and side.id == "__name__" for side in sides) and any(
        isinstance(side, ast.Constant) and side.value == "__main__" for side in sides
    )


def entry_point_errors(module: str, source: str) -> list[str]:
    """Process entry points (`__main__` blocks) belong under app.bootstrap.entrypoints."""
    if (
        module.startswith("app.bootstrap.entrypoints.")
        or module in ENTRY_POINTS
        or module in MAIN_BLOCK_ALLOWED
    ):
        return []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.If) and _is_main_guard(node.test):
            return [f"{module}: process entry point outside app/bootstrap/entrypoints"]
    return []


def console_script_errors(pyproject: str) -> list[str]:
    """Every console script must target main() of a module under app.bootstrap.entrypoints."""
    scripts = tomllib.loads(pyproject).get("project", {}).get("scripts", {})
    return [
        f"console script {name} -> {target}: must be app.bootstrap.entrypoints.<name>:main"
        for name, target in sorted(scripts.items())
        if not CONSOLE_SCRIPT.fullmatch(target)
    ]


def architecture_errors(root: Path) -> list[str]:
    errors = []
    graph = {}
    for path in sorted(root.rglob("*.py")):
        module = ".".join(path.relative_to(root.parent).with_suffix("").parts)
        package = path.name == "__init__.py"
        module = module.removesuffix(".__init__")
        if module == "app":
            errors.extend(wall_clock_errors(module, path.read_text()))
            continue
        if module.split(".")[1] not in LAYERS and module not in ENTRY_POINTS:
            errors.append(f"unclassified application module: {module}")
            continue
        source = path.read_text()
        errors.extend(dependency_errors(module, source, package=package))
        errors.extend(entry_point_errors(module, source))
        graph[module] = dependencies(module, source, package=package)
    pyproject = root.parent / "pyproject.toml"
    if pyproject.exists():
        errors.extend(console_script_errors(pyproject.read_text()))
    return errors + cycle_errors(graph)


if __name__ == "__main__":
    failures = architecture_errors(Path(__file__).resolve().parents[1] / "app")
    for failure in failures:
        print(failure)
    raise SystemExit(bool(failures))
