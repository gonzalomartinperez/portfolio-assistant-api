"""Stateful session and conversation lifecycle over an in-memory store."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    precondition,
    rule,
)

from app.application.conversations import Conversations, digest
from app.domain.conversations import Conversation, Message, Session
from app.domain.errors import RejectedError

pytestmark = pytest.mark.property

EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


class MemoryStore:
    """Ownership-enforcing fake of the ConversationStore port; ordering is by insertion."""

    def __init__(self) -> None:
        self.sessions: dict[str, Session] = {}
        self.conversations: dict[UUID, tuple[UUID, Conversation]] = {}
        self.history: dict[UUID, list[Message]] = {}
        self.ticks = 0

    def now(self) -> datetime:
        self.ticks += 1
        return EPOCH + timedelta(seconds=self.ticks)

    def session(self, secret_digest):
        return self.sessions.get(secret_digest)

    def create_session(self, session_id, secret_digest, csrf, expires):
        self.sessions[secret_digest] = Session(session_id, csrf, expires)

    def rate_limit(self, subject_hash, operation, limit):
        return None

    def delete_session(self, session_id):
        self.sessions = {
            key: value for key, value in self.sessions.items() if value.id != session_id
        }
        for identifier, (owner, _) in list(self.conversations.items()):
            if owner == session_id:
                del self.conversations[identifier]
                del self.history[identifier]

    def owned(self, session_id, conversation_id):
        entry = self.conversations.get(conversation_id)
        if entry is None or entry[0] != session_id:
            raise RejectedError('not_found', 404)
        return entry[1]

    def create(self, session_id, title):
        stamp = self.now()
        conversation = Conversation(uuid4(), title, stamp, stamp)
        self.conversations[conversation.id] = (session_id, conversation)
        self.history[conversation.id] = []
        return conversation

    def list_conversations(self, session_id, limit, cursor):
        rows = [c for owner, c in self.conversations.values() if owner == session_id]
        return sorted(rows, key=lambda row: row.created_at, reverse=True)[:limit]

    def rename(self, session_id, conversation_id, title):
        current = self.owned(session_id, conversation_id)
        renamed = Conversation(current.id, title, current.created_at, self.now())
        self.conversations[conversation_id] = (session_id, renamed)
        return renamed

    def delete(self, session_id, conversation_id):
        self.owned(session_id, conversation_id)
        del self.conversations[conversation_id]
        del self.history[conversation_id]

    def messages(self, session_id, conversation_id, limit, cursor):
        self.owned(session_id, conversation_id)
        return self.history[conversation_id][:limit]

    def prepare_run(self, session_id, conversation_id, content, payload_hash, key):
        self.owned(session_id, conversation_id)
        self.history[conversation_id].append(
            Message(uuid4(), 'user', content, [], self.now())
        )
        return uuid4()


class LifecycleMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.store = MemoryStore()
        self.service = Conversations(self.store, 30, 'key')
        self.sessions: list[tuple[str, Session]] = []
        self.live: dict[
            UUID, tuple[int, str]
        ] = {}  # conversation -> (owner index, title)
        self.deleted: set[UUID] = set()
        self.sent: dict[UUID, list[str]] = {}

    @rule()
    def open_session(self):
        if len(self.sessions) < 3:
            raw, session = self.service.bootstrap('visitor')
            self.sessions.append((raw, session))

    @precondition(lambda self: self.sessions)
    @rule(data=st.data(), title=st.text(min_size=1, max_size=20))
    def create(self, data, title):
        index = data.draw(st.integers(0, len(self.sessions) - 1))
        conversation = self.service.create(self.sessions[index][1], title)
        self.live[conversation.id] = (index, title)
        self.sent[conversation.id] = []

    @precondition(lambda self: self.live)
    @rule(data=st.data(), content=st.text(min_size=1, max_size=20))
    def send(self, data, content):
        identifier = data.draw(st.sampled_from(list(self.live)))
        owner = self.sessions[self.live[identifier][0]][1]
        self.service.prepare_run(owner, identifier, content, 'hash', 'k' * 8)
        self.sent[identifier].append(content)

    @precondition(lambda self: self.live)
    @rule(data=st.data(), title=st.text(min_size=1, max_size=20))
    def rename(self, data, title):
        identifier = data.draw(st.sampled_from(list(self.live)))
        owner = self.sessions[self.live[identifier][0]][1]
        assert self.service.rename(owner, identifier, title).title == title
        self.live[identifier] = (self.live[identifier][0], title)

    @precondition(lambda self: self.live)
    @rule(data=st.data())
    def delete(self, data):
        identifier = data.draw(st.sampled_from(list(self.live)))
        owner = self.sessions[self.live[identifier][0]][1]
        self.service.delete(owner, identifier)
        del self.live[identifier]
        self.deleted.add(identifier)

    @precondition(lambda self: self.live and len(self.sessions) > 1)
    @rule(data=st.data())
    def foreign_access_is_denied(self, data):
        identifier = data.draw(st.sampled_from(list(self.live)))
        owner = self.live[identifier][0]
        other = self.sessions[(owner + 1) % len(self.sessions)][1]
        for action in (
            lambda: self.service.messages(other, identifier, 10, None),
            lambda: self.service.rename(other, identifier, 'x'),
            lambda: self.service.delete(other, identifier),
            lambda: self.service.prepare_run(other, identifier, 'x', 'h', 'k' * 8),
        ):
            with pytest.raises(RejectedError) as caught:
                action()
            assert caught.value.code == 'not_found'

    @precondition(lambda self: self.sessions)
    @rule(data=st.data())
    def end_session(self, data):
        index = data.draw(st.integers(0, len(self.sessions) - 1))
        _, session = self.sessions[index]
        self.service.delete_session(session)
        for identifier, (owner, _) in list(self.live.items()):
            if owner == index:
                del self.live[identifier]
                self.deleted.add(identifier)
        # Keep indices stable: a deleted session stays in the list but cannot authenticate.
        with pytest.raises(RejectedError):
            self.service.authenticate(self.sessions[index][0])

    @invariant()
    def sessions_only_see_their_own_live_conversations(self):
        for index, (raw, session) in enumerate(self.sessions):
            if self.store.session(digest(raw)) is None:
                continue
            listed = {
                row.id for row in self.service.list_conversations(session, 50, None)
            }
            expected = {i for i, (owner, _) in self.live.items() if owner == index}
            assert listed == expected

    @invariant()
    def deleted_conversations_stay_deleted(self):
        for identifier in self.deleted:
            assert identifier not in self.store.conversations
            assert identifier not in self.store.history

    @invariant()
    def message_order_is_preserved(self):
        for identifier, (index, _) in self.live.items():
            session = self.sessions[index][1]
            page = self.service.messages(session, identifier, 100, None)
            assert [message.content for message in page] == self.sent[identifier][:101]
            stamps = [message.created_at for message in page]
            assert stamps == sorted(stamps)


TestLifecycle = LifecycleMachine.TestCase
TestLifecycle.settings = settings(stateful_step_count=50, deadline=None)
