-- Keep tombstones long enough to clean a checkpoint written by a cancelling run.
ALTER TABLE checkpoint_cleanup ADD COLUMN cleaned_at timestamptz;
