-- Run this on the production database to add the 'legal' role to the users table
-- Required before deploying the contract feature
ALTER TABLE `users`
  MODIFY `role` ENUM('admin', 'sales', 'legal') NOT NULL DEFAULT 'sales';
