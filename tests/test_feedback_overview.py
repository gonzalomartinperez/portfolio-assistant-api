"""Private ratings are bounded current opinions, never conversation exports."""

from fastapi.testclient import TestClient

from app.application.feedback import FeedbackSummary
from app.bootstrap.config import Settings
from app.bootstrap.container import create_app

TOKEN = 'synthetic-private-feedback-token-0000'


class Reader:
    calls = 0

    def read(self):
        self.calls += 1
        return FeedbackSummary('2026-10-17T00:00:00+00:00', 2, 1)


def test_private_feedback_is_off_by_default_and_authenticated_when_enabled():
    assert Settings(_env_file=None).feedback_overview_enabled is False
    for enabled in (False, True):
        app = create_app(
            Settings(
                _env_file=None,
                ops_read_token=TOKEN,
                ops_api_commit='a' * 40,
                feedback_overview_enabled=enabled,
            )
        )
        reader = Reader()
        app.state.feedback = reader
        client = TestClient(app)
        assert client.get('/internal/ops/v1/feedback').status_code == 401
        response = client.get(
            '/internal/ops/v1/feedback', headers={'Authorization': 'Bearer ' + TOKEN}
        )
        assert response.status_code == (200 if enabled else 404)
        assert reader.calls == int(enabled)
        assert 'no-store' in response.headers['cache-control']
        if enabled:
            assert response.json() == {
                'schema_version': 1,
                'project': 'portfolio',
                'basis': 'retained_answer_creation',
                'window_days': 7,
                'observed_at': '2026-10-17T00:00:00+00:00',
                'up': 2,
                'down': 1,
            }
        assert '/internal/ops/v1/feedback' not in app.openapi()['paths']
