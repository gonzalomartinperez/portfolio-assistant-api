"""Static import contracts without loading application modules or their clients."""

import ast
import sys
from importlib.util import resolve_name
from pathlib import Path

LAYERS = {'domain', 'application', 'ai', 'infrastructure', 'presentation', 'bootstrap'}
ALLOWED = {
    'domain': {'domain'},
    'application': {'application', 'domain'},
    'ai': {'ai', 'application', 'domain'},
    'infrastructure': {'infrastructure', 'application', 'domain'},
    'presentation': {'presentation', 'application', 'domain'},
    'bootstrap': LAYERS,
}
# Existing operator CLIs retain settings defaults; new adapters must receive inputs.
CLI_SETTINGS = {
    'app.infrastructure.db',
    'app.infrastructure.ledger',
    'app.infrastructure.migrations',
    'app.infrastructure.indexing',
    'app.infrastructure.checkpoints',
}
ENTRY_POINTS = {
    'app.main',
    'app.migrate',
    'app.retention',
    'app.knowledge_sync',
    'app.knowledge_watch',
}


def dependencies(module: str, source: str, *, package: bool = False) -> set[str]:
    result = set()
    parent = module if package else module.rpartition('.')[0]
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            name = node.module or ''
            if node.level:
                name = resolve_name('.' * node.level + name, parent)
            if not (package and name == module):
                result.add(name)
            result.update(f'{name}.{alias.name}' for alias in node.names)
    return result


def dependency_errors(module: str, source: str, *, package: bool = False) -> list[str]:
    layer = 'bootstrap' if module in ENTRY_POINTS else module.split('.')[1]
    errors = []
    for dependency in sorted(dependencies(module, source, package=package)):
        parts = dependency.split('.')
        if parts[0] == 'app':
            if module in CLI_SETTINGS and (
                dependency == 'app.bootstrap.config'
                or dependency.startswith('app.bootstrap.config.')
            ):
                continue
            if len(parts) > 1 and parts[1] in ALLOWED[layer]:
                continue
            # The parent package alone adds no dependency; imported children are checked separately.
            if dependency == 'app':
                continue
            errors.append(f'{module}: forbidden dependency {dependency}')
        elif layer in ('domain', 'application'):
            if parts[0] not in sys.stdlib_module_names:
                errors.append(f'{module}: third-party dependency {dependency}')
            if parts[0] in {
                'os',
                'socket',
                'subprocess',
                'sqlite3',
                'http',
            } or dependency.startswith('urllib.request'):
                errors.append(f'{module}: platform I/O dependency {dependency}')
    tree = ast.parse(source)
    loaders = {'__import__', 'eval', 'exec'}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == 'importlib':
            loaders.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == 'import_module'
            )
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and (
            isinstance(node.func, ast.Name)
            and node.func.id in loaders
            or isinstance(node.func, ast.Attribute)
            and node.func.attr == 'import_module'
        ):
            errors.append(f'{module}: dynamic code/import bypass')
    return errors


def cycle_errors(graph: dict[str, set[str]]) -> list[str]:
    visited: set[str] = set()
    active: set[str] = set()
    errors = []

    def visit(module: str) -> None:
        if module in active:
            errors.append(f'import cycle: {module}')
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


def architecture_errors(root: Path) -> list[str]:
    errors = []
    graph = {}
    for path in sorted(root.rglob('*.py')):
        module = '.'.join(path.relative_to(root.parent).with_suffix('').parts)
        package = path.name == '__init__.py'
        module = module.removesuffix('.__init__')
        if module == 'app':
            continue
        if module.split('.')[1] not in LAYERS and module not in ENTRY_POINTS:
            errors.append(f'unclassified application module: {module}')
            continue
        source = path.read_text()
        errors.extend(dependency_errors(module, source, package=package))
        graph[module] = dependencies(module, source, package=package)
    return errors + cycle_errors(graph)


if __name__ == '__main__':
    failures = architecture_errors(Path(__file__).resolve().parents[1] / 'app')
    for failure in failures:
        print(failure)
    raise SystemExit(bool(failures))
