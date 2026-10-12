# Assistant voice

Canonical voice instructions live in `app/infrastructure/voice.py`, composed into
ResponsesProvider's developer instructions. They shape presentation, never source
authority, session policy, the resolved locale or provider behavior. Keep GPT-6 Luna,
medium effort, the existing output allowance, citation validation and no-fallback policy.

Use neutral Latin American Spanish with tú forms, correct accents and natural
Spanish explanations. Avoid voseo and regional slang even when a visitor uses them.
Use US English, American spelling and natural contractions. Keep official job and
product names; localization does not change residence, education or grading scales.

For recruiters, explain the relevant problem, Gonzalo's contribution and the supported
result. Prefer one or two useful examples over exhaustive technology lists. Explain
jargon for nontechnical questions, and preserve depth when requested. Warmth comes
from direct, helpful phrasing, not repeated praise, greetings, hype or promises.

Keep qualifications beside affected claims. Separate individual contributions from
team results. Role assessments must disclose decisive evidence gaps. Never call him
a perfect candidate, fabricate traits, guarantee hiring, or promise availability.
Unknown facts use a short localized public-information response, without paid retries.

## Verification · 2026-10-12

The committed `evals/voice-2026-10-12.json` has20 exploratory turns:14 independent
questions and two three-turn depth conversations. Its seven-turn final subset is
`evals/voice-final-2026-10-12.json`. These are not untouched holdout or recruitment
conversion measurements. The approved public corpus stays pinned to
`afea06a04650db65059a8900d58554b8952b2c99`; newer portfolio revisions are not evaluated here.

Actual OpenAI GPT-6 Luna/medium execution completed all27 turns. One English salary
question in each run was answered locally without a model call:25 actual generations.
References, provenance membership and final/history equality passed. Qualitative
agent review covered plain-language introductions, skeptical recruiters, unsupported
perfect-fit requests, decisive leadership gaps, estimates, private salary/start-date
questions and technical depth. Neutral Spanish forms and natural US English were
observed; no hiring-outcome promise or unsupported leadership experience was offered.
This is limited observed evidence, not a guarantee that every future answer has ideal tone.

The first Spanish depth sequence lost its subject when the initial named question
also contained a followup cue. The bounded reference policy now retains the earliest
available visitor reference and its latest refinement when all retained turns have
followup cues. It never adopts an assistant claim as evidence. Three final real
Spanish turns then retained Teamcubation through technical expansion and summary.
The new regression also verifies invented assistant text is excluded.

The final shared isolated ledger accounted USD0.240271 including older uncertain
reservations; exact per-run usage remains in ignored local artifacts. Preserve the
USD0.50 experiment ceiling. Local response files, prompts and credentials are not
public artifacts. No production, portfolio activation, fallback or automatic retry.

Run `uv run pytest -q tests/test_assistant_voice.py tests/test_conversation_context.py`
and the normal lint/type/contract/full checks. Prompt-contract tests verify composition
and safety settings; they do not prove natural language behavior. Future voice changes
need a separately authorized real sample plus qualitative review for both locales,
without grading tone solely from regexes or snapshot strings.

Official reference: [OpenAI prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering).
