"""Untrusted interaction metadata cannot introduce identifiers or arbitrary scope."""

import json
from typing import get_args
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.analytics_interactions import REGIONS, SHELL_REGIONS, Region
from app.presentation.analytics import ProductEventBody
from app.presentation.interaction_models import ProductInteractionBody


def click(**changes):
    return {
        'schema_version': 2,
        'project': 'portfolio',
        'source': 'site',
        'event_id': str(uuid4()),
        'event_name': 'public_click',
        'section': 'home',
        'locale': 'en',
        'region_id': 'home-featured',
        'layout_revision': 'portfolio-v1',
        'viewport': 'desktop',
        'cell_x': 0,
        'cell_y': 7,
        **changes,
    }


def test_catalogue_is_closed_and_page_bound_in_both_languages():
    assert set(get_args(Region)) == set().union(SHELL_REGIONS, *REGIONS.values())
    assert len(get_args(Region)) == 30
    for locale in ('en', 'es'):
        for section, regions in REGIONS.items():
            for region in regions | SHELL_REGIONS:
                body = ProductInteractionBody.model_validate(
                    click(section=section, region_id=region, locale=locale)
                )
                assert body.event().region_id == region
                assert len(json.dumps(body.model_dump()).encode()) < 1024


@pytest.mark.parametrize(
    'changes',
    [
        {'region_id': 'contact-channels'},
        {'region_id': 'assistant-history'},
        {'region_id': 'unknown'},
        {'layout_revision': 'portfolio-v2'},
        {'viewport': '1920x1080'},
        {'cell_x': -1},
        {'cell_y': 8},
        {'cell_x': True},
        {'cell_x': '1'},
        {'cell_x': 0.25},
        {'cell_x': None},
        {'cell_y': None},
        {'schema_version': True},
        {'schema_version': 1},
        {'schema_version': 2.0},
        {'locale': 'fr'},
        {'event_id': '../raw-selector'},
        {'country': 'AR'},
        {'text': 'input'},
        {'selector': '#email'},
        {'url': 'https://external.invalid/'},
        {'visitor_id': 'persistent'},
        {'session_id': 'credential'},
        {'target': 'email'},
    ],
)
def test_interactions_fail_closed_for_unknown_or_sensitive_dimensions(changes):
    with pytest.raises(ValidationError):
        ProductInteractionBody.model_validate(click(**changes))


def test_exposure_has_no_cell_and_legacy_semantic_events_remain_v1():
    body = click(event_name='section_exposure')
    with pytest.raises(ValidationError):
        ProductInteractionBody.model_validate(body)
    del body['cell_x'], body['cell_y']
    assert ProductInteractionBody.model_validate(body).event().cell_x is None
    with pytest.raises(ValidationError):
        ProductEventBody.model_validate(body)
    legacy = {
        'schema_version': 1,
        'project': 'portfolio',
        'source': 'site',
        'event_id': str(uuid4()),
        'event_name': 'page_view',
        'section': 'home',
        'locale': 'es',
    }
    assert ProductEventBody.model_validate(legacy).event().name == 'page_view'
    with pytest.raises(ValidationError):
        ProductInteractionBody.model_validate(legacy)


def test_committed_public_examples_validate_against_the_runtime_boundary():
    from pathlib import Path

    examples = json.loads(
        Path('contracts/product-interaction.examples.json').read_text()
    )
    assert len(examples) == 2
    for example in examples:
        assert (
            ProductInteractionBody.model_validate(example).event().layout_revision
            == 'portfolio-v1'
        )
