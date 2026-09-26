# Implementation status

2026-09-26: Bootstrap in progress. Docker is unavailable in this WSL distro; real database and container gates are BLOCKED until Docker integration is enabled. OpenAI real calls are NOT RUN by design.

## Sequence

1. Export the offline HTTP/SSE contract; test schema drift.
2. Implement sessions, migrations, fixture graph, and one browser-to-API flow.
3. Add reviewed public corpus, vector and graph retrieval, and bounded sync.
4. Integrate standalone and native portfolio clients.
5. Verify security, builds, databases, browser behavior and local production artifacts; merge PRs into develop.
