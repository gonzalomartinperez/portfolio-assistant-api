-- Monthly admission/operations reads must not scan the entire retained ledger.
CREATE INDEX spend_ledger_created_at ON spend_ledger(created_at);
