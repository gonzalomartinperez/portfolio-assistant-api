# Analytics direct-edge contract · v1

Freeze identifier: `analytics-direct-edge-v1`, agreed 2026-10-19. This records the
existing direct ingestion design and the verification needed to enable it. It is
not a new event schema, production activation or a shared runtime package.

## One collection path

```text
Website-owned browser collector
  → project's HTTPS API ingestion hostname through Cloudflare
  → the single Coolify/Traefik reverse proxy
  → API validation and transactional PostgreSQL aggregates
  → authenticated project backoffice
```

The website owns event selection and browser delivery. The API owns validation,
quotas, deduplication, retention and report semantics. The backoffice owns validated
private rendering. vps-ops owns effective Cloudflare/CDN routing, origin isolation,
proxy configuration and production activation verification. Each product retains its
own reviewed event vocabulary, configuration, database and access controls.

There is no Business-hosted BFF, PHP endpoint, Worker, authenticated relay or new
shared token for this flow. A first-party collector means website-owned code; the
existing analytics request is cross-origin. Chat transport is a separate concern.
Do not route events through the website server and then attribute that server's
country to the visitor. Do not add an intermediate solely to forward country.

The owner reports Cloudflare and Hostinger CDN enabled for the domains. This is
**owner-reported configuration, not independently verified traffic order**. It does
not prove that the API ingestion hostname is proxied, geolocation is enabled or
that an additional CDN preserves visitor provenance. vps-ops must establish the
actual ingestion chain; the website HTML/CDN path can be different.

## Existing Portfolio contract and settings

Reference implementation: API
[`9e0be556d56d83510412cb0e4038a4f11824a788`](https://github.com/gonzalomartinperez/portfolio-assistant-api/commit/9e0be556d56d83510412cb0e4038a4f11824a788),
public collector
[`954b78dfd53ff202a98f8b598c6d93c5dfd338d4`](https://github.com/gonzalomartinperez/portfolio/commit/954b78dfd53ff202a98f8b598c6d93c5dfd338d4)
and backoffice
[`eccdfe3980e6db12b486eb3e88df923f6c5a509a`](https://github.com/gonzalomartinperez/portfolio-backoffice/commit/eccdfe3980e6db12b486eb3e88df923f6c5a509a).
These references identify implemented behavior, not an executed production chain.
Pequeverso must publish its own compatible profile and acceptance evidence; this
reference does not certify that product's implementation or consent behavior.

| Setting / boundary | Portfolio behavior |
| --- | --- |
| Public collector destination | HTTPS `ANALYTICS_INGEST_URL`, exact `/api/v1/analytics/events`; no URL credentials, query or fragment |
| `PRODUCT_ANALYTICS_ENABLED` | Defaults `false`; disabled ingestion returns 404 |
| `PRODUCT_ANALYTICS_COUNTRY_ENABLED` | Defaults `false`; disabled attribution remains `unknown` even if a country header arrives |
| `PRODUCT_ANALYTICS_COUNTRY_PROXY_IPS` | Exact actual proxy socket addresses, up to 16; no hostname, CIDR, unspecified address or wildcard; required when country attribution is enabled |
| `ALLOWED_ORIGINS` | Explicit website origins; mutation origin checks remain mandatory; never widen to wildcard credentialed CORS |
| Runtime command | Preserve `--no-proxy-headers`; application trust checks use the actual socket peer |

Existing wire artifacts remain [event v1](../../contracts/product-event.schema.json)
and [interaction v2](../../contracts/product-interaction.schema.json), admitted by
one route. Schema numbers do not rename the independent shared experience core or
[private calendar report](../../contracts/product-analytics-v2.schema.json).
Browser delivery omits credentials, disables redirects and retries, has a five-second
abort deadline and bounds in-flight requests. The API enforces the actual 1024-byte
body limit, including chunked bodies, strict JSON and product-owned dimensions.
Cookies and Authorization are forbidden on this public ingestion route. Country,
raw IPs, input text, query strings and arbitrary properties are not browser fields.

See the public collector's committed `src/features/analytics/adapters/http.ts`,
API [HTTP models](../../app/presentation/analytics.py),
[interaction models](../../app/presentation/interaction_models.py) and
[body/origin guards](../../app/presentation/middleware.py). No provider credential,
model call, extra database or new service is needed for product measurements.

## Country provenance boundary

[The API adapter](../../app/presentation/analytics_country.py) requires all of:
country enabled, an actual socket peer matching the configured exact addresses,
and exactly one `CF-IPCountry` value in the [249-code ISO allowlist](../../app/domain/analytics_country.py).
IPv4-mapped IPv6 peers normalize before comparison. Missing/untrusted peers,
malformed/duplicate headers, `XX`, `T1`, lowercase or unknown codes yield `unknown`.
Locale, client JSON and forwarded-IP headers never establish country.

**A trusted proxy address alone cannot authenticate a header's upstream origin.**
If that proxy forwards a spoofed header from a direct-origin request, the API cannot
distinguish it from valid edge input. Before enabling attribution, vps-ops must
restrict origin bypass, verify trusted edge ingress and ensure the proxy preserves
only the authoritative edge header. Neither a DNS record nor a header's mere
presence proves those conditions. Do not replace missing proof with the country
of the Business server, a CDN node, a request's language or a fabricated default.

Cloudflare documents [country-header semantics](https://developers.cloudflare.com/fundamentals/reference/http-headers/#cf-ipcountry),
[geolocation configuration](https://developers.cloudflare.com/network/ip-geolocation/)
and [origin protection](https://developers.cloudflare.com/fundamentals/security/protect-your-origin-server/).
These official references were inspected on 2026-10-19; no account setting was
changed. Ops owns the selected effective mechanism, including any stacked-CDN
constraints. This document does not select another proxy or authorize a new service.

The report's `country_collection: trusted_proxy_header` describes current API
configuration, not a completed Cloudflare verification or every historical row's
provenance. Country is a coarse request-location estimate, not nationality, a
person or precise location. Small known-country buckets and click cells are
withheld below their existing thresholds. Keep unknown and withheld distinct.
Page views deduplicated by event UUID are not unique visitors or people.

## Acceptance matrix and evidence ownership

| Check | Expected result | Evidence owner |
| --- | --- | --- |
| Both collection flags off | No production collection; public route disabled | Product/API configuration |
| Events enabled, country off | Counts can be accepted; country stays unknown | API adapter/persistence tests |
| Country on, exact peer, one valid edge code | Real aggregate stores that code; a report publishes it only after the threshold | API persistence plus Ops ingress proof |
| Untrusted/missing peer or forged forwarded-IP header | Country stays unknown | API boundary tests |
| Duplicate, malformed, unknown or missing country header | Country stays unknown; no default location invented | API boundary tests |
| Browser country/identity/arbitrary fields | Strict input rejection; no record written | API validation tests |
| Wrong origin, cookies/Authorization or oversized/chunked body | Existing origin, credential and byte guards reject it | API HTTP tests |
| Direct access to API container or proxy origin bypass | Denied by effective network/proxy controls, not merely hidden by CORS | Ops isolated ingress harness and later VPS |
| Caller supplies a fake country through public ingress | Caller value cannot survive as authoritative edge data | Ops positive/negative proxy harness |
| Valid simulated edge request through the intended proxy | Exactly one edge value reaches the API; no application peer rewriting | Ops proxy harness, API adapter expectations |
| Proxy recreated/readdressed | Exact configured peer still matches or country fails safely to unknown; no broad trust fallback | Ops deployment lifecycle |
| Repeated event UUID | Existing deduplication does not add a second count | API transactional tests |
| API accepted counts read by an authorized viewer | Country/grid/totals and suppression render; anonymous access denied | Product/API/backoffice integration |

The shared [semantic fixtures](../../contracts/analytics-semantics.examples.json)
contain 14 country cases and eight calendar cases. They are synthetic adapter
inputs, not real edge observations. Run without provider or service access:

```sh
uv run pytest -q tests/test_analytics_country.py tests/test_analytics_periods.py tests/test_product_analytics.py
```

Real restricted PostgreSQL tests in
[`tests/test_interaction_integration.py`](../../tests/test_interaction_integration.py)
exercise enabled country storage and reports using a synthetic TestClient peer;
run only against the maintained owned fixture. They do not authenticate Cloudflare.
The [executed native/API/backoffice receipt](https://github.com/gonzalomartinperez/portfolio-backoffice/blob/eccdfe3980e6db12b486eb3e88df923f6c5a509a/docs/verification/calendar-report-2026-10-18.md#native-ingestion-and-authenticated-rendering-checkpoint)
proves a separate real HTTP/database/rendering flow with country **unknown**.
It must not be relabeled as a real Cloudflare-country test. Future Ops harness
results likewise must distinguish simulated ingress from the actual VPS/account.

## Enablement and stopping conditions

Keep both product collection and country attribution off until their separately
required product/privacy and operational acceptance is recorded. API support for
enabled settings is implemented; a default-off flag is not a fixture-only branch.
Before activation, record exact site/API/backoffice and proxy revisions, the actual
API hostname/edge order, selected image identities, relevant settings without
secrets, positive/negative test results and the owner's explicit approval.

If the edge chain or socket identity cannot be verified, keep attribution off and
country unknown. If origin bypass/spoofing remains possible, do not claim trusted
country readiness. Operational faults remain unavailable, never fabricated zeros.
This contract grants no authority for account changes, credentials, publication,
DNS, production collection, assistant activation or paid provider calls.
