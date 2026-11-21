"""Deterministic offline public contract export; no lifespan or service connections."""

import hashlib
import json
from pathlib import Path

from contracts.site_experience import PortfolioExperience, SiteExperience
from portfolio_assistant.adapters.portfolio.projection import PublicProjection
from portfolio_assistant.main import app
from portfolio_assistant.presentation.analytics import ProductEventBody, ProductSnapshot
from portfolio_assistant.presentation.analytics_report_models import ProductReportSnapshot
from portfolio_assistant.presentation.events import events
from portfolio_assistant.presentation.feedback import FeedbackView
from portfolio_assistant.presentation.interaction_models import ProductInteractionBody
from portfolio_assistant.presentation.operations import OperationalSnapshot


def artifacts():
    return {
        "openapi.json": app.openapi(),
        "feedback.schema.json": FeedbackView.model_json_schema(),
        "product-event.schema.json": ProductEventBody.model_json_schema(),
        "product-interaction.schema.json": ProductInteractionBody.model_json_schema(),
        "product-analytics-v2.schema.json": ProductReportSnapshot.model_json_schema(),
        "product-analytics.schema.json": ProductSnapshot.model_json_schema(),
        "site-experience-v1.schema.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            **SiteExperience.model_json_schema(),
        },
        "site-experience-portfolio-v1.schema.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            **PortfolioExperience.model_json_schema(),
        },
        "operations.schema.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            **OperationalSnapshot.model_json_schema(),
        },
        "knowledge.schema.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            **PublicProjection.model_json_schema(),
        },
        "sse.schema.json": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Portfolio assistant SSE v1",
            **events.json_schema(),
        },
    }


def main():
    schemas = artifacts()
    schemas["manifest.json"] = {
        "contract_version": "1",
        "artifacts": {
            name: hashlib.sha256(
                (json.dumps(schema, indent=2, sort_keys=True) + "\n").encode()
            ).hexdigest()
            for name, schema in schemas.items()
        },
    }
    for name, schema in schemas.items():
        Path(__file__).with_name(name).write_text(
            json.dumps(schema, indent=2, sort_keys=True) + "\n"
        )


if __name__ == "__main__":
    main()
