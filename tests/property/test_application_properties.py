"""Citation mapping, SSE framing, language policy, chunking and parser fuzzing."""

import asyncio
import json
import re
from dataclasses import dataclass, replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.adapters.portfolio.indexing import chunks, projection_spans
from app.adapters.portfolio.projection import PublicProjection
from app.application.contracts import Evidence
from app.application.language import explicit_locale, select_locale
from app.application.runs import (
    citations,
    normalize_citation_markers,
    referenced_sources,
)
from app.presentation.http import execute_run, sse
from scripts.scan_secrets import PATTERNS, matches

pytestmark = pytest.mark.property

SOURCE = Evidence(
    'id',
    'Public source',
    'https://example.test',
    'page',
    'a' * 40,
    'README.md',
    1,
    2,
    'x',
)

# Citation mapping -----------------------------------------------------------


@given(st.integers(1, 5), st.lists(st.integers(1, 5), max_size=8))
def test_citations_map_only_to_supplied_sources(count, numbers):
    assume(all(number <= count for number in numbers))
    sources = tuple(replace(SOURCE, id=str(index)) for index in range(1, count + 1))
    answer = ' '.join(f'claim [{number}]' for number in numbers)
    used = referenced_sources(answer, count)
    assert used == tuple(sorted(set(numbers)))
    mapped = citations(sources, answer, False)
    assert [item['id'] for item in mapped] == [str(number) for number in used]
    normalized = normalize_citation_markers(answer, count)
    # Normalized markers are the contiguous 1..len(used) range, in the same order.
    assert referenced_sources(normalized, len(used)) == tuple(range(1, len(used) + 1))
    assert len(re.findall(r'\[\d+\]', normalized)) == len(numbers)


@given(st.integers(0, 5), st.integers(0, 50))
def test_out_of_range_markers_are_rejected(count, number):
    assume(number < 1 or number > count)
    with pytest.raises(ValueError, match='invalid source reference'):
        referenced_sources(f'unsupported [{number}]', count)


@given(st.text(max_size=200).filter(lambda text: '[' not in text))
def test_text_without_markers_is_untouched_and_cites_nothing(text):
    assert referenced_sources(text, 3) == ()
    assert normalize_citation_markers(text, 3) == text


# SSE framing ----------------------------------------------------------------

TERMINAL = {
    'run.completed': {'state': 'completed'},
    'run.failed': {'code': 'provider_unavailable'},
    'run.cancelled': {},
}
EVENT_NAMES = {
    'run.started',
    'run.status',
    'message.delta',
    'message.completed',
    *TERMINAL,
}


def make_stream(deltas, terminal):
    body = [
        ('run.started', {'state': 'running'}),
        ('run.status', {'phase': 'evidence_found', 'sources': 1}),
        *(('message.delta', {'text': text}) for text in deltas),
        (
            'message.completed',
            {'message_id': str(uuid4()), 'content': ''.join(deltas), 'citations': []},
        ),
        (terminal, TERMINAL[terminal]),
    ]
    return [SimpleNamespace(name=name, payload=payload) for name, payload in body]


async def collect(stream):
    async def execute(*_):
        for event in stream:
            yield event

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(runs=SimpleNamespace(execute=execute))
        ),
        state=SimpleNamespace(request_id='r'),
    )
    return [
        frame
        async for frame in execute_run(request, uuid4(), uuid4(), 'q', 'en')  # type: ignore[arg-type]
    ]


@given(st.lists(st.text(max_size=30), max_size=6), st.sampled_from(sorted(TERMINAL)))
def test_stream_frames_use_the_closed_event_set_with_one_terminal(deltas, terminal):
    frames = asyncio.run(collect(make_stream(deltas, terminal)))
    parsed = []
    for frame in frames:
        assert re.fullmatch(r'event: [a-z.]+\ndata: \{.*\}\n\n', frame, re.DOTALL)
        header, data = frame[:-2].split('\n', 1)
        body = json.loads(data.removeprefix('data: '))
        assert header == f'event: {body["type"]}'
        parsed.append(body)
    assert {body['type'] for body in parsed} <= EVENT_NAMES
    assert [body['sequence'] for body in parsed] == list(range(len(parsed)))
    kinds = [body['type'] for body in parsed]
    assert sum(kind in TERMINAL for kind in kinds) == 1
    assert kinds[-1] == terminal and kinds[0] == 'run.started'


@given(st.text(max_size=20).filter(lambda name: name not in EVENT_NAMES))
def test_unknown_event_names_never_become_frames(name):
    with pytest.raises(ValidationError):
        sse(name, uuid4(), uuid4(), 0, {})


# Language policy ------------------------------------------------------------


@dataclass
class Detector:
    result: str | None

    def supported(self, _text):
        return self.result


@given(st.text(max_size=120))
def test_explicit_locale_is_total_and_closed(text):
    assert explicit_locale(text) in (None, 'en', 'es')


@given(
    st.text(max_size=80),
    st.sampled_from(('en', 'es', 'fr', '')),
    st.sampled_from((None, 'en', 'es')),
)
def test_selected_locale_is_always_supported_and_explicit_wins(
    question, hint, detected
):
    locale = select_locale(question, (), hint, Detector(detected))
    assert locale in ('en', 'es')
    explicit = explicit_locale(question)
    if explicit:
        assert locale == explicit
    elif detected:
        assert locale == detected
    else:
        assert locale == ('es' if hint == 'es' else 'en')


@given(st.sampled_from(('english', 'inglés', 'spanish', 'español')))
def test_explicit_requests_select_the_named_language_regardless_of_detector(name):
    expected = 'en' if name in ('english', 'inglés') else 'es'
    other = 'es' if expected == 'en' else 'en'
    assert (
        select_locale(f'please answer in {name}', (), other, Detector(other))
        == expected
    )


# Chunker --------------------------------------------------------------------

LINES = st.lists(
    st.text(
        st.characters(
            blacklist_categories=('Cs',),
            blacklist_characters='\r\x0b\x0c\x1c\x1d\x1e\x85  ',
        ),
        max_size=60,
    ),
    max_size=200,
)


@given(
    LINES,
    st.sampled_from(('src/content/en/profile.ts', 'README.md', 'docs/development.md')),
)
def test_chunks_are_ordered_disjoint_bounded_and_exact_slices(lines, path):
    content = '\n'.join(lines)
    split = content.splitlines()
    produced = list(chunks(path, content, 'a' * 40))
    previous_end = 0
    for chunk in produced:
        start, end = chunk['start_line'], chunk['end_line']
        assert previous_end < start <= end <= len(split)
        assert end - start + 1 <= 35
        assert chunk['content'] == '\n'.join(split[start - 1 : end]).strip()
        assert len(chunk['content']) >= 30
        previous_end = end
    assert len({chunk['id'] for chunk in produced}) == len(produced)
    assert produced == list(chunks(path, content, 'a' * 40))


@given(LINES)
def test_chunks_cover_every_line_that_carries_enough_text(lines):
    content = '\n'.join(lines)
    split = content.splitlines()
    covered = set()
    for chunk in chunks('src/content/en/profile.ts', content, 'a' * 40):
        covered.update(range(chunk['start_line'], chunk['end_line'] + 1))
    for number, line in enumerate(split, 1):
        if len(line.strip()) >= 30:
            assert number in covered


# Parser and validator fuzzing -----------------------------------------------

JSON = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(max_size=20),
    lambda inner: (
        st.lists(inner, max_size=4)
        | st.dictionaries(st.text(max_size=12), inner, max_size=5)
    ),
    max_leaves=15,
)


@given(JSON)
def test_projection_validator_rejects_arbitrary_json_deterministically(value):
    outcomes = []
    for _ in range(2):
        try:
            PublicProjection.model_validate(value)
            outcomes.append('ok')
        except ValidationError as error:
            outcomes.append(error.json())
    assert outcomes[0] == outcomes[1]


@given(st.text(max_size=300))
def test_projection_spans_only_fail_with_value_errors(content):
    try:
        list(projection_spans(content))
    except ValueError, IndexError:
        pass  # ValueError includes JSONDecodeError; IndexError is an unclosed array


@given(st.binary(max_size=400))
def test_secret_matcher_is_total_deterministic_and_names_only_known_detectors(data):
    found = matches(data)
    assert found == matches(data)
    assert set(found) <= set(PATTERNS)


@given(
    st.binary(max_size=40),
    st.from_regex(
        rb'(?:AKIA|ASIA)[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]{30,40}|sk-[A-Za-z0-9_-]{31,47}[A-Za-z0-9_]',
        fullmatch=True,
    ),
    st.binary(max_size=40),
)
def test_planted_tokens_are_detected_when_delimited(prefix, token, suffix):
    assume(not re.search(rb'\w$', prefix) and not re.search(rb'^\w', suffix))
    assert matches(prefix + b' ' + token + b' ' + suffix)


@pytest.mark.xfail(
    strict=True,
    reason=(
        'openai_token ends with \\b, so a key whose last character is "-" '
        'is not detected: matches(b"sk-" + b"-" * 32) == []'
    ),
)
@given(st.integers(32, 48))
def test_openai_style_tokens_ending_in_a_hyphen_are_detected(length):
    assert matches(b' sk-' + b'-' * length + b' ')
