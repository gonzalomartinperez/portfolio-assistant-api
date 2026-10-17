# Third-party notices

## Scope

Application source and first-party engineering documentation use the standard
[MIT license](LICENSE). The software grant does not relicense personal identity,
portfolio/career content, employer/client marks or third-party materials.
In particular, source excerpts/reference data in `evals/` and identity/content
visible in screenshots under `docs/assets/` retain their original rights. Owned
engineering diagrams and evaluation harness code are software documentation;
they do not grant rights to extract a portrait or imply endorsement. A software
license is not consent to process personal data.

Dependencies and container/base-image components retain their own licenses;
the image's MIT label describes this application's source, not a relicensing of
every included component. The runtime image carries this notice and `LICENSE`.

Runtime dependencies are recorded exactly in `uv.lock`; this project uses
FastAPI, Pydantic/Pydantic Settings, LangGraph and its PostgreSQL checkpointer,
LangChain Core (required by LangGraph), LangSmith (manual synthetic-summary export),
psycopg/psycopg-pool, Neo4j's Python driver,
OpenAI's Python SDK and Uvicorn. PostgreSQL/pgvector and Neo4j Community container
images are pinned separately in `compose.yaml`. Consult each project's packaged
license and image notices when redistributing a build; transitive dependencies
also retain their own notices. This is attribution, not a substitute license list.

Retrieval fixtures use only approved public text from
[gonzalomartinperez/portfolio](https://github.com/gonzalomartinperez/portfolio),
with commit/path/line provenance. Public availability does not grant unrestricted
reuse of personal content. Do not infer rights over linked employer or client work.

## Private instrumentation

OpenTelemetry Python SDK and OTLP HTTP exporter are Apache-2.0; Prometheus Python
client is Apache-2.0. They supply manual instrumentation and private exposition,
not a hosted service or tracking widget. Locked vendor semantic conventions include
a beta version; support decisions are explicit in docs/support-policy.md.
The README technology chips are repository-authored SVG text/surfaces, with no
external logo/font assets or network badge service.
