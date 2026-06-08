# ticket 插件的数据库迁移

CREATE TABLE IF NOT EXISTS tickets (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    title           VARCHAR(256) NOT NULL,
    content         TEXT,
    status          VARCHAR(16) DEFAULT 'open',   -- open / replied / closed
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ticket_replies (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticket_id       BIGINT NOT NULL,
    user_id         INT NOT NULL,
    content         TEXT,
    is_admin        INT DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ticket_id (ticket_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
