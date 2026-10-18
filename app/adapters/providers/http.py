"""Provider-owned HTTP clients with explicit transport and cleanup boundaries."""

from contextlib import AsyncExitStack, ExitStack

from openai import AsyncOpenAI, DefaultAsyncHttpxClient, DefaultHttpxClient, OpenAI


def create_sync_client(*, api_key: str | None, timeout: float = 20) -> OpenAI:
    """Transfer transport ownership only after SDK construction succeeds."""
    if not api_key:
        raise ValueError('provider API key is required')
    with ExitStack() as ownership:
        transport = DefaultHttpxClient(
            verify=True, trust_env=False, follow_redirects=False, timeout=timeout
        )
        ownership.callback(transport.close)
        client = OpenAI(
            api_key=api_key,
            base_url='https://api.openai.com/v1',
            timeout=timeout,
            max_retries=0,
            http_client=transport,
        )
        ownership.pop_all()
        return client


async def create_async_client(
    *, api_key: str | None, timeout: float = 45
) -> AsyncOpenAI:
    """Transfer async transport ownership only after SDK construction succeeds."""
    if not api_key:
        raise ValueError('provider API key is required')
    async with AsyncExitStack() as ownership:
        transport = DefaultAsyncHttpxClient(
            verify=True, trust_env=False, follow_redirects=False, timeout=timeout
        )
        ownership.push_async_callback(transport.aclose)
        client = AsyncOpenAI(
            api_key=api_key,
            base_url='https://api.openai.com/v1',
            timeout=timeout,
            max_retries=0,
            http_client=transport,
        )
        ownership.pop_all()
        return client
