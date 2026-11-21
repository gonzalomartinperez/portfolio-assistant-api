"""Final answer markers and persisted source order must describe the same evidence."""

import asyncio
from dataclasses import replace
from uuid import uuid4

import pytest

from portfolio_assistant.application.contracts import WorkflowEvent
from portfolio_assistant.application.runs import RunService, citations, normalize_citation_markers
from tests.support import FixedClock
from tests.unit.test_workflow import SOURCE, Store


@pytest.mark.parametrize(
    ("text", "expected", "indices"),
    [
        ("First [1], fifth [5].", "First [1], fifth [2].", [1, 5]),
        (
            "Fifth [5], second [2], fifth [5].",
            "Fifth [2], second [1], fifth [2].",
            [2, 5],
        ),
        ("Only [5].", "Only [1].", [5]),
        ("No factual claim.", "No factual claim.", []),
        ("`array[99]` and claim [5].", "`array[99]` and claim [1].", [5]),
        (
            "[7](https://example.test) and [5].",
            "[7](https://example.test) and [1].",
            [5],
        ),
        (
            "```python\nx = [9]\n```\nClaim [5].",
            "```python\nx = [9]\n```\nClaim [1].",
            [5],
        ),
    ],
)
def test_noncontiguous_references_preserve_code_links_and_evidence(text, expected, indices):
    sources = tuple(replace(SOURCE, id=str(index)) for index in range(1, 6))
    assert normalize_citation_markers(text, len(sources)) == expected
    assert [source["id"] for source in citations(sources, text, None)] == [
        str(index) for index in indices
    ]


@pytest.mark.parametrize("text", ["Unsupported [0].", "Unsupported [6]."])
def test_unknown_references_are_rejected_before_normalization(text):
    with pytest.raises(ValueError, match="invalid source reference"):
        normalize_citation_markers(text, 5)


def test_stream_final_and_persistence_use_the_same_canonical_answer():
    sources = tuple(replace(SOURCE, id=str(index)) for index in range(1, 6))

    class Workflow:
        async def stream(self, command):
            yield WorkflowEvent("evidence", sources=sources)
            for text in ("Claim [", "5], another [", "2]."):
                yield WorkflowEvent("delta", text=text)
            yield WorkflowEvent("answer", text="Claim [5], another [2].")

    class RecordingStore(Store):
        async def complete(self, run_id, conversation_id, answer, refs):
            self.refs = refs
            return await super().complete(run_id, conversation_id, answer, refs)

    async def run():
        store = RecordingStore()
        service = RunService(store, Workflow(), fixture=False, clock=FixedClock())
        events = [event async for event in service.execute(uuid4(), uuid4(), "question", "en")]
        assert "".join(
            event.payload["text"] for event in events if event.name == "message.delta"
        ) == ("Claim [5], another [2].")
        final = next(event.payload for event in events if event.name == "message.completed")
        assert store.answer == final["content"] == "Claim [2], another [1]."
        assert final["citations"] == store.refs
        assert [source["id"] for source in store.refs] == ["2", "5"]
        assert events[-1].name == "run.completed"

    asyncio.run(run())


@pytest.mark.parametrize(
    ("fixture", "support"), [(True, None), (False, lambda content, answer, path: True)]
)
def test_run_service_rejects_inconsistent_fixture_wiring(fixture, support):
    with pytest.raises(ValueError, match="citation_support"):
        RunService(Store(), object(), fixture=fixture, citation_support=support, clock=FixedClock())
