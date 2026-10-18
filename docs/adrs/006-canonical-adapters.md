#006 · Canonical adapters and explicit operator composition

Status: accepted and merged through PR93 with real-service/image CI. Date:2026-10-18.

The shared vocabulary calls concrete I/O adapters. The previous infrastructure
package also contained five settings-aware operator conveniences. A blind rename
would preserve adapter→bootstrap coupling, break SQL discovery after nesting and
silently miss monkeypatches attached to reexporting modules.

Concrete modules now live in capability packages beneath app/adapters. Bootstrap
owns settings/default composition for migration, indexing and maintenance. Existing
root ASGI/CLI paths remain. The old infrastructure package is removed after an
in-repository consumer inventory found no remaining runtime callers.
Runtime configuration is captured once for an indexing operation and injected;
provider/database cleanup and budget behavior remain unchanged.

The AST guard rejects the obsolete namespace, including nested modules without
imports, and every adapter→bootstrap dependency. Operator consumers use stable
root CLI modules; no deployed external import dependency has been identified.
Historic receipts continue to describe their original source revisions.

Migration discovery has one fail-closed helper at its new location. Tests freeze
the nine existing SQL filenames/checksums and reject missing resources. Moving
source never edits applied SQL or public/private wire artifacts. Internal test
patches follow canonical implementation/composition globals. Stable root CLI
dispatch is tested without preserving incidental monkeypatch behavior by duplication.

No DI framework, package migration, new service, endpoint or provider is introduced.
The [consumer/preflight evidence](../verification/common-layout-preflight-2026-10-18.md)
records RED and verification requirements. Real-service/image CI, not folder names,
establishes final acceptance. Existing production/image/paid-call holds remain.
