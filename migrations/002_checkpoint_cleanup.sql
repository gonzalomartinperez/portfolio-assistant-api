-- Durable cleanup survives a checkpoint outage after deleting an anonymous owner.
CREATE TABLE checkpoint_cleanup (
    thread_id text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now()
);
