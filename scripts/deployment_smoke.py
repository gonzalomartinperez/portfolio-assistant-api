"""Verify an approved deployment with a no-evidence question that makes no paid call."""

import http.cookiejar
import json
import sys
import urllib.request
from uuid import uuid4

NO_EVIDENCE_QUESTION = 'the what'


def main():
    origin = sys.argv[1].rstrip('/')
    if not origin.startswith('https://'):
        raise ValueError('deployment smoke requires verified HTTPS')
    client = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    headers = {'Origin': origin, 'Content-Type': 'application/json'}

    def request(path, method='GET', body=None, extra=None):
        data = json.dumps(body).encode() if body is not None else None
        return client.open(
            urllib.request.Request(
                origin + path,
                data=data,
                method=method,
                headers={**headers, **(extra or {})},
            ),
            timeout=75,
        )

    with request('/health/ready') as response:
        assert response.status == 200
    with request(
        '/api/v1/session', 'POST', {}, {'X-Session-Bootstrap': '1'}
    ) as response:
        headers['X-CSRF-Token'] = json.load(response)['csrf_token']
    try:
        with request('/api/v1/conversations', 'POST', {}) as response:
            cid = json.load(response)['id']
        terminal = False
        with request(
            f'/api/v1/conversations/{cid}/messages/stream',
            'POST',
            {'content': NO_EVIDENCE_QUESTION, 'locale': 'en'},
            {'Idempotency-Key': str(uuid4())},
        ) as response:
            for line in response:
                if line.startswith(b'data: '):
                    event = json.loads(line[6:])
                    if event['type'] == 'run.completed':
                        terminal = True
                    if event['type'] in ('run.failed', 'run.cancelled'):
                        raise RuntimeError('deployment stream failed')
        assert terminal
    finally:
        with request('/api/v1/session', 'DELETE') as response:
            assert response.status == 204
    print('Readiness, secure session, no-evidence SSE and deletion passed.')


if __name__ == '__main__':
    main()
