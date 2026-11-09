# Codex harness reference (2026-11-09)

Source: official docs (developers.openai.com/codex now redirects to learn.chatgpt.com/docs). Verify keys against the installed `codex --version` before committing config.

- AGENTS.md: global $CODEX_HOME then git root → cwd; per directory AGENTS.override.md > AGENTS.md > fallback names; concatenated root to leaf, closer wins; 32 KiB default cap (project_doc_max_bytes). https://learn.chatgpt.com/docs/agent-configuration/agents-md
- Config: `.codex/config.toml` in repo loads only for trusted projects; cannot set notify/profiles/providers/otel. approval_policy on-request|never|granular; sandbox_mode read-only|workspace-write|danger-full-access; network off by default. https://learn.chatgpt.com/docs/config-file/config-reference · https://learn.chatgpt.com/docs/agent-approvals-security
- Skills: discovered in `.agents/skills` (cwd up to repo root), $HOME/.agents/skills; SKILL.md needs name + description; optional agents/openai.yaml; symlinks followed. https://learn.chatgpt.com/docs/build-skills
- MCP: [mcp_servers.<name>] stdio or HTTP; enabled_tools/disabled_tools; never commit OAuth secrets. https://learn.chatgpt.com/docs/extend/mcp
- CI: `codex exec` (--sandbox, --json, --output-schema, --ephemeral, --ignore-user-config); openai/codex-action@v1 (safety-strategy drop-sudo, allow-users); GitHub code review GA via connector, instructions set in Codex UI. https://learn.chatgpt.com/docs/non-interactive-mode · https://learn.chatgpt.com/docs/github-action · https://learn.chatgpt.com/docs/code-review
- Hooks: SessionStart, PreToolUse, PostToolUse, PermissionRequest, UserPromptSubmit, Stop; `[features] hooks = true`; hooks.json or [hooks] in repo .codex/; each hook trusted by hash. https://learn.chatgpt.com/docs/hooks
- Worktrees: managed under $CODEX_HOME/worktrees; `.worktreeinclude` copies ignored files (desktop only). Cloud environments configured in UI (install script, network allowlist). https://learn.chatgpt.com/docs/environments/git-worktrees · https://learn.chatgpt.com/docs/environments/cloud-environments

Recommended committed set per repo: AGENTS.md, .codex/config.toml (on-request + workspace-write, no network, hooks on, MCP without secrets), .agents/skills/*, optional .github/workflows/codex-review.yml, .worktreeinclude without secrets (do not list .env). Unverified: profile table syntax, execpolicy .rules, environment files in repo.
