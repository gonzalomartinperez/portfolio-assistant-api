> Latest local evidence: [244-turn authorized OpenAI evaluation](verification/live-depth-2026-10-10.md),
> followed by targeted regressions and database cleanup. Older checkpoints below
> are historical; successful transport is not a universal answer-quality or
> production-readiness claim. Main and the portfolio assistant remain unchanged.

# Audit and live-evaluation readiness · 2026-10-04

Audited API revision: `15b6943f741ac80498a5fee611aa74d24250eb6b`.
This is a dated evidence record and closure guide, not permission to use paid
models, publish images, change protections, promote main or deploy. The single
prioritized status checklist remains [work-checklist.md](work-checklist.md).

## Verified baseline

Fresh isolated PostgreSQL/pgvector and Neo4j fixtures passed **196 tests in 11.10
seconds** (173 offline, 23 integration). The regression corpus was public portfolio
`1acbe54906c88398652aebb8eae0c217fd0d8821`. Hybrid retrieval passed all nine cases in
`evals/retrieval.json`; the comparison's vector-only and graph-only strategies did
not pass every case and are not the configured hybrid acceptance result.

The existing local production image `portfolio-assistant-api:question-coverage`
passed non-root SSE and active-stream SIGTERM checks. This audit reused that image;
it did not rebuild or publish it. Its exact ID and prior build evidence are in
[question-coverage.json](verification/question-coverage.json).

Ruff, formatting, strict mypy over 22 inner/AI files, skill validation, question-bank
drift, offline contract tests and Compose validation passed. Local Markdown path
checks found no missing targets; external links and every anchor were not tested.
The redacted scanner found no known credential patterns in 492 historical blobs;
this is not proof that secrets cannot exist. Fixture services were stopped without
removing volumes. No application or sibling-repository source was changed by the audit.

[Quality run 37160535949](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/37160535949)
passed on implementation head `64840989342938ab34b9759b9e72051c87758110`, merged
through PR #34. It is executed CI evidence for that head, not a substitute for
checks on subsequent commits. The 1000-question bank's final fixture runs completed
670 development and 330 holdout cases against public portfolio
`0b363684fd1bafacafbba3924488f51cbc011a5c`; completion is not a factual-quality score.

## Findings and closure criteria

| ID / priority | Observed state | Owner and required closure |
| --- | --- | --- |
| A1 / before paid testing | `scripts/evaluate_assistant.py:evaluation_server` checks development mode and a loopback PostgreSQL host, but does not reject remote Neo4j. A stubbed-server probe accepted `bolt://graph.example.invalid:7687` without network I/O. A local address also cannot establish that a tunneled database is disposable. | API: validate both database destinations, add rejection tests and require an explicitly owned isolated fixture environment. Do not use the current guard as proof of complete isolation. This documentation does not implement the fix. |
| A2 / live quality gate | All 1000 cases remain pending real-answer review. Semantic embeddings, tone, contextual reasoning, citation support, language compliance and actual provider billing are unverified. Citation-number validation establishes reference membership, not whether each claim follows from its source. | API + owner: separately authorize bounded spend, exercise reviewed development cases, then score independent holdout and adversarial cases using the evaluation guide. Record failures and costs; do not tune against holdout responses. |
| A3 / paired UX gate | Inspected frontend develop `aed8ea710c8b847ddc9066aaef5ce48d3793b494` consumes API snapshot `6b1e65f2406ba5ddf21d15c56c34ccf672d90bbb`. It does not yet consume the starter catalog or explicitly handle `knowledge_updating` and `provider_unavailable`. Existing SSE v1 consumers remain compatible. | Web owner: import the committed current snapshot, regenerate types, runtime-validate suggestions and localize both availability states. Verify `/embed` and `/` against the paired local API, including no automatic generation retry. Publish committed browser evidence. |
| A4 / workflow enforcement | Live main/develop protections require strict `checks` and enforce administrators; required approvals are zero and no rulesets were returned. Main has no implemented develop-only source-branch gate. | Repository owner: decide and authorize an enforceable promotion/hotfix policy that preserves protections and requires explicit owner authority. Verify ordinary promotion and unauthorized hotfix rejection. No settings changed in this audit. |
| A5 / maintenance activation | Auto-merge capability is enabled, but the automation variable is unset and `Dependency policy` is not required. Trusted policy files already exist on main `0d2511e6a9d2ab4a4da5c72c194c7a4eb8aa24b8`; default-branch file presence is no longer the missing prerequisite. Actual privileged-token protection visibility and native merge/rebase behavior remain unverified. PR #31 was correctly ineligible (`unexpected_files`) for its Actions update. | Repository owner: follow the narrow activation procedure in dependency-updates.md, verify token access and ordinary-PR check emission before adding the required check, then authorize enabling the variable. Keep major/workflow updates manual. |
| A6 / long-running operation | Retired/staging corpora, graph projections and public embedding cache currently persist. Repeated portfolio changes can grow disk use; no production pruning policy is implemented. | API + vps-ops: measure growth, define recovery retention and safe pruning, preserve active/in-flight versions and needed rollback evidence, and test interruption/recovery before scheduling cleanup. |
| A7 / public-data coordination | Portfolio main observed as `cb0b56baaa50a1521a4e02eee1d67f13c89d19a2`; its optional `public/assistant-knowledge.json` returned 404. Source-text compatibility remains operational. Public CV/editorial reconciliation is still a separate handoff. | Portfolio owner: publish only approved bilingual facts with dates, attribution and source spans using the committed schema, if adopting the projection. Personal questions do not establish unpublished age/nationality. Test updates, removals and conflicting facts through the worker without editing the portfolio here. |
| A8 / operational release gate | Coolify, effective headers, worker probes, proxy peers, capacity, encrypted off-server restoration and schema-compatible rollback have no production verification. No immutable registry artifact has been published. | vps-ops + owner: select compatible prebuilt digests only after authorized publication; verify the deployment contract, migrations/grants, freshness and retention scheduling, streams/disconnects, recovery and effective iframe headers. Production approval is separate. |
| A9 / documentation accuracy | State headers and the frontend handoff referenced older increments; dependency instructions still described default-branch file absence as the activation blocker. | API: this documentation increment reconciles those descriptions and links the dated audit. Runtime, settings and external integrations remain unchanged; documentation closure does not close A1–A8. |

## Before the first authorized OpenAI test

1. Close A1 and establish fresh, explicitly isolated PostgreSQL/Neo4j targets. Apply
   migrations 001–005 and checkpoint setup, then use narrowly scoped runtime and
   worker credentials. Confirm there is no production data or shared agent service.
2. Obtain explicit paid-use authorization and a bounded test allowance within the
   shared USD 10 monthly application ceiling. No API key is needed for the audit;
   never put a real key in commands, Git, images or reports.
3. Verify account access and current standard pricing for GPT-6 Luna and semantic
   embeddings. Keep medium effort, one model, no fallback and no automatic billed
   retry. Configuration and a successful fixture request do not establish account
   access, billing correctness or real-model quality.
4. Configure authorized runtime OpenAI variables using the
   [evaluation procedure](assistant-evaluation.md#authorized-openai-execution).
   Index an immutable approved public revision with semantic embeddings first;
   count indexing and query embedding costs as well as generation.
5. Begin with the representative development sample, not all 1000 paid requests.
   Review response usefulness, evidence attribution, unsupported personal claims,
   source URLs, both languages, topic changes and partial/outage behavior. Increase
   coverage only after checking costs and unresolved failures. Test cancellation
   without pretending it guarantees zero provider charges.
6. Evaluate holdout separately using the maintained acceptance thresholds in
   [assistant-evaluation.md](assistant-evaluation.md). Record the actual compiler,
   dependencies, API/portfolio revisions, corpus ID, model/effort, prices, usage,
   reviewer scores and first-delta/completion timings. Keep secrets and private
   conversations out of public artifacts. Do not publish hidden reasoning.
7. Exercise a new public revision during an active stream: that stream retains
   immutable provenance, subsequent requests use the activated corpus, and stale
   or failed candidates yield availability states when freshness is required.
   Polling/indexing latency means synchronization is not instantaneous.

The official [GPT-6 Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna)
was checked on 2026-10-04: Responses streaming and medium reasoning are supported.
Account access and actual execution were not tested. Python has a supported release
lifecycle rather than an official LTS designation; PostgreSQL 17 and Neo4j 5.26
remain the documented service baseline. No Redis or OpenTelemetry SDK/exporter is
present. LangSmith remains transitive, with external tracing disabled. Avoid adding
services or removing required transitive packages merely to alter the checklist.

Optional reranking/planning, ANN indexes and additional services remain deferred
until reviewed measurements justify them. A source license is still an owner
decision. Neither future improvements nor this audit authorize production work.
