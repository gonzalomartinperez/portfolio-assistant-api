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
