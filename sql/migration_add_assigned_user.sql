-- ComfortLighting — Lead User Assignment Migration
-- Run once on existing databases before deploying this feature.
-- Safe to run on fresh installs too (column does not exist yet).

ALTER TABLE leads
  ADD COLUMN assigned_user_id INT NULL DEFAULT NULL
      AFTER notes,
  ADD CONSTRAINT fk_leads_assigned_user
      FOREIGN KEY (assigned_user_id)
      REFERENCES users (id)
      ON DELETE SET NULL
      ON UPDATE CASCADE,
  ADD INDEX idx_leads_assigned_user (assigned_user_id);

-- Verify
DESCRIBE leads;
SHOW INDEX FROM leads WHERE Key_name = 'idx_leads_assigned_user';
