# Provider transport and resource lifecycle — 2026-10-17

This increment hardens the existing OpenAI transport and cleanup policy. It does
not change model, effort, public/SSE/OPS schemas, dependency versions or hosting.
OpenAI SDK 3.33.0 uses native HTTPX2 2.13.1 / HTTPCore2 2.13.1, with truststore 0.10.4;
legacy HTTPX 0.28.1 remains available for compatibility tests, not the native default.

The committed adapter supplies the SDK's public default client classes with TLS
verification enabled, redirects disabled and proxy/CA environment discovery disabled.
The fixed `https://api.openai.com/v1` origin remains composition-owned. A 307/308
response becomes a provider failure rather than forwarding a visitor's request body
elsewhere. No alternate provider, model fallback or automatic generation retry.
A deliberately required corporate proxy/custom CA needs a separately reviewed
configuration change; adding environment overrides is not a supported bypass.

The shared async client serves generation and query embeddings with a 45 s socket
limit. Synchronous/index embeddings use 20 s; the application run deadline defaults
to 60 s (configured through existing RUN_TIMEOUT_SECONDS). DNS/OS networking can
exceed individual socket deadlines; these are not availability guarantees. Explicit
stream cleanup and cancellation remain required. Client construction transfers
transport ownership only after SDK initialization succeeds; failed initialization
releases the transport. Lifespan cleanup attempts all owned resources even if one
close fails, propagating a single failure unchanged or multiple failures as an exception group.
Cancellation is not swallowed. These checks include partial startup.

The SDK pool defaults remain 1,000 maximum connections / 100 idle / 5 s keepalive expiry.
They are ceilings, not preallocated sockets or evidence of a safe application
concurrency level. No pool tuning or throughput claim was inferred without a VPS
workload measurement. Clients are reused for their existing lifespan/indexing scope.

HTTP/2 remains optional and disabled, and the h2 package is absent from the lock.
No library, parser or server was installed merely to raise a protocol version.
TLS certificate/hostname verification remains enabled. The local managed interpreter
supports TLS 1.3 with a default TLS 1.2 minimum, but no native-client wire negotiation,
container OpenSSL version or future VPS path is certified by this inspection.
The shared browser/reverse-proxy HTTP/TLS policy belongs to vps-ops.

The backoffice's private OPS requests continue to use Node fetch with the existing
exact-origin/path validation, redirect rejection, omitted browser credentials,
no-store responses, abort deadlines and bounded JSON readers. They do not expose
service tokens to browser code. Live authenticated VPS load remains unverified.

At runtime commit `9ad866c2bf92a857df12bdf58d04fbf70c6ca520`, 537 offline tests
passed and 33 service tests were skipped locally; this is not real-service evidence.
Synthetic tests exercise redirect/body behavior, environment isolation, construction
failure and independent cleanup. Full contract, real-database, image and active-SSE
shutdown CI remains mandatory. No real provider calls were made for this increment.
The separately authorized six-case smoke stays attributed to API 02b6f278 and corpus
776ee861; its guarded compatibility clients do not establish native HTTPX2 wire
negotiation for this new source. No new LangSmith export or account was activated.

Official documentation reviewed:
- [OpenAI SDK overview](https://developers.openai.com/api/docs/libraries)
- [HTTPX HTTP/2](https://www.python-httpx.org/http2/)
- [HTTPX certificate verification](https://www.python-httpx.org/advanced/ssl/)

Runtime/image/secret changes remain application-owned; deployment stays vps-ops/Coolify
owned and disabled. Neo4j vendor security acceptance remains an independent production
blocker. Existing source tags stay immutable.
