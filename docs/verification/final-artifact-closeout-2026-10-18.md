# Final local artifact verification · 2026-10-18

Documentation reconciled on 2026-10-19. **Application source is verified; production
security acceptance remains blocked.** This records completed local work rather
than a deployment, registry publication or new live-model evaluation.

## Source and functional evidence

The tested API source is `f9c0f0a169e3174a12c846caab1d273ac1d53632` (protected
release PR116). Its synchronized develop commit is
`6ad190bbcea854e96b1836f61ecfa0f4c00cbd37` (PR117); both have tree
`b1a18643f070085c7c319cfaf2d112a5b4507f40`.
[Main push39174723342](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/39174723342)
and [develop push39175208869](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/39175208869)
passed all six jobs. The disjoint selections passed 819 offline and 47 real-service
tests; these are not live-provider quality scores.

Independent Git-object review confirmed that application files, contracts, locks,
project configuration and Docker recipes match runtime
`b53cd1998e17c27a7b6ba17ac2317d9db6cfcfce`. That runtime's isolated PostgreSQL/Neo4j
acceptance used public producer `12e68c662b855422411ffdfd1d5334f6b4b0e086`, with 97
chunks, the canonical hybrid 9/9 retrieval bank and 20/20 completed fixture HTTP
conversations. See [graph readiness](graph-readiness-2026-10-18.md) and
[public-content compatibility](../coordination/portfolio-content-layout.md).

The backoffice source remains `a124139e1cfa1d0d496fcf76c518830491fc1679`; its
[committed runtime contract](https://github.com/gonzalomartinperez/portfolio-backoffice/blob/a124139e1cfa1d0d496fcf76c518830491fc1679/docs/deployment-contract.md)
is unchanged. No new paired live OAuth or deployed integration test is claimed.
A later documentation-only commit is not a relabeling of the artifact source above.

## Exact local image and payload

| Identity | Value |
| --- | --- |
| Local Docker manifest | `sha256:8fd15296efdc4bf80c6bd407588aaa9e2d0ce4899cf1096be20da1d89ad3c160` |
| OCI configuration | `sha256:6a05035f604b43ebafd2fddff11eedcbd58aa7a40b3203aa96700c88ec900dda` |
| Exported archive SHA256 | `a89502022f920b321897db5dddb0a29e028c4dbc4c763b6aec320cf6c0b0d1cd` |

The artifact has not been published to an application registry. Manifest,
configuration and all compressed layer blobs were verified before scanning.
The payload probe ran as UID 65532 without network access, with a read-only root,
dropped capabilities and bounded CPU/memory. It passed the original assertions:

- Python 3.14.8 and the complete 95-file application hash
  `7d1834e29daaec0d1989e7b5cb1f03471c1fdc8ab0e4dde884ed917ade0617b6`.
- Application imports and fixture-provider settings with paid calls disabled.
- Installed `liblzma5=5.8.1-1+deb13u2` and Python LZMA roundtrip.

The successful probe finished at 23:40:09 UTC. No database-readiness or model call
was part of that no-network probe; the real-service CI remains separate evidence.

### Rejected archive build and correction

The rejected local identity
`sha256:1a1f9810053b8124aa7510acb6edf7eb12a79c25caa69182477946e84faecd1e`
failed the source hash before importing the application. Metadata showed that
UID 65532 could read only 6/95 files: inner root-owned directories retained mode 700.
The private archive harness inherited umask 077 while
[Python's data filter](https://docs.python.org/3.14/library/tarfile.html#tarfile.data_filter)
discarded directory modes. This did not change the committed Dockerfile or ordinary
CI checkout builds.

The corrected extractor preserves the private outer context 700, makes real inner
directories 755 and retains file modes, hashes, path and size guards. Tests reproduced
the original failure under077 and verified 077/022, explicit/implicit directories,
unsafe archives and builder bindings. Thirteen pure harness tests passed.
A first corrected context still reused the bad COPY layer and produced the same
rejected image. A stage-specific
[`--no-cache-filter runtime`](https://docs.docker.com/reference/cli/docker/buildx/build/#no-cache-filter)
then rebuilt only the runtime stage, retaining dependency caches. The new image
passed the unchanged payload. Original failures were preserved; no global cache
prune, assertion relaxation or production-volume change occurred.

## Complete inventory and unresolved findings

Pinned Trivy 0.75.0 completed an offline API-only inventory and CycloneDX 1.7 SBOM
against the verified image. It inspected 183 packages; the SBOM has 184 components,
a distinct measure. The frozen OS database was published 18 October at 18:32 UTC;
its original freshness metadata was retained. No database download or repeat scan
of the unchanged PostgreSQL, backoffice or Neo4j images occurred.

| Result | Count |
| --- | ---: |
| Critical | 0 |
| Fixable high | 0 |
| Unresolved high | 49 |
| Unknown severity | 4 |
| Unidentified packages | 0 |

Coverage was complete for the policy. **The full policy rejected the artifact and
requires manual security review.** The successful inventory is not a clean-image
claim. The LZMA correction removed two unknown-severity entries from the
[earlier API baseline](container-security-2026-10-18.md); the four remaining entries
concern CVE-2026-82560 across Perl packages. No severity override was applied.

On 19 October the [Debian tracker](https://security-tracker.debian.org/tracker/CVE-2026-82560)
still lists Trixie Perl 5.40.1-6+deb13u1 as vulnerable and no-DSA/minor. Upstream
Pod::Text 6.1.1 is not evidence that a supported Debian package is available.
The [official Neo4j catalog](https://neo4j.com/current-neo4j-versions/) and
[release archive](https://neo4j.com/release-notes/database/) still list 5.26.32
as the newest confirmed 5.26 patch. The separate
[Neo4j vendor security hold](neo4j-release-blocker-2026-10-17.md) remains unchanged.
These official metadata checks were not new scans or remediation.

Do not patch vendor jars, suppress unknown findings, silently switch server majors
or drop Git without preserving the corpus worker. A supported repair or separately
reviewed image change needs its own compatibility and full security verification.

## Evidence provenance and operational handoff

Private receipts were independently hash-checked and their summary/configuration/
archive identities joined. No credentials, raw scan logs or conversation answers
are copied into this public report.

| Record | SHA256 |
| --- | --- |
| Successful payload receipt | `61e560ae785f164fb808e164a89215a011962fd391775dcb61e63ae0633249c8` |
| Complete inventory receipt | `97d0801eacfa25d96050376835cfdd90158a22a01b69d7a7784ccb83293ded18` |
| Security summary | `e40c266f5a65d063d9f5ee5332465c473fdee703a5538ee90f7d2474cff9d44e` |
| CycloneDX SBOM | `554a26aaa356855b54ee37500bfb0acd7724148194a4771ba2597cbd742dd73a` |

The original scanner receipt has no embedded end timestamp. It was written at
23:43:10 UTC; a separate post-exit observer at23:44:09 UTC recorded the process
absent and no owned scan containers. That observer is not an atomic original
completion receipt. The builder was stopped; no local reservation remains.

Private vps-ops accepted the source/artifact/security handoff. Follow the
[application runtime contract](../deployment-contract.md): only `/api/v1/*` goes
to FastAPI, while Next retains its authentication and readiness paths. Coolify,
publication, effective headers, secrets, migrations, backup/recovery, resource
allocation and deployment remain separately owned and authorized. No production
assistant/analytics activation, new model calls or registry publication occurred.
Neither local evidence nor source merging proves physical-device behavior, live
OAuth, future VPS capacity or production readiness.
