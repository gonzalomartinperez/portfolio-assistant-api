"""Anonymous conversation policies. Storage authorization is atomic with mutations."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from app.domain.conversations import Conversation, Message, Run, Session
from app.domain.errors import RejectedError


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class ConversationStore(Protocol):
    """Storage operations that enforce ownership in each mutation transaction."""

    def session(self, secret_digest: str) -> Session | None:
        """Resolve an unexpired session by its secret digest."""
        ...

    def create_session(
        self, session_id: UUID, secret_digest: str, csrf: str, expires: datetime
    ) -> None:
        """Persist a generated anonymous credential digest and expiration."""
        ...

    def delete_session(self, session_id: UUID) -> None:
        """Delete owned data and enqueue checkpoint cleanup in the same transaction."""
        ...

    def rate_limit(self, subject_hash: str, operation: str, limit: int) -> None:
        """Atomically consume an hourly allowance or reject the operation."""
        ...

    def create(self, session_id: UUID, title: str) -> Conversation:
        """Create a conversation within the session storage limit."""
        ...

    def list_conversations(
        self, session_id: UUID, limit: int, cursor: datetime | None
    ) -> list[Conversation]:
        """Return a bounded page belonging to the requesting session."""
        ...

    def rename(
        self, session_id: UUID, conversation_id: UUID, title: str
    ) -> Conversation:
        """Rename an owned conversation or raise not_found."""
        ...

    def delete(self, session_id: UUID, conversation_id: UUID) -> None:
        """Delete an owned conversation and enqueue its checkpoint cleanup."""
        ...

    def messages(
        self,
        session_id: UUID,
        conversation_id: UUID,
        limit: int,
        cursor: datetime | None,
    ) -> list[Message]:
        """Return a bounded history page after checking conversation ownership."""
        ...

    def prepare_run(
        self,
        session_id: UUID,
        conversation_id: UUID,
        content: str,
        payload_hash: str,
        key: str,
    ) -> UUID:
        """Atomically enforce ownership, idempotency and run/history limits."""
        ...

    def run(self, session_id: UUID, run_id: UUID, cancel: bool = False) -> Run:
        """Read or cancel a run only when the requesting session owns it."""
        ...

    def feedback(self, session_id: UUID, message_id: UUID, rating: str) -> None:
        """Record feedback only for an owned assistant message."""
        ...


class Conversations:
    """Anonymous-session policies composed with an authorized persistence capability."""

    def __init__(
        self, store: ConversationStore, retention_days: int, rate_hash_key: str
    ):
        self.store = store
        self.retention_days = retention_days
        self.rate_hash_key = rate_hash_key

    def authenticate(self, raw: str | None) -> Session:
        session = self.store.session(digest(raw)) if raw else None
        if session is None:
            raise RejectedError('session_required', 401)
        return session

    def authorize_mutation(self, session: Session, token: str) -> Session:
        if not secrets.compare_digest(token, session.csrf_token):
            raise RejectedError('csrf_denied', 403)
        return session

    def bootstrap(self, subject: str) -> tuple[str, Session]:
        self.store.rate_limit(digest(self.rate_hash_key + subject), 'bootstrap', 20)
        raw, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        session = Session(
            uuid4(), csrf, datetime.now(UTC) + timedelta(days=self.retention_days)
        )
        self.store.create_session(session.id, digest(raw), csrf, session.expires_at)
        return raw, session

    def delete_session(self, session: Session) -> None:
        self.store.delete_session(session.id)

    def create(self, session: Session, title: str) -> Conversation:
        return self.store.create(session.id, title)

    def list_conversations(
        self, session: Session, limit: int, cursor: datetime | None
    ) -> list[Conversation]:
        if not 1 <= limit <= 50:
            raise RejectedError('invalid_limit')
        return self.store.list_conversations(session.id, limit + 1, cursor)

    def rename(
        self, session: Session, conversation_id: UUID, title: str
    ) -> Conversation:
        return self.store.rename(session.id, conversation_id, title)

    def delete(self, session: Session, conversation_id: UUID) -> None:
        self.store.delete(session.id, conversation_id)

    def messages(
        self,
        session: Session,
        conversation_id: UUID,
        limit: int,
        cursor: datetime | None,
    ) -> list[Message]:
        if not 1 <= limit <= 100:
            raise RejectedError('invalid_limit')
        return self.store.messages(session.id, conversation_id, limit + 1, cursor)

    def prepare_run(
        self,
        session: Session,
        conversation_id: UUID,
        content: str,
        payload_hash: str,
        key: str,
    ) -> UUID:
        self.store.rate_limit(
            digest(self.rate_hash_key + str(session.id)), 'message', 30
        )
        return self.store.prepare_run(
            session.id, conversation_id, content, payload_hash, key
        )

    def run(self, session: Session, run_id: UUID, cancel: bool = False) -> Run:
        return self.store.run(session.id, run_id, cancel)

    def feedback(self, session: Session, message_id: UUID, rating: str) -> None:
        self.store.feedback(session.id, message_id, rating)
