-- Run as the migration owner after every reviewed migration, in the assistant DB.
-- Login passwords are provisioned interactively/outside Git, never in this script.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='assistant_runtime') THEN
    CREATE ROLE assistant_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
  END IF;
END $$;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO assistant_runtime;
GRANT SELECT ON schema_migrations, checkpoint_migrations, knowledge_versions,
  chunks, source_files, knowledge_watch TO assistant_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON sessions, conversations, messages, runs,
  feedback, spend_ledger, rate_events, checkpoint_cleanup, checkpoints,
  checkpoint_blobs, checkpoint_writes TO assistant_runtime;
