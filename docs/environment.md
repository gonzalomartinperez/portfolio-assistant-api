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
| EMBEDDINGS_PROVIDER | fixture | Only deterministic 64D hash embeddings are currently implemented |
| ALLOW_PAID_AI | false | Requires openai provider, a key and separate owner authorization |
| OPENAI_API_KEY | unset | Server-only; never read/use a real key without authorization |
| OPENAI_MODEL | gpt-6-luna | Existing adapter default; access/pricing remain unverified |
| MONTHLY_BUDGET_USD | 10.00 | Positive finite ceiling; no automatic spending authorization |
| RESERVE_CUTOFF_USD | 9.00 | Atomic admission ceiling, at most monthly budget |
| RESERVATION_USD | 0.05 | Must conservatively cover bounded maximum input/output at configured prices |
| INPUT_USD_PER_MILLION / OUTPUT_USD_PER_MILLION | 0.10 / 0.50 | Fixture configuration examples, **not a current model price claim**; explicitly configure for production paid mode |
| LANGSMITH_TRACING / LANGCHAIN_TRACING_V2 | disabled by fixture script/image | Do not enable external conversation tracing without a privacy review |

Compose-only variables: `COMPOSE_PROJECT_NAME`, `POSTGRES_PORT`, `NEO4J_PORT`,
`NEO4J_HTTP_PORT`. `ASSISTANT_PROJECT` sets the project selected by the fixture
script. They do not change application policy. Bind database ports only to loopback
for local work; keep both databases on private networks in a VPS deployment.

Fixed policy bounds are documented in the threat model. Raising them requires an
explicit code/review/evaluation change, not a silent environment override.
