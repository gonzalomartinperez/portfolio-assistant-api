-- Unlinked operational facts survive conversation deletion; never store content/owner IDs.
CREATE TABLE operational_executions (
    trace_id text PRIMARY KEY CHECK (trace_id ~ '^[a-f0-9]{32}$'),
    started_at timestamptz NOT NULL,
    outcome text NOT NULL CHECK (outcome IN ('completed','cancelled','failed')),
    duration_ms double precision NOT NULL CHECK (duration_ms>=0 AND duration_ms<=1000000),
    first_token_ms double precision CHECK (first_token_ms>=0 AND first_token_ms<=1000000),
    stages jsonb NOT NULL CHECK (jsonb_typeof(stages)='array' AND jsonb_array_length(stages)<=32),
    error_code text CHECK (error_code IN ('provider_unavailable','generation_failed','budget_exhausted','knowledge_updating','dependency_unavailable','other')),
    sampled boolean NOT NULL DEFAULT false
);
CREATE INDEX operational_executions_started ON operational_executions(started_at);
ALTER TABLE spend_ledger ADD COLUMN input_tokens bigint CHECK (input_tokens>=0);
ALTER TABLE spend_ledger ADD COLUMN output_tokens bigint CHECK (output_tokens>=0);
