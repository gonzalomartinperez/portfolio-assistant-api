-- Run as the migration owner after every reviewed migration, in the assistant DB.
-- Login passwords are provisioned interactively/outside Git, never in this script.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='assistant_runtime') THEN
    CREATE ROLE assistant_runtime NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='portfolio_api_runtime') THEN
    CREATE ROLE portfolio_api_runtime NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
  END IF;
  IF EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname='portfolio_api_runtime'
      AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls OR rolinherit
        OR EXISTS (SELECT 1 FROM pg_auth_members WHERE member=pg_roles.oid))
  ) THEN
    RAISE EXCEPTION 'restricted project API identity is required';
  END IF;
END $$;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO assistant_runtime, portfolio_api_runtime;
GRANT SELECT ON schema_migrations, checkpoint_migrations, knowledge_versions,
  chunks, source_files, knowledge_watch TO assistant_runtime, portfolio_api_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON sessions, conversations, messages, runs,
  feedback, spend_ledger, rate_events, checkpoint_cleanup, checkpoints,
  checkpoint_blobs, checkpoint_writes TO assistant_runtime, portfolio_api_runtime;

-- Operational facts contain no session/conversation content; API may append/read only.
GRANT SELECT, INSERT ON operational_executions TO assistant_runtime, portfolio_api_runtime;

-- Anonymous bounded product counts; no shared conversation identifiers.
GRANT SELECT, INSERT, DELETE ON product_event_dedupe TO assistant_runtime, portfolio_api_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON product_event_counts TO assistant_runtime, portfolio_api_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON product_daily_counts, product_interaction_counts TO assistant_runtime, portfolio_api_runtime;
GRANT SELECT, INSERT, UPDATE ON product_collection_status TO assistant_runtime, portfolio_api_runtime;
