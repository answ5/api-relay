# cards 插件的数据库迁移

CREATE TABLE IF NOT EXISTS card_batches (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128) NOT NULL,
    amount          DECIMAL(14, 6) NOT NULL,
    total_count     INT DEFAULT 0,
    redeemed_count  INT DEFAULT 0,
    expires_at      DATETIME,
    created_by      INT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS cards (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id        BIGINT NOT NULL,
    code_hash       VARCHAR(64) NOT NULL UNIQUE,
    amount          DECIMAL(14, 6) NOT NULL,
    status          VARCHAR(16) DEFAULT 'unused',
    redeemed_by     INT,
    redeemed_at     DATETIME,
    expires_at      DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_batch_id (batch_id),
    INDEX idx_status (status),
    INDEX idx_redeemed_by (redeemed_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
