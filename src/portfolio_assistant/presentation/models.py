from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from portfolio_assistant.application.presentation_context import PortfolioPath, Presentation, Theme
from portfolio_assistant.presentation.problems import ErrorBody

__all__ = ["ErrorBody"]

Locale = Literal["en", "es"]


class HealthView(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"status": "ok", "version": "0123456789abcdef0123456789abcdef01234567"}]
        }
    )

    status: Literal["ok"]
    version: str


class ReadinessView(HealthView):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ok",
                    "version": "0123456789abcdef0123456789abcdef01234567",
                    "schema_version": "009",
                }
            ]
        }
    )

    schema_version: str | None


class SessionView(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "csrf_token": "opaque-csrf-token",
                    "expires_at": "2026-11-29T12:00:00Z",
                    "retention_days": 7,
                }
            ]
        }
    )

    csrf_token: str
    expires_at: datetime
    retention_days: int = 7


class ConversationCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"title": "New conversation"}, {}]})

    title: str = Field(default="New conversation", max_length=80)


class ConversationUpdate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"title": "Filomena questions"}]})

    title: str = Field(min_length=1, max_length=80)


class ConversationView(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "00000000-0000-0000-0000-000000000002",
                    "title": "New conversation",
                    "created_at": "2026-11-22T12:00:00Z",
                    "updated_at": "2026-11-22T12:00:05Z",
                }
            ]
        }
    )

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class Page(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": "00000000-0000-0000-0000-000000000002",
                            "title": "New conversation",
                            "created_at": "2026-11-22T12:00:00Z",
                            "updated_at": "2026-11-22T12:00:05Z",
                        }
                    ],
                    "next_cursor": None,
                }
            ]
        }
    )

    items: list[ConversationView]
    next_cursor: str | None = None


class MessageView(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "00000000-0000-0000-0000-000000000003",
                    "role": "assistant",
                    "content": "Filomena is one of the projects described in the portfolio [1].",
                    "citations": [
                        {
                            "id": "3f2a000000000000000000000000000000000000000000000000000000000000",
                            "label": "src/content/en/projects.ts",
                            "url": "https://github.com/gonzalomartinperez/portfolio/blob/1acbe54906c88398652aebb8eae0c217fd0d8821/src/content/en/projects.ts#L1-L12",
                            "source_type": "code",
                            "commit_sha": "1acbe54906c88398652aebb8eae0c217fd0d8821",
                            "path": "src/content/en/projects.ts",
                            "start_line": 1,
                            "end_line": 12,
                        }
                    ],
                    "created_at": "2026-11-22T12:00:05Z",
                }
            ]
        }
    )

    id: UUID
    role: Literal["user", "assistant"]
    content: str
    citations: list[Citation] = []
    created_at: datetime


class MessagePage(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": "00000000-0000-0000-0000-000000000003",
                            "role": "assistant",
                            "content": "Filomena is one of the projects described in the portfolio [1].",
                            "citations": [
                                {
                                    "id": "3f2a000000000000000000000000000000000000000000000000000000000000",
                                    "label": "src/content/en/projects.ts",
                                    "url": "https://github.com/gonzalomartinperez/portfolio/blob/1acbe54906c88398652aebb8eae0c217fd0d8821/src/content/en/projects.ts#L1-L12",
                                    "source_type": "code",
                                    "commit_sha": "1acbe54906c88398652aebb8eae0c217fd0d8821",
                                    "path": "src/content/en/projects.ts",
                                    "start_line": 1,
                                    "end_line": 12,
                                }
                            ],
                            "created_at": "2026-11-22T12:00:05Z",
                        }
                    ],
                    "next_cursor": "2026-11-22T12:00:05+00:00",
                }
            ]
        }
    )

    items: list[MessageView]
    next_cursor: str | None = None


class Citation(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "3f2a000000000000000000000000000000000000000000000000000000000000",
                    "label": "src/content/en/projects.ts",
                    "url": "https://github.com/gonzalomartinperez/portfolio/blob/1acbe54906c88398652aebb8eae0c217fd0d8821/src/content/en/projects.ts#L1-L12",
                    "source_type": "code",
                    "commit_sha": "1acbe54906c88398652aebb8eae0c217fd0d8821",
                    "path": "src/content/en/projects.ts",
                    "start_line": 1,
                    "end_line": 12,
                }
            ]
        }
    )

    id: str
    label: str
    url: str
    source_type: Literal["page", "code"]
    commit_sha: str | None = None
    path: str | None = None
    start_line: int | None = None
    end_line: int | None = None


class MessageContext(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "theme": "dark",
                    "opened_path": "/work",
                    "current_path": "/about",
                    "presentation": "compact",
                }
            ]
        },
    )

    theme: Theme
    opened_path: PortfolioPath
    current_path: PortfolioPath
    presentation: Presentation


class SendMessage(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"content": "What is Filomena?", "locale": "en"},
                {"content": "¿Qué experiencia tiene Gonzalo?", "locale": "es"},
            ]
        }
    )

    content: str = Field(min_length=1, max_length=4000)
    locale: Locale = "en"
    context: MessageContext | None = None


class RunView(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "conversation_id": "00000000-0000-0000-0000-000000000002",
                    "state": "completed",
                    "message_id": "00000000-0000-0000-0000-000000000003",
                    "error_code": None,
                    "created_at": "2026-11-22T12:00:00Z",
                    "updated_at": "2026-11-22T12:00:05Z",
                }
            ]
        }
    )

    id: UUID
    conversation_id: UUID
    state: Literal["pending", "running", "completed", "failed", "cancelled", "interrupted"]
    message_id: UUID | None = None
    error_code: str | None = None
    created_at: datetime
    updated_at: datetime


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"rating": "up"}]})

    rating: Literal["up", "down"]


class StarterPrompt(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "projects",
                    "topic": "projects",
                    "question": "Which projects best illustrate Gonzalo’s work?",
                }
            ]
        }
    )

    id: str = Field(pattern=r"^[a-z0-9-]{1,80}$")
    topic: Literal["profile", "experience", "projects", "education", "achievement"]
    question: str = Field(min_length=1, max_length=500)


class SuggestionsView(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "corpus_version": "corpus-a4e4aa84b466",
                    "source_commit": "1acbe54906c88398652aebb8eae0c217fd0d8821",
                    "items": [
                        {
                            "id": "projects",
                            "topic": "projects",
                            "question": "Which projects best illustrate Gonzalo’s work?",
                        }
                    ],
                }
            ]
        }
    )

    corpus_version: str = Field(min_length=1, max_length=100)
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    items: list[StarterPrompt] = Field(max_length=6)
