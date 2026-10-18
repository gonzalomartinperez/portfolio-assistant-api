"""Deterministic offline public contract export; no lifespan or service connections."""

import hashlib
import json
from pathlib import Path

from app.infrastructure.public_projection import PublicProjection
from app.main import app
from app.presentation.analytics import ProductEventBody, ProductSnapshot
from app.presentation.analytics_report_models import ProductReportSnapshot
from app.presentation.events import events
from app.presentation.feedback import FeedbackView
from app.presentation.interaction_models import ProductInteractionBody
from app.presentation.operations import OperationalSnapshot
from contracts.site_experience import PortfolioExperience, SiteExperience


def artifacts():
    return {
        'openapi.json': app.openapi(),
        'feedback.schema.json': FeedbackView.model_json_schema(),
        'product-event.schema.json': ProductEventBody.model_json_schema(),
        'product-interaction.schema.json': ProductInteractionBody.model_json_schema(),
        'product-analytics-v2.schema.json': ProductReportSnapshot.model_json_schema(),
        'product-analytics.schema.json': ProductSnapshot.model_json_schema(),
        'site-experience-v1.schema.json': {
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
            **SiteExperience.model_json_schema(),
        },
        'site-experience-portfolio-v1.schema.json': {
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
            **PortfolioExperience.model_json_schema(),
        },
        'operations.schema.json': {
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
            **OperationalSnapshot.model_json_schema(),
        },
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
