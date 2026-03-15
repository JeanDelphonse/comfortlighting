-- Migration: AI Agent Research Log
-- Run after all prior migrations have been applied.

CREATE TABLE agent_research_log (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    lead_id          INT NULL,
    run_id           VARCHAR(36) NOT NULL UNIQUE,
    company_searched VARCHAR(255) NOT NULL,
    user_id          INT NOT NULL,
    fields_populated INT NOT NULL DEFAULT 0,
    fields_not_found INT NOT NULL DEFAULT 0,
    tokens_used      INT NOT NULL DEFAULT 0,
    run_duration_sec DECIMAL(6,2) NOT NULL DEFAULT 0,
    search_count     INT NOT NULL DEFAULT 0,
    urls_fetched     INT NOT NULL DEFAULT 0,
    raw_json         LONGTEXT NOT NULL,
    status           VARCHAR(20) NOT NULL DEFAULT 'success',
    error_message    TEXT NULL,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_arl_lead FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE SET NULL,
    CONSTRAINT fk_arl_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
    INDEX idx_arl_lead    (lead_id),
    INDEX idx_arl_user    (user_id),
    INDEX idx_arl_created (created_at)
);

ALTER TABLE leads
    ADD COLUMN agent_research_run_id VARCHAR(36) NULL DEFAULT NULL AFTER notes,
    ADD INDEX idx_leads_agent_run (agent_research_run_id);

-- Seed ROI model parameters into system_config (safe to re-run: INSERT IGNORE)
INSERT IGNORE INTO system_config (config_key, config_value, updated_by) VALUES
    ('agent_watts_per_sqft',    '2.5',   'migration'),
    ('agent_led_reduction',     '0.60',  'migration'),
    ('agent_hours_per_year',    '4000',  'migration'),
    ('agent_maintenance_factor','0.20',  'migration'),
    ('agent_cost_per_sqft',     '3.50',  'migration'),
    ('agent_rebate_factor',     '0.15',  'migration'),
    ('agent_utility_rate',      '0.13',  'migration'),
    ('agent_daily_token_budget','500000','migration');
