"""Store contract: the ownership and expiry cases the in-memory FakeStore only imitates."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.adapters.postgres.conversations import PostgresConversations
from app.application.conversations import digest
from app.bootstrap.maintenance import connect
from app.domain.errors import RejectedError

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv('TEST_INTEGRATION') != '1', reason='requires real PostgreSQL'
    ),
]


@pytest.fixture
def store():
    created = []
    adapter = PostgresConversations(connect)

    def session(expires):
        session_id, secret = uuid4(), uuid4().hex
        adapter.create_session(session_id, digest(secret), 'csrf', expires)
        created.append(session_id)
        return session_id, secret

    adapter.make = session
    yield adapter
    with connect() as conn:
        conn.execute('DELETE FROM sessions WHERE id=ANY(%s)', (created,))


def test_expired_session_does_not_resolve(store):
    soon = datetime.now(UTC) + timedelta(hours=1)
    live_id, live = store.make(soon)
    _, expired = store.make(datetime.now(UTC) - timedelta(seconds=1))
    assert store.session(digest(live)).id == live_id
    assert store.session(digest(expired)) is None
    assert store.session(digest('unknown')) is None


def test_foreign_session_gets_not_found_for_every_owned_object(store):
    soon = datetime.now(UTC) + timedelta(hours=1)
    owner, _ = store.make(soon)
    foreign, _ = store.make(soon)
    conversation = store.create(owner, 'owned').id
    run = store.prepare_run(owner, conversation, 'hi', 'hash', 'k' * 8)
    for call in (
        lambda: store.rename(foreign, conversation, 'x'),
        lambda: store.delete(foreign, conversation),
        lambda: store.messages(foreign, conversation, 10, None),
        lambda: store.prepare_run(foreign, conversation, 'hi', 'hash', 'j' * 8),
        lambda: store.run(foreign, run),
        lambda: store.run(foreign, run, cancel=True),
        lambda: store.feedback(foreign, uuid4(), 'up'),
    ):
        with pytest.raises(RejectedError) as caught:
            call()
        assert (caught.value.status, caught.value.code) == (404, 'not_found')
    assert store.run(owner, run).id == run
