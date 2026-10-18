# Product analytics v1 — local, disabled by default

This is a separate contract from best-effort operations v1. It counts accepted
interactions, never unique visitors, completed downloads, sent contacts or revenue.
No production collection or legal exemption is approved by this implementation.
Public portfolio code remains owned by its repository; no hooks are installed here.

## Public contract

`POST /api/v1/analytics/events` returns 204 for accepted events and duplicate IDs.
`PRODUCT_ANALYTICS_ENABLED=false` is the runtime default; disabled ingestion and
private reads return 404. Enabling is independent of enabling the assistant.
No browser secret, session bootstrap or CSRF token is used: this endpoint does not
mutate an authenticated resource. Cookie/Authorization-bearing requests are rejected.
The existing exact `ALLOWED_ORIGINS` list and mutation Origin guard apply; requests
without Origin or from an unapproved origin fail closed. CORS is not bot authentication.
Existing credentialed assistant CORS is unchanged; analytics clients MUST use fetch
`credentials: 'omit'`, `referrerPolicy: 'no-referrer'`, `cache: 'no-store'` and JSON.
Never use the session transport or persist a retry queue. Failure must not block links.

```json
{
  "schema_version": 1,
  "project": "portfolio",
  "source": "site",
  "event_id": "12345678-1234-4234-8234-123456789abc",
  "event_name": "cv_link_open",
  "section": "cv",
  "locale": "es",
  "target": "es"
}
```

The ID is random UUIDv4 per event, used only for duplicate delivery detection.
Unknown fields, arbitrary properties, URLs, text, timestamps, country, identifiers
and unsupported dimensions fail validation. Maximum actual body size is 1,024 bytes,
including chunked input; global request timeout is 10 seconds. No payload logging.
Schemas: `contracts/product-event.schema.json`, `product-analytics.schema.json`;
public OpenAPI includes only ingestion, never private aggregate routes.

| Event | Section | Target |
| --- | --- | --- |
| page_view | home/about/work/filomena/stack/education/cv/contact | absent |
| navigation_click | destination section from the same list | absent |
| section_open | work | rampy/teamcubation/cooperativa-obrera/independent |
| cv_link_open | cv | en/es |
| contact_link_open | reviewed section from the list | email/linkedin/github |
| company_link_open | work | rampy/teamcubation/cooperativa-obrera |

A page view means a committed document/SPA route, excluding prefetch, theme changes,
component remounts and bfcache restoration. Section expansion means explicit details
activation. The host implements those semantics and transient deduplication; server
validation cannot prove a human actually clicked. No assistant browser events yet.

## Storage, bounds and privacy

Migration 007 adds two tables to existing PostgreSQL, no service or collector.
An isolated global transaction lock enforces at most 60 new IDs/minute and 10,000
accepted events/UTC day across all clients. Returns 429 at the limit. This is an
abuse/storage bound, not fair per-person allocation; an attacker can exhaust it.
Statement/lock timeouts are 2 seconds/500 ms. No IP is used by this feature.

Only event ID + server receipt time are retained for dedupe. Counts are grouped by
server UTC day and allowlisted dimensions. No raw payloads, IP/UA/referrer, visitor,
session/conversation/run IDs, questions or answers are stored or exported. Country
is always `unknown`; no unverified proxy header is used. Do not join with IAM.
The API/proxy necessarily process network addresses; their logs remain a separate
ops-owned retention/privacy review, not evidence the whole system is anonymous.

**Local test limits:** dedupe 24 hours; aggregates current UTC day + six previous
UTC days. Ingestion opportunistically deletes up to 1,000 expired IDs and old daily
cells inside its transaction. `python -m app.retention` also prunes expired rows,
including when ingestion is off. Logical expiry is not physical deletion or backup
erasure; schedule maintenance and define encrypted backup expiry before production.
Replays after ID expiry may count again. No unique-visitor or exact-ledger claim.
These conservative local defaults do not approve production retention, geography,
small-cell disclosure or consent applicability. Private owner/invited-viewer reads
only; there is no public aggregate API. Optional consent-dependent metrics stay off.

## Private backoffice read

`GET /internal/ops/v1/product-analytics` uses existing server-only `OPS_READ_TOKEN`;
no-store and private proxy exclusion apply as with operations v1. The response has
schema_version 1, project portfolio, window_days 7, country unknown and bounded daily
counts. Empty array means no accepted events in the window; disabled/unavailable
must not render as zero. No source token reaches browser props or JSON.

Operational execution counts remain explicitly best effort and separate. Reliable
historical generation totals are not implemented by this slice; do not count SSE
fragments, replay generation or relabel existing observations as a financial ledger.
No paid model request is needed to collect or test website events.

## Upgrade, rollback and activation gates

Apply 007 once through the existing checksum-verified migration runner and reapply
`deploy/runtime-grants.sql`. Existing API/session/SSE paths are unchanged. The schema checker rejects applied
migrations missing from a checkout: pre-007 images become unready after 007, even
though its tables are additive. Rollback must use a reviewed forward-fix image that
retains migration 007 and its checksum, disables analytics and reverts the affected
behavior. Do not delete 007, weaken schema validation or restore over new writes.
Rolling back source does not undo DDL or erase data. Existing backups include these tables;
restore to an isolated database and verify duplicate/quota behavior before admission.

Before enabling real collection: portfolio hook/network tests and truthful bilingual
notice; owner approval of retention/rights/contact and applicable privacy basis;
ops effective Origin/proxy/no payload logging/private route checks; storage/restore
measurements and quota monitoring. No consent exemption inferred from cookieless or
personal-site status. No acceptance banner is introduced; omit any measure requiring
consent instead. App/ops image publication or main merge is not activation approval.

Primary references reviewed 2026-10-17:
[CNIL analytics guidance](https://www.cnil.fr/fr/node/677) explains conditional
exemptions, not a certification for this system;
[W3C table guidance](https://www.w3.org/WAI/tutorials/tables/caption-summary/)
informs dashboard captions and semantic alternatives. Actual jurisdictions and
operator rights-handling details require owner confirmation, not invented boilerplate.

## Version 2 interaction and calendar extension

The additive public input is defined by
[`product-interaction.schema.json`](../contracts/product-interaction.schema.json)
and [synthetic examples](../contracts/product-interaction.examples.json).
`POST /api/v1/analytics/events` keeps the six original `schema_version: 1` semantic
events unchanged. New `schema_version: 2` accepts **only** `public_click` and
`section_exposure`; it does not change chat/session/SSE contracts or authorize
collection on the public website. The website owner imports a committed snapshot.

Each new event supplies the reviewed page section, EN/ES locale, closed `region_id`,
`layout_revision: portfolio-v1` and coarse viewport `mobile` (<832 CSS px), `tablet`
(832–1023) or `desktop` (>=1024). Public clicks additionally require paired integer
`cell_x`/`cell_y` in 0–7, relative to the reviewed region. Exposure prohibits cells.
Page-bound region validation permits only the 30 reviewed IDs (header/footer are
shared); it rejects arbitrary URLs, selectors, pixels, text, country, visitor/session
IDs and assistant/auth/form content. No replay, input capture or persistent browser
identity is introduced. Keyboard actions retain appropriate semantic v1 events,
without fabricated pointer coordinates.

The host client must positively allowlist public regions, exclude sensitive ancestors
and dynamic canvas/graph content, accept genuine primary-pointer clicks and preserve
natural scrolling. Exposure means an approved bounded heading/paragraph target or approved paragraph-start sentinel is at
least 50% geometrically intersecting for 500 ms continuously while the document is
visible. Hidden state, route departure and unmount cancel pending dwell; reentry
requires a new dwell. Deduplicate within the committed route visit/region/layout/
viewport, surviving React StrictMode and theme changes. A later route visit can count
again. This is not proof of reading, occlusion, attention or a unique person.

Both versions share the original UUID replay window (24 hours), atomic global
**60 events/minute and 10,000/day** ceilings, 1 KiB request maximum and no-credentials
policy. There is no automatic retry, sampling extrapolation or quota increase.
The client's new-interaction lane must not displace semantic page views. Counts are
best-effort received events, not a census; blockers, opt-out, navigation, quotas and
network failure can reduce them. Do not claim every click or unique visits.

### Storage, read compatibility and retention

Migration 009 adds aggregate daily semantic/country counts, region/grid counts and
two collection timestamps, without changing prior migration files. Existing seven-day
semantic facts backfill as country unknown. The original private v1 snapshot remains
unchanged. The new authenticated `GET /internal/ops/v2/product-analytics` has a
[separate bounded schema](../contracts/product-analytics-v2.schema.json).

Parameters are `period=day|week|month`, `offset=0|1|2`, reviewed `section` and
`region_id`, `viewport=mobile|tablet|desktop`, `locale=all|en|es`. Defaults are current
month/home/home-featured/desktop/all. Reject unknown/duplicate parameters and a region
from the wrong page. The selection separates responsive layouts; never merge raw
coordinates across different layouts or viewports. A consistent read-only transaction
uses parameterized queries, bounded result dimensions and existing SQL timeouts.

Periods are **UTC calendar** `[start,end)` intervals: ISO Monday-start week and actual
calendar month, including leap years and year transitions. The current interval is
partial. First/last observed timestamps describe received data, not continuous client
coverage or uptime. The snapshot explicitly says `received_events_only`. No unique
visitor count is inferred or summed from daily values. Aggregates retain **93 UTC
days** so current/previous/two-months-previous calendar selections fit; dedupe remains
24 hours and the compatibility v1 view retains seven days. New retention pruning is
bounded to 1,000 expired rows per aggregate table per operation. Review backlog and
backup retention operationally; application deletion does not erase existing backups.

Country buckets with fewer than three observations become `withheld`, distinct from
unknown. Grid cells below three clicks are withheld; the response reports the number
of suppressed clicks and offers no exact pointer path. This limits detail; it is not
an anonymity or differential-privacy guarantee. The dashboard must label these states
and provide a text/table alternative to the grid. Semantic totals, country totals
and cells refer to different selections; do not invent a conversion/attention rate.

### Optional Cloudflare country boundary

Default `PRODUCT_ANALYTICS_COUNTRY_ENABLED=false` yields unknown. When separately
approved, set `PRODUCT_ANALYTICS_COUNTRY_PROXY_IPS` to exact socket-peer addresses
(up to 16, no DNS names, CIDR or wildcard). Attribution requires that enabled flag,
a matching actual socket peer and one valid `CF-IPCountry` header. Forwarded-client
headers, locale, SSR/Hostinger geography and client JSON cannot supply the country.
Missing, duplicated, malformed, `XX`, `T1` or unrecognized labels remain unknown.
The country is an estimate of the request origin, not nationality or exact location.

[Cloudflare's official country feature](https://developers.cloudflare.com/network/ip-geolocation/)
is available on Free; country-only configuration avoids city/coordinate transforms.
Its [header documentation](https://developers.cloudflare.com/fundamentals/reference/http-headers/#cf-ipcountry)
describes the special unknown/Tor values. No GeoIP service, local geolocation database,
account credentials or external lookup is used by this application.

**vps-ops must verify** browser → Cloudflare → trusted proxy → API, overwrite/reject
spoofed input headers, restrict origin bypass and ensure Uvicorn preserves the actual
proxy socket peer. DNS ownership alone proves none of those conditions. A request
forwarded from a website server would identify that server, not the page visitor;
the approved browser collector sends directly to ingestion with credentials omitted.
The application cannot validate the entire network chain. Keep attribution off until
its effective configuration/negative tests are accepted. No production setup changed.

### Migration, grants and rollback

Run the real migrator, then reapply exact runtime grants for the three new tables.
Runtime credentials must never migrate. Migration 009 backfills only already retained
aggregate facts and updates no conversation, corpus, checkpoint or IAM rows. The
migration runner remains transactional/checksummed. As before, an older image that
lacks an installed migration refuses strict readiness; rolling back an image does
not reverse the schema. Preserve dumps/roles and a tested compatible source revision;
review a forward recovery or separately rehearsed database recovery with vps-ops.

The v2 `country_collection` field describes the **current configuration**, not
proof of a verified Cloudflare account or the provenance of every historical row.
Turning collection off leaves retained historical aggregates available; unknown
and withheld country buckets remain explicitly distinct.
