# Assistant quality evaluation

`evals/assistant.json` contains 120 authored bilingual questions (60 English, 60
Spanish), 40 held out from prompt tuning, and 40 adversarial prompts. Existing
`evaluate_conversations` core/continuity suites cover 15 multi-turn scenarios.
These are evaluation inputs and review rubrics, not verified answers or public RAG
content. Review status remains pending until actual model output is assessed.

## Safe local fixture execution

After isolated migrations and pinned public indexing:

```sh
uv run python -m scripts.evaluate_assistant --mode fixture --split all --limit 10 --output artifacts/assistant-fixture.json
uv run python -m scripts.evaluate_assistant --mode fixture --split adversarial --limit 40 --output artifacts/adversarial-fixture.json
uv run python -m scripts.evaluate_conversations --suite core --output artifacts/conversations.json
uv run python -m scripts.evaluate_conversations --suite continuity --output artifacts/continuity.json
```

The harness owns a loopback server and rejects nonlocal/production databases.
Synthetic loopback-proxy visitor addresses allow representative users through the
unchanged per-subject limits; this is a test-only configuration, not a production
rate exception. It deletes its own sessions and leaves usage reservations intact.
It never automatically retries a generation. Fixture configuration explicitly
selects both fixture adapters and never loads a key from `.env.local`.

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
