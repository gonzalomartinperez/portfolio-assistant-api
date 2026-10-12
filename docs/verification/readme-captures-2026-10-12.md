# Native assistant README captures

Captured on 2026-10-12 from a tracked archive of portfolio revision
`bcae79e704daca02cfe0ef488377de60b85dfff8`, without modifying its working tree or rollout.
The isolated local build enables the assistant only in that test archive. The public
portfolio remains disabled.

The capture uses the available local Node 24.21.0, Next.js 16.3.8 and Playwright 1.63.0
Chromium toolchain. The referenced portfolio manifest has since moved to Next.js 16.4.0;
this is visual evidence using the stated toolchain, not a clean-install compatibility
claim for that newer framework. The optimized build and its TypeScript check passed.

Two public questions and their exact answers/citations are replayed from the authorized
GPT-6 Luna/medium evaluation: `intro-en` and `metrics-en` in the ignored
`artifacts/voice-20261012/answers.json`. See [voice evaluation](../assistant-voice.md)
for the original provider verification. No new paid calls occurred. Only the resulting
images are published, never full evaluation logs, sessions or credentials.

The fixture exercises the existing HTTP/SSE adapter and real conversation components.
History is returned newest-first, as required by the API. The capture checks the
submitted question, completed answer, source disclosure and composer, then expands the
same panel for the recruiter introduction. A follow-up remains an unsent draft.

Desktop viewport: 1440 × 1200 CSS pixels, device scale 2, dark/English, reduced motion.
Panel-element PNGs preserve intrinsic geometry and exclude unrelated page content.
No image compositing, invented metrics, text overlays or model-answer rewriting is used.
Both images were visually inspected for question/answer order, legible sources,
composer visibility, clipping and absence of development indicators.

Initial development captures were rejected because they showed incidental development
indicators and the fixture's incomplete history. The first production build failed on
untyped temporary capture callbacks; those callbacks were fixed and the build rerun
without disabling type checks. These captures do not prove production routing, live
availability, mobile-device behavior or complete portfolio regression acceptance.
