"""Interoperability vocabulary does not expand either product's ingestion authority."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.analytics_interactions import REGIONS, SHELL_REGIONS
from app.presentation.analytics import ProductEventBody
from app.presentation.interaction_models import ProductInteractionBody
from contracts.site_experience import (
    COMMERCE_EVENTS,
    SECTION_ROUTES,
    PortfolioExperience,
    SiteExperience,
)


def core(**changes):
    return {
        'schema_version': 1,
        'project': 'portfolio',
        'source': 'site',
        'event_id': str(uuid4()),
        'event_name': 'public_click',
        'route': '/',
        'layout_revision': 'portfolio-v1',
        'viewport_bucket': 'desktop',
        'section_id': 'home-featured',
        'locale': 'en',
        'cell_x': 0,
        'cell_y': 7,
        **changes,
    }


@pytest.mark.parametrize('name', ['page_view', 'section_view', *COMMERCE_EVENTS])
def test_semantic_vocabulary_requires_no_coordinates_and_reviewable_commerce_target(
    name,
):
    payload = core(event_name=name)
    del payload['cell_x'], payload['cell_y']
    if name in COMMERCE_EVENTS:
        payload['target_id'] = 'synthetic-product'
    SiteExperience.model_validate(payload)
    with pytest.raises(ValidationError):
        SiteExperience.model_validate({**payload, 'cell_x': 0, 'cell_y': 0})
    if name in COMMERCE_EVENTS:
        del payload['target_id']
        with pytest.raises(ValidationError):
            SiteExperience.model_validate(payload)


@pytest.mark.parametrize(
    'changes',
    [
        {'schema_version': True},
        {'schema_version': 1.0},
        {'event_name': 'Purchase'},
        {'event_name': 'section_open'},
        {'route': '/about?secret=synthetic'},
        {'route': '/about#fragment'},
        {'route': 'https://external.invalid/'},
        {'route': '//external'},
        {'route': '/%61uth'},
        {'route': '/../admin'},
        {'cell_x': True},
        {'cell_y': 8},
        {'cell_x': None},
        {'cell_y': 0.5},
        {'target_id': None},
        {'country': 'AR'},
        {'text': 'synthetic'},
        {'input': 'synthetic'},
        {'transcript': 'synthetic'},
        {'selector': '#email'},
        {'consent': True},
        {'fixture': True},
        {'session_id': 'synthetic'},
        {'event_id': 'persistent-user'},
        {'layout_revision': 'raw layout name'},
    ],
)
def test_core_rejects_unbounded_or_sensitive_fields(changes):
    with pytest.raises(ValidationError):
        SiteExperience.model_validate(core(**changes))


def test_portfolio_profile_requires_exact_public_route_locale_region_and_layout():
    for section, path in SECTION_ROUTES.items():
        for locale in ('en', 'es'):
            route = path if locale == 'en' else '/es' + (path if path != '/' else '')
            for region in REGIONS[section] | SHELL_REGIONS:
                PortfolioExperience.model_validate(
                    core(
                        route=route,
                        locale=locale,
                        section_id=region,
                    )
                )
    for changes in [
        {'route': '/auth'},
        {'route': '/assistant'},
        {'route': '/es/assistant'},
        {'route': '/es', 'locale': 'en'},
        {'route': '/about'},
        {'layout_revision': 'portfolio-v2'},
        {'project': 'pequeverso'},
        {'section_id': 'home-unreviewed'},
    ]:
        with pytest.raises(ValidationError):
            PortfolioExperience.model_validate(core(**changes))


def test_existing_wire_examples_map_offline_without_renaming_or_expanding_ingestion():
    examples = json.loads(
        Path('contracts/product-interaction.examples.json').read_text()
    )
    for example in examples:
        path = SECTION_ROUTES[example['section']]
        route = (
            path if example['locale'] == 'en' else '/es' + (path if path != '/' else '')
        )
        mapped = {
            'schema_version': 1,
            'project': example['project'],
            'source': 'site',
            'event_id': example['event_id'],
            'event_name': 'section_view'
            if example['event_name'] == 'section_exposure'
            else 'public_click',
            'route': route,
            'layout_revision': example['layout_revision'],
            'viewport_bucket': example['viewport'],
            'section_id': example['region_id'],
            'locale': example['locale'],
        }
        if example['event_name'] == 'public_click':
            mapped.update(cell_x=example['cell_x'], cell_y=example['cell_y'])
        PortfolioExperience.model_validate(mapped)
        ProductInteractionBody.model_validate(example)
        for public_model in (ProductInteractionBody, ProductEventBody):
            with pytest.raises(ValidationError):
                public_model.model_validate(mapped)


def test_core_schema_and_profile_publish_cross_field_constraints():
    for model in (SiteExperience, PortfolioExperience):
        schema = model.model_json_schema()
        assert schema['additionalProperties'] is False
        assert schema['allOf'][0]['then']['required'] == ['cell_x', 'cell_y']
        assert schema['allOf'][1]['then']['required'] == ['target_id']
    schema = PortfolioExperience.model_json_schema()
    assert len(schema['allOf']) == 18
    assert set(schema['properties']['event_name']['enum']) == {
        'public_click',
        'section_view',
    }
