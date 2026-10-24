FROM postgres:18.6-alpine3.24@sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873 AS vector-build
RUN apk add --no-cache build-base=0.5-r4 clang21=21.1.8-r3 llvm21-dev=21.1.8-r1 \
    && wget -O /tmp/pgvector.tar.gz https://codeload.github.com/pgvector/pgvector/tar.gz/refs/tags/v0.8.7 \
    && echo 'cac0b10c360f05b2d521200105ba3697e773d4cd3731f5a915a7e37ebe0bea85  /tmp/pgvector.tar.gz' | sha256sum -c - \
    && tar -xzf /tmp/pgvector.tar.gz -C /tmp \
    && cd /tmp/pgvector-0.8.7 \
    && make -j1 OPTFLAGS="" \
    && make DESTDIR=/extension install \
    && mkdir -p /extension/usr/share/doc/pgvector \
    && cp LICENSE README.md /extension/usr/share/doc/pgvector/ \
    && apk info -v > /extension/usr/share/doc/pgvector/build-packages.txt

FROM postgres:18.6-alpine3.24@sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873
COPY --from=vector-build /extension/ /
# Root startup/ownership repair is unsupported; preserve XML, ICU and the official entrypoint.
RUN apk add --no-cache libxml2=2.13.9-r2 brotli-libs=1.2.1-r0 \
    && rm /usr/local/bin/gosu \
    && test "$(id -u postgres)" = 70 && test "$(id -g postgres)" = 70 \
    && apk info -v > /usr/share/assistant-postgres-packages.txt
COPY infra/docker/postgres/project-postgres-bootstrap.psql infra/docker/postgres/project-pg_hba.conf /usr/local/share/portfolio-postgres/
LABEL org.opencontainers.image.source="https://github.com/gonzalomartinperez/portfolio-assistant-api"
# The official entrypoint skips root ownership repair when already non-root.
USER 70:70
