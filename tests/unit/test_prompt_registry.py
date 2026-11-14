"""Prompt files, prompts.lock and rendering stay in step; assembled text never drifts."""

import asyncio
import re
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.adapters.prompts import default_prompts, load_prompts, prompt_files
from app.adapters.providers import answer
from app.domain.prompts import (
    PromptError,
    PromptSpec,
    lock_text,
    parse_prompt,
    prompt_version,
    render,
)

PROMPTS = Path(answer.__file__).parents[2] / 'prompts'
SNAPSHOTS = Path(__file__).parent / 'snapshots'


def copy_prompts(tmp_path: Path) -> Path:
    target = tmp_path / 'prompts'
    shutil.copytree(PROMPTS, target)
    return target


def test_committed_lock_matches_every_prompt_file():
    # Fails when a prompt changes without `python -m scripts.update_prompts_lock --write`.
    specs = load_prompts(PROMPTS)
    assert specs
    assert set(prompt_files(PROMPTS)) == {path.name for path in PROMPTS.glob('*.md')}
    assert lock_text(prompt_files(PROMPTS)) == (PROMPTS / 'prompts.lock').read_text()


def test_default_prompts_are_read_only():
    with pytest.raises(TypeError):
        default_prompts()['answer'] = None  # type: ignore[index]


def test_duplicate_prompt_id_fails(tmp_path):
    root = copy_prompts(tmp_path)
    (root / 'dup.md').write_text(
        (root / 'voice.en.md').read_text().replace('voice-en', 'voice-es')
    )
    (root / 'prompts.lock').write_text(lock_text(prompt_files(root)))
    with pytest.raises(PromptError, match='duplicate'):
        load_prompts(root)


def test_edited_prompt_without_lock_update_fails(tmp_path):
    root = copy_prompts(tmp_path)
    path = root / 'voice.en.md'
    path.write_text(path.read_text() + 'Extra instruction.\n')
    with pytest.raises(PromptError, match='without a prompts.lock update'):
        load_prompts(root)


def test_prompt_without_lock_entry_or_stale_entry_fails(tmp_path):
    root = copy_prompts(tmp_path)
    (root / 'new.md').write_text(
        '---\nid: new\nversion: 1\nowner: x\nlast-reviewed: 2026-11-14\n---\nHi\n'
    )
    with pytest.raises(PromptError, match='differ'):
        load_prompts(root)
    (root / 'new.md').unlink()
    (root / 'voice.es.md').unlink()
    with pytest.raises(PromptError, match='differ'):
        load_prompts(root)


def test_every_prompt_file_has_complete_front_matter():
    for name, data in prompt_files(PROMPTS).items():
        head = data.decode().split('---\n')[1]
        keys = [line.split(':')[0] for line in head.splitlines()]
        assert keys == ['id', 'version', 'owner', 'last-reviewed'], name


def test_missing_front_matter_fails():
    with pytest.raises(PromptError):
        parse_prompt(b'No front matter here\n')


def test_unknown_or_missing_placeholder_fails():
    spec = PromptSpec('x', '1', 'a' * 64, 'Date {current_date} {secret}')
    with pytest.raises(PromptError):
        render(spec, current_date='2026-11-14', secret='s')
    with pytest.raises(PromptError):
        render(PromptSpec('x', '1', 'a' * 64, 'Date {current_date}'))


def test_prompt_version_format():
    value = prompt_version(default_prompts().values())
    pieces = value.split(',')
    assert len(pieces) == 5
    assert all(re.fullmatch(r'[a-z-]+@1\+[0-9a-f]{12}', piece) for piece in pieces)
    assert answer.developer_prompt('es', True, date(2026, 11, 14))[1].startswith(
        'web-context@1+'
    )


@dataclass
class Web:
    text: str = 'web'


@pytest.mark.parametrize('locale', ['en', 'es'])
@pytest.mark.parametrize('web', [False, True])
def test_developer_message_is_byte_identical_to_the_inline_original(
    locale, web, monkeypatch
):
    captured = {}

    class Events:
        def __aiter__(self):
            return self.iterate()

        async def iterate(self):
            yield SimpleNamespace(
                type='response.completed',
                response=SimpleNamespace(
                    usage=SimpleNamespace(input_tokens=1, output_tokens=2)
                ),
            )

        async def close(self):
            pass

    class Responses:
        async def create(self, **kwargs):
            captured['message'] = kwargs['input'][0]['content']
            return Events()

    async def supplement(question, evidence, search):
        return Web() if search else None

    monkeypatch.setattr(answer, 'supplement', supplement)
    provider = answer.ResponsesProvider(
        SimpleNamespace(responses=Responses()),
        'model',
        web_search=object() if web else None,
        today=lambda: date(2026, 11, 14),
    )

    async def run():
        return [item async for item in provider.stream('q', 'evidence', locale)]

    usage = asyncio.run(run())[-1]
    name = f'developer_{locale}_{"web" if web else "plain"}.txt'
    assert captured['message'] == (SNAPSHOTS / name).read_text(encoding='utf-8')
    assert usage.prompt_version.startswith('web-context@' if web else 'answer@')


HEAD = b'---\nid: x\nversion: 1\nowner: o\nlast-reviewed: 2026-11-14\n---\n'


@pytest.mark.parametrize(
    'body',
    [
        b'stray } brace',
        b'open { brace',
        b'{language!r}',
        b'{current_date:>20}',
        b'{nope}',
    ],
)
def test_invalid_placeholders_fail_at_parse(body):
    with pytest.raises(PromptError):
        parse_prompt(HEAD + body + b'\n')


def test_escaped_braces_render_literally():
    spec = parse_prompt(HEAD + b'Use {{ok}} on {current_date}\n')
    assert render(spec, current_date='d') == 'Use {ok} on d'


def test_startup_fails_fast_on_a_bad_prompt_registry(monkeypatch):
    from app.bootstrap import container
    from app.bootstrap.config import Settings

    def broken():
        raise PromptError('stale lock')

    monkeypatch.setattr(container, 'default_prompts', broken)
    with pytest.raises(PromptError):
        container.create_app(Settings(_env_file=None))


def test_usage_settled_log_has_prompt_version_and_no_prompt_text(caplog):
    import contextlib
    from decimal import Decimal

    from app.adapters.postgres import ledger

    @contextlib.contextmanager
    def connection():
        yield SimpleNamespace(execute=lambda *args: None)

    version = 'answer@1+b4f38ad5eabb'
    with caplog.at_level('INFO', logger='portfolio_assistant'):
        ledger.settle(
            '00000000-0000-0000-0000-000000000001',
            1,
            2,
            connection=connection,
            input_price=Decimal(1),
            output_price=Decimal(1),
            prompt_version=version,
        )
    text = ' '.join(record.getMessage() for record in caplog.records)
    assert version in text
    assert 'AI assistant' not in text
