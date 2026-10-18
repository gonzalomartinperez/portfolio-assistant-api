# Site experience interoperability · v1

This freezes a small, product-adaptable vocabulary. It is independent of operational
telemetry, assistant quality, financial accounting and advertising attribution.
It does **not** add an ingestion endpoint, change current wire events, authorize
collection, or implement Pequeverso routes, roles, catalogue or consent.

Artifacts generated offline by `python -m contracts.export`:

- [Core schema](../contracts/site-experience-v1.schema.json): bounded interoperability
  envelope, **insufficient by itself to admit a product event**.
- [Portfolio profile](../contracts/site-experience-portfolio-v1.schema.json): only the
  two existing region-aware interactions, exact routes, locales, layout and regions.
- [Contract models](../contracts/site_experience.py) and
  [behavioral tests](../tests/test_site_experience_contract.py).

Actual checks and limitations are recorded in the
[dated verification receipt](verification/site-experience-contract-2026-10-18.md).

Pequeverso owns and must publish its own stricter profile, reviewed routes/regions,
target catalogue, runtime validator and independent private aggregate API. Do not
admit an event merely because it passes the core. Profile changes require review;
do not silently reassign an existing region or layout revision to a different surface.
No shared runtime package, database, controller or cross-project token is required.

## Frozen vocabulary

| Event | Meaning | Coordinates / target |
| --- | --- | --- |
| `page_view` | A committed public document or SPA route; no prefetch, remount, theme update or bfcache recount | No coordinates or target |
| `section_view` | Approved bounded heading/paragraph or paragraph-start sentinel intersects at least 50% for 500 ms continuously while visible | No coordinates or target |
| `public_click` | Genuine primary-pointer activation in a positively reviewed public region | Both integer cells 0–7; no target |
| `product_interest` | Explicit activation to inspect a reviewed product's details | Approved product `target_id`; no coordinates |
| `affiliate_click` | Explicit activation of a reviewed outbound affiliate destination | Approved destination `target_id`; no coordinates |
| `checkout_intent` | Explicit activation requesting a reviewed checkout handoff | Approved destination `target_id`; no coordinates |

The last three are optional product capabilities, not Portfolio features. An
outbound click or handoff is not a completed navigation, purchase, payment,
attributed conversion or Hotmart transaction. No `Purchase` event, revenue,
campaign attribution, Meta/CAPI change or consent exemption is introduced.

`section_view` is geometry/dwell, not reading or attention. Hide, route departure
and unmount cancel dwell; reentry requires a new dwell. Deduplicate within the
committed route visit/region/layout/viewport; preserve this across StrictMode and
theme changes. A later route visit may count again. Exclude forms, inputs,
contenteditable, auth/admin, assistant/transcripts, canvas and dynamic graphs.
Keyboard actions must not manufacture pointer cells. Semantic actions and clicks
are different counts, never an automatically inferred conversion funnel.

## Envelope and profiles

Core fields are `schema_version: 1`, reviewed `project`, `source: site`, random
UUIDv4 `event_id`, `event_name`, `route`, `layout_revision`, `viewport_bucket`,
`section_id` and `locale: en|es`. A profile must narrow all route/region/layout and
target values to its reviewed surface/catalogue and enforce their relationships.
The core's short ASCII slug/path patterns are size/syntax limits, not allowlists.
In particular, a syntactically valid `/auth` or unknown product slug is **not** an
approved event. Portfolio's profile rejects them.

- `route`: canonical public path only, at most 128 characters; no origin, query,
  fragment, percent-encoded alternative, user-entered path or route parameters
  containing identities. Localized paths and locale must agree.
- `section_id`: reviewed region or page-level bucket defined by the product
  profile, never a DOM selector, arbitrary label, title or input.
- `layout_revision`: approved immutable layout identifier, at most 64 characters.
  Viewport buckets are `mobile`, `tablet`, `desktop`; Portfolio uses <832,
  832–1023 and >=1024 CSS pixels. Other profiles must state their own thresholds;
  never compare coordinate grids across different product/layout/viewport profiles.
- `cell_x`/`cell_y`: paired 8×8 region-relative cells for `public_click` only.
  No raw pixels, trajectories or document-wide replay. Absent for other events,
  including explicit nulls. `target_id` is likewise absent except for the three
  optional semantic commerce actions; no arbitrary URL is accepted as a target.
- No text, inputs, auth, transcripts, cookies, visitor/session IDs, country,
  client timestamps, consent declaration or fixture trust flag belongs in input.
  Fixture/source classification is controlled by the server/test environment and
  shown explicitly in private reports, not trusted from browser assertions.

## Portfolio compatibility

The existing public [v1 semantic](../contracts/product-event.schema.json) and
[v2 interaction](../contracts/product-interaction.schema.json) payloads remain
unchanged on `POST /api/v1/analytics/events`. **Do not POST the new core/profile
envelope to that endpoint.** Contract tests verify that it is rejected by the
current input models. Schema version 1 here belongs to this separate contract,
not to the existing v1 payload namespace.

| Current Portfolio field/event | Canonical interpretation |
| --- | --- |
| `section` + `locale` | Exact public `route` from the committed page allowlist |
| `region_id` | `section_id` |
| `viewport` | `viewport_bucket` |
| `section_exposure` | `section_view` with the geometry/dwell definition above |
| `public_click` + `cell_x`/`cell_y` | Same event and grid |
| `section_open` | Explicit details expansion; **never** map to `section_view` |

The Portfolio profile covers only normalized `public_click` and `section_view`
from the existing v2 examples. Its offline mapping test is not a newly deployed
normalizer. Existing v1 `page_view` facts lack region/layout/viewport metadata:
retain their original semantic aggregates; do not fabricate the missing values or
retroactively claim that they satisfy this new envelope. A future richer page-view
producer/profile requires an independently reviewed increment.

## Storage, country and admission

The implemented Portfolio [analytics contract](product-analytics.md) remains
authoritative: shared transactional 60 new events/minute and 10,000/day quotas,
1 KiB maximum body, UUID replay suppression for 24 hours, seven-day legacy view,
93 UTC days for detailed aggregates, bounded pruning and separate private reads.
New events must not receive a separate quota that bypasses existing limits.
No raw event/transcript storage, IAM joins or persistent browser identity.
Retention includes an explicit backup-expiry/recovery review; logical pruning is
not proof of physical erasure. Pequeverso must publish its own measured limits,
grants, migrations and restore evidence rather than inheriting these values.

Country is assigned only by a verified server-side network trust chain; unknown
by default. Do not use client JSON, locale, SSR geography or untrusted forwarded
headers. Portfolio's current implementation and production gates are described
in the existing contract. Small country buckets and grid cells below three are
withheld in the detailed report; this is not an anonymity guarantee.

Private aggregate endpoints stay independent of operational contract versions.
Portfolio uses `/internal/ops/v2/product-analytics`; the shared path prefix does
not turn these counts into ops telemetry. Missing, disabled or unreachable data
must render unavailable rather than zero. Received-event coverage does not prove
uptime, unique people, complete collection or a financial ledger.

All production collection remains OFF. An independently approved fixture-only
collector must be visibly labelled, omit credentials, avoid payload logging and
retries, and drop unsent events/abort pending delivery on revocation. Revocation
must not create a retry queue or claim to undo an already accepted request.
Changing Meta/CAPI or its existing consent is outside this increment. Neither
this schema freeze nor a source merge approves activation or deployment.
