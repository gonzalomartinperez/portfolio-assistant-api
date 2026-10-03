-- Public-source vectors only: never cache visitor queries or transcripts here.
CREATE TABLE public_embedding_cache (
    content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    provider text NOT NULL CHECK (provider='openai'),
    model text NOT NULL CHECK (model='text-embedding-3-small'),
    embedding vector(1536) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(content_hash,provider,model)
);
