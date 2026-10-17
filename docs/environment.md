# Configuration reference

Settings are validated in `app/bootstrap/config.py`. Environment variables override
`.env.local`; never commit that file. `.env.example` contains public fixture defaults.
Use `scripts/fixture-env.sh` for isolated test ports. Do not put API credentials in
frontend builds or command output. Fixture mode performs no paid model calls.

| Variable | Default | Purpose / constraint |
| --- | --- | --- |
| ENVIRONMENT | development | production enables strict secure deployment validation |
| DATABASE_URL | local assistant DB on 5433 | psycopg DSN; production requires explicit nondefault credentials/host |
| NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD | bolt loopback 7688 / neo4j / change-me | Graph projection and bounded traversal; replace defaults for production |
| ALLOWED_ORIGINS | localhost:3000, localhost:3001 (HTTP) | Comma-separated exact browser origins; HTTPS only in production |
| SECURE_COOKIES | false | true required in production; changes cookie to __Host-assistant_session |
| RATE_HASH_KEY | local-fixture-only | Random ≥32-character value required in production |
| TRUSTED_PROXY_IPS | empty | Exact immediate peers trusted to supply X-Forwarded-For; never trust all peers |
| RETENTION_DAYS | 7 | Anonymous session lifetime, allowed 1–30; run retention CLI every minute |
| RUN_TIMEOUT_SECONDS | 60 | Total generation deadline, greater than zero and at most 120 |
| AI_PROVIDER | fixture | fixture or explicitly enabled openai |
| EMBEDDINGS_PROVIDER | fixture | fixture hash64-v1 (64D) or authorized openai text-embedding-3-small (1536D) |
| ALLOW_PAID_AI | false | Requires openai provider, a key and separate owner authorization |
| OPENAI_API_KEY | unset | Server-only; never read/use a real key without authorization |
| OPENAI_MODEL | gpt-6-luna | Only gpt-6-luna accepted; account access remains unverified |
| MONTHLY_BUDGET_USD | 10.00 | Positive finite ceiling, at most approved USD 10; not spending authorization |
| RESERVE_CUTOFF_USD | 10.00 | Atomic admission ceiling, at most monthly budget |
| RESERVATION_USD | 0.05 | Must conservatively cover bounded maximum input/output at configured prices |
| INPUT_USD_PER_MILLION / OUTPUT_USD_PER_MILLION | 0.10 / 0.50 | Fixture configuration examples, **not a current model price claim**; explicitly configure for production paid mode |
| LANGSMITH_TRACING / LANGCHAIN_TRACING_V2 | disabled by fixture script/image | Enabling either is rejected; external tracing is out of scope |

Compose-only variables: `COMPOSE_PROJECT_NAME`, `POSTGRES_PORT`, `NEO4J_PORT`,
`NEO4J_HTTP_PORT`. `ASSISTANT_PROJECT` sets the project selected by the fixture
script. They do not change application policy. Bind database ports only to loopback
for local work; keep both databases on private networks in a VPS deployment.

Fixed policy bounds are documented in the threat model. Raising them requires an
explicit code/review/evaluation change, not a silent environment override.

| Added variable | Default | Constraint |
| --- | --- | --- |
| OPENAI_REASONING_EFFORT | medium | Only medium; no automatic escalation |
| EMBEDDING_USD_PER_MILLION | 0.02 | Finite positive price; verify current OpenAI price before paid use |
| NEO4J_DATABASE | neo4j | Explicit graph database name |
| KNOWLEDGE_POLL_SECONDS | 60 | Integer 10–300 seconds |
| KNOWLEDGE_FRESHNESS_SECONDS | 90 | Integer 30–600 seconds, strictly greater than poll interval |
| REQUIRE_FRESH_KNOWLEDGE | false | Required true for production OpenAI; local pinned fixtures may stay false |
| OTEL_SDK_DISABLED | true | Optional manual private OTLP export; false requires operations configuration and private collector |
| OPS_READ_TOKEN | unset | Runtime-only URL-safe secret, 32–256 characters; enables read-only internal operations API |
| OPS_API_COMMIT | unset | Full 40-character lowercase source SHA; required with operations token |
| OPS_TRACE_SAMPLE_RATIO | 0.1 | Fraction 0–1; affects trace drilldown/export, not aggregate observation |
| OTEL_PRIVATE_ENDPOINT | unset | Private HTTP(S) origin without credentials/path/query |

Production OpenAI also requires OpenAI semantic embeddings. The output ceiling is
8,192 tokens including reasoning, fixed in policy; it is not a requested answer length.
Configuration does not authorize paid calls. Visitors' query text may be sent to
OpenAI for embeddings; it is never indexed into the public corpus. Responses use
`store=False`, which does not establish provider Zero Data Retention.

Support and upgrade decisions: [supported-version policy](support-policy.md). Python3.14.8 remains the verified runtime; PostgreSQL18 uses a separate data volume.

See [private observability](private-observability.md) for auth, data exclusions,
retention, vendor environment restrictions and measurement limits.

The application pins all OpenAI SDK clients to `https://api.openai.com/v1` and
sets generation/embedding retries to zero. `OPENAI_BASE_URL` is not a supported
application override and cannot redirect provider credentials or public corpus
requests to another provider. Private operational origins are configured separately.

## Optional official-documentation complement

`WEB_SEARCH_ENABLED` defaults to false. `WEB_SEARCH_TIMEOUT_SECONDS` defaults to 12
(1–15); `WEB_SEARCH_USD_PER_CALL` defaults to USD0.01 and must cover the reviewed fee.
These are runtime configuration, not credentials. Enabling also requires authorized
OpenAI mode and paid allowance. The existing backend-only OpenAI key is reused.
No new service, volume or migration is needed. See [bounded web policy](bounded-web-context.md)
for exact routing, privacy, cache, accounting and failure semantics. Production
activation remains separately authorized and vps-ops-owned.

## Optional product interaction counts

`PRODUCT_ANALYTICS_ENABLED` is a runtime boolean, default false. See
[product analytics](product-analytics.md) for the separate v1 schema, global quotas,
local retention, no-cookie ingestion and private aggregate boundary. No browser
secret or additional service is required. Enabling production is not authorized.

`FEEDBACK_OVERVIEW_ENABLED` is a runtime boolean, default false, gating a private
current-rating aggregate only. It does not enable public collection, raw message
review or training. See [feedback and improvement](feedback-and-improvement.md).
