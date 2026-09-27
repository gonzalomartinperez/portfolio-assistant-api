"""Executable dependency direction, including relative imports and cycles."""

import ast
from pathlib import Path

ROOT = Path(__file__).parents[1] / 'app'
LAYERS = {'domain', 'application', 'ai', 'infrastructure', 'presentation', 'bootstrap'}
ALLOWED = {
    'domain': {'domain'},
    'application': {'application', 'domain'},
    'ai': {'ai', 'application', 'domain'},
    'infrastructure': {'infrastructure', 'application', 'domain', 'bootstrap'},
    'presentation': {'presentation', 'application', 'domain'},
    'bootstrap': LAYERS,
}


def test_layer_dependencies():
    import sys

    for layer in LAYERS:
        for path in (ROOT / layer).rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    prefix = '.'.join(path.relative_to(ROOT.parent).parts[:-1])
                    if node.level:
                        prefix = '.'.join(
                            prefix.split('.')[: len(prefix.split('.')) - node.level + 1]
                        )
                        modules = [prefix + '.' + (node.module or '')]
                    else:
                        modules = [node.module or '']
                else:
                    continue
                for module in modules:
                    parts = module.split('.')
                    if parts[0] == 'app':
                        assert len(parts) > 1 and parts[1] in ALLOWED[layer], (
                            path,
                            module,
                        )
                        # Infrastructure may consume the immutable settings adapter, never composition.
                        if layer == 'infrastructure' and parts[1] == 'bootstrap':
                            assert module == 'app.bootstrap.config', (path, module)
                    elif layer in ('domain', 'application'):
                        assert parts[0] in sys.stdlib_module_names, (path, module)


def test_inner_and_http_layers_do_not_execute_queries():
    for layer in ('domain', 'application', 'presentation', 'ai'):
        for path in (ROOT / layer).rglob('*.py'):
            source = path.read_text()
            assert not any(
                sql in source
                for sql in ('SELECT ', 'INSERT INTO ', 'UPDATE runs ', 'MATCH (')
            ), path


def test_modules_have_no_import_cycles():
    graph = {}
    for path in ROOT.rglob('*.py'):
        module = '.'.join(path.relative_to(ROOT.parent).with_suffix('').parts)
        edges = set()
        for node in ast.walk(ast.parse(path.read_text())):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith('app.')
            ):
                edges.add(node.module)
        graph[module] = edges

    def walk(module, stack):
        assert module not in stack, stack + [module]
        for child in graph.get(module, ()):
            walk(child, stack + [module])

    for module in graph:
        walk(module, [])
