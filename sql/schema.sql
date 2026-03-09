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
  `role`       ENUM('admin','sales') NOT NULL DEFAULT 'sales',
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
  `sq_ft`                  INT,
  `targets`                TEXT,
  `potential`              DECIMAL(12,2),
  `progress`               VARCHAR(100),
  `expected`               DATE,
  `roi`                    DECIMAL(5,2),
  `annual_sales_locations`  TEXT,
  INDEX `idx_company_name` (`company_name`),
  INDEX `idx_action`       (`action`),
  INDEX `idx_progress`     (`progress`),
  INDEX `idx_expected`     (`expected`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- --------------------------------------------------------
-- Seed: default admin account  (password: Admin1234!)
-- Generate a fresh hash via: password_hash('Admin1234!', PASSWORD_BCRYPT)
-- --------------------------------------------------------
INSERT INTO `users` (`username`, `email`, `password`, `role`) VALUES
('admin', 'admin@comfortlighting.net', '$2y$12$Q9v3SZqF8YKjL1mN7pXuuOKxD2HcG5JvR0tE4AiWsBnMfCd3Zolqe', 'admin');

-- --------------------------------------------------------
-- Seed: sample leads for testing
-- --------------------------------------------------------
INSERT INTO `leads`
  (`company_name`,`action`,`contact`,`address`,`number`,`email`,`notes`,`sq_ft`,`targets`,`potential`,`progress`,`expected`,`roi`,`annual_sales_locations`)
VALUES
('Acme Pharma Labs','Contacted','Jane Smith – Facilities Mgr','123 Research Blvd, Boston MA 02115','617-555-0101','jsmith@acmepharma.com','Initial call on 2026-03-01. Interested in LED retrofit.',45000,'Clean rooms, corridors',85000.00,'Qualified','2026-06-30',18.50,'$12M annual revenue. 2 other MA locations.'),
('Metro Cold Storage','Quote Requested','Bob Torres – VP Ops','88 Warehouse Way, Chicago IL 60601','312-555-0202','btorres@metrocold.com','Quote requested for freezer aisles. Follow up sent.',120000,'Freezer aisles, loading docks',210000.00,'Proposal','2026-05-15',22.00,'$30M revenue. 4 Midwest facilities.'),
('Summit Auto Showroom','New Lead','Alice Park – GM','501 Auto Row, Dallas TX 75201','214-555-0303','apark@summitauto.com','Referred by vendor contact.',18000,'Showroom floor, service bays',47500.00,'Prospect','2026-08-01',15.00,NULL);
