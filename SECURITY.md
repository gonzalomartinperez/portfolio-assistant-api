# Security

Report vulnerabilities privately through
[GitHub private vulnerability reporting](https://github.com/gonzalomartinperez/portfolio-assistant-api/security/advisories/new).
The feature was enabled and verified through the GitHub API on 2026-09-27.
Do not put credentials, personal data or exploit details in public issues.

The project is a fixture-backed engineering release candidate, not a deployed
production service. Security fixes target `develop`; there is no published
support SLA or production uptime commitment. Include the affected commit,
reproduction, impact and a minimal redacted example in a report.

See the [threat model](docs/threat-model.md) for implemented controls and residual
risks. Prompt injection is not solved. Fixture tests do not establish real-model
safety. Real credentials and paid calls require explicit owner authorization.
