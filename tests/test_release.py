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
