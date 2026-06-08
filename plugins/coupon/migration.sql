# coupon 插件的数据库迁移

CREATE TABLE IF NOT EXISTS coupons (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    code            VARCHAR(32) NOT NULL UNIQUE,
    discount_type   VARCHAR(16) NOT NULL DEFAULT 'fixed',  -- fixed / percent
    discount_value  DECIMAL(14, 6) NOT NULL DEFAULT 0,
    min_amount      DECIMAL(14, 6) DEFAULT 0,
    max_uses        INT DEFAULT 0,       -- 0 = unlimited
    used_count      INT DEFAULT 0,
    status          VARCHAR(16) DEFAULT 'active',
    expires_at      DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
