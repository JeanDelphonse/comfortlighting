-- ComfortLighting — Re-seed expense subcategories
-- Run this if subcategories are missing from the expense_categories table
-- (e.g. the original migration_create_lead_activities.sql was run but
--  phpMyAdmin truncated the inline-commented INSERT).
-- Safe to run even if some rows already exist (INSERT IGNORE).

INSERT IGNORE INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (10, 1, 'Personal vehicle mileage', 0, 1, 1, 1),
  (11, 1, 'Rental car',               0, 0, 1, 2),
  (12, 1, 'Parking / tolls',          0, 0, 1, 3),
  (13, 1, 'Rideshare / taxi',         0, 0, 1, 4),
  (14, 1, 'Vehicle wash',             0, 0, 1, 5);

INSERT IGNORE INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (15, 2, 'Airfare',                 0, 0, 1, 1),
  (16, 2, 'Hotel / lodging',         0, 0, 1, 2),
  (17, 2, 'Airport transportation',  0, 0, 1, 3),
  (18, 2, 'Baggage fees',            0, 0, 1, 4),
  (19, 2, 'Train / bus fare',        0, 0, 1, 5);

INSERT IGNORE INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (20, 3, 'Client meals',           1, 0, 1, 1),
  (21, 3, 'Rep meals (per diem)',   0, 0, 1, 2),
  (22, 3, 'Coffee / refreshments', 0, 0, 1, 3),
  (23, 3, 'Client entertainment',  1, 0, 1, 4),
  (24, 3, 'Catering for demos',    1, 0, 1, 5);

INSERT IGNORE INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (25, 4, 'LED fixture samples',         0, 0, 1, 1),
  (26, 4, 'Demo kits',                   0, 0, 1, 2),
  (27, 4, 'Printed proposals/brochures', 0, 0, 1, 3),
  (28, 4, 'Branded leave-behinds',       0, 0, 1, 4);

INSERT IGNORE INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (29, 5, 'Holiday / appreciation gifts',  1, 0, 1, 1),
  (30, 5, 'Seasonal baskets / gift cards', 1, 0, 1, 2);

INSERT IGNORE INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (31, 6, 'Lux meter rental/purchase', 0, 0, 1, 1),
  (32, 6, 'Lift rental',               0, 0, 1, 2),
  (33, 6, 'Survey materials',          0, 0, 1, 3),
  (34, 6, 'Facility access badges',    0, 0, 1, 4);

INSERT IGNORE INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (35, 7, 'Mobile phone business use',        0, 0, 1, 1),
  (36, 7, 'Hotel internet',                   0, 0, 1, 2),
  (37, 7, 'Video conferencing subscriptions', 0, 0, 1, 3);

INSERT IGNORE INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (38, 8, 'Trade show / conference fees', 0, 0, 1, 1),
  (39, 8, 'Association memberships',      0, 0, 1, 2),
  (40, 8, 'Notary fees',                  0, 0, 1, 3);

INSERT IGNORE INTO `expense_categories` (`id`, `parent_id`, `name`, `requires_attendees`, `is_mileage`, `active`, `sort_order`) VALUES
  (41, 9, 'Postage',                     0, 0, 1, 1),
  (42, 9, 'Office supplies',             0, 0, 1, 2),
  (43, 9, 'Other pre-approved expenses', 0, 0, 1, 3);

-- Verify
SELECT COUNT(*) AS subcategory_count FROM expense_categories WHERE parent_id IS NOT NULL;
