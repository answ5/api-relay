# payment_manual 插件的数据库迁移

-- 创建 payment_orders 表
CREATE TABLE IF NOT EXISTS payment_orders (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    amount      DECIMAL(14, 6) NOT NULL,
    bonus       DECIMAL(14, 6) DEFAULT 0,
    payment_method  VARCHAR(16) DEFAULT 'manual',
    payment_channel VARCHAR(32),
    status      VARCHAR(16) DEFAULT 'pending',
    epay_trade_no   VARCHAR(128) UNIQUE,
    epay_url        VARCHAR(512),
    stripe_pi_id    VARCHAR(128) UNIQUE,
    paid_at     DATETIME,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
