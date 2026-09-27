"""Public v1 stream payloads; framework-private events never cross this boundary."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.presentation.models import Citation


class Payload(BaseModel):
    model_config = ConfigDict(extra='forbid')


class StartedPayload(Payload):
    state: Literal['running']


class StatusPayload(Payload):
    phase: Literal['evidence_found']
    sources: int = Field(ge=0, le=5)


class DeltaPayload(Payload):
    text: str


class MessagePayload(Payload):
    message_id: UUID
    content: str
    citations: list[Citation]


class CompletedPayload(Payload):
    state: Literal['completed']


class FailedPayload(Payload):
    code: str


class Envelope(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal['1'] = '1'
    run_id: UUID
    conversation_id: UUID
    sequence: int = Field(ge=0)
    timestamp: datetime


class Started(Envelope):
    type: Literal['run.started']
    payload: StartedPayload


class Status(Envelope):
    type: Literal['run.status']
    payload: StatusPayload


class Delta(Envelope):
    type: Literal['message.delta']
    payload: DeltaPayload


class MessageCompleted(Envelope):
    type: Literal['message.completed']
    payload: MessagePayload


class Completed(Envelope):
    type: Literal['run.completed']
    payload: CompletedPayload


class Failed(Envelope):
    type: Literal['run.failed']
    payload: FailedPayload


class Cancelled(Envelope):
    type: Literal['run.cancelled']
    payload: Payload


StreamEvent = Annotated[
    Started | Status | Delta | MessageCompleted | Completed | Failed | Cancelled,
    Field(discriminator='type'),
]
events = TypeAdapter(StreamEvent)
