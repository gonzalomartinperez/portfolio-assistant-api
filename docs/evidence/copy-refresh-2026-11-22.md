# Copy refresh draft, 2026-11-22 (M6-7, OD-09)

Status: **draft awaiting owner approval.** The README changes in the same pull request describe only what
the repository verifiably contains. The GitHub repository description and topics below are not applied:
`gh repo edit` runs only after the owner approves this copy (M6 lead brief).

## Sources for every claim

| Claim | Source |
|---|---|
| Bilingual, US English and neutral Latin American Spanish | `evals/golden/manifest.json` (EN 40, ES 40); `src/portfolio_assistant/presentation/problems.py` (EN and ES messages) |
| FastAPI and LangGraph | `pyproject.toml` dependencies; `src/portfolio_assistant/ai/workflow.py` |
| Hybrid lexical, vector and graph retrieval; PostgreSQL 18 with pgvector; Neo4j 5.26 | `src/portfolio_assistant/ai/retrieval/`; `infra/docker/postgres/Dockerfile`; CI Neo4j service pin |
| Cited answers over SSE | `contracts/` SSE schema; `docs/reference/api-contract.md` |
| RFC 9457 problem documents | ADR 030 |
| Atomic spend cap | `src/portfolio_assistant/domain/budget.py`; atomic reservation in the PostgreSQL ledger adapter |
| Golden and retrieval eval gates | `just eval-golden`; `evals/baselines/retrieval.json` (hybrid Recall@5 0.810 on 131 queries) |
| 1,000-question assistant bank | `evals/assistant.json` (`cases`: 1000) |
| SBOM and provenance on release candidates | CI container job; `scripts/release_candidate.py` |

Not claimed anywhere: live answer quality, latency in production, user numbers, or that the assistant is
deployed. Golden replay has no committed cassettes yet, so no pass rate is stated.

## Repository description (current, then proposed)

Current: "Bilingual RAG assistant for my portfolio: FastAPI and LangGraph, hybrid lexical, vector and graph
retrieval (pgvector, Neo4j), cited answers over SSE and a 1,000-question eval bank."

Proposed (248 characters): "Bilingual (EN/ES) RAG assistant API for my portfolio: FastAPI and LangGraph,
hybrid lexical, vector and graph retrieval on PostgreSQL 18 and pgvector, cited answers over SSE, RFC 9457
errors, an atomic spend cap and golden and retrieval eval gates."

## Topics (current 17, proposed 19)

Keep: `ai-assistant`, `fastapi`, `langgraph`, `neo4j`, `pgvector`, `portfolio`, `postgresql`, `python`,
`retrieval-augmented-generation`, `server-sent-events`, `clean-architecture`, `openai`, `agentic-ai`,
`graphrag`, `langchain`, `llm-evaluation`, `rag`.

Add: `mutation-testing`, `sbom`.

Homepage stays `https://gonzalomartinperez.com/work#project-portfolio-assistant`.

## Command to apply after approval

```sh
gh repo edit gonzalomartinperez/portfolio-assistant-api \
  --description "<approved description>" \
  --add-topic mutation-testing --add-topic sbom
```

If ADR 018's retirement of Neo4j executes later, remove `neo4j` and `graphrag` and the graph wording in the
same change.
