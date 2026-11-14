# Public assistant-knowledge handoff

Owner: portfolio. No portfolio files or feature flags were changed here. Public main
was inspected at `f2fca923a4d109937378e0f12779f817688fd537` for evaluation and later
at `e770c3894732f69f96e45c2459a7c2b341bb29aa`. The index remains deliberately frozen
for comparison; production synchronization remains the existing versioned worker.

Those paths/revisions describe the historical evaluation. The current producer's
eight-file relocation and required reader/worker compatibility are recorded in the
[content-layout handoff](portfolio-content-layout.md). Review the corresponding
`content/{en,es}/projects.ts` paths after that coordinated cutover; retain historical
citations at their original committed paths.

Before enabling the native assistant, review public descriptions in
`src/content/en/projects.ts`, `src/content/es/projects.ts` and, if adopted,
`public/assistant-knowledge.json` under the existing knowledge schema. The current
approved evidence documents integration boundaries but not this assistant's stack
clearly enough; the model therefore distinguishes documented client work from
unconfirmed details of the portfolio assistant.

Suggested owner-reviewed facts, backed by this public API repository and its final
committed implementation/evidence: LangGraph orchestrates the workflow; PostgreSQL/
pgvector and Neo4j provide source-backed retrieval; GPT-6 Luna uses medium effort;
no automatic generation retry or alternate provider exists; optional official-documentation
context is bounded and never establishes career/personal facts. The separate public
backoffice repository implements authenticated private operations, not a second public
chat. Describe capabilities as implemented/prepared, not deployed or enabled.

Do not publish keys, private prompts, operational credentials or career-ops material.
Do not add unpublished age/nationality from residence or graduation dates. Keep dates,
qualifiers, personal/team attribution and deployment status explicit in both languages.
This is a data/content handoff, not authorization to change launcher, CSP, DNS or deployment.

Verification after an approved public commit: import only that committed revision,
confirm index activation and immutable citations, ask about this assistant's stack
in both languages, and repeat direct/continuity cases without letting web documentation
stand in for portfolio evidence. Keep the existing disabled assistant flag unchanged
until separately approved. The API/public SSE schema is unchanged by this increment.
