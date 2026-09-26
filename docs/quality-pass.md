# Quality pass: risk order and acceptance

Observed on 2026-09-26 against the locked checkout and real local PostgreSQL/Neo4j.

| Priority | Baseline evidence | Acceptance gate |
| --- | --- | --- |
| 1: unsupported answers | Direct Filomena works, but Rampy, education and portfolio implementation return no evidence; the English Filomena answer can use Spanish text | Reviewed bilingual questions retrieve the relevant public spans; unknown questions remain unanswered; citations match active source records |
| 2: stream truth | First delta about 186 ms after POST, but the complete answer is generated before 60-character deltas are emitted | A simulated Responses stream yields each upstream delta through the public SSE path; cancellation and terminal state agree with persisted run state |
| 3: transport and security | Session, CSRF, ownership and duplicate-key tests pass; production settings permit local defaults | Production configuration rejects development credentials, insecure cookies, localhost origins and predictable hash keys; request and stream limits have tests |
| 4: frontend quality | Both production builds and Chromium fixture journey pass; standalone presentation is visually disconnected from the portfolio and both clients have async races | Shared contract is validated at runtime; desktop/mobile, both locales and themes, keyboard and recovery tests pass on production builds |
| 5: operations | Real DB tests pass locally; deployment and load claims remain conditional | CI runs real integration, artifacts build and local smoke passes; measured local resources and explicit VPS limits documented |

The release remains fixture-only. Real OpenAI calls, a physical mobile device, VPS load, DNS, deployment and `main` promotion remain separate gates.

## Decisions

- The LangGraph run has strategy, retrieval, validation and generation nodes. Its PostgreSQL checkpoint is scoped by a server-authorized run ID; it never grants access to an HTTP object. The public SSE stream forwards custom text events as the provider yields them. [OpenAI's Responses streaming guide](https://developers.openai.com/api/docs/guides/streaming-responses) documents `stream=True`, `response.output_text.delta` and `response.completed`; the paid path is tested only with a simulated client.
- Retrieval compares anchored lexical spans, real pgvector nearest neighbors and an explicit read-only `Project` → `SUPPORTED_BY` → `Document` traversal. The edge means a reviewed public project source mentions that project in the active portfolio commit. Graph records are a projection; PostgreSQL owns the active version. Vector distance alone cannot authorize an answer. Only allowlisted path, commit, line URL and stored content hash matches can be cited.
- The fixture is an exact-source excerpt viewer. Its short deterministic deltas exercise the transport but do not simulate model quality. No paid embedding or completion is permitted by default. A failed or incomplete upstream response keeps its reservation until usage is known; budget accounting never assumes a refund.
- Application SQL migrations are applied once in filename order with checksums and a transaction lock. Existing installs adopt the idempotent initial migration; rollback of data-bearing changes uses a verified PostgreSQL restore. Checkpointer setup runs after application migrations.
