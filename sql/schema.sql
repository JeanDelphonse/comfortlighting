-- ComfortLighting Lead Inventory Management System
-- Database: comfortlighting | User: comfort | Host: localhost
-- Engine: InnoDB | Charset: utf8mb4 | Collation: utf8mb4_unicode_ci

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- --------------------------------------------------------
-- Users table
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `id`         INT AUTO_INCREMENT PRIMARY KEY,
  `username`   VARCHAR(100)  NOT NULL UNIQUE,
  `email`      VARCHAR(255)  NOT NULL UNIQUE,
  `password`   VARCHAR(255)  NOT NULL COMMENT 'bcrypt hash',
  `role`       ENUM('admin','sales','legal') NOT NULL DEFAULT 'sales',
  `active`     TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Leads table
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `leads` (
  `id`                     INT AUTO_INCREMENT PRIMARY KEY,
  `created_at`             DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`             DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `company_name`           VARCHAR(255) NOT NULL,
  `action`                 VARCHAR(100) NOT NULL,
  `contact`                VARCHAR(255) NOT NULL,
  `address`                TEXT,
  `number`                 VARCHAR(30)  NOT NULL,
  `email`                  VARCHAR(255) NOT NULL,
  `notes`                  TEXT,
  `assigned_user_id`        INT NULL DEFAULT NULL,
  `sq_ft`                  INT,
  `targets`                TEXT,
  `potential`              DECIMAL(12,2),
  `progress`               VARCHAR(100),
  `expected`               DATE,
  `roi`                    DECIMAL(5,2),
  `annual_sales_locations`  TEXT,
  INDEX `idx_company_name`         (`company_name`),
  INDEX `idx_action`               (`action`),
  INDEX `idx_progress`             (`progress`),
  INDEX `idx_expected`             (`expected`),
  INDEX `idx_leads_assigned_user`  (`assigned_user_id`),
  CONSTRAINT `fk_leads_assigned_user`
      FOREIGN KEY (`assigned_user_id`) REFERENCES `users`(`id`)
      ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Proposals table
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `proposals` (
  `id`               INT AUTO_INCREMENT PRIMARY KEY,
  `lead_id`          INT NOT NULL UNIQUE,
  `raw_llm_text`     TEXT,
  `greeting`         TEXT,
  `problem`          TEXT,
  `solution`         TEXT,
  `value_prop`       TEXT,
  `next_step`        TEXT,
  `edited_by`        VARCHAR(100),
  `proposal_sent`    TINYINT(1) NOT NULL DEFAULT 0,
  `sent_at`          DATETIME,
  `pdf_generated_at` DATETIME,
  `created_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_proposals_lead` FOREIGN KEY (`lead_id`) REFERENCES `leads`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Contracts table
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `contracts` (
  `id`                      INT AUTO_INCREMENT PRIMARY KEY,
  `lead_id`                 INT NOT NULL UNIQUE,
  `version`                 INT NOT NULL DEFAULT 1,
  `raw_llm_text`            LONGTEXT,
  `section_parties`         TEXT,
  `section_recitals`        TEXT,
  `section_scope`           TEXT,
  `section_compensation`    TEXT,
  `section_timeline`        TEXT,
  `section_warranties`      TEXT,
  `section_performance`     TEXT,
  `section_indemnification` TEXT,
  `section_liability`       TEXT,
  `section_termination`     TEXT,
  `section_dispute`         TEXT,
  `section_governing_law`   TEXT,
  `section_notices`         TEXT,
  `section_entire_agreement` TEXT,
  `section_signatures`      TEXT,
  `generated_by`            VARCHAR(100) NOT NULL,
  `edited_by`               VARCHAR(100),
  `approved`                TINYINT(1) NOT NULL DEFAULT 0,
  `approved_by`             VARCHAR(100),
  `approved_at`             DATETIME,
  `contract_sent`           TINYINT(1) NOT NULL DEFAULT 0,
  `sent_by`                 VARCHAR(100),
  `sent_at`                 DATETIME,
  `pdf_exported_at`         DATETIME,
  `created_at`              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_contracts_lead` FOREIGN KEY (`lead_id`) REFERENCES `leads`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Contract versions table
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `contract_versions` (
  `id`                  INT AUTO_INCREMENT PRIMARY KEY,
  `contract_id`         INT NOT NULL,
  `version_number`      INT NOT NULL,
  `full_text_snapshot`  LONGTEXT NOT NULL,
  `saved_by`            VARCHAR(100) NOT NULL,
  `saved_at`            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_contract_versions_contract` FOREIGN KEY (`contract_id`) REFERENCES `contracts`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Clause templates table
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `clause_templates` (
  `id`                INT AUTO_INCREMENT PRIMARY KEY,
  `clause_key`        VARCHAR(100) NOT NULL,
  `clause_text`       LONGTEXT NOT NULL,
  `version`           INT NOT NULL DEFAULT 1,
  `active`            TINYINT(1) NOT NULL DEFAULT 1,
  `approved_by_legal` VARCHAR(100),
  `created_at`        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_clause_key` (`clause_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── system_config ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `system_config` (
  `id`           INT AUTO_INCREMENT PRIMARY KEY,
  `config_key`   VARCHAR(100) NOT NULL UNIQUE,
  `config_value` VARCHAR(500) NOT NULL,
  `updated_by`   VARCHAR(100) NULL,
  `updated_at`   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── expense_categories ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `expense_categories` (
  `id`                     INT AUTO_INCREMENT PRIMARY KEY,
  `parent_id`              INT NULL DEFAULT NULL,
  `name`                   VARCHAR(100) NOT NULL,
  `requires_attendees`     TINYINT(1) NOT NULL DEFAULT 0,
  `requires_receipt_above` DECIMAL(10,2) NULL DEFAULT NULL,
  `is_mileage`             TINYINT(1) NOT NULL DEFAULT 0,
  `active`                 TINYINT(1) NOT NULL DEFAULT 1,
  `sort_order`             INT NOT NULL DEFAULT 0,
  CONSTRAINT `fk_expense_categories_parent`
      FOREIGN KEY (`parent_id`) REFERENCES `expense_categories`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── lead_activities ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `lead_activities` (
  `id`               INT AUTO_INCREMENT PRIMARY KEY,
  `lead_id`          INT NOT NULL,
  `user_id`          INT NOT NULL,
  `activity_date`    DATE NOT NULL,
  `category_id`      INT NOT NULL,
  `subcategory_id`   INT NULL,
  `activity_type`    VARCHAR(50) NOT NULL,
  `amount`           DECIMAL(10,2) NULL,
  `miles_driven`     DECIMAL(7,1) NULL,
  `mileage_rate`     DECIMAL(5,4) NULL,
  `destination`      VARCHAR(255) NOT NULL,
  `purpose`          VARCHAR(500) NOT NULL,
  `attendees`        TEXT NULL,
  `attendee_count`   INT NULL,
  `outcome`          VARCHAR(50) NOT NULL,
  `next_action`      VARCHAR(500) NULL,
  `payment_method`   VARCHAR(50) NOT NULL,
  `reimbursable`     TINYINT(1) NOT NULL DEFAULT 0,
  `receipt_attached` TINYINT(1) NOT NULL DEFAULT 0,
  `receipt_filename` VARCHAR(255) NULL,
  `notes`            TEXT NULL,
  `status`           ENUM('Draft','Submitted','Approved','Rejected','Reimbursed')
                     NOT NULL DEFAULT 'Draft',
  `submitted_at`     DATETIME NULL,
  `reviewed_by`      VARCHAR(100) NULL,
  `reviewed_at`      DATETIME NULL,
  `review_notes`     TEXT NULL,
  `reimbursed_at`    DATETIME NULL,
  `created_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_lead_activities_lead_id` (`lead_id`),
  INDEX `idx_lead_activities_user_id` (`user_id`),
  INDEX `idx_lead_activities_date`    (`activity_date`),
  INDEX `idx_lead_activities_status`  (`status`),
  CONSTRAINT `fk_lead_activities_lead`
      FOREIGN KEY (`lead_id`) REFERENCES `leads`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_lead_activities_user`
      FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- --------------------------------------------------------
-- Seed: default admin account (password set separately)
-- After running this schema, set the password via:
--   python set_admin_password.py admin <your_password>
-- --------------------------------------------------------
INSERT INTO `users` (`username`, `email`, `password`, `role`) VALUES
('admin', 'admin@comfortlighting.net', 'UNSET', 'admin');

-- --------------------------------------------------------
-- Seed: sample leads for testing
-- --------------------------------------------------------
INSERT INTO `leads`
  (`company_name`,`action`,`contact`,`address`,`number`,`email`,`notes`,`sq_ft`,`targets`,`potential`,`progress`,`expected`,`roi`,`annual_sales_locations`)
VALUES
('Acme Pharma Labs','Contacted','Jane Smith – Facilities Mgr','123 Research Blvd, Boston MA 02115','617-555-0101','jsmith@acmepharma.com','Initial call on 2026-03-01. Interested in LED retrofit.',45000,'Clean rooms, corridors',85000.00,'Qualified','2026-06-30',18.50,'$12M annual revenue. 2 other MA locations.'),
('Metro Cold Storage','Quote Requested','Bob Torres – VP Ops','88 Warehouse Way, Chicago IL 60601','312-555-0202','btorres@metrocold.com','Quote requested for freezer aisles. Follow up sent.',120000,'Freezer aisles, loading docks',210000.00,'Proposal','2026-05-15',22.00,'$30M revenue. 4 Midwest facilities.'),
('Summit Auto Showroom','New Lead','Alice Park – GM','501 Auto Row, Dallas TX 75201','214-555-0303','apark@summitauto.com','Referred by vendor contact.',18000,'Showroom floor, service bays',47500.00,'Prospect','2026-08-01',15.00,NULL);
