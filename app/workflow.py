import asyncio
import os
from decimal import Decimal
from typing import TypedDict

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph

from .config import settings
from .ledger import reserve, settle
from .provider import OpenAIAdapter, fixture_message


class State(TypedDict):
    question: str
    locale: str
    evidence: str
    answer: str
    run_id: str


def generate(state: State) -> dict:
    if not state['evidence']:
        return {'answer': fixture_message(state['question'], '', state['locale'])}
    if settings().ai_provider == 'fixture':
        return {'answer': fixture_message(state['question'], state['evidence'], state['locale'])}
    if settings().ai_provider != 'openai' or not settings().allow_paid_ai:
        raise RuntimeError('provider_disabled')
    reserve(state['run_id'], Decimal(settings().reservation_usd))
    adapter = OpenAIAdapter.from_config()
    answer = asyncio.run(adapter.complete(state['question'], state['evidence']))
    usage = getattr(adapter, 'usage', None)
    if usage and getattr(usage, 'input_tokens', None) is not None and getattr(usage, 'output_tokens', None) is not None:
        settle(state['run_id'], usage.input_tokens, usage.output_tokens)
    return {'answer': answer}



builder = StateGraph(State)
builder.add_node('generate', generate)
builder.add_edge(START, 'generate')
builder.add_edge('generate', END)
os.environ.setdefault('LANGGRAPH_STRICT_MSGPACK', 'true')


def run_workflow(state: State, thread_id: str) -> State:
    with PostgresSaver.from_conn_string(settings().database_url) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        return graph.invoke(state, config={'configurable': {'thread_id': thread_id}})


def delete_checkpoint(thread_id: str) -> None:
    with PostgresSaver.from_conn_string(settings().database_url) as checkpointer:
        checkpointer.delete_thread(thread_id)
