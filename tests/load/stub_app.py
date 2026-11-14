"""ASGI app for load runs: the real routers and workflow over fakes and a stubbed provider."""

from tests.support_app import StubProvider, build_app

app = build_app(provider=StubProvider(chunks=8, delay=0.02))
