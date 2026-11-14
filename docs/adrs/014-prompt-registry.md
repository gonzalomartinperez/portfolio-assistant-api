# ADR014: Prompt registry in git with a lock file

Status: accepted (2026-11-14, master plan task M2-6, decision PAA-D7).

## Context and problem

The developer prompt (about 4.5 KB) was an inline f-string in
`app/adapters/providers/answer.py` plus `voice_instructions()`. It had no version and no
hash, so a quality change could not be tied to a prompt change and nothing recorded which
prompt produced an answer or a cost line. Privacy rules forbid hosted tracing (PAA-D8, [ADR021](021-tracing-off-no-hosted-prompt-registry.md)).

## Options considered

1. Keep inline strings. Cheapest, but no identity, review surface or drift check.
2. Markdown files with front matter plus `prompts.lock` (sha256) in git. Reviewed like
   code, offline, deterministic, no new dependency.
3. Hosted registry such as LangSmith prompts. Rejected: tracing stays off (PAA-D8), it
   adds a network dependency to prompt loading and moves reviewed behaviour out of git.

## Decision

Option 2.

- Files live in `app/prompts/`: `answer.md`, `web-context.md`, `voice-recruiter.md`,
  `voice.en.md`, `voice.es.md`. Front matter holds `id`, `version`, `owner`,
  `last-reviewed`. Body lines are joined with single spaces and each piece is followed
  by one space, so the rendered developer message is byte-identical to the former
  inline text (characterization snapshots in `tests/unit/snapshots/`).
- Placeholders (`{current_date}`, `{language}`) are filled with `str.format_map`; names
  outside the allowlist, or missing values, raise `PromptError`. The date comes from an
  injectable `today` callable on `ResponsesProvider`.
- `prompts.lock` records `id`, `version` and sha256 of the file bytes per file. Loading
  fails on any mismatch, missing file or missing entry.
  `python -m scripts.update_prompts_lock --write` regenerates it deliberately;
  `--check` verifies it.
- `prompt_version` is `id@version+sha256[:12]` for every piece used, comma-separated
  (for example `answer@1+b4f38ad5eabb,voice-recruiter@1+...,voice-en@1+...`). It is on
  `Usage`, the `usage_settled` log line and the evaluation report header (all pieces).
  Prompt text is never logged.

## Placement

`PromptSpec`, front matter parsing, lock verification, rendering and `prompt_version` are
pure stdlib policy in `app/domain/prompts.py` (ADR001). Reading the files through
`importlib.resources` is I/O and lives in `app/adapters/prompts.py`; assembly of the
pieces for a locale stays in the provider adapter (`providers/voice.py`). `app/prompts/`
holds data only (no Python), so the architecture guard sees no new layer. The project is
installed editable in the image ([ADR017](017-canonical-api-image.md)) and the Dockerfile
copies `app/`, so the files ship without packaging changes.

## Consequences

- A prompt edit needs a lock update and is visible in diffs. The sha256 prefix in
  `prompt_version` changes on any edit; a `version` bump is expected for semantic changes but
  is not enforced.
- Bodies are whitespace-normalised into one line (lines joined by single spaces), so
  paragraph breaks are not expressible. Placeholders must be plain allowlisted names
  (no conversions or format specs); `{{`/`}}` escape literal braces. Startup loads the
  registry in `create_app` and fails fast on a stale lock.
- Cassette keys (assistant-quality section 12) can add the prompt id and sha256 later.
- Prompt gate by profile `assistant-quality` is a later task.

## Confirmation

- `tests/unit/test_prompt_registry.py`: committed lock matches the files (prompt change
  without lock update fails), edited copy or missing/extra entry raises, front matter
  keys, unknown placeholders, `prompt_version` format, and byte-identical developer
  messages for en/es with and without web context.
- `uv run python -m scripts.update_prompts_lock --check`.
- `tests/test_architecture.py` keeps the layering.
