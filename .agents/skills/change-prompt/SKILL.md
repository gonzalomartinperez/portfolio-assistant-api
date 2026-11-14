---
name: change-prompt
description: "Edits an assistant prompt file under app/prompts, regenerates prompts.lock and runs the offline checks the change needs. Use when asked to change, tune or shorten the answer, voice or web-context prompt, to update prompts.lock, or to list what a prompt change invalidates. Not for running evaluations (use evaluate-assistant), retrieval rules (use api-maintain-knowledge) or API contract edits (use refresh-contract); re-recording and any spend are owner-only."
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# change-prompt

Tools: Read, Grep, Glob, Bash, Edit, Write. This skill does not authorize commits, pushes, merges, paid calls
or deployment (AGENTS.md). No live or paid call and no real API key; re-recording cassettes and any spend are
owner-only. Never tune a prompt against held-out answers; never open `evals/full/holdout.sealed.jsonl`.

## Checklist

- [ ] [ADR014](../../../docs/adrs/014-prompt-registry.md) and the Prompts section of CONTRIBUTING.md read
- [ ] Only the intended file under `app/prompts/` edited; placeholders unchanged unless the allowlist changed
- [ ] `version` bumped for a semantic change, lock regenerated deliberately, lock diff reviewed
- [ ] Offline prompt tests green; characterization snapshots updated only when the rendered text change is intended
- [ ] Needed re-records listed, not executed

## Procedure

1. Identify the piece: `answer.md`, `web-context.md`, `voice-recruiter.md`, `voice.en.md` or `voice.es.md`.
   Voice pieces are assembled per locale in `app/adapters/providers/voice.py`; tone rules are in
   [assistant voice](../../../docs/assistant-voice.md).
2. Edit the file. Keep the front matter (`id`, `version`, `owner`, `last-reviewed`), keep `{current_date}` and
   `{language}` as the only placeholders, and keep Spanish natural neutral Latin American Spanish.
3. Bump `version` for a semantic change, then regenerate and review the lock:
   `uv run python -m scripts.update_prompts_lock --write` and `git diff app/prompts/prompts.lock`.
   Confirm with `uv run python -m scripts.update_prompts_lock --check`. Never hand-edit a sha256.
4. Run `uv run pytest -q tests/unit/test_prompt_registry.py tests/unit/test_assistant_voice.py -p no:cacheprovider`.
   If a rendered-prompt snapshot in `tests/unit/snapshots/` fails and the change is intended, update that snapshot
   in the same change and say so; an unintended diff means the edit is wrong.
5. Run `just check` and `just test` through the test-runner agent. `prompt_version` has the form
   `id@version+sha256[:12]` and appears in usage logs and reports, so quote it in the evidence.
6. List what the change invalidates. Cassette keys include `prompt_version`, so every golden cassette recorded with
   the old prompt becomes a miss: `just eval-golden` exits 3 ("re-record required") once cassettes exist (none are
   committed yet). Also list golden items whose `required_facts` or `forbidden_claims` depend on the wording and the
   retrieval and budget baselines. Re-recording is `uv run python -m evals.harness.golden --record`, which needs
   `EVAL_RECORDING=1`, `EVAL_ENVIRONMENT=eval-live`, `ALLOW_PAID_AI=true` and a USD 2 campaign cap; it is paid and
   owner-only, so never run it. The `eval-record.yml` workflow is not available yet. Offline quality evidence comes
   from evaluate-assistant, not from this skill.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

Files changed, old and new `prompt_version`, lock diff summary, commands run with their final line, snapshot
changes (intended or not), re-records needed (owner-only), fixture versus live evidence stated separately.
