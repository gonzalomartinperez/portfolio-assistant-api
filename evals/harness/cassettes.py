"""Cassettes at the provider port (assistant-quality.md section 12, ADR013).

The unit recorded is one ``Provider.stream`` result: ordered text deltas plus ``Usage``
(including ``prompt_version``). The key is the sha256 of the canonical JSON of
(prompt_version, model id, reasoning effort, max_output_tokens, assembled messages
including evidence), where the messages come from the same pure function the real
provider uses, so a key always describes the request the provider would send. Files hold
only deltas, usage and the key metadata: no headers, no credentials, no request bodies.

Web search is outside the cassette lane (the key assumes no web supplement) and the
prompt date is pinned (``CASSETTE_DATE``) so a recording does not expire at midnight;
the recording provider must be built with the same pinned date.

``ReplayProvider`` is record mode ``none``: a missing key raises ``CassetteMissingError``
and is remembered in ``missing`` (the app may swallow the error as a failed run), so the
lane can exit with code 3. ``RecordingCassetteProvider`` writes missing keys only and is
the DR-04 hard stop: it refuses to run without ``ALLOW_PAID_AI`` and an explicit campaign
budget of at most USD 2, and refuses any call that could exceed the campaign cap or the
USD 8 monthly cap kept in the committed ledger.
"""

import hashlib
import json
import os
import re
from collections.abc import AsyncGenerator, Callable, Mapping
from contextlib import aclosing
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import ROUND_UP, Decimal
from pathlib import Path

from app.adapters.providers.answer import (
    REASONING_EFFORT,
    ModelRequest,
    assemble_request,
    visitor_inputs,
)
from app.application.contracts import Provider, Usage
from app.application.conversation_context import Turn
from app.application.presentation_context import PresentationContext
from app.domain.budget import MAX_OUTPUT_TOKENS
from app.domain.fixture import fixture_message

CASSETTE_ROOT = Path('evals/cassettes')
LEDGER_PATH = CASSETTE_ROOT / 'spend-ledger.json'
CASSETTE_DATE = date(2026, 11, 14)
RE_RECORD_MESSAGE = 're-record required: prompt, model or evidence changed'
EXIT_RE_RECORD = 3
CAMPAIGN_CAP_USD = Decimal('2.00')
MONTHLY_CAP_USD = Decimal('8.00')


class CassetteMissingError(Exception):
    """Record mode ``none`` found no cassette for the request key."""

    def __init__(self, key: str) -> None:
        super().__init__(f'{RE_RECORD_MESSAGE} (key {key})')
        self.key = key


class CassetteFormatError(ValueError):
    """A cassette file is not in the documented format."""


class RecordingRefusedError(Exception):
    """Recording was not authorized (paid AI flag or an explicit capped budget)."""


class SpendCapError(Exception):
    """A call could exceed the per-campaign or the monthly cap; nothing was sent."""


@dataclass(frozen=True)
class CassetteConfig:
    root: Path
    model: str
    reasoning_effort: str = REASONING_EFFORT
    max_output_tokens: int = MAX_OUTPUT_TOKENS
    today: date = CASSETTE_DATE


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def cassette_key(request: ModelRequest, config: CassetteConfig) -> str:
    payload = {
        'prompt_version': request.prompt_version,
        'model': config.model,
        'reasoning_effort': config.reasoning_effort,
        'max_output_tokens': config.max_output_tokens,
        'messages': request.messages,
    }
    return hashlib.sha256(canonical_json(payload).encode('utf-8')).hexdigest()


def prompt_slug(prompt_version: str) -> str:
    """Filesystem-safe directory name for a prompt_version (never a path component)."""
    return re.sub(r'[^A-Za-z0-9@+._-]+', '_', prompt_version).lstrip('.') or '_'


def cassette_path(root: Path, request: ModelRequest, key: str) -> Path:
    return root / prompt_slug(request.prompt_version) / f'{key}.jsonl'


def build_request(
    question: str,
    evidence: str,
    locale: str,
    history: tuple[Turn, ...],
    context: PresentationContext | None,
    config: CassetteConfig,
) -> ModelRequest:
    question, history = visitor_inputs(question, history)
    return assemble_request(
        question, evidence, locale, history, context, None, config.today
    )


@dataclass(frozen=True)
class Cassette:
    deltas: tuple[str, ...]
    usage: Usage | None


def read_cassette(path: Path, key: str) -> Cassette:
    deltas: list[str] = []
    usage: Usage | None = None
    meta = False
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        try:
            row = json.loads(line)
            kind = row['type']
            if kind == 'meta' and number == 1 and row['key'] == key:
                meta = True
            elif kind == 'delta' and meta and usage is None:
                deltas.append(str(row['text']))
            elif kind == 'usage' and meta and usage is None:
                usage = Usage(
                    int(row['input_tokens']),
                    int(row['output_tokens']),
                    row.get('prompt_version'),
                )
            else:
                raise CassetteFormatError(f'{path}:{number}: unexpected row')
        except (ValueError, KeyError, TypeError) as error:
            raise CassetteFormatError(f'{path}:{number}: invalid cassette') from error
    if not meta:
        raise CassetteFormatError(f'{path}: missing meta row for key')
    return Cassette(tuple(deltas), usage)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f'.{path.name}.tmp')
    temporary.write_text(text, encoding='utf-8')
    os.replace(temporary, path)


def write_cassette(
    path: Path,
    key: str,
    request: ModelRequest,
    config: CassetteConfig,
    deltas: list[str],
    usage: Usage | None,
) -> None:
    rows: list[dict[str, object]] = [
        {
            'type': 'meta',
            'key': key,
            'prompt_version': request.prompt_version,
            'model': config.model,
            'reasoning_effort': config.reasoning_effort,
            'max_output_tokens': config.max_output_tokens,
        },
        *({'type': 'delta', 'text': text} for text in deltas),  # type: ignore[list-item]
    ]
    if usage is not None:
        rows.append(
            {
                'type': 'usage',
                'input_tokens': usage.input_tokens,
                'output_tokens': usage.output_tokens,
                'prompt_version': usage.prompt_version,
            }
        )
    _atomic_write(path, ''.join(canonical_json(row) + '\n' for row in rows))


async def _replay(cassette: Cassette) -> AsyncGenerator[str | Usage]:
    for text in cassette.deltas:
        yield text
    if cassette.usage is not None:
        yield cassette.usage


class ReplayProvider:
    """Record mode ``none``: serve recorded streams, fail on a missing key."""

    def __init__(self, config: CassetteConfig) -> None:
        self.config = config
        self.missing: list[str] = []

    async def stream(
        self,
        question: str,
        evidence: str,
        locale: str,
        history: tuple[Turn, ...] = (),
        context: PresentationContext | None = None,
    ) -> AsyncGenerator[str | Usage]:
        if not evidence:  # The real provider answers without a model call.
            yield fixture_message(question, evidence, locale)
            return
        request = build_request(
            question, evidence, locale, history, context, self.config
        )
        key = cassette_key(request, self.config)
        path = cassette_path(self.config.root, request, key)
        if not path.is_file():
            self.missing.append(key)
            raise CassetteMissingError(key)
        async for item in _replay(read_cassette(path, key)):
            yield item


def load_ledger(path: Path) -> dict[str, Decimal]:
    """Read the committed month -> USD ledger; a missing or invalid file fails closed."""
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
        ledger = {str(month): Decimal(str(usd)) for month, usd in raw.items()}
    except (OSError, ValueError, AttributeError, ArithmeticError) as error:
        raise RecordingRefusedError(
            f'spend ledger {path} is missing or invalid'
        ) from error
    if any(
        not re.fullmatch(r'\d{4}-\d{2}', month) or not usd.is_finite() or usd < 0
        for month, usd in ledger.items()
    ):
        raise RecordingRefusedError(f'spend ledger {path} is invalid')
    return ledger


def recording_enabled(environ: Mapping[str, str] = os.environ) -> bool:
    """The explicit campaign switch: both flags, checked by the CLI and the recorder."""
    return (
        environ.get('EVAL_RECORDING') == '1'
        and environ.get('EVAL_ENVIRONMENT') == 'eval-live'
    )


def save_ledger(path: Path, ledger: dict[str, Decimal]) -> None:
    # Round charges up so the persisted total never understates the spend.
    body = {
        month: str(usd.quantize(Decimal('0.000001'), rounding=ROUND_UP))
        for month, usd in sorted(ledger.items())
    }
    _atomic_write(path, json.dumps(body, indent=2, sort_keys=True) + '\n')


class RecordingCassetteProvider:
    """Write missing cassettes by calling the real provider, under the DR-04 hard stop."""

    def __init__(
        self,
        inner: Provider,
        config: CassetteConfig,
        *,
        allow_paid_ai: bool,
        campaign_budget_usd: Decimal | None,
        input_usd_per_million: Decimal,
        output_usd_per_million: Decimal,
        ledger_path: Path = LEDGER_PATH,
        clock: Callable[[], date] = lambda: datetime.now(UTC).date(),
    ) -> None:
        if not recording_enabled():
            raise RecordingRefusedError(
                'recording requires EVAL_RECORDING=1 and EVAL_ENVIRONMENT=eval-live'
            )
        if not allow_paid_ai:
            raise RecordingRefusedError('recording requires ALLOW_PAID_AI=true')
        if any(
            not price.is_finite() or price <= 0
            for price in (input_usd_per_million, output_usd_per_million)
        ):
            raise RecordingRefusedError('token prices must be finite and positive')
        if (
            config.reasoning_effort != REASONING_EFFORT
            or config.max_output_tokens != MAX_OUTPUT_TOKENS
            or getattr(inner, 'model', config.model) != config.model
        ):
            raise RecordingRefusedError(
                'cassette config does not describe the request the provider sends'
            )
        if (
            campaign_budget_usd is None
            or not campaign_budget_usd.is_finite()
            or not 0 < campaign_budget_usd <= CAMPAIGN_CAP_USD
        ):
            raise RecordingRefusedError(
                f'recording requires an explicit --campaign-budget-usd of at most {CAMPAIGN_CAP_USD}'
            )
        load_ledger(ledger_path)
        self.inner = inner
        self.config = config
        self.budget = campaign_budget_usd
        self.input_price = input_usd_per_million
        self.output_price = output_usd_per_million
        self.ledger_path = ledger_path
        self.clock = clock
        self.spent = Decimal(0)
        self.recorded: list[str] = []

    def cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        return (
            Decimal(input_tokens) * self.input_price
            + Decimal(output_tokens) * self.output_price
        ) / 1_000_000

    def worst_case(self, request: ModelRequest) -> Decimal:
        """Upper bound of one call: bytes bound the input tokens, output is the maximum."""
        sent = sum(len(m['content'].encode('utf-8')) for m in request.messages)
        return self.cost(sent, self.config.max_output_tokens)

    def _guard(self, reserve: Decimal) -> None:
        month = f'{self.clock():%Y-%m}'
        month_total = load_ledger(self.ledger_path).get(month, Decimal(0))
        if self.spent + reserve > self.budget:
            raise SpendCapError(
                f'campaign budget USD {self.budget} would be exceeded; owner decides'
            )
        if month_total + reserve > MONTHLY_CAP_USD:
            raise SpendCapError(
                f'monthly eval cap USD {MONTHLY_CAP_USD} would be exceeded; owner decides'
            )

    def _charge(self, amount: Decimal) -> None:
        month = f'{self.clock():%Y-%m}'
        ledger = load_ledger(self.ledger_path)
        ledger[month] = ledger.get(month, Decimal(0)) + amount
        self.spent += amount
        save_ledger(self.ledger_path, ledger)

    async def stream(
        self,
        question: str,
        evidence: str,
        locale: str,
        history: tuple[Turn, ...] = (),
        context: PresentationContext | None = None,
    ) -> AsyncGenerator[str | Usage]:
        if not evidence:
            yield fixture_message(question, evidence, locale)
            return
        request = build_request(
            question, evidence, locale, history, context, self.config
        )
        key = cassette_key(request, self.config)
        path = cassette_path(self.config.root, request, key)
        if (
            path.is_file()
        ):  # Incremental: existing keys are replayed, never re-recorded.
            async for item in _replay(read_cassette(path, key)):
                yield item
            return
        reserve = self.worst_case(request)
        self._guard(reserve)
        deltas: list[str] = []
        usage: Usage | None = None
        complete = False
        try:
            async with aclosing(
                self.inner.stream(question, evidence, locale, history, context)
            ) as stream:
                async for item in stream:
                    if isinstance(item, Usage):
                        usage = item
                    else:
                        deltas.append(item)
                    yield item
            complete = True
        finally:
            # Absence of usage never implies a refund: charge the worst case.
            self._charge(
                self.cost(usage.input_tokens, usage.output_tokens)
                if usage is not None
                else reserve
            )
        if complete:
            write_cassette(path, key, request, self.config, deltas, usage)
            self.recorded.append(key)
