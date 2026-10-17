# Architecture diagram conventions

The [overview SVG](assets/architecture-overview.svg) is a first-party editable vector
source, not a screenshot or generated UI. The README keeps the equivalent Mermaid
logical view in a native disclosure. Update both when a responsibility or flow changes;
this is a context/component overview, not a class diagram or deployment acceptance.
The asset contains no scripts, foreign HTML, external images/fonts or remote requests.
No diagram/runtime dependency or proprietary design tool is needed to edit it.

| Question | Suitable view | Orientation |
| --- | --- | --- |
| Who calls what, across which boundary? | System context / components | Left-to-right for a short request pipeline |
| What happens in time? | UML sequence | Actors across; time down |
| Which decision or release gate follows? | Activity / flow | Top-to-bottom for long phases and gates |
| Which legal transition or relationship matters? | State / class UML | Match the actual model; avoid decorative taxonomy |

Cards identify components; dashed frames identify trust boundaries. Solid arrows are
requests/synchronization; dashed arrows return data. A two-ended arrow identifies a
read/lookup exchange. Labels carry meaning independently of color. Ownership, access
and missing observations remain explicit; no arrows imply automatic training, public
service-token access or production activation.

The overview uses a small neutral/cyan palette aligned with the portfolio. CSS variables
centralize canvas, surfaces, text, borders and connectors. `prefers-color-scheme`
provides light/dark variants inside the same source; system fonts avoid remote assets.
Measured minimum text contrast is5.21:1 (light) /8.87:1 (dark); meaningful connectors
and boundary strokes are at least3.53:1 /4.49:1. Values use sRGB relative luminance.
See [embedded color-scheme behavior](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/prefers-color-scheme).
It is a static document graphic: no decorative animation, tracking or JavaScript.

Review at full intrinsic size and in a390px README context, both themes. Check text
fits its card, connectors do not cross labels, title/legend are legible, original-image
zoom works and accompanying prose/alt text explains the flow without depending on the
figure. The compact inline preview is an overview; open the original for small labels.
Mermaid remains editable and must render on GitHub, not only parse locally. A graphical
edit is documentation work, never authority to alter contracts or infrastructure.

Local visual evidence is ignored under `.artifacts/architecture-review` in the backoffice
workspace; the delivery report identifies the exact source and checks actually run.
No physical-device or screen-reader certification follows from this diagram review.
