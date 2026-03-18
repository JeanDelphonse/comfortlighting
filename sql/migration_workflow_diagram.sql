-- Migration: Lead Workflow Diagram
-- Database: comfortlighting
-- Run this on a fresh install. On existing installs that already ran
-- an earlier version of this migration, run only the ALTER TABLE at the
-- bottom of this file.

-- Add columns to leads table for workflow diagram
ALTER TABLE leads
  ADD COLUMN IF NOT EXISTS previous_progress VARCHAR(100) NULL AFTER agent_research_run_id,
  ADD COLUMN IF NOT EXISTS stage_changed_at  DATETIME    NULL AFTER previous_progress;

CREATE INDEX IF NOT EXISTS idx_leads_stage_changed ON leads(stage_changed_at);

-- Set initial stage_changed_at for existing leads based on updated_at
UPDATE leads SET stage_changed_at = updated_at WHERE stage_changed_at IS NULL;

-- Create lead_stage_history table
CREATE TABLE IF NOT EXISTS lead_stage_history (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  lead_id       INT          NOT NULL,
  from_stage    VARCHAR(100) NULL,
  to_stage      VARCHAR(100) NOT NULL,
  changed_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  changed_by_id INT          NULL,
  reason        VARCHAR(500) NULL,
  days_in_stage DECIMAL(7,1) NULL,
  CONSTRAINT fk_lsh_lead FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE,
  CONSTRAINT fk_lsh_user FOREIGN KEY (changed_by_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_lsh_lead       (lead_id),
  INDEX idx_lsh_changed_at (changed_at)
);

-- If upgrading from an earlier version of this migration that created the
-- table without days_in_stage, run:
-- ALTER TABLE lead_stage_history ADD COLUMN IF NOT EXISTS days_in_stage DECIMAL(7,1) NULL;
