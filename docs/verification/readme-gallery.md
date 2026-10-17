# README gallery provenance

Captured on 2026-10-12 from the native portfolio source and production-build fixture
workspace described in [the original capture record](readme-captures-2026-10-12.md).
Portfolio source: `bcae79e704daca02cfe0ef488377de60b85dfff8`. Runtime: Node 24.21.0,
Next.js 16.3.8, Chromium/Playwright 1.63.0, WSL Linux. The manifest/toolchain limitation
in the original record still applies; this is visual evidence, not a new clean-install
verification of the independently owned portfolio.

| Frame | Scene and evidence |
| --- | --- |
| [Welcome](../assets/gallery/01-welcome.png) | Real native empty state and starter prompt. HTTP session/catalog use deterministic fixtures. |
| [Expanded conversation](../assets/gallery/02-expanded-conversation.png) | Exact public `intro-en` answer and citations recorded during authorized GPT-6 Luna/medium evaluation. |
| [Compact sources](../assets/gallery/03-compact-sources.png) | Exact public `metrics-en` recorded answer, preserving the distinction between estimates and audited measurements. |
| [History](../assets/gallery/04-history.png) | Real conversation drawer after fixture completion, with shared conversation controls. |
| [Interrupted](../assets/gallery/05-interrupted.png) | Fixture intentionally ends SSE without a terminal event; UI preserves partial output and labels interruption. |
| [Unavailable](../assets/gallery/06-unavailable.png) | Session fixture returns 503; capture waits for the actual unavailable state, not a loading placeholder. |
| [Mobile Spanish](../assets/gallery/07-mobile-es.png) | Recorded `metrics-es` answer in the actual Spanish/light mobile presentation. |

Desktop uses 1440 × 1000 CSS pixels; the expanded frame uses 1440 × 1200. Mobile is
390 × 844. Device scale is 2, with reduced motion. Frames capture the actual panel
at intrinsic proportions; long compact/mobile conversations remain naturally scrollable.
Only width is constrained in README, never image height. Original PNGs are linked.

The harness drives the actual presentation, controller and HTTP/SSE adapter. History is
newest-first, matching the API. The helper’s unavailable-mode readiness assertion was
replaced only in the isolated capture script with a wait for the real terminal failure;
product code/tests were not weakened. The initial welcome selector found both sidebar
and main avatars; it was narrowed to the transcript’s visible avatar before recapture.

Images are inspected for legibility, focus/encuadre, source association, safe errors and
absence of development indicators. No model output is rewritten, no UI is composited and
no visitor credentials, private prompts or real personal conversation logs are published.
No new paid calls or portfolio deployment/enablement occurred.

Reproduction uses the portfolio’s pinned browser fixture and actual native controls,
not a parallel demonstration UI. Its maintained verification entry point is
`npx playwright test tests/browser/assistant.spec.ts`; run that only in an owned isolated
checkout with the documented production-build and TLS fixture prerequisites. This API
repository does not modify or start the owner’s portfolio environment. Capture-only
workspace/scripts remain ignored local artifacts. Physical phones, live availability
and production routing are outside this gallery’s evidence.

## README presentation validation

GitHub’s Markdown API produced sanitized GFM with all eight images, nonempty alt text
and the expandable mobile/failure section. Every image loaded in a local reader preview
at 1280px and 390px widths. Gallery captures were inspected; preview CSS is a review aid,
not pixel parity with GitHub’s current theme. Local Markdown and HTML references all
resolve and no image forces height or distorts aspect ratio. Structural skill validation
and the redacted tracked-content/history secret scan passed. Full application CI remains
the authority for merging these documentation changes.

## Actual GitHub diagram verification — 2026-10-17

A fresh read-only Chromium156.0.8078.4 context opened the public GitHub README
at API `fa3acf079077633a12eb8afb4aae2af52aa76d03`. GitHub's own
`viewscreen.githubusercontent.com/markdown/mermaid` rendered all three diagrams
without syntax/parse errors. The check inspected actual SVG labels for the knowledge
flow, Bootstrap/layer dependencies and OAuth-protected operations, not renderer icons.
GitHub did not expose a semantic Mermaid version; none is claimed. The companion
backoffice's two diagrams also rendered. No private ops document, credential or
conversation was uploaded, and no Mermaid dependency or browser install was added.
Source diagram bodies remain unchanged in this increment; this is dated rendering
evidence, not a guarantee about every future GitHub renderer release.
