"""Release inputs must be immutable before they reach an operator's shell."""

import pytest

from scripts.release_manifest import manifest


def test_manifest_rejects_tags_and_shell_input():
    image = 'ghcr.io/owner/api@sha256:' + 'a' * 64
    revision = 'b' * 40
    result = manifest(image, image, revision, revision)
    assert result['production_authorized'] is False
    assert result['api']['commit'] == revision
    for invalid in ('ghcr.io/owner/api:latest', image + ';id', '$(id)', ''):
        with pytest.raises(ValueError):
            manifest(invalid, image, revision, revision)
    with pytest.raises(ValueError):
        manifest(image, image, 'develop', revision)


def test_deployment_probe_cannot_retrieve_or_invoke_provider():
    import asyncio

    from app.ai.retrieval import PublicRetrieval
    from scripts.deployment_smoke import NO_EVIDENCE_QUESTION

    class ForbiddenIndex:
        async def candidates(self, question):
            raise AssertionError('deployment probe must not access embedding/index')

    assert (
        asyncio.run(
            PublicRetrieval(ForbiddenIndex()).search(NO_EVIDENCE_QUESTION, 'en')
        )
        == ()
    )


def test_optional_backoffice_pairing_checks_current_private_contracts():
    from pathlib import Path

    import yaml

    workflow = yaml.safe_load(Path('.github/workflows/quality.yml').read_text())
    steps = workflow['jobs']['container']['steps']
    checkout = next(
        step
        for step in steps
        if step.get('with', {}).get('path') == 'frontend-contract'
    )
    assert checkout['with']['repository'] == 'gonzalomartinperez/portfolio-backoffice'
    assert checkout['with']['persist-credentials'] is False
    guard = next(
        step
        for step in steps
        if step.get('name') == 'Verify the paired backoffice private contract bytes'
    )
    for name in (
        'operations.schema.json',
        'product-analytics.schema.json',
        'feedback.schema.json',
    ):
        assert name in guard['run']
    assert 'sse.schema.json' not in guard['run']
    assert guard['if'] == "inputs.frontend_commit != ''"
