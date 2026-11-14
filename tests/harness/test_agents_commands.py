"""AGENTS.md, the justfile and the CI static job name the same commands (ecosystem 15.6)."""

import re

import yaml

from tests.support import ROOT

CI_ONLY = ('python3 -m scripts.ci_identity', 'uv sync --frozen', 'mkdir -p artifacts')


def recipes() -> dict[str, list[str]]:
    """Parse recipe bodies from the justfile without needing the `just` binary."""
    found: dict[str, list[str]] = {}
    current = None
    for line in (ROOT / 'justfile').read_text().splitlines():
        header = re.match(r'^([a-z][a-z0-9-]*)(?:\s+[^:]*)?:\s*$', line)
        if header:
            current = header[1]
            found[current] = []
        elif current and line.startswith('    ') and line.strip():
            found[current].append(line.strip().lstrip('@'))
        elif not line.strip() or line.startswith('#'):
            continue
        else:
            current = None
    return found


def static_job_commands() -> list[str]:
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    commands = []
    for step in workflow['jobs']['static']['steps']:
        if 'run' not in step or step.get('if'):
            continue
        for line in step['run'].strip().splitlines():
            if not line.startswith(CI_ONLY):
                commands.append(line.strip())
    return commands


def test_check_recipe_equals_ci_static_job():
    ci = static_job_commands()
    unit = [c for c in ci if c.startswith('uv run pytest')]
    assert len(unit) == 1
    assert recipes()['check'] == [c for c in ci if c not in unit]
    assert unit[0].startswith(recipes()['test'][0])


def test_agents_commands_are_runnable_recipes():
    agents = (ROOT / 'AGENTS.md').read_text()
    named = set(re.findall(r'`just ([a-z][a-z0-9-]*)`', agents))
    assert {'check', 'test'} <= named
    assert named <= set(recipes())
    body = '\n'.join(line for lines in recipes().values() for line in lines)
    for command in re.findall(r'`(uv run [^`]+)`', agents):
        assert command.replace('TEST_INTEGRATION=1 ', '') in body or command in body, (
            command
        )


def test_recipes_never_touch_secrets_or_paid_providers():
    text = (ROOT / 'justfile').read_text()
    assert '.env' not in text.replace('`.env*`', '')
    assert 'ALLOW_PAID_AI=true' not in text
    assert 'openai' not in text.lower()
