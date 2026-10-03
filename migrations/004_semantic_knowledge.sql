-- Additive: keep fixture vectors and old readers available during upgrades.
ALTER TABLE chunks ADD COLUMN semantic_embedding vector(1536);
ALTER TABLE chunks ADD COLUMN search_document tsvector GENERATED ALWAYS AS (
    to_tsvector('simple', content)
) STORED;
CREATE INDEX chunks_search_document ON chunks USING gin(search_document);
ALTER TABLE knowledge_versions ADD COLUMN embedding_provider text NOT NULL DEFAULT 'fixture';
ALTER TABLE knowledge_versions ADD COLUMN embedding_model text NOT NULL DEFAULT 'hash64-v1';
CREATE UNIQUE INDEX knowledge_one_active ON knowledge_versions ((status)) WHERE status='active';
CREATE TABLE knowledge_watch (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    observed_commit text NOT NULL CHECK (observed_commit ~ '^[0-9a-f]{40}$'),
    checked_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE spend_ledger ADD CONSTRAINT spend_nonnegative CHECK (
    reserved_usd > 0 AND (actual_usd IS NULL OR actual_usd >= 0)
);
