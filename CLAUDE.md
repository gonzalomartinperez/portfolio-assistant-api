# Claude Code entry point

Read and follow the canonical repository operating contract:

@AGENTS.md

Skills are task guidance, not additional authority. Canonical skills live in
`.agents/skills/` and are linked from `.claude/skills/`; discovery and verification are documented in `docs/agent-skills.md`.

Subagents to use: test-runner for checks, reviewer before commits, architecture-reviewer for structural changes, eval-runner for offline evaluation numbers.
