# Claude Code harness reference (2026-11-09, Claude Code 2.1.316)

Sources: code.claude.com/docs (memory, settings, permissions, hooks, sub-agents, skills, plugins marketplace, mcp, github-actions, headless, worktrees, workflows).

- CLAUDE.md loads root→cwd; if a CLAUDE.md exists, AGENTS.md is not read by default → portable pattern: AGENTS.md holds shared rules, CLAUDE.md = `@AGENTS.md` + Claude-only lines. < 200 lines; path-scoped rules in `.claude/rules/*.md`.
- `.claude/settings.json` committed; deny > ask > allow; Bash rules are not a security boundary → hard guards via PreToolUse hooks; `Read(**/.env*)` deny; defaultMode auto/bypass only in user settings.
- Hooks: PreToolUse/PostToolUse/Stop/SubagentStop/SessionStart/WorktreeCreate…; exit 2 blocks; PostToolUse Edit|Write → format; PreToolUse Edit|Write → block lockfiles/.env/secrets; PreToolUse Bash → block destructive commands; Stop → fast tests with loop guard (verify).
- Project subagents `.claude/agents/*.md` (name, description, tools, disallowedTools, model, effort, maxTurns, isolation: worktree). Nesting allowed up to 3 levels by default (CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH).
- Skills `.claude/skills/<name>/SKILL.md`; Claude Code does NOT read `.agents/skills` → keep canonical `.agents/skills` (Codex reads it) with per-skill symlinks in `.claude/skills`. Description+when_to_use ≤ 1,536 chars; body < 500 lines.
- Cross-repo sharing: plugin marketplace in a central repo (`.claude-plugin/marketplace.json`), declared per repo via `extraKnownMarketplaces` + `enabledPlugins`; plugin subagents ignore hooks/permissionMode → safety hooks stay in each repo.
- `.mcp.json` committed without secrets (playwright for web repos).
- CI: anthropics/claude-code-action@v1 (minimal permissions, --max-turns, allowed_bots); headless `claude -p` with --max-budget-usd, --output-format json.
- Parallel: worktrees (`claude -w`, `.claude/worktrees/` gitignored, `.worktreeinclude`), Workflow tool (up to 16 concurrent agents, scripts in `.claude/workflows/*.js`), `/batch`.
