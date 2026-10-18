# syntax=docker/dockerfile:1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e
FROM python:3.14.8-slim-trixie@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS runtime-base
# The reviewed public-source CLI uses Git; no HTTP endpoint exposes it.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git=1:2.47.3-0+deb13u1 libpcre2-8-0=10.46-1~deb13u3 \
    liblzma5=5.8.1-1+deb13u2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

FROM runtime-base AS dependencies
COPY --from=ghcr.io/astral-sh/uv:0.13.1@sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock LICENSE THIRD_PARTY_NOTICES.md ./
RUN --mount=type=cache,id=vps-ops-uv-python314,target=/root/.cache/uv,sharing=locked uv sync --frozen --no-dev --no-install-project

FROM runtime-base AS runtime
LABEL org.opencontainers.image.licenses="MIT"
RUN /usr/local/bin/python -m pip uninstall --yes pip \
    && rm -rf /usr/local/lib/python3.14/ensurepip
COPY --from=dependencies /app/.venv /app/.venv
COPY app ./app
COPY migrations ./migrations
COPY contracts ./contracts
COPY LICENSE THIRD_PARTY_NOTICES.md ./
ENV PATH=/app/.venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false
USER 65532:65532
STOPSIGNAL SIGTERM
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=8s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5)"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers", "--timeout-graceful-shutdown", "15"]
