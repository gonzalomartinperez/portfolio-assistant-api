# Future VPS deployment checklist

This repository is not deployed. `main` and the live portfolio remain unchanged.

- Use TLS for the API and web origins. Set exact `ALLOWED_ORIGINS` for the actual portfolio and chat hostnames. Enable `SECURE_COOKIES=true`; the API then uses the host-only `__Host-assistant_session` cookie. Use a random `RATE_HASH_KEY` and private database credentials. Keep Neo4j and PostgreSQL on internal networks only.
- Route POST SSE with proxy buffering disabled, long enough read timeout, and no response caching. Verify fragmented streaming and cancellation through the actual proxy before release.
- Run migrations once, then sync reviewed public content. Pin image digests for rollback. Never put model credentials in the portfolio or web build.
- PostgreSQL backups require encryption and off-site storage with a restore drill. Neo4j Community uses an offline `neo4j-admin database dump`, or the public graph projection can be rebuilt after PostgreSQL restore. Online backup is not available in Community.
- Measure API, web, PostgreSQL, Neo4j and Coolify memory/CPU/disk under representative traffic on the chosen VPS. KVM 2 fit remains unproven. Decide whether to increase resources before deployment.
- OpenAI account access, an explicit spending authorization, VPS purchase/configuration, DNS, proxy and `develop` to `main` promotion are separate release gates.
