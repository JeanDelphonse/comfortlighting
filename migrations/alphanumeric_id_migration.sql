-- =============================================================================
-- ComfortLighting Alphanumeric Primary Key Migration
-- Version: 1.0  |  Date: 2026-03-18
-- Run via migrations/populate_new_ids.py (Python migration runner)
-- DO NOT run directly in MySQL client — use the Python runner for error
-- handling, logging, and rollback capability.
-- =============================================================================

-- =============================================================================
-- STEP 3: Add new_id VARCHAR(17) columns to all tables
-- Values are populated by populate_new_ids.py (not by SQL)
-- =============================================================================

ALTER TABLE users              ADD COLUMN new_id VARCHAR(17) NULL AFTER id;
ALTER TABLE leads              ADD COLUMN new_id VARCHAR(17) NULL AFTER id;
ALTER TABLE proposals          ADD COLUMN new_id VARCHAR(17) NULL AFTER id;
ALTER TABLE contracts          ADD COLUMN new_id VARCHAR(17) NULL AFTER id;
ALTER TABLE contract_versions  ADD COLUMN new_id VARCHAR(17) NULL AFTER id;
ALTER TABLE clause_templates   ADD COLUMN new_id VARCHAR(17) NULL AFTER id;
ALTER TABLE lead_activities    ADD COLUMN new_id VARCHAR(17) NULL AFTER id;
ALTER TABLE expense_categories ADD COLUMN new_id VARCHAR(17) NULL AFTER id;
ALTER TABLE lead_stage_history ADD COLUMN new_id VARCHAR(17) NULL AFTER id;
ALTER TABLE agent_research_log ADD COLUMN new_id VARCHAR(17) NULL AFTER id;
ALTER TABLE system_config      ADD COLUMN new_id VARCHAR(17) NULL AFTER id;

-- (Run populate_new_ids.py here to fill new_id values for all rows)

-- =============================================================================
-- STEP 4: Add and populate FK mapping columns
-- Executed after new_id values are populated in parent tables
-- =============================================================================

-- leads FK columns
ALTER TABLE leads ADD COLUMN assigned_user_id_new VARCHAR(17) NULL;
UPDATE leads l JOIN users u ON l.assigned_user_id = u.id
  SET l.assigned_user_id_new = u.new_id
  WHERE l.assigned_user_id IS NOT NULL;

-- proposals FK columns
ALTER TABLE proposals ADD COLUMN lead_id_new VARCHAR(17) NULL;
UPDATE proposals p JOIN leads l ON p.lead_id = l.id
  SET p.lead_id_new = l.new_id;

-- contracts FK columns
ALTER TABLE contracts ADD COLUMN lead_id_new VARCHAR(17) NULL;
UPDATE contracts c JOIN leads l ON c.lead_id = l.id
  SET c.lead_id_new = l.new_id;

-- contracts.approved_by: currently stores username, migrate to user FK
ALTER TABLE contracts ADD COLUMN approved_by_new VARCHAR(17) NULL;
UPDATE contracts c JOIN users u ON c.approved_by = u.username
  SET c.approved_by_new = u.new_id
  WHERE c.approved_by IS NOT NULL;

-- contract_versions FK columns
ALTER TABLE contract_versions ADD COLUMN contract_id_new VARCHAR(17) NULL;
UPDATE contract_versions cv JOIN contracts c ON cv.contract_id = c.id
  SET cv.contract_id_new = c.new_id;

-- lead_activities FK columns
ALTER TABLE lead_activities ADD COLUMN lead_id_new VARCHAR(17) NULL;
UPDATE lead_activities la JOIN leads l ON la.lead_id = l.id
  SET la.lead_id_new = l.new_id;

ALTER TABLE lead_activities ADD COLUMN user_id_new VARCHAR(17) NULL;
UPDATE lead_activities la JOIN users u ON la.user_id = u.id
  SET la.user_id_new = u.new_id;

ALTER TABLE lead_activities ADD COLUMN category_id_new VARCHAR(17) NULL;
UPDATE lead_activities la JOIN expense_categories ec ON la.category_id = ec.id
  SET la.category_id_new = ec.new_id;

ALTER TABLE lead_activities ADD COLUMN subcategory_id_new VARCHAR(17) NULL;
UPDATE lead_activities la JOIN expense_categories ec ON la.subcategory_id = ec.id
  SET la.subcategory_id_new = ec.new_id
  WHERE la.subcategory_id IS NOT NULL;

-- expense_categories self-referencing FK
ALTER TABLE expense_categories ADD COLUMN parent_id_new VARCHAR(17) NULL;
UPDATE expense_categories ec_child
  JOIN expense_categories ec_parent ON ec_child.parent_id = ec_parent.id
  SET ec_child.parent_id_new = ec_parent.new_id
  WHERE ec_child.parent_id IS NOT NULL;

-- lead_stage_history FK columns
ALTER TABLE lead_stage_history ADD COLUMN lead_id_new VARCHAR(17) NULL;
UPDATE lead_stage_history lsh JOIN leads l ON lsh.lead_id = l.id
  SET lsh.lead_id_new = l.new_id;

ALTER TABLE lead_stage_history ADD COLUMN changed_by_id_new VARCHAR(17) NULL;
UPDATE lead_stage_history lsh JOIN users u ON lsh.changed_by_id = u.id
  SET lsh.changed_by_id_new = u.new_id
  WHERE lsh.changed_by_id IS NOT NULL;

-- agent_research_log FK columns
ALTER TABLE agent_research_log ADD COLUMN lead_id_new VARCHAR(17) NULL;
UPDATE agent_research_log arl JOIN leads l ON arl.lead_id = l.id
  SET arl.lead_id_new = l.new_id
  WHERE arl.lead_id IS NOT NULL;

ALTER TABLE agent_research_log ADD COLUMN user_id_new VARCHAR(17) NULL;
UPDATE agent_research_log arl JOIN users u ON arl.user_id = u.id
  SET arl.user_id_new = u.new_id;

-- Verify: no NULL new FK values where source was NOT NULL
-- SELECT COUNT(*) FROM leads WHERE assigned_user_id IS NOT NULL AND assigned_user_id_new IS NULL;
-- SELECT COUNT(*) FROM lead_activities WHERE lead_id_new IS NULL;
-- (Should all be 0 — investigate and fix before proceeding)


-- =============================================================================
-- STEP 5: Drop old FK constraints (child tables first, then parent tables)
-- Constraint names may vary — check SHOW CREATE TABLE to confirm names
-- =============================================================================

-- contract_versions
ALTER TABLE contract_versions DROP FOREIGN KEY fk_cv_contract;
-- lead_activities
ALTER TABLE lead_activities DROP FOREIGN KEY fk_la_lead;
ALTER TABLE lead_activities DROP FOREIGN KEY fk_la_user;
ALTER TABLE lead_activities DROP FOREIGN KEY fk_la_category;
ALTER TABLE lead_activities DROP FOREIGN KEY fk_la_subcategory;
-- lead_stage_history
ALTER TABLE lead_stage_history DROP FOREIGN KEY fk_lsh_lead;
ALTER TABLE lead_stage_history DROP FOREIGN KEY fk_lsh_changed_by;
-- proposals
ALTER TABLE proposals DROP FOREIGN KEY fk_prop_lead;
-- contracts
ALTER TABLE contracts DROP FOREIGN KEY fk_con_lead;
ALTER TABLE contracts DROP FOREIGN KEY fk_con_approved_by;
-- leads
ALTER TABLE leads DROP FOREIGN KEY fk_lead_assigned_user;
-- agent_research_log
ALTER TABLE agent_research_log DROP FOREIGN KEY fk_arl_lead;
ALTER TABLE agent_research_log DROP FOREIGN KEY fk_arl_user;
-- expense_categories self-ref
ALTER TABLE expense_categories DROP FOREIGN KEY fk_ec_parent;


-- =============================================================================
-- STEP 6: Rename columns — parent tables first, then child tables
-- Pattern: add id2 alias, drop old id, rename id2 to id
-- =============================================================================

-- ── users ────────────────────────────────────────────────────────────────────
ALTER TABLE users DROP PRIMARY KEY;
ALTER TABLE users RENAME COLUMN new_id TO id2;
ALTER TABLE users DROP COLUMN id;
ALTER TABLE users RENAME COLUMN id2 TO id;
ALTER TABLE users ADD PRIMARY KEY (id);
ALTER TABLE users MODIFY COLUMN id VARCHAR(17) NOT NULL;

-- ── expense_categories (self-ref FK; do parent column before child) ──────────
ALTER TABLE expense_categories DROP PRIMARY KEY;
ALTER TABLE expense_categories RENAME COLUMN new_id TO id2;
ALTER TABLE expense_categories DROP COLUMN id;
ALTER TABLE expense_categories RENAME COLUMN id2 TO id;
ALTER TABLE expense_categories ADD PRIMARY KEY (id);
ALTER TABLE expense_categories MODIFY COLUMN id VARCHAR(17) NOT NULL;
-- rename self-ref FK column
ALTER TABLE expense_categories DROP COLUMN parent_id;
ALTER TABLE expense_categories RENAME COLUMN parent_id_new TO parent_id;
ALTER TABLE expense_categories MODIFY COLUMN parent_id VARCHAR(17) NULL;

-- ── system_config ─────────────────────────────────────────────────────────────
ALTER TABLE system_config DROP PRIMARY KEY;
ALTER TABLE system_config RENAME COLUMN new_id TO id2;
ALTER TABLE system_config DROP COLUMN id;
ALTER TABLE system_config RENAME COLUMN id2 TO id;
ALTER TABLE system_config ADD PRIMARY KEY (id);
ALTER TABLE system_config MODIFY COLUMN id VARCHAR(17) NOT NULL;

-- ── clause_templates ──────────────────────────────────────────────────────────
ALTER TABLE clause_templates DROP PRIMARY KEY;
ALTER TABLE clause_templates RENAME COLUMN new_id TO id2;
ALTER TABLE clause_templates DROP COLUMN id;
ALTER TABLE clause_templates RENAME COLUMN id2 TO id;
ALTER TABLE clause_templates ADD PRIMARY KEY (id);
ALTER TABLE clause_templates MODIFY COLUMN id VARCHAR(17) NOT NULL;

-- ── leads ─────────────────────────────────────────────────────────────────────
ALTER TABLE leads DROP PRIMARY KEY;
ALTER TABLE leads RENAME COLUMN new_id TO id2;
ALTER TABLE leads DROP COLUMN id;
ALTER TABLE leads RENAME COLUMN id2 TO id;
ALTER TABLE leads ADD PRIMARY KEY (id);
ALTER TABLE leads MODIFY COLUMN id VARCHAR(17) NOT NULL;
-- FK column: assigned_user_id
ALTER TABLE leads DROP COLUMN assigned_user_id;
ALTER TABLE leads RENAME COLUMN assigned_user_id_new TO assigned_user_id;
ALTER TABLE leads MODIFY COLUMN assigned_user_id VARCHAR(17) NULL;

-- ── proposals ─────────────────────────────────────────────────────────────────
ALTER TABLE proposals DROP PRIMARY KEY;
ALTER TABLE proposals RENAME COLUMN new_id TO id2;
ALTER TABLE proposals DROP COLUMN id;
ALTER TABLE proposals RENAME COLUMN id2 TO id;
ALTER TABLE proposals ADD PRIMARY KEY (id);
ALTER TABLE proposals MODIFY COLUMN id VARCHAR(17) NOT NULL;
-- FK column: lead_id
ALTER TABLE proposals DROP COLUMN lead_id;
ALTER TABLE proposals RENAME COLUMN lead_id_new TO lead_id;
ALTER TABLE proposals MODIFY COLUMN lead_id VARCHAR(17) NOT NULL;

-- ── contracts ─────────────────────────────────────────────────────────────────
ALTER TABLE contracts DROP PRIMARY KEY;
ALTER TABLE contracts RENAME COLUMN new_id TO id2;
ALTER TABLE contracts DROP COLUMN id;
ALTER TABLE contracts RENAME COLUMN id2 TO id;
ALTER TABLE contracts ADD PRIMARY KEY (id);
ALTER TABLE contracts MODIFY COLUMN id VARCHAR(17) NOT NULL;
-- FK column: lead_id
ALTER TABLE contracts DROP COLUMN lead_id;
ALTER TABLE contracts RENAME COLUMN lead_id_new TO lead_id;
ALTER TABLE contracts MODIFY COLUMN lead_id VARCHAR(17) NOT NULL;
-- FK column: approved_by (was VARCHAR(100) username, now VARCHAR(17) user FK)
ALTER TABLE contracts DROP COLUMN approved_by;
ALTER TABLE contracts RENAME COLUMN approved_by_new TO approved_by;
ALTER TABLE contracts MODIFY COLUMN approved_by VARCHAR(17) NULL;

-- ── contract_versions ─────────────────────────────────────────────────────────
ALTER TABLE contract_versions DROP PRIMARY KEY;
ALTER TABLE contract_versions RENAME COLUMN new_id TO id2;
ALTER TABLE contract_versions DROP COLUMN id;
ALTER TABLE contract_versions RENAME COLUMN id2 TO id;
ALTER TABLE contract_versions ADD PRIMARY KEY (id);
ALTER TABLE contract_versions MODIFY COLUMN id VARCHAR(17) NOT NULL;
-- FK column: contract_id
ALTER TABLE contract_versions DROP COLUMN contract_id;
ALTER TABLE contract_versions RENAME COLUMN contract_id_new TO contract_id;
ALTER TABLE contract_versions MODIFY COLUMN contract_id VARCHAR(17) NOT NULL;

-- ── lead_activities ───────────────────────────────────────────────────────────
ALTER TABLE lead_activities DROP PRIMARY KEY;
ALTER TABLE lead_activities RENAME COLUMN new_id TO id2;
ALTER TABLE lead_activities DROP COLUMN id;
ALTER TABLE lead_activities RENAME COLUMN id2 TO id;
ALTER TABLE lead_activities ADD PRIMARY KEY (id);
ALTER TABLE lead_activities MODIFY COLUMN id VARCHAR(17) NOT NULL;
-- FK columns
ALTER TABLE lead_activities DROP COLUMN lead_id;
ALTER TABLE lead_activities RENAME COLUMN lead_id_new TO lead_id;
ALTER TABLE lead_activities MODIFY COLUMN lead_id VARCHAR(17) NOT NULL;
ALTER TABLE lead_activities DROP COLUMN user_id;
ALTER TABLE lead_activities RENAME COLUMN user_id_new TO user_id;
ALTER TABLE lead_activities MODIFY COLUMN user_id VARCHAR(17) NOT NULL;
ALTER TABLE lead_activities DROP COLUMN category_id;
ALTER TABLE lead_activities RENAME COLUMN category_id_new TO category_id;
ALTER TABLE lead_activities MODIFY COLUMN category_id VARCHAR(17) NOT NULL;
ALTER TABLE lead_activities DROP COLUMN subcategory_id;
ALTER TABLE lead_activities RENAME COLUMN subcategory_id_new TO subcategory_id;
ALTER TABLE lead_activities MODIFY COLUMN subcategory_id VARCHAR(17) NULL;

-- ── lead_stage_history ────────────────────────────────────────────────────────
ALTER TABLE lead_stage_history DROP PRIMARY KEY;
ALTER TABLE lead_stage_history RENAME COLUMN new_id TO id2;
ALTER TABLE lead_stage_history DROP COLUMN id;
ALTER TABLE lead_stage_history RENAME COLUMN id2 TO id;
ALTER TABLE lead_stage_history ADD PRIMARY KEY (id);
ALTER TABLE lead_stage_history MODIFY COLUMN id VARCHAR(17) NOT NULL;
-- FK columns
ALTER TABLE lead_stage_history DROP COLUMN lead_id;
ALTER TABLE lead_stage_history RENAME COLUMN lead_id_new TO lead_id;
ALTER TABLE lead_stage_history MODIFY COLUMN lead_id VARCHAR(17) NOT NULL;
ALTER TABLE lead_stage_history DROP COLUMN changed_by_id;
ALTER TABLE lead_stage_history RENAME COLUMN changed_by_id_new TO changed_by_id;
ALTER TABLE lead_stage_history MODIFY COLUMN changed_by_id VARCHAR(17) NULL;

-- ── agent_research_log ────────────────────────────────────────────────────────
ALTER TABLE agent_research_log DROP PRIMARY KEY;
ALTER TABLE agent_research_log RENAME COLUMN new_id TO id2;
ALTER TABLE agent_research_log DROP COLUMN id;
ALTER TABLE agent_research_log RENAME COLUMN id2 TO id;
ALTER TABLE agent_research_log ADD PRIMARY KEY (id);
ALTER TABLE agent_research_log MODIFY COLUMN id VARCHAR(17) NOT NULL;
-- FK columns
ALTER TABLE agent_research_log DROP COLUMN lead_id;
ALTER TABLE agent_research_log RENAME COLUMN lead_id_new TO lead_id;
ALTER TABLE agent_research_log MODIFY COLUMN lead_id VARCHAR(17) NULL;
ALTER TABLE agent_research_log DROP COLUMN user_id;
ALTER TABLE agent_research_log RENAME COLUMN user_id_new TO user_id;
ALTER TABLE agent_research_log MODIFY COLUMN user_id VARCHAR(17) NOT NULL;


-- =============================================================================
-- STEP 7: Restore FK constraints
-- =============================================================================

-- leads.assigned_user_id → users.id
ALTER TABLE leads
  ADD CONSTRAINT fk_lead_assigned_user
  FOREIGN KEY (assigned_user_id) REFERENCES users(id)
  ON DELETE SET NULL ON UPDATE CASCADE;

-- proposals.lead_id → leads.id
ALTER TABLE proposals
  ADD CONSTRAINT fk_prop_lead
  FOREIGN KEY (lead_id) REFERENCES leads(id)
  ON DELETE CASCADE;

-- contracts.lead_id → leads.id
ALTER TABLE contracts
  ADD CONSTRAINT fk_con_lead
  FOREIGN KEY (lead_id) REFERENCES leads(id)
  ON DELETE CASCADE;

-- contracts.approved_by → users.id
ALTER TABLE contracts
  ADD CONSTRAINT fk_con_approved_by
  FOREIGN KEY (approved_by) REFERENCES users(id)
  ON DELETE SET NULL;

-- contract_versions.contract_id → contracts.id
ALTER TABLE contract_versions
  ADD CONSTRAINT fk_cv_contract
  FOREIGN KEY (contract_id) REFERENCES contracts(id)
  ON DELETE CASCADE;

-- expense_categories.parent_id → expense_categories.id (self-ref)
ALTER TABLE expense_categories
  ADD CONSTRAINT fk_ec_parent
  FOREIGN KEY (parent_id) REFERENCES expense_categories(id)
  ON DELETE SET NULL;

-- lead_activities.lead_id → leads.id
ALTER TABLE lead_activities
  ADD CONSTRAINT fk_la_lead
  FOREIGN KEY (lead_id) REFERENCES leads(id)
  ON DELETE CASCADE;

-- lead_activities.user_id → users.id
ALTER TABLE lead_activities
  ADD CONSTRAINT fk_la_user
  FOREIGN KEY (user_id) REFERENCES users(id)
  ON DELETE RESTRICT;

-- lead_activities.category_id → expense_categories.id
ALTER TABLE lead_activities
  ADD CONSTRAINT fk_la_category
  FOREIGN KEY (category_id) REFERENCES expense_categories(id);

-- lead_activities.subcategory_id → expense_categories.id
ALTER TABLE lead_activities
  ADD CONSTRAINT fk_la_subcategory
  FOREIGN KEY (subcategory_id) REFERENCES expense_categories(id);

-- lead_stage_history.lead_id → leads.id
ALTER TABLE lead_stage_history
  ADD CONSTRAINT fk_lsh_lead
  FOREIGN KEY (lead_id) REFERENCES leads(id)
  ON DELETE CASCADE;

-- lead_stage_history.changed_by_id → users.id
ALTER TABLE lead_stage_history
  ADD CONSTRAINT fk_lsh_changed_by
  FOREIGN KEY (changed_by_id) REFERENCES users(id)
  ON DELETE SET NULL;

-- agent_research_log.lead_id → leads.id
ALTER TABLE agent_research_log
  ADD CONSTRAINT fk_arl_lead
  FOREIGN KEY (lead_id) REFERENCES leads(id)
  ON DELETE SET NULL;

-- agent_research_log.user_id → users.id
ALTER TABLE agent_research_log
  ADD CONSTRAINT fk_arl_user
  FOREIGN KEY (user_id) REFERENCES users(id)
  ON DELETE RESTRICT;


-- =============================================================================
-- STEP 8: Integrity verification queries (run manually, expect all zeros)
-- =============================================================================

-- Row count verification (compare with pre-migration counts)
SELECT 'users'              AS tbl, COUNT(*) AS rows FROM users
UNION ALL SELECT 'leads',              COUNT(*) FROM leads
UNION ALL SELECT 'proposals',          COUNT(*) FROM proposals
UNION ALL SELECT 'contracts',          COUNT(*) FROM contracts
UNION ALL SELECT 'contract_versions',  COUNT(*) FROM contract_versions
UNION ALL SELECT 'clause_templates',   COUNT(*) FROM clause_templates
UNION ALL SELECT 'lead_activities',    COUNT(*) FROM lead_activities
UNION ALL SELECT 'expense_categories', COUNT(*) FROM expense_categories
UNION ALL SELECT 'lead_stage_history', COUNT(*) FROM lead_stage_history
UNION ALL SELECT 'agent_research_log', COUNT(*) FROM agent_research_log
UNION ALL SELECT 'system_config',      COUNT(*) FROM system_config;

-- FK orphan checks (should all return 0 rows)
SELECT COUNT(*) AS orphan_leads_users
  FROM leads WHERE assigned_user_id IS NOT NULL
    AND assigned_user_id NOT IN (SELECT id FROM users);

SELECT COUNT(*) AS orphan_proposals_leads
  FROM proposals WHERE lead_id NOT IN (SELECT id FROM leads);

SELECT COUNT(*) AS orphan_la_leads
  FROM lead_activities WHERE lead_id NOT IN (SELECT id FROM leads);

SELECT COUNT(*) AS orphan_la_users
  FROM lead_activities WHERE user_id NOT IN (SELECT id FROM users);

-- Note: Receipt files are stored in uploads/receipts/{lead_id}/ directories.
-- After migration, existing receipt directories use old integer lead IDs.
-- Move them manually: rename uploads/receipts/47/ to uploads/receipts/LED-YYMMDD-XXXXXX/
-- where LED-YYMMDD-XXXXXX is the new ID assigned to the lead that had integer id=47.
