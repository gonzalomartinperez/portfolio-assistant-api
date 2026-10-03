# Assistant quality evaluation

`evals/assistant.json` contains **1000 questions** in 100 intent families: five
variations for each English/Spanish locale hint. The source is
`evals/assistant-intents.json`: three authored bilingual phrasings per family
(600 questions), plus concise and evidence-limits request variants (400 questions).
This distinction avoids presenting format variants as 1000 independent intents.

The 120 original cases retain their IDs and wording. All variations of a family
share one split: 670 development cases and 330 holdout cases, with no paraphrase
leakage between them. Forty additional adversarial prompts are preserved. Language
policy cases deliberately include mixed/unsupported input languages; output must
still be English or Spanish. Existing conversation suites cover 15 multi-turn scenarios.

Topics include profile, recent roles, public agent/RAG work, projects, qualified
metrics, education, role fit, public personal information and privacy boundaries.
Question topics were reviewed against committed public portfolio
`0b363684fd1bafacafbba3924488f51cbc011a5c`. Older project names can remain documented
in experience even when absent from the featured-project list. Never turn a leading
question, missing nationality/age, estimated metric or employer context into a fact.

These are evaluation inputs, **not runtime knowledge, memorized answers or training
data**. The RAG reads the active public corpus and is not restricted to these
questions. Keep both bank files outside indexing, prompts and production images.
More question coverage does not create missing facts or prove live-model quality.

## Maintain the bank

Edit the canonical intent source, keeping paraphrases semantically aligned and
English/Spanish copy natural. Do not hand-edit the generated artifact. Family IDs
and existing case IDs are stable; split changes require explicit review. Then run:

```sh
uv run python -m scripts.build_assistant_bank
uv run python -m scripts.build_assistant_bank --check
uv run pytest -q tests/test_grounded_assistant.py
```

The compiler rejects duplicate normalized wording/identities, missing locales and
oversized questions. CI validates generated drift and the tests check family split
isolation. Default ten-case sampling spans ten topics and both locale hints rather
than spending a paid sample on ten paraphrases of one question. Full sampling is
without replacement. Report initial corpus/version and per-answer citation revisions.

## Safe local fixture execution

After isolated migrations and pinned public indexing:

```sh
uv run python -m scripts.evaluate_assistant --mode fixture --split all --limit 1000 --output artifacts/assistant-fixture-1000.json
uv run python -m scripts.evaluate_assistant --mode fixture --split adversarial --limit 40 --output artifacts/adversarial-fixture.json
uv run python -m scripts.evaluate_conversations --suite core --output artifacts/conversations.json
uv run python -m scripts.evaluate_conversations --suite continuity --output artifacts/continuity.json
```

The harness owns a loopback server and rejects nonlocal/production databases.
Synthetic loopback-proxy visitor addresses allow representative users through the
unchanged per-subject limits; this is a test-only configuration, not a production
rate exception. It deletes its own sessions and leaves usage reservations intact.
It never automatically retries a generation. Each case uses a separate synthetic
benchmark-network address; production rate limits are unchanged. Failed/incomplete
terminal events produce a nonzero exit code after the report is written. Fixture configuration explicitly
selects both fixture adapters and never loads a key from `.env.local`.

Recorded fixture runs and their limitations are in
[question coverage evidence](verification/question-coverage.json). The expanded
development bank exposed spoken-language retrieval selecting technical paragraphs;
the ranking now prefers public profile language fields while excluding programming
language questions and response-language preferences. The fixture preserves both
published proficiency levels, including in concise answers. Real-model answer
quality still needs separately authorized review.

## Authorized OpenAI execution

Only after owner approval: configure the isolated database and environment with
AI_PROVIDER=openai, EMBEDDINGS_PROVIDER=openai, ALLOW_PAID_AI=true and a private
runtime OPENAI_API_KEY. Supply explicit reviewed pricing and remain within the
USD 10 monthly ceiling shared with other application operations. Index semantic
knowledge first; readiness rejects a mismatched fixture corpus. No paid calls or
keys belong in CI, committed reports, shell history or command arguments.

Then run the same harness with `--mode openai --allow-paid`, initially `--limit 10`.
Increase coverage after reviewing readiness, behavior, costs and remaining budget.
The flag is not standing authorization. Evaluate development and holdout separately;
do not tune prompts using holdout answers. The report leaves human_scores null and
live_quality_verified false: timing and successful SSE are not answer-quality scores.

Review factual accuracy, abstention, supported language, source support and utility.
Record corpus/source revision, model, effort, prices, timing, incurred costs and
reviewer evidence. Distinguish unknown personal facts from confirmed public facts.
Review every citation's actual support, not only whether its URL resolves.

Acceptance targets: retrieval Recall@5 >=95% on answerable reviewed holdout;
correct facts/abstention >=95%; valid citation provenance 100%; citation support
>=95%; language >=99% on unambiguous cases; zero thematic third-language replies
and zero observed privacy/authorization violations in the finite adversarial bank.
Critical safety failures block readiness independently of averages. Fixture excerpts
cannot establish any of these real-model percentages or universal safety guarantees.

Local language benchmark: 120 synthetic messages, Lingua low-accuracy mode, Python
3.14.4 under WSL Linux x86_64: cold initialization+first detection 32.602 ms,
warm p95 3.432 ms, whole-process peak RSS 175.61 MiB. This is detector evidence,
not browser performance or future VPS capacity. The native wheel adds ~162 MiB
compressed download, a deliberate dependency tradeoff requiring production measurement.

LangSmith remains a transitive LangChain dependency; no tracer/exporter is enabled.
There is no OpenTelemetry dependency or exporter. Removing a required transitive
package by patching dependencies would break reproducibility; configuration rejects
external tracing instead. Operational redacted local logs are retained.
