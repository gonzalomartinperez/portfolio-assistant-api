# Third-party notices

Application source has no selected license. Dependency licenses apply to their
own code and do not license this repository's source. No third-party image or
visual asset is bundled here.

Runtime dependencies are recorded exactly in `uv.lock`; this project uses
FastAPI, Pydantic/Pydantic Settings, LangGraph and its PostgreSQL checkpointer,
LangChain Core (required by LangGraph), psycopg/psycopg-pool, Neo4j's Python driver,
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
