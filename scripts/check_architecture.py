"""Check architecture rules that an import graph cannot express."""

import ast
import re
import sys
import tomllib
from importlib.util import resolve_name
from pathlib import Path

LAYERS = {"domain", "application", "ai", "adapters", "presentation", "bootstrap"}
PACKAGE = "portfolio_assistant"
COMPATIBILITY_NAMESPACE = "app"
# Keep the module dispatchers and ASGI target at the top of the application package.
ENTRY_POINTS = {"portfolio_assistant.main"}
SHIMS = {module.removeprefix("portfolio_assistant.") for module in ENTRY_POINTS}
CLOCK_MODULE = "portfolio_assistant.adapters.clock"
WALL_CLOCK_READS = {
    "datetime.datetime.now",
    "datetime.datetime.utcnow",
    "datetime.datetime.today",
    "datetime.date.today",
    "time.time",
    "time.time_ns",
    # Without a timestamp argument these read the wall clock; src/portfolio_assistant/ has no use for them.
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
    layer = module.split(".", 2)[1] if "." in module else ""
    if module != PACKAGE and layer not in LAYERS and module not in ENTRY_POINTS:
        return [f"unclassified application module: {module}"]
    errors = []
    for dependency in sorted(dependencies(module, source, package=package)):
        root, _, child = dependency.partition(".")
        if root == COMPATIBILITY_NAMESPACE:
            errors.append(f"{module}: forbidden compatibility dependency {dependency}")
        elif root == PACKAGE and child and child.split(".")[0] not in LAYERS | SHIMS:
            errors.append(f"{module}: forbidden dependency {dependency}")
        elif layer in ("domain", "application") and root != PACKAGE:
            if root not in sys.stdlib_module_names:
                errors.append(f"{module}: third-party dependency {dependency}")
            if dependency.startswith("urllib.request"):
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
    """Catch module cycles, including self-imports and package-to-descendant cycles."""
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


# Modules allowed to keep a `__main__` block outside src/portfolio_assistant/bootstrap/entrypoints, with the reason.
MAIN_BLOCK_ALLOWED = {
    "portfolio_assistant.bootstrap.evaluation_export": "documented opt-in operator command (python -m)",
}
CONSOLE_SCRIPT = re.compile(r"portfolio_assistant\.bootstrap\.entrypoints\.[a-z_]+:main")


def _is_main_guard(test: ast.expr) -> bool:
    if not (isinstance(test, ast.Compare) and len(test.comparators) == 1):
        return False
    sides = (test.left, test.comparators[0])
    return any(isinstance(side, ast.Name) and side.id == "__name__" for side in sides) and any(
        isinstance(side, ast.Constant) and side.value == "__main__" for side in sides
    )


def entry_point_errors(module: str, source: str) -> list[str]:
    """Process entry points (`__main__` blocks) belong under portfolio_assistant.bootstrap.entrypoints."""
    if (
        module.startswith("portfolio_assistant.bootstrap.entrypoints.")
        or module in ENTRY_POINTS
        or module in MAIN_BLOCK_ALLOWED
    ):
        return []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.If) and _is_main_guard(node.test):
            return [
                f"{module}: process entry point outside src/portfolio_assistant/bootstrap/entrypoints"
            ]
    return []


def console_script_errors(pyproject: str) -> list[str]:
    """Every console script must target main() of a module under portfolio_assistant.bootstrap.entrypoints."""
    scripts = tomllib.loads(pyproject).get("project", {}).get("scripts", {})
    return [
        f"console script {name} -> {target}: must be portfolio_assistant.bootstrap.entrypoints.<name>:main"
        for name, target in sorted(scripts.items())
        if not CONSOLE_SCRIPT.fullmatch(target)
    ]


def architecture_errors(root: Path) -> list[str]:
    paths = sorted(root.rglob("*.py"))
    # Import Linter skips namespace package directories and their descendants.
    packages = {parent for path in paths for parent in path.parents if parent.is_relative_to(root)}
    errors = [
        f"{package.relative_to(root.parent)}: missing __init__.py"
        for package in sorted(packages)
        if not (package / "__init__.py").is_file()
    ]
    # Import Linter's graph also skips paths that are not importable module names (for example
    # `batch-jobs/` or `a.b.py`), so a module there would escape every contract.
    errors.extend(
        f"{path.relative_to(root.parent)}: not an importable module path"
        for path in paths
        if not all(
            part.isidentifier() for part in path.relative_to(root.parent).with_suffix("").parts
        )
    )
    graph = {}
    for path in paths:
        module = ".".join(path.relative_to(root.parent).with_suffix("").parts)
        package = path.name == "__init__.py"
        module = module.removesuffix(".__init__")
        source = path.read_text()
        errors.extend(dependency_errors(module, source, package=package))
        errors.extend(entry_point_errors(module, source))
        graph[module] = dependencies(module, source, package=package)
    return errors + cycle_errors(graph)


if __name__ == "__main__":
    repo = Path(__file__).resolve().parents[1]
    failures = architecture_errors(repo / "src" / PACKAGE)
    failures += console_script_errors((repo / "pyproject.toml").read_text())
    for failure in failures:
        print(failure)
    raise SystemExit(bool(failures))
