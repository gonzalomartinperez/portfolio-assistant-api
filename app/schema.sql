CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS sessions (
  id uuid PRIMARY KEY, secret_digest text NOT NULL UNIQUE, csrf_token text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS conversations (
  id uuid PRIMARY KEY, session_id uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  title text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS conversations_owner ON conversations(session_id, updated_at DESC);
CREATE TABLE IF NOT EXISTS messages (
  id uuid PRIMARY KEY, conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('user','assistant')), content text NOT NULL,
  citations jsonb NOT NULL DEFAULT '[]', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS messages_conversation ON messages(conversation_id, created_at);
CREATE TABLE IF NOT EXISTS runs (
  id uuid PRIMARY KEY, conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  idempotency_key text NOT NULL, payload_hash text NOT NULL,
  state text NOT NULL CHECK (state IN ('pending','running','completed','failed','cancelled','interrupted')),
  message_id uuid REFERENCES messages(id) ON DELETE SET NULL, error_code text,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(conversation_id,idempotency_key)
);
CREATE UNIQUE INDEX IF NOT EXISTS runs_one_active ON runs(conversation_id) WHERE state IN ('pending','running');
CREATE TABLE IF NOT EXISTS feedback (
  message_id uuid PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
  session_id uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  rating text NOT NULL CHECK (rating IN ('up','down')), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS knowledge_versions (
  id text PRIMARY KEY, status text NOT NULL CHECK (status IN ('staging','active','retired')),
  source_commit text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS chunks (
  id text PRIMARY KEY, knowledge_version text NOT NULL REFERENCES knowledge_versions(id),
  content text NOT NULL, title text NOT NULL, url text NOT NULL,
  source_type text NOT NULL CHECK (source_type IN ('page','code')),
  path text, start_line integer, end_line integer, content_hash text NOT NULL,
  embedding_provider text NOT NULL, embedding_model text NOT NULL, embedding vector(64) NOT NULL
);
CREATE INDEX IF NOT EXISTS chunks_version ON chunks(knowledge_version);
CREATE TABLE IF NOT EXISTS spend_ledger (
  id uuid PRIMARY KEY, run_id uuid UNIQUE REFERENCES runs(id) ON DELETE SET NULL,
  kind text NOT NULL, reserved_usd numeric(12,6) NOT NULL, actual_usd numeric(12,6),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rate_events (
  id uuid PRIMARY KEY, subject_hash text NOT NULL, operation text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS rate_events_lookup ON rate_events(subject_hash,operation,created_at DESC);

ALTER TABLE runs ADD COLUMN IF NOT EXISTS lease_until timestamptz;
UPDATE runs SET lease_until=now()-interval '1 second' WHERE state IN ('pending','running') AND lease_until IS NULL;
