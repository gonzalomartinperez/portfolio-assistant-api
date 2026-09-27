"""Local fixture HTTP measurements; requires an isolated seeded database."""

import json
import statistics
import time
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def main():
    samples = []
    with TestClient(app, client=(str(uuid4()), 50000)) as client:
        origin = {'Origin': 'http://localhost:3000', 'X-Session-Bootstrap': '1'}
        csrf = client.post('/api/v1/session', headers=origin, json={}).json()[
            'csrf_token'
        ]
        headers = {'Origin': origin['Origin'], 'X-CSRF-Token': csrf}
        cid = client.post('/api/v1/conversations', headers=headers, json={}).json()[
            'id'
        ]
        for question in [
            'What is Filomena?',
            '¿Dónde estudió Gonzalo?',
            'quasar xylophone',
        ]:
            started = time.perf_counter()
            result = client.post(
                f'/api/v1/conversations/{cid}/messages/stream',
                headers={**headers, 'Idempotency-Key': str(uuid4())},
                json={
                    'content': question,
                    'locale': 'es' if question.startswith('¿') else 'en',
                },
            )
            assert result.status_code == 200 and 'event: run.completed' in result.text
            samples.append(
                {
                    'question': question,
                    'elapsed_ms': round((time.perf_counter() - started) * 1000, 1),
                    'bytes': len(result.content),
                }
            )
        client.delete('/api/v1/session', headers=headers)
    print(
        json.dumps(
            {
                'samples': samples,
                'median_ms': statistics.median(x['elapsed_ms'] for x in samples),
                'note': 'TestClient buffers SSE; this is total request latency, not time to first delta.',
            },
            indent=2,
        )
    )


if __name__ == '__main__':
    main()
