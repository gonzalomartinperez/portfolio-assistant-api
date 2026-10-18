# Owned PostgreSQL fixture startup regression

Preserved RED: post-develop source923f5d32215203d6a09efd2ef1dec8e49225d4e5,
[Quality39093024368](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/39093024368).
The real database job failed during bootstrap of the calendar integration fixture:
36tests passed,1failed. The Docker wrapper deliberately redacts command output,
so this record does not invent an exact PostgreSQL stderr message. Container,
static, workflow and secret jobs passed; the required aggregate correctly failed.
No blind rerun or success relabeling was used.

The old readiness loop accepted a socket SELECT1. The
[official PostgreSQL entrypoint](https://github.com/docker-library/postgres/blob/master/docker-entrypoint.sh)
starts a temporary socket-only server with empty listen_addresses for initdb hooks,
then stops it before exec of the final postmaster. Accepting that socket query can
race shutdown/bootstrap even when a container is running and has a published port.
This is a concrete fixture race compatible with the observed failure; the regression
below must establish it on the actual owned image before acceptance.

The corrected waiter requires a nonempty SHOW listen_addresses response before
bootstrap. Readiness probes have3s command bounds inside a30s deadline. It tolerates
the temporary shutdown, but never retries bootstrap/migrations or a generation.
No host-admin HBA rule, credential exposure, production change or blanket sleep is
introduced. Existing label/source/port guards and owned cleanup remain intact.

Two offline tests exercise temporary socket state, shutdown and fail-closed timeout.
A real-service regression adds an8s delay only inside a fresh owned initdb fixture:
it observes SELECT1 succeeding while listen_addresses is empty, then invokes the
real waiter and proves final restricted-role TCP access. The database/init scripts,
images, schema bytes and production runtime are unchanged. This artificial delay
is a test of the lifecycle boundary, never a product loading delay.

Local unit/static checks are separate from the pending hosted real regression.
No local Docker/build/browser or paid provider was invoked during another owner's
lease. Keep the original RED and record this fix's exact-head CI result, rather
than treating an earlier PR's green run as post-merge acceptance.

## Executed correction

PR99 head98fe65b9461f24aba1c0f1294045bb95b480433b passed all six paired jobs in
[Quality39093823788](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/39093823788).
The database job executed38 real-service tests successfully in39.38seconds, including
the controlled temporary-server regression, then bilingual fixture evaluation and
independent dual-application IAM/recovery checks. Static ran696 offline tests.
Normal develop mergea5707b24bf1853e44b9888794bcfb7575e462cea has its own post-merge
run; its outcome must be recorded separately. The original failed run remains intact.
