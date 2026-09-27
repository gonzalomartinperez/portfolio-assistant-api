# Source this file from the repository root. These values are public fixture defaults.
export COMPOSE_PROJECT_NAME="${ASSISTANT_PROJECT:-assistant-fixture}"
export POSTGRES_PORT="${POSTGRES_PORT:-55433}"
export NEO4J_PORT="${NEO4J_PORT:-57688}"
export NEO4J_HTTP_PORT="${NEO4J_HTTP_PORT:-57475}"
export DATABASE_URL="postgresql://assistant:assistant@127.0.0.1:${POSTGRES_PORT}/assistant"
export NEO4J_URI="bolt://127.0.0.1:${NEO4J_PORT}"
export AI_PROVIDER=fixture ALLOW_PAID_AI=false EMBEDDINGS_PROVIDER=fixture
export LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false
