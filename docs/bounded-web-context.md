# Portfolio-first tools and optional web context

The assistant's purpose is Gonzalo's approved public profile, projects and directly
relevant technical explanations. Internet access supplements that purpose; it never
establishes career facts, personal details, availability or achievements.

## Capability inventory and boundaries

| Capability | Actual implementation and constraints |
| --- | --- |
| Public retrieval | Hybrid lexical/semantic ranking, verified immutable spans, at most five sources and 19,000 evidence characters |
| Graph relationships | Parameterized bounded Neo4j queries over source-backed active-version relations; no model-generated Cypher |
| Conversation continuity | Owned session/history, at most twelve prior turns / 8,000 characters; visitor text is not evidence |
| Language | Local detection, server-resolved English/Spanish, supported output guard; no extra routing model |
| Web complement | One fixed technical query, at most two built-in calls for one fixed topic, exact approved domain and validated document URLs |
| Generation | GPT-6 Luna, medium effort, streaming, no automatic retry or alternate model/provider |
| Actions | No model shell, browser navigation, email, writes, private-document lookup or arbitrary database tools |

The model does not autonomously choose tools or query parameters. Domain policy
requires an explicit supported technology, a portfolio/person/project anchor, an
explanation or current-documentation request, and that technology in retrieved public
evidence. Ambiguous multi-technology requests, private-data requests, visitor URLs,
email addresses and unrelated requests do not activate web search. This conservative
router is not a universal semantic classifier; the generation prompt also constrains
scope. Regression tests cover both routing and real response behavior.

Topics and query/domain pairs are canonical in `app/domain/web_policy.py`:
LangGraph, Neo4j, pgvector, PostgreSQL, FastAPI, Next.js and OpenTelemetry. GitHub
references are additionally restricted to `/pgvector/pgvector`; allowing the GitHub
search domain does not make other repositories acceptable evidence.

## Data flow, accounting and failure behavior

The search adapter receives only a fixed public technical query. No visitor question,
history, presentation metadata, session identifier or credential enters that query.
The final generation receives a separately labelled untrusted technical supplement;
public portfolio evidence remains authoritative for claims about Gonzalo. External
sources use visible document links rather than immutable career-source citation cards.
The public v1/SSE schemas are unchanged. A citation/link does not independently verify
an answer, and prompt instructions are not a proof against all injection attempts.

Search uses the same authorized OpenAI account/model with medium effort, `store=false`,
a low search context, at most two tool calls, 2,048 output-token ceiling and no automatic retry.
The account-level fee and input/output tokens share the atomic monthly spend ledger,
including semantic embeddings and normal generation. Before I/O, the search reserves
its full 1,050,000-token model-window cost at the documented long-context multipliers
plus two call fees. With the current standard prices this is USD0.231536. Known usage
settles actual cost; cancellation, timeout or absent usage retains the reservation.
This conservative amount can skip optional search near the budget ceiling.

Successful public summaries cache for one hour in memory, at most seven topics, with
per-topic request coalescing. Different topics do not block each other. Cache misses
wait at most the configured timeout for the topic lock and at most that timeout for
network completion. An optional-search timeout, invalid result or insufficient search
budget leaves the answer grounded in the RAG alone; no invented browsing claim is
allowed. OpenAI API errors report provider unavailability. Cancellation propagates;
there is no second generation or fallback provider. No external summary is persisted
as a portfolio fact, and no visitor query is cached.

## Configuration and rollout

`WEB_SEARCH_ENABLED=false` is the safe default. Enabling requires explicitly authorized
OpenAI generation and paid allowance. `WEB_SEARCH_TIMEOUT_SECONDS` is 1–15 (default12).
`WEB_SEARCH_USD_PER_CALL` must cover the reviewed fee (default USD0.01); prices are runtime
configuration, not an invoice guarantee. No new service, migration, secret type or
client-side key is required. Changes require restarting the API, not rebuilding UI.
Vps-ops owns any later production activation; the portfolio remains disabled.

The frozen exploratory manifest `evals/web-context-2026-10-13.json` contains 264 turns:
the previously reviewed 244-turn suite plus fourteen bilingual technical-complement
requests and six scope/security requests. These are exposed regressions, not fresh
holdout. Live results, exact corpus revision, cost and first-output/completion timing
are recorded separately under `docs/verification/`; structural tests alone do not
establish actual model quality. Raw answers and signed/secret artifacts stay ignored.

Verify with the existing frozen install, Ruff, strict mypy, unit/real-service tests,
contract export/drift, image smoke and isolated authorized evaluation commands.
Focused regression: `uv run pytest -q tests/test_web_context.py`.

Official references checked 2026-10-13:
[web search](https://developers.openai.com/api/docs/guides/tools-web-search),
[GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna),
[pricing](https://developers.openai.com/api/docs/pricing) and
[agent safety](https://developers.openai.com/api/docs/guides/agent-builder-safety).

Live exploration exposed OpenAI attribution parameters in citation URLs. Only the
exact `utm_source=openai` pair and a bounded document anchor are removed before
revalidating the canonical HTTPS authority/path; arbitrary query parameters remain
rejected. Named public technology spans now retain a retrieval slot when generic
portfolio documents crowd the top five. This does not establish technology expertise
from a mere mention; the answer must preserve the actual source attribution.

The search request allows automatic tool choice but explicitly requests one search
and no follow-up browsing; results exceeding two reported built-in calls are rejected.
Live observations showed that a requested call ceiling alone is insufficient evidence
of the returned sequence. Actual reported usage/call count is validated and charged,
including rejected results. Search results can be unavailable without changing
portfolio facts.

Input detection now reuses the bounded six-language normal-accuracy model used by
the output guard, rather than an all-language low-accuracy model. Ambiguous proper
names preserve the supported locale hint; explicit English/Spanish requests retain
priority. The frozen 264-question replay produced only six intentional language
switches relative to hints, in 710ms including initialization on the local WSL host.
This is tool-policy evidence, not a universal language-detection guarantee.
