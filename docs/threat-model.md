# Threat model and privacy

Assets: anonymous session credentials, conversation text, public-source integrity,
provider budget and deployment credentials. Trust boundaries are browser → HTTP,
HTTP → application/storage, public Git → indexing, workflow → provider and
operator → deployment. The model authorizes none of them.

| Boundary / threat | Executable control | Remaining limit |
| --- | --- | --- |
| Anonymous session theft / cross-session access | High-entropy host-only HttpOnly cookie, SHA-256 digest at rest, expiration, owner predicates on reads/mutations; ownership tests cover history, rename, deletion, streaming, run read/cancel and feedback | A stolen browser cookie grants that anonymous session; no account recovery |
| Cross-site mutation | Exact Origin allowlist, credentialed CORS without wildcards, constant-time CSRF token comparison, bootstrap header and JSON content type | SameSite=Lax assumes same-site frontend/API hosts; unrelated cross-site hosting needs a coordinated cookie/versioning review |
| Production cookie/config errors | Production requires HTTPS origins, secure __Host cookie, explicit DB/graph credentials and random rate hash key | TLS and actual proxy/browser behavior are deployment checks |
| Abuse / runaway cost | 32 KiB request bytes, 4,000-char question, 100 conversations/session, 200 history rows/conversation, one active run/conversation, four global active runs, 20 bootstraps/IP/hour, 30 messages/session/hour; atomic reservations | Distributed attackers can consume anonymous allowances; reverse-proxy connection/body deadlines still matter |
| Unbounded AI work | Five source chunks, 22,000-char context, 40,000-char emergency output bound, 8,192 provider output/reasoning tokens, 60-second default run deadline; bounded connection/query waits | Fixture embeddings do not establish live semantic quality; prices must be revalidated before paid use |
| Provider credentials / tools | Fixture default, explicit paid opt-in, startup validation, no model tools, no authorization delegated to prompts, no mutation/query execution from model text | A real provider receives the question and bounded public evidence when explicitly enabled |
| Prompt injection | Source content remains user-level data beneath developer instructions; no tool capabilities; fixture rejects known hostile excerpt patterns; public SSE allowlist | Prompts and regexes do not solve injection. A live model may still produce unsupported claims or disclose prompt text |
| Malicious ingestion / SSRF | Sole approved Git remote, fixed HTTPS fetch with redirects/rewrite disabled, explicit path/mode allowlist, blob-size check, UTF-8 decoding, subprocess timeout, no file execution/submodules | Public source review is still required; local origin metadata alone is not proof of public approval |
| Graph/SQL injection | Parameterized values, fixed Cypher templates, version predicates, bounded traversal/query timeout, provenance/hash validation | An authorized operator controlling databases can corrupt indexes; rebuild from reviewed source |
| Failed indexing | Advisory lock, staging version, one graph transaction and activation only after both projections verify | Retired/staging versions consume disk until explicit operator cleanup |
| Sensitive logs/errors | Generated correlation IDs, structured route/status/count/timing/token/cost records, safe error codes, no request bodies/cookies/prompts/SQL exception text | Third-party server logging and reverse proxy access logs need deployment review; external tracing is disabled for fixture/container |
| Deletion / crash | Transactional delete plus durable checkpoint tombstones, retries via retention CLI, seven-day session expiry, lease interruption | Schedule retention every minute. Recent tombstones remain ten minutes to catch late writes; DB downtime delays physical cleanup |
| Admin abuse | No indexing/admin HTTP routes; CLI requires operator filesystem and database access | Operators must restrict shell access and protect backup credentials |

Conversation state and checkpoints may contain questions and public context. They
are not part of retrieval knowledge, and there is no conversational memory product.
Deletion cascades messages, feedback and run ownership. Spend entries retain
amount/time with run references cleared for monthly budget enforcement; rate hashes
are purged after two days. Retention is configurable from 1–30 days, default seven.
Backups have an independent operator retention/deletion policy and must be encrypted.

## Security verification and reporting

Use [SECURITY.md](../SECURITY.md) for private reports. `scripts/scan_secrets.py`
checks known credential patterns in Git blobs and tracked files and emits only
paths/object IDs/detector names. The 2026-09-27 scan found no matches in 135 history
blobs; this limited detector is not an exhaustive secret audit or replacement for
provider-side scanning. Never print suspected values or rewrite history/rotate
external credentials without owner authorization.

## Authorized live evaluation (not run)

Obtain explicit paid-use authorization and a reviewed maximum spend first. Confirm
model access, current token prices, conservative reservation and provider retention
settings. Use only the public corpus and synthetic questions. Evaluate bilingual
facts, attribution caveats, unsupported employers/metrics, direct and retrieved
injection, citations, partial failure and real streaming through the intended
proxy. Record costs and failures; do not treat a small passing sample as proof of
safety. No live credentials or paid calls were used for this implementation.
