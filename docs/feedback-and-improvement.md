# Voluntary context and evidence-based improvement

The assistant can use volunteered context to answer a relevant professional question.
It does not train a model, add visitor claims to the public corpus or turn private
conversation text into analytics. A helpful response need not repeat an email,
phone number or unrelated third-party detail. Provider instructions encourage that
behavior without scolding people for sharing context; instructions are not proof
that every model answer will comply.

## Implemented minimization

`app/domain/privacy.py` recognizes common ASCII email, explicit international-phone,
and OpenAI-key/Bearer-like patterns. Retrieval questions and outbound bounded history
use the minimized text; the concrete Responses adapter also applies it before provider
I/O, including direct adapter calls. Public source evidence is intentionally unchanged.
Replacements do not increase character/UTF-8 bounds for the tested patterns; dates,
version numbers and ordinary career context remain intact. Model/reasoning/output
limits, store=false, zero retries and language rules are unchanged.

This is best effort, not a comprehensive PII detector. Names, local-format numbers,
addresses and other sensitive context can remain. Original messages are still stored
under the established private session/history policy; this change is not database
redaction, anonymization or a physical-erasure guarantee. Providers can still receive
remaining question/history/evidence needed for the response. Store=false does not
establish OpenAI Zero Data Retention. Do not promise that all private data is removed.
No transcript, contact, token or identifier is added to logs/operational/product metrics.

## Actual feedback signal

The existing authenticated, CSRF-protected public rating operation accepts only up/down
for a message owned by the session. Repeated ratings replace the current vote; they do
not create multiple votes. Deleting the owned conversation/session cascades the rows.
No freeform comment, new visitor identity or automatic-learning pipeline is added.

Optional `FEEDBACK_OVERVIEW_ENABLED=false` gates the private read:
`GET /internal/ops/v1/feedback`, authenticated with existing server-only OPS_READ_TOKEN.
The separate `contracts/feedback.schema.json` describes version1, project portfolio,
observed_at, seven-day window, basis retained_answer_creation, and up/down counts.
No public OpenAPI route, raw content, message/session ID or service credential is returned.
The runtime database grant already covers SELECT on feedback/messages; no migration,
collector, port or persistent store is added. No-store/private-proxy requirements apply.

The window is based on **answer creation**, because the current table has no rating
submission timestamp. Counts are the current opinions on retained assistant answers
created within seven rolling days, not lifetime events, unique people, verified answer
correctness or an immutable quality ledger. Votes can change and deletion reduces totals.
Unavailable/off must not become zero. The backoffice consumer is separately integrated
against an identified committed schema; this repository does not ship its screen.

## Human improvement workflow

1. Review authorized aggregate counts, their window, sample size and limitations.
   A downvote is a triage signal; counts alone cannot explain which fact or wording failed.
2. Describe a reproducible public-profile scenario without copying raw messages,
   contacts, private career material or conversation identifiers into issues/Git.
   There is no raw-conversation review/export capability in this increment.
3. Add a synthetic bilingual case to the existing canonical
   `evals/assistant-intents.json` or conversation suite. Keep family splits and public
   provenance intact. Use [the maintained harness](assistant-evaluation.md), not a
   second feedback-specific evaluation system.
4. A human reviews a task PR changing approved content, retrieval or prompt behavior;
   run fixture/unit/contract/real-service checks as applicable. A live evaluation is a
   separately authorized paid action, not a consequence of a rating or an Actions run.
5. Integrate reviewed source, record actual evidence and select a compatible release.
   Deployment/collection activation remain separately authorized and ops-owned.

This is a concrete manual maintenance procedure supported by persisted ratings,
private aggregate reads and the existing evaluation/PR tooling. It is not automatic
fine-tuning, self-modifying prompts, an anonymization service or conversation analytics.
Future raw-chat review would require its own purpose/access/retention/deletion/notice
contract before implementation; an owner's wish to improve quality does not enable it.

## Verification boundary

Synthetic unit tests cover identifier handling, non-increasing/idempotent text,
normal input acceptance, re-grounding and private-read defaults. Real OpenAI SDK tests
use MockTransport to inspect outbound JSON without external calls and preserve approved
public evidence. These prove request construction, not natural-language compliance.
The isolated PostgreSQL lifecycle test covers vote replacement and deletion reflected
in aggregates; exact CI receipts belong to the PR. No paid provider calls are required.
