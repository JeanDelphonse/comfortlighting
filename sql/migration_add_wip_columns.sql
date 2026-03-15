-- Migration: Add WIP columns to leads table
-- Run this on existing databases to enable the WIP Board feature

ALTER TABLE leads
ADD COLUMN wip TINYINT(1) NOT NULL DEFAULT 0 AFTER annual_sales_locations,
ADD COLUMN wip_since DATETIME NULL AFTER wip;

CREATE INDEX idx_leads_wip ON leads(wip);

-- Note: "In Progress" should already exist in PROGRESS_VALUES if using the latest constants.py
-- If not, add it: ALTER TABLE leads MODIFY progress VARCHAR(100); then manually update any leads as needed