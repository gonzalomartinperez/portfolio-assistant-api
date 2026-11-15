"""Characterization of OpenAIWebSearch.search: every guard, cache and rejection path."""

import asyncio
import time
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from openai import APIError

from app.adapters.providers.web_search import CacheEntry, OpenAIWebSearch
from app.application.web_context import WebReference, WebSupplement
from app.domain.errors import BudgetExhaustedError, ProviderUnavailableError
from app.domain.web_policy import TOPICS, WebTopic

TOPIC = TOPICS[0]
BASE = "https://docs.langchain.com/oss/"
USAGE = SimpleNamespace(input_tokens=7, output_tokens=3)


class Ledger:
    def __init__(self, exhausted=False):
        self.exhausted = exhausted
        self.reserved = 0
        self.settled = []

    async def reserve(self):
        if self.exhausted:
            raise BudgetExhaustedError("budget")
        self.reserved += 1
        return uuid4()

    async def settle(self, identifier, inputs, outputs, calls):
        self.settled.append((inputs, outputs, calls))


def citation(url=BASE, title="Doc", kind="url_citation"):
    return SimpleNamespace(type=kind, title=title, url=url)


def message(*annotations, kind="output_text"):
    return SimpleNamespace(
        type="message", content=[SimpleNamespace(type=kind, annotations=list(annotations))]
    )


def reply(
    output=None,
    text="Summary",
    status="completed",
    calls=1,
    usage=USAGE,
):
    items = [SimpleNamespace(type="web_search_call") for _ in range(calls)]
    items += [message(citation())] if output is None else output
    return SimpleNamespace(status=status, output_text=text, usage=usage, output=items)


def make(result=None, error=None, ledger=None, timeout=1):
    class Responses:
        def __init__(self):
            self.count = 0

        async def create(self, **kwargs):
            self.count += 1
            if error is not None:
                raise error
            return result

    responses = Responses()
    ledger = ledger or Ledger()
    return OpenAIWebSearch(SimpleNamespace(responses=responses), ledger, timeout), ledger, responses


def run(search, topic=TOPIC):
    return asyncio.run(search.search(topic))


def test_unsupported_topic_is_rejected_before_any_work():
    search, ledger, responses = make(reply())
    with pytest.raises(ValueError, match="^unsupported public technical topic$"):
        run(search, WebTopic("Other", "example.org", "q"))
    assert ledger.reserved == 0 and responses.count == 0


def test_fresh_positive_and_negative_cache_entries_short_circuit():
    search, ledger, responses = make(reply())
    value = WebSupplement("x", "cached", ())
    search.cache[TOPIC.name] = CacheEntry(time.monotonic() + 100, value)
    assert run(search) is value
    search.cache[TOPIC.name] = CacheEntry(time.monotonic() + 100, None)
    assert run(search) is None
    assert ledger.reserved == 0 and responses.count == 0


def test_expired_cache_entry_is_refreshed():
    search, ledger, _ = make(reply())
    search.cache[TOPIC.name] = CacheEntry(time.monotonic() - 1, None)
    assert run(search) is not None and ledger.reserved == 1


def test_lock_wait_timeout_returns_none_without_reserving_or_releasing():
    async def scenario():
        search, ledger, responses = make(reply(), timeout=0.05)
        lock = search.locks[TOPIC.name]
        await lock.acquire()
        assert await search.search(TOPIC) is None
        assert lock.locked() and ledger.reserved == 0 and responses.count == 0
        assert search.cache == {}

    asyncio.run(scenario())


def test_cache_filled_while_waiting_for_the_lock_is_reused():
    async def scenario():
        search, ledger, responses = make(reply())
        lock = search.locks[TOPIC.name]
        await lock.acquire()
        task = asyncio.create_task(search.search(TOPIC))
        await asyncio.sleep(0)
        value = WebSupplement("x", "filled", ())
        search.cache[TOPIC.name] = CacheEntry(time.monotonic() + 100, value)
        lock.release()
        assert await task is value
        assert not lock.locked() and ledger.reserved == 0 and responses.count == 0

    asyncio.run(scenario())


def test_exhausted_budget_returns_none_without_caching_and_releases_lock():
    search, _, responses = make(reply(), ledger=Ledger(exhausted=True))
    assert run(search) is None
    assert responses.count == 0 and search.cache == {}
    assert not search.locks[TOPIC.name].locked()


def test_provider_api_error_is_masked_and_releases_lock():
    error = APIError("secret detail", httpx.Request("POST", "https://x.test"), body=None)
    search, ledger, _ = make(error=error)
    with pytest.raises(ProviderUnavailableError, match="^provider_unavailable$") as caught:
        run(search)
    assert caught.value.__cause__ is None and caught.value.__suppress_context__
    assert ledger.reserved == 1 and ledger.settled == [] and search.cache == {}
    assert not search.locks[TOPIC.name].locked()


def test_successful_lookup_settles_usage_and_caches_for_an_hour():
    search, ledger, _ = make(reply(text=f"See {BASE}"))
    before = time.monotonic()
    value = run(search)
    assert value == WebSupplement(TOPIC.name, f"See {BASE}", (WebReference("Doc", BASE),))
    assert ledger.settled == [(7, 3, 1)]
    entry = search.cache[TOPIC.name]
    assert entry.value is value and 3599 < entry.expires - before < 3601


def test_missing_usage_skips_settlement_but_still_returns_value():
    search, ledger, _ = make(reply(usage=None))
    assert run(search) is not None
    assert ledger.reserved == 1 and ledger.settled == []


@pytest.mark.parametrize(
    ("status", "calls"),
    [("incomplete", 1), ("failed", 2), ("completed", 0), ("completed", 3)],
)
def test_incomplete_or_wrong_call_count_is_unavailable_but_settled(status, calls):
    search, ledger, _ = make(reply(status=status, calls=calls))
    before = time.monotonic()
    assert run(search) is None
    assert ledger.settled == [(7, 3, calls)]
    entry = search.cache[TOPIC.name]
    assert entry.value is None and 59 < entry.expires - before < 61


def test_two_search_calls_are_accepted():
    search, _, _ = make(reply(calls=2))
    assert run(search) is not None


def test_unrelated_items_contents_and_annotations_are_ignored():
    output = [
        SimpleNamespace(type="reasoning"),
        message(citation(kind="file_citation"), kind="refusal"),
        message(citation(kind="file_citation")),
        message(citation(BASE + "a", "A")),
    ]
    search, _, _ = make(reply(output=output, text="Body"))
    value = run(search)
    assert value.references == (WebReference("A", BASE + "a"),)


def test_attribution_is_canonicalized_in_text_and_references():
    output = [message(citation(BASE + "?utm_source=openai", "A"))]
    search, _, _ = make(reply(output=output, text=f"x {BASE}?utm_source=openai y"))
    value = run(search)
    assert value.text == f"x {BASE} y" and value.references == (WebReference("A", BASE),)


def test_outside_citation_rejects_whole_answer_with_short_negative_cache():
    output = [message(citation(BASE + "a", "A"), citation("https://evil.test/", "E"))]
    search, ledger, _ = make(reply(output=output))
    assert run(search) is None
    assert ledger.settled == [(7, 3, 1)] and search.cache[TOPIC.name].value is None


def test_references_are_deduplicated_titled_truncated_and_capped_at_four():
    annotations = [
        citation(BASE + "a", "A"),
        citation(BASE + "a", "A"),
        citation(BASE + "b", ""),
        citation(BASE + "c", "x" * 200),
        citation(BASE + "d", "D"),
        citation(BASE + "e", "E"),
        citation(BASE + "f", "F"),
    ]
    search, _, _ = make(reply(output=[message(*annotations)]))
    value = run(search)
    assert [ref.url for ref in value.references] == [BASE + s for s in "acde"]
    assert value.references[1].title == "x" * 160


def test_answer_without_usable_references_is_unavailable():
    for output in ([message()], [message(citation(BASE, ""))]):
        search, _, _ = make(reply(output=output))
        assert run(search) is None
        assert search.cache[TOPIC.name].value is None


@pytest.mark.parametrize(
    ("text", "accepted"), [("", False), ("a", True), ("a" * 6000, True), ("a" * 6001, False)]
)
def test_text_length_bounds_are_inclusive(text, accepted):
    search, _, _ = make(reply(text=text))
    assert (run(search) is not None) is accepted


def test_timeout_is_unavailable_with_negative_cache_and_unsettled():
    class Slow:
        async def create(self, **kwargs):
            await asyncio.Event().wait()

    ledger = Ledger()
    search = OpenAIWebSearch(SimpleNamespace(responses=Slow()), ledger, timeout=0.05)
    assert run(search) is None
    assert ledger.reserved == 1 and ledger.settled == []
    assert search.cache[TOPIC.name].value is None
    assert not search.locks[TOPIC.name].locked()
