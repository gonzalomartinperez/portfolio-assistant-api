"""LangGraph implements the application workflow; no concrete I/O dependencies."""

from collections.abc import AsyncGenerator
from contextlib import aclosing
from dataclasses import asdict
from typing import Any, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from app.application.answer import generate
from app.application.contracts import (
    Accounting,
    AnswerCommand,
    Evidence,
    Provider,
    Retrieval,
    WorkflowEvent,
)


class State(TypedDict):
    question: str
    locale: str
    run_id: str
    sources: list[dict[str, Any]]
    answer: str


class LangGraphWorkflow:
    def __init__(
        self,
        retrieval: Retrieval,
        provider: Provider,
        accounting: Accounting | None = None,
        checkpointer: BaseCheckpointSaver[Any] | None = None,
    ) -> None:
        async def retrieve(state: State) -> dict[str, Any]:
            sources = await retrieval.search(state['question'], state['locale'])
            return {'sources': [asdict(s) for s in sources[:5]]}

        async def answer(state: State) -> dict[str, str]:
            writer = get_stream_writer()
            command = AnswerCommand(state['run_id'], state['question'], state['locale'])
            sources = tuple(Evidence(**s) for s in state['sources'])
            parts = []
            async with aclosing(
                generate(command, sources, provider, accounting)
            ) as stream:
                async for delta in stream:
                    parts.append(delta)
                    writer(delta)
            return {'answer': ''.join(parts)}

        builder = StateGraph(State)
        builder.add_node('retrieve', retrieve)
        builder.add_node('answer', answer)
        builder.add_edge(START, 'retrieve')
        builder.add_edge('retrieve', 'answer')
        builder.add_edge('answer', END)
        self.graph = builder.compile(checkpointer=checkpointer)

    async def stream(self, command: AnswerCommand) -> AsyncGenerator[WorkflowEvent]:
        state: State = {
            'question': command.question,
            'locale': command.locale,
            'run_id': command.run_id,
            'sources': [],
            'answer': '',
        }
        sources: tuple[Evidence, ...] = ()
        raw = self.graph.astream(
            state,
            config={
                'configurable': {'thread_id': command.run_id},
                'recursion_limit': 4,
            },
            stream_mode=['custom', 'updates'],
        )
        if not isinstance(raw, AsyncGenerator):
            raise TypeError('workflow stream must support explicit closure')
        async with aclosing(raw) as events:
            async for mode, event in events:
                if mode == 'custom':
                    yield WorkflowEvent('delta', text=event)
                elif 'retrieve' in event:
                    sources = tuple(Evidence(**s) for s in event['retrieve']['sources'])
                    yield WorkflowEvent('evidence', sources=sources)
                elif 'answer' in event:
                    yield WorkflowEvent(
                        'answer', text=event['answer']['answer'], sources=sources
                    )
