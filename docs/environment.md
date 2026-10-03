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
| OTEL_SDK_DISABLED | true | False is rejected |

Production OpenAI also requires OpenAI semantic embeddings. The output ceiling is
8,192 tokens including reasoning, fixed in policy; it is not a requested answer length.
Configuration does not authorize paid calls. Visitors' query text may be sent to
OpenAI for embeddings; it is never indexed into the public corpus. Responses use
`store=False`, which does not establish provider Zero Data Retention.
