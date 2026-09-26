from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

Locale = Literal['en', 'es']


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str


class SessionView(BaseModel):
    csrf_token: str
    expires_at: datetime
    retention_days: int = 7


class ConversationCreate(BaseModel):
    title: str = Field(default='New conversation', max_length=80)


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=80)


class ConversationView(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class Page(BaseModel):
    items: list[ConversationView]
    next_cursor: str | None = None


class MessageView(BaseModel):
    id: UUID
    role: Literal['user', 'assistant']
    content: str
    citations: list['Citation'] = []
    created_at: datetime


class MessagePage(BaseModel):
    items: list[MessageView]
    next_cursor: str | None = None


class Citation(BaseModel):
    id: str
    label: str
    url: str
    source_type: Literal['page', 'code']
    commit_sha: str | None = None
    path: str | None = None
    start_line: int | None = None
    end_line: int | None = None


class SendMessage(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    locale: Locale = 'en'


class RunView(BaseModel):
    id: UUID
    conversation_id: UUID
    state: Literal['pending', 'running', 'completed', 'failed', 'cancelled', 'interrupted']
    message_id: UUID | None = None
    error_code: str | None = None
    created_at: datetime
    updated_at: datetime


class FeedbackCreate(BaseModel):
    rating: Literal['up', 'down']


class SSEEnvelope(BaseModel):
    type: Literal['run.started', 'run.status', 'message.delta', 'message.completed', 'run.completed', 'run.failed', 'run.cancelled']
    schema_version: Literal['1'] = '1'
    run_id: UUID
    conversation_id: UUID
    sequence: int
    timestamp: datetime
    payload: dict
