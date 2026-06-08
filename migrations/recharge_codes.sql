-- Create recharge_codes table for user top-up
CREATE TABLE IF NOT EXISTS `recharge_codes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `code` VARCHAR(64) NOT NULL UNIQUE,
    `amount` DECIMAL(14,4) NOT NULL DEFAULT 0,
    `status` ENUM('unused', 'used') NOT NULL DEFAULT 'unused',
    `note` VARCHAR(255) DEFAULT NULL,
    `redeemed_by` INT DEFAULT NULL,
    `redeemed_at` DATETIME DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_code` (`code`),
    INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
