"""Pure domain and application invariants checked over generated inputs."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from portfolio_assistant.domain.analytics_periods import calendar_window
from portfolio_assistant.domain.budget import MAX_INPUT_TOKENS, MAX_OUTPUT_TOKENS, Budget
from portfolio_assistant.domain.evidence import ALIASES, lexical_score, tokens
from portfolio_assistant.domain.portfolio_paths import (
    canonical_key,
    key_paths,
    profile_parts,
    profile_paths,
)
from portfolio_assistant.domain.privacy import SECRET, minimize_visitor_text
from portfolio_assistant.domain.web_budget import WebBudget

if TYPE_CHECKING:
    from portfolio_assistant.domain.evidence import EvidenceRecord

pytestmark = pytest.mark.property

LOCALES = st.sampled_from(("en", "es"))
TOPICS = st.sampled_from(("profile", "experience", "projects", "education"))
SLUGS = st.from_regex(r"[a-z0-9]+(?:-[a-z0-9]+)*", fullmatch=True)
PRICE = st.decimals(min_value=Decimal("0.01"), max_value=Decimal(100), places=2, allow_nan=False)


# Budget math ---------------------------------------------------------------


@st.composite
def budgets(draw):
    input_price, output_price = draw(PRICE), draw(PRICE)
    floor = (
        Decimal(MAX_INPUT_TOKENS) * input_price + Decimal(MAX_OUTPUT_TOKENS) * output_price
    ) / Decimal(1000000)
    reservation = floor + draw(st.decimals(min_value=0, max_value=5, places=2))
    cutoff = reservation + draw(st.decimals(min_value=0, max_value=50, places=2))
    monthly = cutoff + draw(st.decimals(min_value=0, max_value=50, places=2))
    return Budget(monthly, cutoff, reservation, input_price, output_price)


@given(budgets())
def test_reservation_never_exceeds_ceiling_and_covers_the_largest_request(budget):
    assert budget.reservation <= budget.cutoff <= budget.monthly
    assert budget.cost(MAX_INPUT_TOKENS, MAX_OUTPUT_TOKENS) <= budget.reservation


@given(
    budgets(),
    st.integers(0, MAX_INPUT_TOKENS),
    st.integers(0, MAX_OUTPUT_TOKENS),
    st.integers(0, 1000),
    st.integers(0, 1000),
)
def test_cost_is_nonnegative_and_monotone_in_usage(budget, tokens, out, more_in, more_out):
    assert budget.cost(tokens, out) >= 0
    assert budget.cost(tokens + more_in, out + more_out) >= budget.cost(tokens, out)


@given(budgets(), st.integers(max_value=-1, min_value=-(10**6)))
def test_negative_usage_is_rejected(budget, negative):
    with pytest.raises(ValueError):
        budget.cost(negative, 0)
    with pytest.raises(ValueError):
        budget.cost(0, negative)


@given(
    PRICE,
    PRICE,
    PRICE,
    st.integers(0, 2_000_000),
    st.integers(0, 10_000),
    st.integers(0, 5),
)
def test_web_cost_is_bounded_by_the_reserved_maximum_input_window(
    input_price, output_price, fee, inputs, outputs, calls
):
    budget = WebBudget(Decimal(1), input_price, output_price, fee)
    cost = budget.cost(min(inputs, 1050000), min(outputs, 2048), min(calls, 2))
    assert 0 <= cost <= budget.maximum


@given(PRICE, PRICE, PRICE, st.integers(0, 272000), st.integers(0, 4096))
def test_web_cost_never_underestimates_exact_arithmetic(
    input_price, output_price, fee, inputs, outputs
):
    budget = WebBudget(Decimal(1), input_price, output_price, fee)
    exact = (Decimal(inputs) * input_price + Decimal(outputs) * output_price) / Decimal(
        1000000
    ) + fee
    assert budget.cost(inputs, outputs, 1) >= exact


# Privacy minimization -------------------------------------------------------

EMAILS = st.builds(
    "{}@{}.{}".format,
    st.from_regex(r"[A-Za-z0-9][A-Za-z0-9._%+-]{0,19}", fullmatch=True),
    st.from_regex(r"[A-Za-z0-9-]{0,19}[A-Za-z0-9]", fullmatch=True),
    st.from_regex(r"[A-Za-z]{2,6}", fullmatch=True),
)
SECRETS = st.from_regex(r"sk-[A-Za-z0-9_-]{20,40}", fullmatch=True)
PHONES = st.from_regex(r"\+[0-9]{10,14}", fullmatch=True)
VISITOR_TEXT = st.text(max_size=300)


@given(VISITOR_TEXT)
def test_minimization_is_idempotent_and_never_longer(text):
    once = minimize_visitor_text(text)
    assert len(once) <= len(text)
    assert minimize_visitor_text(once) == once


@given(VISITOR_TEXT, SECRETS, EMAILS, PHONES, VISITOR_TEXT)
def test_minimization_removes_the_patterns_it_redacts(prefix, secret, email, phone, suffix):
    for token in (secret, email, phone):
        text = f"{prefix} {token} {suffix}"
        result = minimize_visitor_text(text)
        assert len(result) <= len(text)
        assert token not in result


@pytest.mark.xfail(
    strict=True,
    reason=(
        "EMAIL starts with \\b, so a local part with no leading word character "
        'is not redacted: minimize_visitor_text(" .@0.AA ") == " .@0.AA "'
    ),
)
def test_email_with_a_punctuation_only_local_part_is_redacted():
    assert ".@0.AA" not in minimize_visitor_text(" .@0.AA ")


@given(VISITOR_TEXT)
def test_minimized_text_has_no_remaining_secret_matches(text):
    result = minimize_visitor_text(text)
    assert SECRET.search(result) is None


@given(VISITOR_TEXT.filter(lambda text: "@" not in text and "+" not in text))
def test_text_without_redaction_triggers_only_changes_through_secrets(text):
    assume(SECRET.search(text) is None)
    assert minimize_visitor_text(text) == text


# Portfolio paths ------------------------------------------------------------


@given(LOCALES, TOPICS)
def test_canonical_key_is_layout_neutral_and_round_trips(locale, topic):
    current, legacy = profile_paths(locale, topic)
    key = canonical_key(current)
    assert key == canonical_key(legacy) == f"{locale}/{topic}"
    assert profile_parts(current) == profile_parts(legacy) == (locale, topic)
    assert set(key_paths(key)) == {current, legacy}
    assert all(canonical_key(path) == key for path in key_paths(key))


@given(LOCALES, TOPICS, SLUGS)
def test_entity_keys_round_trip_through_the_key_format(locale, topic, slug):
    legacy = profile_paths(locale, topic)[1]
    key = canonical_key(legacy, slug)
    assert key == f"{locale}/{topic}#{slug}"
    assert canonical_key(profile_paths(locale, topic)[0], slug) == key
    assert set(key_paths(key)) == set(profile_paths(locale, topic))


@given(st.text(max_size=60))
def test_non_profile_paths_are_returned_unchanged_and_reject_entities(path):
    assume(profile_parts(path) is None)
    assert canonical_key(path) == path
    with pytest.raises(ValueError):
        canonical_key(path, "entity")


# Analytics periods ----------------------------------------------------------

INSTANTS = st.datetimes(
    min_value=datetime(2001, 1, 1),
    max_value=datetime(2099, 12, 31),
    timezones=st.one_of(
        st.just(UTC),
        st.just(ZoneInfo("America/Argentina/Buenos_Aires")),
        st.builds(timezone, st.timedeltas(timedelta(hours=-12), timedelta(hours=14))),
    ),
)
PERIODS = st.sampled_from(("day", "week", "month"))


@given(INSTANTS, PERIODS, st.integers(0, 2))
def test_calendar_window_is_half_open_aligned_and_timezone_independent(now, period, offset):
    window = calendar_window(now, period, offset)
    assert window.start < window.end
    if period == "week":
        assert window.start.weekday() == 0 and (window.end - window.start).days == 7
    if period == "month":
        assert window.start.day == 1 and window.end.day == 1
    if period == "day":
        assert (window.end - window.start).days == 1
    today = now.astimezone(UTC).date()
    assert window.partial == (window.start <= today < window.end)
    assert window.partial == (offset == 0)
    # Same instant expressed in any offset yields the same window.
    assert calendar_window(now.astimezone(UTC), period, offset) == window


@given(INSTANTS, PERIODS)
def test_calendar_windows_tile_without_gaps(now, period):
    older = calendar_window(now, period, 1)
    newer = calendar_window(now, period, 0)
    assert older.end == newer.start


@given(INSTANTS, PERIODS, st.integers(0, 2))
def test_calendar_window_contains_the_utc_day_it_describes(now, period, offset):
    window = calendar_window(now, period, offset)
    probe = datetime.combine(window.start, datetime.min.time(), tzinfo=UTC)
    assert calendar_window(probe, period, 0).start == window.start


@given(
    st.datetimes(min_value=datetime(2001, 1, 1), max_value=datetime(2099, 12, 31)),
    PERIODS,
    st.integers().filter(lambda value: not 0 <= value <= 2),
)
def test_invalid_offsets_and_naive_instants_are_rejected(naive, period, offset):
    with pytest.raises(ValueError):
        calendar_window(naive, period, 0)
    with pytest.raises(ValueError):
        calendar_window(naive.replace(tzinfo=UTC), period, offset)


# Evidence scoring -----------------------------------------------------------


def _legacy_lexical_score(row: EvidenceRecord, terms: set[str], locale: str) -> float:
    """Freeze the operation order and multipliers before the complexity refactor."""
    content = tokens(row["content"])
    path = tokens(row["path"])
    if row["path"] == "README.md":
        path.add("portfolio")
    expanded = terms | set().union(*(ALIASES.get(term, set()) for term in terms))
    anchors = expanded & (content | path)
    if not anchors:
        return 0
    score = 3.0 * len(terms & (content | path)) + len(anchors) + 2 * len(expanded & path)
    if "portfolio" in terms and row["path"] == "README.md":
        score *= 2
        if "Engineering at a glance" in row["content"]:
            score *= 5
    if (
        terms & {"study", "studied", "estudio", "estudios"}
        and row["path"].endswith("/education.ts")
        and row["start_line"] == 1
    ):
        score *= 5
    if (
        row["path"].endswith("/experience.ts")
        and "contributions:" in row["content"]
        and terms & content
    ):
        score *= 3
    if row["path"].endswith("/projects.ts") and terms & content:
        tech = bool(terms & {"technologies", "technology", "tecnologias", "stack"})
        if (tech and "stack: technologyNames" in row["content"]) or (
            not tech and "summary:" in row["content"]
        ):
            score *= 3
    profile = profile_parts(row["path"])
    if profile is not None and profile[0] == locale:
        score *= 1.35
    elif profile is not None:
        score *= 0.45
    return score


def _evidence_row(path: str, content: str, start_line: int) -> EvidenceRecord:
    return {
        "path": path,
        "content": content,
        "start_line": start_line,
        "end_line": start_line,
        "url": "",
        "content_hash": "",
    }


@pytest.mark.parametrize(
    ("path", "content", "start_line", "terms", "locale", "expected"),
    [
        ("README.md", "", 1, set(), "en", 0),
        ("README.md", "", 1, {"portfolio"}, "en", 12.0),
        ("README.md", "Engineering at a glance", 1, {"portfolio"}, "en", 60.0),
        ("src/content/en/education.ts", "University", 1, {"study"}, "en", 27.0),
        ("content/en/education.ts", "University", 2, {"study"}, "es", 1.8),
        ("other/experience.ts", "contributions: agents", 1, {"agents"}, "en", 12.0),
        ("other/experience.ts", "contributions: agents", 1, {"ai"}, "en", 1.0),
        ("other/projects.ts", "stack: technologyNames", 1, {"stack"}, "en", 12.0),
        ("other/projects.ts", "summary: stack", 1, {"stack"}, "en", 4.0),
        ("other/projects.ts", "summary: agents", 1, {"agents"}, "en", 12.0),
        ("other/projects.ts", "stack: technologyNames, agents", 1, {"agents"}, "en", 4.0),
        ("other/projects.ts", "summary: agents", 1, {"ai"}, "en", 1.0),
    ],
)
def test_lexical_score_applies_only_the_matching_boosts(
    path, content, start_line, terms, locale, expected
):
    assert lexical_score(_evidence_row(path, content, start_line), terms, locale) == expected


@given(
    st.one_of(
        st.sampled_from(("README.md", "docs/README.md")),
        st.builds(
            lambda locale, topic, legacy: profile_paths(locale, topic)[legacy],
            LOCALES,
            TOPICS,
            st.integers(0, 1),
        ),
    ),
    st.lists(
        st.sampled_from(
            (
                "Engineering at a glance",
                "contributions:",
                "stack: technologyNames",
                "summary:",
                "Tecnologías",
                "English",
                "university",
                "agents",
                "portfolio",
            )
        )
        | st.text(max_size=60),
        max_size=9,
    ).map(" ".join),
    st.integers(1, 3),
    st.sets(st.sampled_from((*ALIASES, "portfolio", "agents", "technology", "stack", "english"))),
    LOCALES,
)
def test_lexical_score_matches_the_frozen_implementation(path, content, start_line, terms, locale):
    row = _evidence_row(path, content, start_line)
    actual = lexical_score(row, terms, locale)
    expected = _legacy_lexical_score(row, terms, locale)
    assert type(actual) is type(expected)
    assert float(actual).hex() == float(expected).hex()
