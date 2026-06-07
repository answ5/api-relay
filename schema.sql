-- Auto-generated schema for API Relay
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(128) DEFAULT '',
    balance DECIMAL(14,4) DEFAULT 0,
    status INT DEFAULT 1,
    role VARCHAR(16) DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(64) DEFAULT '',
    key_prefix VARCHAR(8) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    models TEXT,
    rate_limit_per_minute INT DEFAULT 60,
    balance_limit DECIMAL(14,4) DEFAULT 0,
    status INT DEFAULT 1,
    group_name VARCHAR(32) DEFAULT 'default',
    last_used_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS channels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    base_url VARCHAR(256) NOT NULL,
    api_key VARCHAR(512) NOT NULL,
    weight INT DEFAULT 10,
    priority INT DEFAULT 0,
    status INT DEFAULT 1,
    models TEXT,
    circuit_breaker JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS model_pricing (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(128) NOT NULL UNIQUE,
    channel_id INT NOT NULL,
    billing_method VARCHAR(16) DEFAULT 'per_token',
    prompt_token_price_1k DECIMAL(14,6) DEFAULT 0,
    completion_token_price_1k DECIMAL(14,6) DEFAULT 0,
    request_price DECIMAL(14,6) DEFAULT 0,
    image_price_per_generation DECIMAL(14,6),
    status INT DEFAULT 1,
    groups TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    request_id VARCHAR(64) NOT NULL,
    user_id INT NOT NULL,
    token_id INT,
    channel_id INT,
    model_name VARCHAR(128) NOT NULL,
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    billing_method VARCHAR(16) DEFAULT 'per_token',
    user_cost DECIMAL(14,6) DEFAULT 0,
    upstream_cost DECIMAL(14,6) DEFAULT 0,
    response_ms INT DEFAULT 0,
    is_stream INT DEFAULT 0,
    status VARCHAR(16) DEFAULT 'success',
    ip VARCHAR(45) DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_request_id (request_id),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS transactions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    amount DECIMAL(14,4) NOT NULL,
    type VARCHAR(16) NOT NULL,
    balance_after DECIMAL(14,4),
    note TEXT,
    log_id BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS request_payloads (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    request_id VARCHAR(64) NOT NULL,
    request_body LONGBLOB,
    response_body LONGBLOB,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_request_id (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
