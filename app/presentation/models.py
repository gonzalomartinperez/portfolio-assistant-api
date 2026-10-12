from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.application.presentation_context import PortfolioPath, Presentation, Theme

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
    citations: list[Citation] = []
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


class MessageContext(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    theme: Theme
    opened_path: PortfolioPath
    current_path: PortfolioPath
    presentation: Presentation


class SendMessage(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    locale: Locale = 'en'
    context: MessageContext | None = None


class RunView(BaseModel):
    id: UUID
    conversation_id: UUID
    state: Literal[
        'pending', 'running', 'completed', 'failed', 'cancelled', 'interrupted'
    ]
    message_id: UUID | None = None
    error_code: str | None = None
    created_at: datetime
    updated_at: datetime


class FeedbackCreate(BaseModel):
    rating: Literal['up', 'down']


class StarterPrompt(BaseModel):
    id: str = Field(pattern=r'^[a-z0-9-]{1,80}$')
    topic: Literal['profile', 'experience', 'projects', 'education', 'achievement']
    question: str = Field(min_length=1, max_length=500)


class SuggestionsView(BaseModel):
    corpus_version: str = Field(min_length=1, max_length=100)
    source_commit: str = Field(pattern=r'^[0-9a-f]{40}$')
    items: list[StarterPrompt] = Field(max_length=6)
