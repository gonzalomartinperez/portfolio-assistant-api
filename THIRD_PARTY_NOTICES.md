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
