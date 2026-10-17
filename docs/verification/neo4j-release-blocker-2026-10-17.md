# Neo4j release blocker — observed 2026-10-17

**Production release remains blocked.** The current pinned5.26.32 vendor and a rebuilt
same-version candidate retain unresolved security findings. Green API/PostgreSQL CI
is not a full Neo4j Java security assessment or a clean-stack claim.

The candidate official index
`sha256:0a6e7aedf54a531f76286032d4365ead65b11cca05e4a15cdf23b8e53d6db02b`
resolves to Linux amd64 manifest
`sha256:47ea172cbd3eb5c5128c3117233dbe567af795d916f3fa48814716c50986b1af`
and config/image ID
`sha256:4e4837b1c3649f458cc4ff43f8b47eb5ab4dc2f84e79beb82685f063f04b576a`.
The official index/platform raw SHA256 chain was verified. This candidate is **not
adopted in the accepted service configuration**. The earlier pinned index remains
`sha256:f1e52d4dc6da122468c4a3c1050a4f5e117f6d3268625237c34d49166f0d6082`.

[Deep Quality39059599423](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/39059599423)
at source `baa8abfee53a6788a21d05beb0907ae2429ecdc9`, report created
2026-10-17T18:49:57Z, correctly failed its remediation gate:

| Finding | Current candidate result |
| --- | --- |
| CRITICAL |1, linux-libc-dev6.12.113-1, CVE-2026-43185, no fix listed |
| Fixable HIGH |4 Jackson findings;2.22.2 remains alongside2.22.3 |
| Unfixed HIGH |107 |
| All severities |1261 findings; none suppressed |

Core CVE-2026-89407/89425 and databind CVE-2026-91776/91777 list2.22.3 fixes.
The retained old-image inventory locates the vulnerable shaded copies inside
`var/lib/neo4j/lib/parquet-jackson-1.18.1.jar`; replacing ordinary Jackson jars alone
would not establish that this embedded copy was fixed. Current candidate package
inventory still reports both2.22.2 and2.22.3. No jar modification, exclusion or scanner
suppression was applied. Header findings do not identify the running host kernel;
applicability is unresolved, not waived.

Scanner: pinned Trivy0.75.0. OS DBv2 UpdatedAt2026-10-16T01:13:54Z,
DownloadedAt2026-10-17T18:49:22Z. Java DBv1 UpdatedAt2026-10-17T01:07:50Z,
DownloadedAt2026-10-17T18:49:56Z. These are dated observations, not perpetual freshness.
The same-version vendor changelog advertises Jackson2.22.3; that does not prove that
all shaded copies in immutable distribution bytes are fixed.

[Verification PR71](https://github.com/gonzalomartinperez/portfolio-assistant-api/pull/71)
preserves the rejected candidate evidence and strict reproducible scan/manifest-receipt
work, while retaining the old runtime pin. Its explicit assessment input does not
turn ordinary source checks into vendor release acceptance.
It must not be merged as a successful security repair. A compatible vendor fix,
full updated OS/Java rescan and isolated runtime/store/recovery evidence are required
before selecting a replacement. No later5.26 patch was confirmed during this audit.
Do not force an unreviewed server major or delete useful rejected-candidate work.

No production was deployed, registry image published, shared volume touched or paid
model invoked. Application-source improvements can be reviewed independently, but
neither a source tag nor green ordinary CI authorizes the blocked database release.
