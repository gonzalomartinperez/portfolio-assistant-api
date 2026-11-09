# Sources

Every external source this plan relies on, with date and commercial-interest flag. **Provenance:** URLs and flags are taken from the shared research notes written 2026-11-09 (copied into [research/](research/)); the planner of this repository did not re-fetch them in this task. Where a claim is the planner's own synthesis it is marked as such in the plan text. Flag key: **P** primary or official; **B** blog or secondary; **C** commercial interest in the topic or tool (as flagged in the research notes, or stated here when the owner of the page sells a related product).

## 1. Repository evidence read for this plan (not external)

| Item | Reference | Date |
|---|---|---|
| Source tree, AGENTS.md, CONTRIBUTING.md, README.md, pyproject, Dockerfile, workflows, evals, scripts, tests, docs | `origin/develop` `e749ca762fb3f1e74225d9126d4eb1bbd88e2885` | 2026-11-09 |
| v1 plan (kept where right) | `origin/main` `3da09ef82878165c063b9c9742eaf4fb8c2ee50b`, `docs/master-plan/` | 2026-10-24 content |
| Measured audit | `audit/portfolio-assistant-api/` (planner bundle; compact copies in [audit/](audit/)) and sibling `audit/pequeverso-assistant-api/` for comparison | 2026-11-09 |

## 2. Assistant evaluation (research note [03](research/03-rag-evals.md))

| Source | URL | Flag |
|---|---|---|
| Anthropic, Demystifying evals for AI agents | https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents | P, C (model vendor) |
| Husain, Evals FAQ | https://hamel.dev/blog/posts/evals-faq/ | B, C (sells evals training) |
| Husain, Creating an LLM-as-a-Judge that drives business results | https://hamel.dev/blog/posts/llm-judge/ | B, C |
| Shankar et al., Who Validates the Validators? | https://arxiv.org/abs/2404.12272 | P |
| ranx | https://pypi.org/project/ranx/ | P (MIT) |
| How to Correctly Report LLM-as-a-Judge Evaluations | https://arxiv.org/html/2511.21140v3 | P |
| LLM-judge measurement error (Rogan-Gladen versus PPI) | https://www.arxiv.org/pdf/2601.05420 | P |
| Yan, Evaluating the effectiveness of LLM-evaluators | https://eugeneyan.com/writing/llm-evaluators/ | B |
| MEMERAG multilingual RAG meta-evaluation | https://aclanthology.org/2025.findings-emnlp.849 | P (summary only) |
| XRAG cross-lingual RAG | https://arxiv.org/abs/2505.10089 | P |
| AbstentionBench | https://arxiv.org/abs/2506.09038 | P |
| tau-bench (pass^k) | https://arxiv.org/pdf/2406.12045 | P |
| ALCE citations | https://arxiv.org/pdf/2305.14627 | P |
| RAGChecker | https://arxiv.org/pdf/2408.08067 | P |
| GraphRAG-Bench, When to use graphs in RAG | https://arxiv.org/abs/2506.02404 ; https://arxiv.org/abs/2506.05690 | P |
| OWASP Top 10 for LLM Applications 2025 | https://genai.owasp.org/llm-top-10/ | P |
| OpenAI to acquire Promptfoo | https://openai.com/index/openai-to-acquire-promptfoo/ | C (fetch blocked in the research run; facts via secondary coverage) |
| LangSmith datasets, prompts, pytest integration | https://docs.langchain.com/langsmith/manage-datasets ; https://docs.langchain.com/langsmith/manage-prompts ; https://docs.langchain.com/langsmith/pytest | P, C (LangChain sells LangSmith) |
| Leakage-free RAG benchmarks, held-out leakage | https://arxiv.org/html/2605.08838 ; https://arxiv.org/abs/2601.13227 | P |

## 3. Python architecture and tooling ([02](research/02-python-architecture.md), [10](research/10-standards-dependencies.md))

| Source | URL | Flag |
|---|---|---|
| Google Python Style Guide | https://google.github.io/styleguide/pyguide.html | P |
| import-linter docs | https://import-linter.readthedocs.io/en/stable/ | P |
| uv Docker guide | https://docs.astral.sh/uv/guides/integration/docker/ | P (Astral, now OpenAI-owned per [02], flagged C) |
| Ruff docs | https://docs.astral.sh/ruff/ | P, C (same owner) |
| FastAPI SSE tutorial | https://fastapi.tiangolo.com/tutorial/server-sent-events/ | P |
| Python 3.14 What's New | https://docs.python.org/3/whatsnew/3.14.html | P |
| psycopg 3 pools | https://psycopg.org/psycopg3/docs/advanced/pool.html | P |
| Neo4j driver best practices | https://neo4j.com/blog/developer/neo4j-driver-best-practices/ | P, C (Neo4j vendor) |
| Cosmic Python (hexagonal in Python) | https://www.cosmicpython.com/book/preface.html | B |
| RFC 9457 Problem Details for HTTP APIs | https://www.rfc-editor.org/rfc/rfc9457 | P |

## 4. Testing ([04](research/04-testing.md))

| Source | URL | Flag |
|---|---|---|
| mutmut | https://github.com/boxed/mutmut | P |
| Hypothesis docs and changelog | https://hypothesis.readthedocs.io | P |
| Schemathesis stateful testing | https://schemathesis.readthedocs.io/en/latest/guides/stateful-testing/ | P |
| oasdiff | https://github.com/oasdiff/oasdiff | P, C (hosted tier) |
| diff-cover | https://pypi.org/project/diff_cover/ | P |
| Petrovic et al., Practical Mutation Testing at Scale (Google) | https://arxiv.org/pdf/2102.11378v1 | P |
| Trail of Bits, Mutation testing for the agentic era | https://blog.trailofbits.com/2026/04/01/mutation-testing-for-the-agentic-era/ | B, C (consultancy) |
| Testcontainers for Python | https://testcontainers-python.readthedocs.io/en/latest/ | P |

## 5. CI, supply chain, containers ([05](research/05-cicd-supply-chain.md), [11](research/11-containers-dynamic-ci.md))

| Source | URL | Flag |
|---|---|---|
| GitHub Actions secure use | https://docs.github.com/en/actions/reference/security/secure-use | P |
| Dependabot options reference | https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference | P |
| release-please | https://github.com/googleapis/release-please-action | P |
| Artifact attestations | https://docs.github.com/en/actions/concepts/security/artifact-attestations | P |
| Docker attestations in CI | https://docs.docker.com/build/ci/github-actions/attestations/ | P |
| zizmor | https://docs.zizmor.sh | P |
| OpenSSF Scorecard | https://securityscorecards.dev | P |
| SLSA v1.2 | https://slsa.dev/spec/v1.2 | P |
| Trivy compromise advisory (March 2026) | https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23 | P |
| endoflife.date, Python devguide, Node schedule | https://endoflife.date ; https://devguide.python.org/versions/ ; https://raw.githubusercontent.com/nodejs/Release/main/schedule.json | P |
| Distroless | https://github.com/GoogleContainerTools/distroless | P |
| Coolify firewall and Docker packet filtering | https://coolify.io/docs/knowledge-base/server/firewall ; https://docs.docker.com/engine/network/packet-filtering-firewalls/ | P |

## 6. Documentation and agent harness ([08](research/08-docs-readme-skills.md))

| Source | URL | Flag |
|---|---|---|
| Agent Skills specification | https://agentskills.io/specification | P |
| MADR | https://adr.github.io/madr/ | P |
| Diataxis | https://diataxis.fr | P |
| Keep a Changelog | https://keepachangelog.com | P |
| FastAPI README as a showcase model | https://github.com/fastapi/fastapi | P |
| Claude Code docs (memory, settings, hooks, sub-agents, skills, plugins, GitHub Actions) | https://code.claude.com/docs ([15](research/15-claude-code-harness.md)) | P, C (Anthropic) |
| Codex docs (AGENTS.md, config, hooks, skills, action) | https://learn.chatgpt.com/docs ([14](research/14-codex-harness.md)) | P, C (OpenAI) |

## 7. Repository-cited sources (from the repo's own decision log, read at the SHA above)

| Source | URL | Flag |
|---|---|---|
| OpenAI Responses streaming guide | https://developers.openai.com/api/docs/guides/streaming-responses | P, C (provider) |
| OpenAI model page `gpt-6-luna` | https://developers.openai.com/api/docs/models/gpt-6-luna | P, C |
| Neo4j 5 configuration reference (usage report and Bolt telemetry) | https://neo4j.com/docs/operations-manual/5/configuration/configuration-settings/#config_dbms.usage_report.enabled | P, C |
| pgvector | https://github.com/pgvector/pgvector | P |

Unverified items and where they are flagged: Dependabot grouped-PR behaviour ([ci-cd.md](ci-cd.md) section 8), mutmut on Python 3.14 ([testing.md](testing.md) section 6), `lingua` share of the image and Neo4j marginal gain ([audit.md](audit.md), README section 6), configured model prices ([assistant-quality.md](assistant-quality.md) section 12), licence and health columns ([dependencies.md](dependencies.md)).
