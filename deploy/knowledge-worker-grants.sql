-- Run as the assistant database migration owner after reviewed migrations.
-- Cluster provisioning creates this login; this script never creates roles/secrets.
DO $$ BEGIN
  IF current_database()<>'portfolio_assistant' OR NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname='portfolio_api_worker'
      AND NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls OR rolinherit)
      AND NOT EXISTS (SELECT 1 FROM pg_auth_members WHERE member=pg_roles.oid)
  ) THEN
    RAISE EXCEPTION 'restricted project worker identity is required';
  END IF;
END $$;
GRANT USAGE ON SCHEMA public TO portfolio_api_worker;
GRANT SELECT ON schema_migrations TO portfolio_api_worker;
GRANT SELECT,INSERT,UPDATE,DELETE ON knowledge_versions,chunks,source_files TO portfolio_api_worker;
GRANT SELECT,INSERT,UPDATE ON knowledge_watch TO portfolio_api_worker;
GRANT SELECT,INSERT ON public_embedding_cache TO portfolio_api_worker;
GRANT SELECT,INSERT,UPDATE ON spend_ledger TO portfolio_api_worker;
