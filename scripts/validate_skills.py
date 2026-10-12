"""Validate the portable skill catalog without executing instructions or following URLs."""

import argparse
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

from scripts.scan_secrets import matches

NAME = re.compile(r'api-[a-z0-9]+(?:-[a-z0-9]+)*')
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')
PRIVATE_PATH = re.compile(r'/home/|/Users/|/mnt/[cd]/|[A-Z]:\\')


def validate(root: Path) -> list[str]:
    """Return location-only findings; malformed text or suspected secrets stay redacted."""
    root = root.resolve()
    errors = []
    canonical = root / '.claude/skills'
    discovery = root / '.agents/skills'
    if not canonical.is_dir() or not discovery.is_dir():
        return ['missing canonical or discovery directory']
    names = set()
    folders = list(canonical.iterdir())
    if not folders:
        errors.append('empty catalog')
    for folder in folders:
        location = folder.relative_to(root).as_posix()
        path = folder / 'SKILL.md'
        if folder.is_symlink() or not folder.is_dir() or not path.is_file():
            errors.append(f'{location}: expected a canonical directory with SKILL.md')
            continue
        text = path.read_text()
        front = re.match(r'\A---\n(.*?)\n---\n(.+)', text, re.DOTALL)
        try:
            if front is None:
                raise ValueError
            metadata = yaml.safe_load(front[1])
            node = yaml.compose(front[1])
            if not isinstance(metadata, dict) or set(metadata) != {
                'name',
                'description',
            }:
                raise ValueError
            if not isinstance(node, yaml.MappingNode) or len(node.value) != 2:
                raise ValueError
            name, description = metadata['name'], metadata['description']
            if (
                not isinstance(name, str)
                or not NAME.fullmatch(name)
                or len(name) > 64
                or name != folder.name
                or name in names
                or not isinstance(description, str)
                or not 1 <= len(description.strip()) <= 1024
                or not front[2].strip()
            ):
                raise ValueError
            names.add(name)
        except yaml.YAMLError, ValueError:
            errors.append(f'{location}: invalid or duplicate portable metadata')
        for resource in folder.rglob('*'):
            relative = resource.relative_to(root).as_posix()
            if resource.is_symlink():
                errors.append(f'{relative}: canonical resources must not be symlinks')
            elif resource.is_dir() and not any(resource.iterdir()):
                errors.append(f'{relative}: empty scaffolding directory')
            elif resource.is_file():
                if resource.name == 'SKILL.md' and resource != path:
                    errors.append(
                        f'{relative}: nested skill creates ambiguous discovery'
                    )
                data = resource.read_bytes()
                if matches(data):
                    errors.append(f'{relative}: suspected secret (value redacted)')
                if resource.suffix == '.md':
                    body = data.decode()
                    if PRIVATE_PATH.search(body) or re.search(
                        r'\b(?:TODO|FIXME|TBD)\b', body
                    ):
                        errors.append(
                            f'{relative}: private path or unfinished scaffolding'
                        )
                    for target in LINK.findall(body):
                        uri = urlsplit(target)
                        if uri.scheme in ('https', 'http'):
                            continue
                        destination = (resource.parent / unquote(uri.path)).resolve()
                        if (
                            uri.scheme
                            or not destination.is_relative_to(root)
                            or not destination.exists()
                        ):
                            errors.append(f'{relative}: missing or escaping reference')
                        elif destination.suffix == '.sh' and not os.access(
                            destination, os.X_OK
                        ):
                            errors.append(
                                f'{relative}: referenced shell resource is not executable'
                            )
                    for module in re.findall(
                        r'uv run python -m (scripts\.[a-z_]+)', body
                    ):
                        if not (root / (module.replace('.', '/') + '.py')).is_file():
                            errors.append(f'{relative}: missing Python command module')
    if {entry.name for entry in discovery.iterdir()} != {
        entry.name for entry in folders
    }:
        errors.append('Codex discovery entries differ from the canonical catalog')
    for entry in discovery.iterdir():
        expected = '../../.claude/skills/' + entry.name
        if (
            not entry.is_symlink()
            or os.readlink(entry) != expected
            or not entry.resolve().is_relative_to(root)
            or not (entry / 'SKILL.md').is_file()
        ):
            errors.append(
                f'.agents/skills/{entry.name}: invalid relative discovery link'
            )
    commands = root / '.claude/commands'
    if commands.is_dir() and any(p.stem in names for p in commands.rglob('*.md')):
        errors.append('Claude command duplicates a discovered skill name')
    for name in ('AGENTS.md', 'CLAUDE.md'):
        path = root / name
        if not path.is_file():
            errors.append(f'{name}: missing operating entry point')
        elif matches(path.read_bytes()) or PRIVATE_PATH.search(path.read_text()):
            errors.append(f'{name}: suspected secret or machine-specific private path')
    if (root / 'CLAUDE.md').is_file() and '@AGENTS.md' not in (
        root / 'CLAUDE.md'
    ).read_text():
        errors.append('CLAUDE.md must explicitly import the canonical AGENTS.md')
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--root', type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    errors = validate(args.root)
    print(json.dumps({'passed': not errors, 'findings': errors}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
