"""Session and conversation policies at the storage boundary."""

from datetime import timedelta
from hashlib import sha256
from unittest.mock import Mock, call
from uuid import uuid4

import pytest

from portfolio_assistant.application.conversations import Conversations, ConversationStore
from portfolio_assistant.domain.conversations import Conversation, Message, Session
from portfolio_assistant.domain.errors import RejectedError
from tests.support import FIXED_NOW, FixedClock
from tests.support_app import FakeStore


@pytest.fixture
def conversations():
    store = Mock(spec=ConversationStore, wraps=FakeStore())
    return Conversations(store, 7, "fixture-rate-key", clock=FixedClock()), store


@pytest.fixture
def session():
    return Session(uuid4(), "fixture-csrf", FIXED_NOW + timedelta(days=7))


def test_bootstrap_consumes_the_visitor_allowance_and_persists_a_digest(conversations):
    service, store = conversations

    raw, session = service.bootstrap("test-client")

    assert session.id.version == 4
    assert session.expires_at == FIXED_NOW + timedelta(days=7)
    assert raw != session.csrf_token
    subject_hash = sha256(b"fixture-rate-keytest-client").hexdigest()
    credential_digest = sha256(raw.encode()).hexdigest()
    assert store.mock_calls == [
        call.rate_limit(subject_hash, "bootstrap", 20),
        call.create_session(session.id, credential_digest, session.csrf_token, session.expires_at),
    ]
    assert service.authenticate(raw) == session


@pytest.mark.parametrize("raw", [None, ""], ids=["missing", "empty"])
def test_missing_session_cookie_is_rejected_before_storage_lookup(conversations, raw):
    service, store = conversations

    with pytest.raises(RejectedError, match=r"^session_required$") as error:
        service.authenticate(raw)

    assert error.value.status == 401
    store.session.assert_not_called()


def test_unrecognized_session_cookie_is_rejected(conversations):
    service, _ = conversations

    with pytest.raises(RejectedError, match=r"^session_required$") as error:
        service.authenticate("unknown-cookie")

    assert error.value.status == 401


def test_session_csrf_token_authorizes_a_mutation(conversations, session):
    service, _ = conversations

    assert service.authorize_mutation(session, session.csrf_token) == session


def test_csrf_token_from_another_session_cannot_authorize_a_mutation(conversations, session):
    service, _ = conversations
    _, other_session = service.bootstrap("other-client")

    with pytest.raises(RejectedError, match=r"^csrf_denied$") as error:
        service.authorize_mutation(session, other_session.csrf_token)

    assert error.value.status == 403


@pytest.mark.parametrize(("limit", "fetch_size"), [(1, 2), (50, 51)])
def test_conversation_page_fetches_lookahead_with_the_supplied_cursor(
    conversations, session, limit, fetch_size
):
    service, store = conversations
    cursor = FIXED_NOW - timedelta(hours=1)
    rows = [Conversation(uuid4(), "Project discussion", cursor, cursor)]
    store.list_conversations.return_value = rows

    assert service.list_conversations(session, limit, cursor) == rows
    store.list_conversations.assert_called_once_with(session.id, fetch_size, cursor)


@pytest.mark.parametrize("limit", [0, 51])
def test_invalid_conversation_page_size_never_reaches_storage(conversations, session, limit):
    service, store = conversations

    with pytest.raises(RejectedError, match=r"^invalid_limit$") as error:
        service.list_conversations(session, limit, None)

    assert error.value.status == 400
    store.list_conversations.assert_not_called()


@pytest.mark.parametrize(("limit", "fetch_size"), [(1, 2), (100, 101)])
def test_message_page_fetches_lookahead_for_the_owned_conversation(
    conversations, session, limit, fetch_size
):
    service, store = conversations
    conversation_id = uuid4()
    cursor = FIXED_NOW - timedelta(minutes=1)
    rows = [Message(uuid4(), "user", "Tell me about the API.", [], cursor)]
    store.messages.return_value = rows

    assert service.messages(session, conversation_id, limit, cursor) == rows
    store.messages.assert_called_once_with(session.id, conversation_id, fetch_size, cursor)


@pytest.mark.parametrize("limit", [0, 101])
def test_invalid_message_page_size_never_reaches_storage(conversations, session, limit):
    service, store = conversations

    with pytest.raises(RejectedError, match=r"^invalid_limit$") as error:
        service.messages(session, uuid4(), limit, None)

    assert error.value.status == 400
    store.messages.assert_not_called()


def test_prepare_run_consumes_session_allowance_before_submitting_idempotent_payload(
    conversations, session
):
    service, store = conversations
    conversation_id, run_id = uuid4(), uuid4()
    content = "Tell me about the API."
    payload_hash = sha256(content.encode()).hexdigest()
    idempotency_key = "message-attempt"
    store.prepare_run.return_value = run_id

    prepared = service.prepare_run(session, conversation_id, content, payload_hash, idempotency_key)

    assert prepared == run_id
    subject_hash = sha256(f"fixture-rate-key{session.id}".encode()).hexdigest()
    assert store.mock_calls == [
        call.rate_limit(subject_hash, "message", 30),
        call.prepare_run(session.id, conversation_id, content, payload_hash, idempotency_key),
    ]


def test_rate_limited_message_does_not_prepare_a_run(conversations, session):
    service, store = conversations
    store.rate_limit.side_effect = RejectedError("rate_limited", 429)

    with pytest.raises(RejectedError, match=r"^rate_limited$") as error:
        service.prepare_run(session, uuid4(), "Question", "payload-hash", "message-attempt")

    assert error.value.status == 429
    store.prepare_run.assert_not_called()


def test_inspecting_a_run_forwards_no_cancellation_to_the_store(session):
    store = FakeStore()
    _, run_id, _ = store.seed(session.id)
    service = Conversations(store, 7, "fixture-rate-key", clock=FixedClock())

    run = service.run(session, run_id)

    assert run.id == run_id
    assert run.state == "running"


def test_cancelling_a_run_forwards_the_cancellation_with_the_session(session):
    store = FakeStore()
    _, run_id, _ = store.seed(session.id)
    service = Conversations(store, 7, "fixture-rate-key", clock=FixedClock())
    other = Session(uuid4(), "other-csrf", session.expires_at)

    with pytest.raises(RejectedError, match=r"^not_found$"):
        service.run(other, run_id, cancel=True)

    assert service.run(session, run_id, cancel=True).state == "cancelled"


def test_feedback_records_the_rating_against_the_sessions_message(conversations, session):
    service, store = conversations
    message_id = uuid4()
    store.feedback.return_value = None

    service.feedback(session, message_id, "up")

    store.feedback.assert_called_once_with(session.id, message_id, "up")
