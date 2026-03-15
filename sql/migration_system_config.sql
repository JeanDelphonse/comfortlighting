-- ComfortLighting — system_config table
-- Run this BEFORE migration_create_lead_activities.sql on existing databases.

CREATE TABLE IF NOT EXISTS `system_config` (
  `id`           INT AUTO_INCREMENT PRIMARY KEY,
  `config_key`   VARCHAR(100) NOT NULL UNIQUE,
  `config_value` VARCHAR(500) NOT NULL,
  `updated_by`   VARCHAR(100) NULL,
  `updated_at`   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- IRS standard mileage rate for 2026 (update annually)
INSERT INTO `system_config` (`config_key`, `config_value`, `updated_by`)
VALUES ('irs_mileage_rate', '0.6700', 'system')
ON DUPLICATE KEY UPDATE `config_value` = VALUES(`config_value`);
