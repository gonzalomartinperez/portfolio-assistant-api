"""One bounded, checkpointed run. PostgreSQL session ownership stays in HTTP."""

import os
from decimal import Decimal
from typing import TypedDict

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from .config import settings
from .ledger import reserve, settle
from .provider import StreamingOpenAIAdapter, fixture_message
from .retrieval import retrieve


class State(TypedDict):
    question: str
    locale: str
    run_id: str
    strategy: str
    rows: list[dict]
    commits: list[str]
    evidence: str
    answer: str


def choose_strategy(state: State) -> dict:
    return {'strategy': 'hybrid'}


def find_evidence(state: State) -> dict:
    rows, commits = retrieve(state['question'], state['locale'], strategy=state['strategy'])
    return {'rows': [dict(row) for row in rows], 'commits': commits}


def validate_evidence(state: State) -> dict:
    rows = state['rows'][:5]
    # Bound model input and make the untrusted source boundary explicit.
    evidence = '\n'.join(f'PUBLIC SOURCE {row["path"]} lines {row["start_line"]}-{row["end_line"]}:\n{row["content"][:6000]}' for row in rows)
    return {'rows': rows, 'evidence': evidence[:22000]}


def generate(state: State) -> dict:
    writer = get_stream_writer()
    if not state['rows'] or settings().ai_provider == 'fixture':
        answer = fixture_message(state['question'], state['evidence'], state['locale'])
        for offset in range(0, len(answer), 48):
            writer({'type': 'delta', 'text': answer[offset:offset + 48]})
        return {'answer': answer}
    if settings().ai_provider != 'openai' or not settings().allow_paid_ai:
        raise RuntimeError('provider_disabled')
    reserve(state['run_id'], Decimal(settings().reservation_usd))
    adapter = StreamingOpenAIAdapter.from_config()
    parts = []
    for delta in adapter.stream(state['question'], state['evidence']):
        parts.append(delta)
        writer({'type': 'delta', 'text': delta})
    usage = adapter.usage
    if usage and getattr(usage, 'input_tokens', None) is not None and getattr(usage, 'output_tokens', None) is not None:
        settle(state['run_id'], usage.input_tokens, usage.output_tokens)
    # Unknown usage keeps the conservative reservation; failure never refunds incurred work.
    return {'answer': ''.join(parts)}


builder = StateGraph(State)
builder.add_node('strategy', choose_strategy)
builder.add_node('retrieve', find_evidence)
builder.add_node('validate', validate_evidence)
builder.add_node('generate', generate)
builder.add_edge(START, 'strategy')
builder.add_edge('strategy', 'retrieve')
builder.add_edge('retrieve', 'validate')
builder.add_edge('validate', 'generate')
builder.add_edge('generate', END)
os.environ.setdefault('LANGGRAPH_STRICT_MSGPACK', 'true')


def stream_workflow(state: State, thread_id: str):
    with PostgresSaver.from_conn_string(settings().database_url) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        yield from graph.stream(state, config={'configurable': {'thread_id': thread_id}}, stream_mode=['custom', 'updates'])


def delete_checkpoint(thread_id: str) -> None:
    with PostgresSaver.from_conn_string(settings().database_url) as checkpointer:
        checkpointer.delete_thread(thread_id)
