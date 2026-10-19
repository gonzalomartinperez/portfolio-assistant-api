# Exact-image security inventory · 2026-10-18

Four local Linux amd64 images were exported, bound to their OCI manifest/configuration
and layer checksums, scanned with Trivy 0.75.0 and converted to CycloneDX. The baseline
API source is `33c544dead74e0d30283516b6653b0e0aea84bca`; the backoffice source is
`a124139e1cfa1d0d496fcf76c518830491fc1679`. These are local image identities,
not published registry artifacts or production acceptance.

| Role | Local image identity | Packages | Critical | Fixable high | Unfixed high | Unknown severity |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| API / knowledge worker | `sha256:bf33ddd3193b8600bb1c3e78ce76c6ac891af54fc073f6c95e6cd4025d0f5589` | 183 | 0 | 0 | 49 | 6 |
| PostgreSQL | `sha256:974756c82a82f18767587ee6814ea7928b0ebf498ca7aa529b0c925740d11d39` | 53 | 0 | 0 | 0 | 0 |
| Backoffice | `sha256:f9fb41823f8a3245b2f246af8e834279a99bd7b829b14d21a8474767e0b3048b` | 183 | 0 | 0 | 0 | 0 |
| Vendor Neo4j | `sha256:f1e52d4dc6da122468c4a3c1050a4f5e117f6d3268625237c34d49166f0d6082` | 338 | 2 | 17 | 100 | 350 |

Counts are package/finding pairs, not unique vulnerabilities or exploitability proof.
PostgreSQL has two lower-severity findings; backoffice has 31. Their inventory policies
passed, which does not certify application authorization, VPS capacity or deployment.
API and Neo4j remain blocked in the release assessment. Neo4j includes a real Java
inventory with ten Jackson package entries; Java was not skipped to obtain a result.

The vulnerability database was published at 18:32 UTC and downloaded at 19:36 UTC.
The Java index was published at 00:58 UTC and downloaded at 16:06 UTC. After registry
transport failures, an explicitly authorized read-only copy of the two public Java
tool-data files was verified by checksum. Original timestamps were preserved; scanner
binary equality between projects was not assumed. Our pinned executable successfully
read both formats and scanned the images offline with network access disabled.

## Correctable application finding

The baseline inherited `liblzma5` version `5.8.1-1+deb13u1`. Debian identifies
`5.8.1-1+deb13u2` as the fixed Trixie security package in
[DSA-6549-1](https://security-tracker.debian.org/tracker/DSA-6549-1).
The application recipe now pins that signed package. The real image smoke also
checks the installed package version and a Python LZMA compression/decompression
round trip. A new image and its rescan must establish the correction; the baseline
result above is retained and must not be relabeled as the patched image's result.

The other four unknown API entries concern Perl packages and
[CVE-2026-82560](https://security-tracker.debian.org/tracker/CVE-2026-82560).
At the inspection cut, Debian listed Trixie as unfixed and classified its handling
as no-DSA/minor. This is triage evidence, not an automatic severity override or waiver.
Unfixed high findings also require explicit assessment before production selection.

## Vendor and evidence boundaries

The selected Neo4j image remains rejected. Findings include the installed
`linux-libc-dev` package, vulnerable Jackson 2.22.2 and the same LZMA update.
Do not replace vendor jars, suppress records or equate a container package inventory
with the host kernel's security status. A supported vendor update or a separately
reviewed image change requires its own runtime/graph and full security verification.

The four inventories, SBOMs, database hashes and original failed transport attempts
are retained in private local verification artifacts. The completed inventory receipt
SHA-256 is `b67ad0e6b215b29d69f44a9bace9f35e788ced3f5d898193362a7c4416d31e6f`.
No secrets, model calls, production deployment or registry publication were involved.
Reproduce through the [image verification procedure](neo4j-vendor-refresh-2026-10-17.md)
and current runtime/CI commands; database freshness and findings change over time.


## Completed patched-image verification

The baseline above remains historical. The
[final artifact closeout](final-artifact-closeout-2026-10-18.md) records the new
source-bound image, successful unchanged LZMA/source payload assertions and complete
inventory/SBOM. Its unknown count is 4 rather than 6; 49 unresolved high findings and
the separate Neo4j hold remain. The full production assessment did not pass.
