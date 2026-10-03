"""Deterministic offline public contract export; no lifespan or service connections."""

import hashlib
import json
from pathlib import Path

from app.infrastructure.public_projection import PublicProjection
from app.main import app
from app.presentation.events import events


def artifacts():
    return {
        'openapi.json': app.openapi(),
        'knowledge.schema.json': {
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
            **PublicProjection.model_json_schema(),
        },
        'sse.schema.json': {
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
            'title': 'Portfolio assistant SSE v1',
            **events.json_schema(),
        },
    }


def main():
    schemas = artifacts()
    schemas['manifest.json'] = {
        'contract_version': '1',
        'artifacts': {
            name: hashlib.sha256(
                (json.dumps(schema, indent=2, sort_keys=True) + '\n').encode()
            ).hexdigest()
            for name, schema in schemas.items()
        },
    }
    for name, schema in schemas.items():
        Path(__file__).with_name(name).write_text(
            json.dumps(schema, indent=2, sort_keys=True) + '\n'
        )


if __name__ == '__main__':
    main()
