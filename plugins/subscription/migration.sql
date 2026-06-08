# subscription 插件的数据库迁移

CREATE TABLE IF NOT EXISTS plans (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(64) NOT NULL,
    description     TEXT,
    price_monthly   DECIMAL(14, 6) DEFAULT 0,
    price_yearly    DECIMAL(14, 6) DEFAULT 0,
    quota_per_day   BIGINT DEFAULT 0,
    rate_limit      INT DEFAULT 60,
    max_models      INT DEFAULT 0,
    status          INT DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS subscriptions (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    plan_id         INT NOT NULL,
    period          VARCHAR(8) DEFAULT 'monthly',
    status          VARCHAR(16) DEFAULT 'active',
    started_at      DATETIME,
    expires_at      DATETIME,
    auto_renew      INT DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
