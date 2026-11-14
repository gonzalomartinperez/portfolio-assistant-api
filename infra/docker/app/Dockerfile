# syntax=docker/dockerfile:1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e
# Targets: api (default, last stage) and worker (adds git for the public-source CLI).
FROM python:3.14.8-slim-trixie@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS base
# apt, libapt-pkg7.0, zlib1g and liblzma5 are pinned to their fixed Debian security versions.
RUN apt-get update && apt-get install -y --no-install-recommends \
    liblzma5=5.8.1-1+deb13u2 \
    apt=3.0.4 libapt-pkg7.0=3.0.4 zlib1g=1:1.3.dfsg+really1.3.1-1+deb13u1 \
    && rm -rf /var/lib/apt/lists/* \
    && /usr/local/bin/python -m pip uninstall --yes pip \
    && rm -rf /usr/local/lib/python3.14/ensurepip
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/app/.venv/bin:$PATH
ENV LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false

FROM base AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.1@sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
COPY pyproject.toml uv.lock LICENSE THIRD_PARTY_NOTICES.md ./
RUN --mount=type=cache,id=portfolio-assistant-api-uv-py314,target=/root/.cache/uv,sharing=locked \
    uv sync --locked --no-dev --no-install-project
COPY app ./app
COPY migrations ./migrations
COPY contracts ./contracts
# Editable project install: console scripts exist and `app` resolves from /app,
# where migration_paths() reads /app/migrations.
RUN --mount=type=cache,id=portfolio-assistant-api-uv-py314,target=/root/.cache/uv,sharing=locked \
    uv sync --locked --no-dev

FROM base AS worker
ARG VERSION=dev
ARG REVISION=unknown
ARG CREATED=unknown
LABEL org.opencontainers.image.title="portfolio-assistant-api-worker" \
      org.opencontainers.image.source="https://github.com/gonzalomartinperez/portfolio-assistant-api" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.created="${CREATED}" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.description="Grounded portfolio assistant API" \
      org.opencontainers.image.documentation="https://github.com/gonzalomartinperez/portfolio-assistant-api/tree/main/docs"
# The reviewed public-source CLI uses Git; no HTTP endpoint exposes it.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git=1:2.47.3-0+deb13u1 libpcre2-8-0=10.46-1~deb13u3 libbrotli1=1.1.0-2+deb13u1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /app /app
USER 65532:65532
CMD ["assistant-knowledge-watch"]

FROM base AS api
ARG VERSION=dev
ARG REVISION=unknown
ARG CREATED=unknown
LABEL org.opencontainers.image.title="portfolio-assistant-api" \
      org.opencontainers.image.source="https://github.com/gonzalomartinperez/portfolio-assistant-api" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.created="${CREATED}" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.description="Grounded portfolio assistant API" \
      org.opencontainers.image.documentation="https://github.com/gonzalomartinperez/portfolio-assistant-api/tree/main/docs"
COPY --from=build /app /app
USER 65532:65532
STOPSIGNAL SIGTERM
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=8s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=5)"]
CMD ["assistant-api"]
