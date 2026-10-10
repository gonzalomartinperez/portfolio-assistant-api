"""LangGraph implements the application workflow; no concrete I/O dependencies."""

from collections.abc import AsyncGenerator
from contextlib import aclosing
from typing import TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from app.application.answer import bounded_sources, generate
from app.application.contracts import (
    Accounting,
    AnswerCommand,
    Evidence,
    Provider,
    Retrieval,
    WorkflowEvent,
)
from app.application.conversation_context import (
    Turn,
    bounded_history,
    retrieval_question,
)
from app.application.language import LanguageDetector, select_locale
from app.application.presentation_context import PresentationContext


class EvidenceData(TypedDict):
    id: str
    title: str
    url: str
    source_type: str
    commit_sha: str
    path: str
    start_line: int
    end_line: int
    content: str


def evidence_data(source: Evidence) -> EvidenceData:
    return {
        'id': source.id,
        'title': source.title,
        'url': source.url,
        'source_type': source.source_type,
        'commit_sha': source.commit_sha,
        'path': source.path,
        'start_line': source.start_line,
        'end_line': source.end_line,
        'content': source.content,
    }


class RetrievalUpdate(TypedDict):
    sources: list[EvidenceData]


class State(TypedDict):
    question: str
    history: tuple[Turn, ...]
    locale: str
    run_id: str
    sources: list[EvidenceData]
    answer: str
    context: PresentationContext | None


class LangGraphWorkflow:
    def __init__(
        self,
        retrieval: Retrieval,
        provider: Provider,
        accounting: Accounting | None = None,
        checkpointer: BaseCheckpointSaver[str] | None = None,
        detector: LanguageDetector | None = None,
    ) -> None:
        async def retrieve(state: State) -> RetrievalUpdate:
            sources = await retrieval.search(
                retrieval_question(state['question'], state['history']), state['locale']
            )
            return {'sources': [evidence_data(s) for s in bounded_sources(sources)]}

        async def answer(state: State) -> dict[str, str]:
            writer = get_stream_writer()
            command = AnswerCommand(
                state['run_id'],
                state['question'],
                state['locale'],
                state['history'],
                state['context'],
            )
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
        self.detector = detector

    async def stream(self, command: AnswerCommand) -> AsyncGenerator[WorkflowEvent]:
        history = bounded_history(command.history)
        locale = (
            select_locale(command.question, history, command.locale, self.detector)
            if self.detector
            else command.locale
        )
        state: State = {
            'question': command.question,
            'history': bounded_history(command.history),
            'locale': locale,
            'run_id': command.run_id,
            'sources': [],
            'answer': '',
            'context': command.context,
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
