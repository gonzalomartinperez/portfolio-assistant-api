# Disposable analytics integration demo

This local-only harness creates a fresh, labelled project PostgreSQL with separate
API and IAM databases and starts the real API on loopback HTTPS. It is not production
Compose, a controller, a Cloudflare proof or full assistant readiness. No Neo4j,
corpus, provider credential or paid model call is used; `/health/ready` may correctly
remain unavailable. Product ingestion and authenticated aggregate reads are the
capabilities under test. vps-ops retains all production ownership.

Prerequisites: frozen API/Node dependencies, local Docker, OpenSSL, the application-owned
PostgreSQL image and free ports8317/3317. Coordinate the site3381 browser/build lease
with its owner. Do not stop an existing listener or use an external database URL.

From this repository, with no `OPENAI_*` variables in the process:

```sh
uv run python -m scripts.analytics_demo --authorize-fixture \
  --postgres-image portfolio-assistant-postgres:project-proof \
  --site-origin https://127.0.0.1:3381
```

Use the local image build procedure in [project database verification](verification/project-postgres-2026-10-17.md).
The command prints only the task-owned fixture directory. All databases and passwords
are newly generated; it cannot select a caller's database. It applies real API
migrations and direct runtime grants, then serves with the restricted runtime role.
Country collection stays off, with real accepted events attributed to unknown.
Default lifetime is45minutes (configurable1–60); SIGTERM or expiry shuts down the
server and removes only owned database/container/network/volume resources. SIGKILL
cannot guarantee cleanup; use the labelled receipt and existing guarded fixture
cleanup rather than blanket Docker pruning.

The directory contains `tls.crt`, `tls.key`, `demo.json`, `backoffice.env` and
`iam-migration.env`. Private configuration/key files are0600 inside a0700 directory.
Never print, commit, screenshot or upload them or `sessions.json`. The certificate
is disposable and only valid for local loopback; Node trusts it through
`NODE_EXTRA_CA_CERTS`, not by disabling TLS verification globally. The safe receipt
records source/dirty status and explicitly does not certify assistant readiness.

In the backoffice checkout, set a task-specific path to that printed directory:

```sh
demo_dir=/path/to/the/printed/analytics-demo-directory
node --env-file="$demo_dir/iam-migration.env" scripts/auth-migrate.ts --project-grants
node --env-file="$demo_dir/backoffice.env" scripts/auth-fixture-session.ts
# Build normally first; prepare standalone public/static assets as documented.
NODE_EXTRA_CA_CERTS="$demo_dir/tls.crt" \
  node --env-file="$demo_dir/backoffice.env" .next/standalone/server.js
```

Node reads `NODE_EXTRA_CA_CERTS` when the process starts; the CLI `--env-file`
alone does not establish trust early enough. Set the public certificate path in
the parent environment as shown; never use `NODE_TLS_REJECT_UNAUTHORIZED=0`.

The session tool verifies the live fixture's exact Docker ID, UUID/source labels,
loopback binding and IAM runtime identity before creating synthetic owner/viewer
sessions. Use these only in the isolated browser harness; live OAuth is not tested.
The web process receives the runtime connection, never the migrator connection.
Protect the generated cookie file as a credential; no private-session artifacts
belong in CI uploads or public galleries.

The portfolio owner builds its disabled-assistant fixture client with the API
ingestion URL and approved origin above. Start a fresh browser context that trusts
the local certificate only for the fixture. Keep the original combined60events/minute
and10,000/day limits; agree the total seed/browser event count first. Do not retry
events automatically. The demo starts without seeding; a fixture dataset or mock
dashboard is not evidence that native client delivery has persisted in PostgreSQL.

Before claiming integration, inspect real browser delivery, duplicate handling,
database aggregates and the authenticated backoffice result at the same source
revisions. Record synthetic provenance, partial/current UTC periods, country unknown
and withheld grid cells. Test unauthorized reads, failure and teardown separately.
No main promotion, release tag, paid call or public activation follows from this command.
