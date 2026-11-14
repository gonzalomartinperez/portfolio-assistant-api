# Neo4j vendor security refresh — 2026-10-17

Status: **verification tooling, not a successful vendor repair**. The candidate
assessment failed. Production release remains blocked. Ordinary source CI and a source
tag do not assert full vendor security acceptance.
No production deployment, existing-store mutation, image publication, Java jar
replacement, scanner suppression or server-major upgrade is authorized here.

## Why the immutable bytes matter

The official registry tag `neo4j:5.26.32-community-trixie` was queried read-only on
2026-10-17. Its current index is
`sha256:0a6e7aedf54a531f76286032d4365ead65b11cca05e4a15cdf23b8e53d6db02b`,
Linux amd64 manifest
`sha256:47ea172cbd3eb5c5128c3117233dbe567af795d916f3fa48814716c50986b1af`.
The previous pinned index
`sha256:f1e52d4dc6da122468c4a3c1050a4f5e117f6d3268625237c34d49166f0d6082`
has a different amd64 manifest
`sha256:57ecb62bbb0c41c98fb69e08ee014c959926f3bd16ee8ef466c4a1e298f6157c`.
The reviewed config/image ID is
`sha256:4e4837b1c3649f458cc4ff43f8b47eb5ab4dc2f84e79beb82685f063f04b576a`.
`deploy/neo4j-image.json` now records the retained baseline descriptor, not this
rejected candidate. Its amd64 configuration is
`sha256:a6ac4fbb3863670c42fd72cb8fbcb500ba5c2e67538eaac98e45f56936807c81`;
the old manifest raw bytes and configuration link were independently verified again
on2026-10-17. Index and platform manifest raw
bytes were independently SHA256-verified against official registry responses;
the manifest links to this configuration. Same version/tag is not proof of identical or repaired package bytes. Compose and
CI retain the previously accepted index, which itself has unresolved findings.
This does not promote a known-vulnerable baseline into production acceptance.

Ops supplied the exact old-image scan from 2026-10-13T11:18:37Z, Trivy0.75.0,
OS DB updated 06:41:11Z and Java DB updated 01:09:47Z that day. It reported one
CRITICAL /112 HIGH including four fixable Jackson HIGH issues: core2.22.2
CVE-2026-89407/89425 and databind2.22.2 CVE-2026-91776/91777, fixed in2.22.3.
The critical linux-libc-dev6.12.111-1 CVE-2026-43185 had no listed fix. These
are historical findings of the old digest, not a scan of the candidate or proof
that a container runs that kernel. Runtime applicability remains unresolved.

[The vendor changelog](https://github.com/neo4j/neo4j/wiki/Neo4j-5.26-changelog)
currently lists Jackson2.22.3 and Netty4.1.138.Final for5.26.32. This motivated
checking the republished official image; changelog prose alone does not prove
that our old pin contains those fixes. No confirmed later5.26 patch was selected.

## Evidence procedure and gates

Normal PR CI tests the actual pinned Neo4j with PostgreSQL, retrieval and HTTP/SSE
lifecycle. An explicit manual dispatch of the **existing Quality workflow** with
`verify_vendor_image=true` deep-scans the exact selected service image with full OS and Java inventories,
pinned Trivy0.75.0, current advisory metadata, no ignore file, all packages and a
bounded ten-minute scanner timeout. It uses the hosted ephemeral runner, not
another agent's VM/services. It does not add another image build/server lifecycle.

`scripts.database_security_receipt` binds the report to the reviewed config ID, exact artifact name and approved repo
digests. It also re-fetches bounded official index/platform metadata and verifies
SHA256 plus the amd64→configuration chain; a caller-supplied image ID alone is insufficient. It
requires OS+jar inventories and scanner/DB provenance, shows relevant Jackson
versions/header findings plus complete severity counts. The current CLI fails on
**every CRITICAL and fixable HIGH** finding, including critical findings without a
published fix. Unfixed HIGH findings remain visible for production assessment;
a green remediation gate is not a clean-image claim or risk waiver. The API image's stricter existing
all-critical gate is unchanged. Old scans remain historical, never relabeled fresh.

No ~1GB Java advisory download is added to every ordinary PR. Run this explicit
release assessment before accepting a changed vendor digest and again with current
advisory data before deployment. Passing ordinary API/PG scans does not establish
Neo4j security acceptance. Preserve report/run IDs and scanner timestamps in the
handoff. Deep scanning the candidate does not establish a production backup restore
or reverse-store compatibility; migrations and recovery remain independently gated.

## Rejected candidate evidence

[Deep run39059599423](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/39059599423)
at source `baa8abfee53a6788a21d05beb0907ae2429ecdc9` correctly failed against candidate
0a6e7aed: one unresolved CRITICAL, four fixable Jackson HIGH,107 unfixed HIGH,
1261 findings overall. Normal2.22.3 jars coexist with vulnerable2.22.2 copies;
the changelog was not sufficient evidence. No finding was suppressed. See the
[complete dated blocker](neo4j-release-blocker-2026-10-17.md) for scanner/DB times.

The input defaults false to keep source validation separate from explicit vendor
assessment. This is not a disabled release gate: **vps-ops must require a fresh,
successful exact-selected-digest OS/Java receipt plus disposition of every critical
finding before publication/release selection**. That production controller is outside
this repository and not activated here. A missing assessment remains a release blocker.
When requested, this step fails the existing required `checks` gate on findings or
incomplete artifact binding; no `continue-on-error`, ignore file or waiver is used.

Run, for example, `gh workflow run quality.yml --ref <reviewed-ref> -f verify_vendor_image=true`.
Record the exact source SHA, selected index/platform/config, report and advisory times.
Never use a green ordinary dispatch with the default false as a deep assessment.

## October18 correction and metadata recheck

The previous CLI threshold rejected only fixable critical/high findings, despite
this handoff treating unresolved critical findings as release blockers. A synthetic
unfixed-header critical and an unfixed-Java critical both reproduced an incorrect
successful exit. The CLI now fails for either case while preserving the full receipt,
package counts and `production_accepted=false`. Fixable critical/high, mixed findings,
unfixed-HIGH visibility and no-finding behavior have separate regression cases.
The verifier's receipt now has an explicit typed shape and is included in the
existing strict mypy command/CI job, without changing dependency locks or adding a
second checker. Untrusted report metadata retains `object` types; the gate uses
validated integer counts. A header finding still does not identify the host kernel; lack of exposure evidence
must not turn an unresolved critical assessment green. No suppression or waiver
mechanism is introduced.

Read-only official registry verification at2026-10-18T14:01:07Z observed the same
rejected candidate index0a6e7aed, amd64 manifest47ea172c and config4e4837b1 recorded
above. SHA256 of the fetched manifest bytes matched the descriptor. The
`5.26.33-community-trixie` tag returned HTTP404; the official changelog still listed
5.26.32 first. This is a metadata observation, not a fresh image scan or evidence
that a different artifact is safe. No image was pulled/built or pin changed.
The [Debian tracker](https://security-tracker.debian.org/tracker/CVE-2026-43185)
continues to mark the selected stable line vulnerable; that source-package status
alone does not establish runtime exploitability. Vendor remediation and production
acceptance remain blocked independently of ordinary application-source CI.
