-- =============================================================================
-- EMERGENCY ROLLBACK — ComfortLighting Alphanumeric ID Migration
-- Run ONLY if migration fails mid-execution (Phase 3 or 4)
-- The original integer id columns are unchanged during Steps 3-4,
-- so this rollback is safe at any point before Step 5 (DROP old constraints).
-- =============================================================================

-- Drop new_id columns added in STEP 3
ALTER TABLE users              DROP COLUMN IF EXISTS new_id;
ALTER TABLE leads              DROP COLUMN IF EXISTS new_id;
ALTER TABLE proposals          DROP COLUMN IF EXISTS new_id;
ALTER TABLE contracts          DROP COLUMN IF EXISTS new_id;
ALTER TABLE contract_versions  DROP COLUMN IF EXISTS new_id;
ALTER TABLE clause_templates   DROP COLUMN IF EXISTS new_id;
ALTER TABLE lead_activities    DROP COLUMN IF EXISTS new_id;
ALTER TABLE expense_categories DROP COLUMN IF EXISTS new_id;
ALTER TABLE lead_stage_history DROP COLUMN IF EXISTS new_id;
ALTER TABLE agent_research_log DROP COLUMN IF EXISTS new_id;
ALTER TABLE system_config      DROP COLUMN IF EXISTS new_id;

-- Drop partial FK mapping columns added in STEP 4
ALTER TABLE leads              DROP COLUMN IF EXISTS assigned_user_id_new;
ALTER TABLE proposals          DROP COLUMN IF EXISTS lead_id_new;
ALTER TABLE contracts          DROP COLUMN IF EXISTS lead_id_new;
ALTER TABLE contracts          DROP COLUMN IF EXISTS approved_by_new;
ALTER TABLE contract_versions  DROP COLUMN IF EXISTS contract_id_new;
ALTER TABLE lead_activities    DROP COLUMN IF EXISTS lead_id_new;
ALTER TABLE lead_activities    DROP COLUMN IF EXISTS user_id_new;
ALTER TABLE lead_activities    DROP COLUMN IF EXISTS category_id_new;
ALTER TABLE lead_activities    DROP COLUMN IF EXISTS subcategory_id_new;
ALTER TABLE expense_categories DROP COLUMN IF EXISTS parent_id_new;
ALTER TABLE lead_stage_history DROP COLUMN IF EXISTS lead_id_new;
ALTER TABLE lead_stage_history DROP COLUMN IF EXISTS changed_by_id_new;
ALTER TABLE agent_research_log DROP COLUMN IF EXISTS lead_id_new;
ALTER TABLE agent_research_log DROP COLUMN IF EXISTS user_id_new;

-- Verify original integer PKs are intact
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

-- Row counts should match pre-migration values exactly.
-- If they do, the rollback is complete. Keep maintenance mode on
-- and restore from mysqldump backup if counts do not match.
