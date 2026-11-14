# Judge calibration

Scaffolding for PAA-D5 (see `docs/master-plan/assistant-quality.md` section 8.2). This directory holds
the label schema, the review interface and, later, the labels. Bootstrapping and validating labels is
deferred to M6-3. Nothing here enters a gate: labels are calibration data only, and no CI workflow
references a judge until it is validated.

## Protocol

1. Two independent agents bootstrap 160 labels: 40 pass and 40 fail for each of the two criteria
   (`helpful_complete`, `tone_fit`). They do not see each other's labels.
2. Disagreements go to a third agent.
3. The owner spot-checks a 20% sample once (DR-05) and records `spot_check_label`.
4. Split: 10-20 train, 40-45 dev, 40-45 test (per criterion).
5. Acceptance on the test split: TPR >= 0.90, TNR >= 0.85, lower confidence bound of Cohen's kappa >= 0.6.
   Re-validate on any judge model, prompt or domain change.
6. Until validated, judged quality is reported as "not validated".

## Files

- `label.schema.json`: JSON Schema 2020-12 for one label (one JSON object per JSONL line).
- `labels/`: will hold the JSONL label files (currently only `.gitkeep`).
- `review.html`: self-contained review interface (no network, no build step). Open it in a browser.

## Privacy

Labels carry `answer_ref` (for example `private://run-2026-11/abc123`), never answer text. The schema
rejects any other field, so a raw `answer` cannot be committed. Answer text is supplied only to the
review interface through a local, untracked items file.

## Review interface

Open `review.html` and pick a local JSONL of items. Each line:
`{"id", "criterion", "item_id", "locale", "question", "answer_ref", "answer", "split"?, "label"?, "labeller"?}`.
`answer` is displayed only and is never exported. Keys: `1` pass, `2` fail, `D` skip, arrows navigate,
`U` clear the current label, `Ctrl/Cmd+Enter` saves and advances, `Ctrl/Cmd+S` exports. In spot-check mode
(items that carry an agent `label`) the agent label is shown and your choice is stored as
`spot_check_label`. Export downloads JSONL that validates against the schema. Data stays in the
browser; nothing is sent anywhere.
