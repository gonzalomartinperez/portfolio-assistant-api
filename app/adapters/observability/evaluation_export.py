"""One synchronous aggregate run; no automatic visitor tracing or raw report input."""

from dataclasses import asdict
from datetime import UTC, datetime
from uuid import uuid4

from langsmith import Client
from langsmith.utils import LangSmithError
from requests import Session
from requests.exceptions import RequestException
from urllib3.util.retry import Retry

from app.application.evaluation_export import EvaluationSummary

ENDPOINT = 'https://api.smith.langchain.com'
PROJECT = 'portfolio-synthetic-evaluations'


class EvaluationSession(Session):
    def request(self, method, url, **kwargs):
        if method != 'POST' or url != ENDPOINT + '/runs':
            raise ValueError('unexpected evaluation export destination')
        kwargs['allow_redirects'] = False
        response = super().request(method, url, **kwargs)
        if 300 <= response.status_code < 400:
            raise RequestException('evaluation export redirect rejected')
        return response


class LangSmithEvaluationExporter:
    def __init__(self, key: str):
        self._key = key

    def export(self, summary: EvaluationSummary) -> bool:
        # Client construction is invocation-scoped; importing this adapter has no I/O.
        session = EvaluationSession()
        session.trust_env = False
        client = None
        try:
            client = Client(
                api_urls={ENDPOINT: self._key},
                api_key=self._key,
                session=session,
                auto_batch_tracing=False,
                retry_config=Retry(total=0),
                timeout_ms=(2000, 5000),
                hide_inputs=True,
                hide_outputs=True,
                hide_metadata=lambda metadata: {
                    key: value
                    for key, value in metadata.items()
                    if key in asdict(summary) or key == 'model'
                },
                omit_traced_runtime_info=True,
                tracing_mode='langsmith',
                tracing_sampling_rate=1.0,
                workspace_id='',
            )
            now = datetime.now(UTC)
            client.create_run(
                name='synthetic-evaluation-summary',
                inputs={},
                outputs={},
                run_type='chain',
                project_name=PROJECT,
                id=uuid4(),
                start_time=now,
                end_time=now,
                extra={'metadata': {**asdict(summary), 'model': 'gpt-6-luna'}},
                tags=['synthetic', 'aggregate-only'],
                dangerously_allow_filesystem=False,
            )
            return True
        except LangSmithError, RequestException, ValueError:
            # SDK failures may include response bodies. Never surface their text.
            return False
        finally:
            if client is not None:
                client.close()
            session.close()
