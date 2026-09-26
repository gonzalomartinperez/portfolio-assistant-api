# Future VPS deployment checklist

This repository is not deployed. `main` and the live portfolio remain unchanged.

- Set `ENVIRONMENT=production` so startup rejects local credentials, localhost origins, insecure cookies and a predictable rate hash key. Use TLS for the API and web origins. Set exact `ALLOWED_ORIGINS` for the actual portfolio and chat hostnames. Enable `SECURE_COOKIES=true`; the API then uses the host-only `__Host-assistant_session` cookie. Use a random `RATE_HASH_KEY` and private database credentials. Keep Neo4j and PostgreSQL on internal networks only. Set `TRUSTED_PROXY_IPS` to the reverse proxy's exact internal addresses; only those peers may supply `X-Forwarded-For` for bootstrap rate limiting.
- Route POST SSE with proxy buffering disabled, long enough read timeout, and no response caching. Verify fragmented streaming and cancellation through the actual proxy before release.
- Run `python -m app.migrate` as an explicit one-shot step before starting the API, then sync the reviewed public commit. Never mutate an applied migration; its checksum is checked on startup. Pin image digests for rollback. Never put model credentials in the portfolio or web build. Paid calls also require explicit per-million-token prices and reservation values for the selected model; fixture mode remains the default.
- PostgreSQL backups require encryption and off-site storage with a restore drill. Neo4j Community uses an offline `neo4j-admin database dump`, or the public graph projection can be rebuilt after PostgreSQL restore. Online backup is not available in Community.
- Measure API, web, PostgreSQL, Neo4j and Coolify memory/CPU/disk under representative traffic on the chosen VPS. KVM 2 fit remains unproven. Decide whether to increase resources before deployment.
- OpenAI account access, an explicit spending authorization, VPS purchase/configuration, DNS, proxy and `develop` to `main` promotion are separate release gates.

## Local resource observation

Measured on 2026-09-26 with `docker stats --no-stream` after the services were idle following fixture browser tests. The production API image used 85 MiB, web image 70 MiB, PostgreSQL 64 MiB and Neo4j 655 MiB RSS-equivalent container memory, about 874 MiB combined before the OS, proxy, Coolify, file cache and traffic headroom. Local Docker images occupied 4.5 GB and project volumes about 608 MB at that point. This is a single idle WSL measurement, not a KVM 2 capacity claim. A load run including Coolify and deployment proxy remains necessary before VPS selection.
