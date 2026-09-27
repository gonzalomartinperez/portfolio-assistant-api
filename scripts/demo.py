"""Exercise the public fixture API without displaying anonymous credentials."""

import argparse
import json
from uuid import uuid4

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://localhost:8000')
    parser.add_argument('--locale', choices=['en', 'es'], default='en')
    args = parser.parse_args()
    with httpx.Client(base_url=args.url, timeout=70) as client:
        bootstrap = client.post(
            '/api/v1/session',
            headers={'Origin': 'http://localhost:3000', 'X-Session-Bootstrap': '1'},
            json={},
        )
        bootstrap.raise_for_status()
        headers = {
            'Origin': 'http://localhost:3000',
            'X-CSRF-Token': bootstrap.json()['csrf_token'],
        }
        try:
            conversation = client.post(
                '/api/v1/conversations', headers=headers, json={}
            )
            conversation.raise_for_status()
            question = (
                '¿Dónde estudió Gonzalo?'
                if args.locale == 'es'
                else 'What is Filomena?'
            )
            with client.stream(
                'POST',
                f'/api/v1/conversations/{conversation.json()["id"]}/messages/stream',
                headers={**headers, 'Idempotency-Key': str(uuid4())},
                json={'content': question, 'locale': args.locale},
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith('data: '):
                        event = json.loads(line[6:])
                        if event['type'] == 'message.delta':
                            print(event['payload']['text'], end='', flush=True)
                        elif event['type'] in ('run.failed', 'run.cancelled'):
                            raise RuntimeError(event['type'])
                print()
        finally:
            client.delete('/api/v1/session', headers=headers).raise_for_status()


if __name__ == '__main__':
    main()
