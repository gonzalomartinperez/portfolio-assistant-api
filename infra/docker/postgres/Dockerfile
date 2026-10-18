FROM pgvector/pgvector:0.8.7-pg18@sha256:2358fcba361ed2233a5ed81b5fe4ca779ccb304120ce531a3bf51c0ed7e2bc11
# Upstream application tags can lag stable-distribution security packages.
RUN DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=3 -o Acquire::http::Timeout=30 update \
    && DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=3 -o Acquire::http::Timeout=30 upgrade --yes \
    && rm -rf /var/lib/apt/lists/* /usr/local/bin/gosu
RUN dpkg-query --show > /usr/share/assistant-postgres-packages.txt
COPY infra/docker/postgres/project-postgres-bootstrap.psql infra/docker/postgres/project-pg_hba.conf /usr/local/share/portfolio-postgres/
LABEL org.opencontainers.image.source="https://github.com/gonzalomartinperez/portfolio-assistant-api"
# The official entrypoint skips root ownership repair when already non-root.
USER postgres
