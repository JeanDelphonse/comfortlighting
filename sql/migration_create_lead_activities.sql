-- ComfortLighting — Sales Activity & Expense Tracking Migration
-- Run AFTER migration_system_config.sql on existing databases.
-- Safe on fresh installs.

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
      FOREIGN KEY (`parent_id`) REFERENCES `expense_categories`(`id`)
      ON DELETE SET NULL
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
  INDEX `idx_lead_activities_lead_id`      (`lead_id`),
  INDEX `idx_lead_activities_user_id`      (`user_id`),
  INDEX `idx_lead_activities_date`         (`activity_date`),
  INDEX `idx_lead_activities_status`       (`status`),
  CONSTRAINT `fk_lead_activities_lead`
      FOREIGN KEY (`lead_id`) REFERENCES `leads`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_lead_activities_user`
      FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_lead_activities_category`
      FOREIGN KEY (`category_id`) REFERENCES `expense_categories`(`id`),
  CONSTRAINT `fk_lead_activities_subcategory`
      FOREIGN KEY (`subcategory_id`) REFERENCES `expense_categories`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── Seed: 9 top-level categories ─────────────────────────────────────────────
INSERT INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (1, NULL, 'Vehicle & Mileage',           0, 0, 1, 1),
  (2, NULL, 'Travel & Lodging',            0, 0, 1, 2),
  (3, NULL, 'Meals & Entertainment',       1, 0, 1, 3),
  (4, NULL, 'Samples & Demo Materials',    0, 0, 1, 4),
  (5, NULL, 'Client Gifts',                1, 0, 1, 5),
  (6, NULL, 'Site Assessment',             0, 0, 1, 6),
  (7, NULL, 'Communication & Technology',  0, 0, 1, 7),
  (8, NULL, 'Professional Fees',           0, 0, 1, 8),
  (9, NULL, 'Other / Miscellaneous',       0, 0, 1, 9);

-- ── Seed: Vehicle & Mileage subcategories ────────────────────────────────────
INSERT INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (10, 1, 'Personal vehicle mileage', 0, 1, 1, 1),
  (11, 1, 'Rental car',               0, 0, 1, 2),
  (12, 1, 'Parking / tolls',          0, 0, 1, 3),
  (13, 1, 'Rideshare / taxi',         0, 0, 1, 4),
  (14, 1, 'Vehicle wash',             0, 0, 1, 5);

-- ── Seed: Travel & Lodging subcategories ─────────────────────────────────────
INSERT INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (15, 2, 'Airfare',                 0, 0, 1, 1),
  (16, 2, 'Hotel / lodging',         0, 0, 1, 2),
  (17, 2, 'Airport transportation',  0, 0, 1, 3),
  (18, 2, 'Baggage fees',            0, 0, 1, 4),
  (19, 2, 'Train / bus fare',        0, 0, 1, 5);

-- ── Seed: Meals & Entertainment subcategories ────────────────────────────────
INSERT INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (20, 3, 'Client meals',           1, 0, 1, 1),
  (21, 3, 'Rep meals (per diem)',   0, 0, 1, 2),
  (22, 3, 'Coffee / refreshments', 0, 0, 1, 3),
  (23, 3, 'Client entertainment',  1, 0, 1, 4),
  (24, 3, 'Catering for demos',    1, 0, 1, 5);

-- ── Seed: Samples & Demo Materials subcategories ─────────────────────────────
INSERT INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (25, 4, 'LED fixture samples',         0, 0, 1, 1),
  (26, 4, 'Demo kits',                   0, 0, 1, 2),
  (27, 4, 'Printed proposals/brochures', 0, 0, 1, 3),
  (28, 4, 'Branded leave-behinds',       0, 0, 1, 4);

-- ── Seed: Client Gifts subcategories ─────────────────────────────────────────
INSERT INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (29, 5, 'Holiday / appreciation gifts',  1, 0, 1, 1),
  (30, 5, 'Seasonal baskets / gift cards', 1, 0, 1, 2);

-- ── Seed: Site Assessment subcategories ──────────────────────────────────────
INSERT INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (31, 6, 'Lux meter rental/purchase', 0, 0, 1, 1),
  (32, 6, 'Lift rental',               0, 0, 1, 2),
  (33, 6, 'Survey materials',          0, 0, 1, 3),
  (34, 6, 'Facility access badges',    0, 0, 1, 4);

-- ── Seed: Communication & Technology subcategories ───────────────────────────
INSERT INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (35, 7, 'Mobile phone business use',        0, 0, 1, 1),
  (36, 7, 'Hotel internet',                   0, 0, 1, 2),
  (37, 7, 'Video conferencing subscriptions', 0, 0, 1, 3);

-- ── Seed: Professional Fees subcategories ────────────────────────────────────
INSERT INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (38, 8, 'Trade show / conference fees', 0, 0, 1, 1),
  (39, 8, 'Association memberships',      0, 0, 1, 2),
  (40, 8, 'Notary fees',                  0, 0, 1, 3);

-- ── Seed: Other / Miscellaneous subcategories ────────────────────────────────
INSERT INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (41, 9, 'Postage',                     0, 0, 1, 1),
  (42, 9, 'Office supplies',             0, 0, 1, 2),
  (43, 9, 'Other pre-approved expenses', 0, 0, 1, 3);
