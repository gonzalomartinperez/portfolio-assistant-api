from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Session:
    id: UUID
    csrf_token: str
    expires_at: datetime


@dataclass(frozen=True)
class Conversation:
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Message:
    id: UUID
    role: str
    content: str
    citations: list[dict[str, object]]
    created_at: datetime


@dataclass(frozen=True)
class Run:
    id: UUID
    conversation_id: UUID
    state: str
    message_id: UUID | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime
