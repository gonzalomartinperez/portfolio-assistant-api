# ADR 003: production ownership and Coolify

Accepted by owner; supersedes ADR 002's application-owned shared production stack.

Private vps-ops owns shared production composition, ingress, TLS, networks, volumes,
resources, secret delivery, migrations scheduling, backup/recovery and releases.
Coolify is selected for both assistant applications on the future Hostinger KVM 4.
The portfolio remains on Business. Application repositories own tested images,
runtime contracts, health endpoints and migration implementations.

The release flow is source → application CI → tested image → separately authorized
immutable publication → vps-ops release selection → approved Coolify deployment.
No merge/publication implies deployment authorization. No VPS source builds,
application deployment webhooks or competing controllers are introduced.

Retain old production assets as frozen transfer references until vps-ops confirms
adoption. Keep application/local smoke tests; they do not prove Coolify behavior.
The [runtime contract](../deployment-contract.md) inventories transfer assets,
requirements and unverified decisions. This avoids two independently maintained
production stacks while preserving useful prior work. Exact Coolify image-digest
and rollback workflows remain the vps-ops owner's verification responsibility.
