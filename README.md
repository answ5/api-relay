# API Relay

轻量级 OpenAI 兼容 API 中转站。基于 Python FastAPI + MySQL，支持多用户、多渠道、Token 计费、流式转发。

## 特性

- ✅ **OpenAI 兼容** — 完整兼容 `/v1/chat/completions`、`/v1/images/generations` 等接口
- ✅ **多用户** — API Key 鉴权，独立额度管理
- ✅ **多渠道** — 支持多个上游 API 通道，自动路由
- ✅ **流式转发** — SSE 流式响应，逐 token 转发
- ✅ **计费系统** — 按请求计费 (quota_type=1)，自动扣费
- ✅ **管理 API** — 17 个 Admin 接口，用户/渠道/Token 全量管理
- ✅ **请求日志** — 完整请求日志 + 自动清理

## 快速开始

### 环境要求

- Python 3.11+
- MySQL / MariaDB

### 安装

```bash
git clone https://github.com/answ5/api-relay.git
cd api-relay
pip install -r requirements.txt
```

### 配置

编辑 `config.yaml`：

```yaml
app:
  host: "0.0.0.0"
  port: 8000
  debug: false

database:
  host: "localhost"
  port: 3306
  user: "relay"
  password: ""
  database: "api_relay"

# 管理员初始账号
admin:
  username: "admin"
  password: "admin123"
```

### 运行

```bash
python -m app.main
```

### 初始化

首次启动会自动创建数据库表。然后通过管理 API 创建用户和渠道。

## API 文档

### 用户接口 (OpenAI 兼容)

| 接口 | 描述 |
|------|------|
| `POST /v1/chat/completions` | 聊天补全 |
| `POST /v1/images/generations` | 图片生成 |
| `GET /v1/models` | 模型列表 |

### 管理接口

| 接口 | 描述 |
|------|------|
| `POST /api/admin/auth/login` | 管理员登录 |
| `GET/POST /api/admin/users` | 用户管理 |
| `GET/POST /api/admin/tokens` | Token 管理 |
| `GET/POST /api/admin/channels` | 渠道管理 |
| `GET/POST /api/admin/models` | 模型配置 |
| `GET /api/admin/stats` | 统计 |
| `GET /api/admin/logs` | 日志 |
| `GET /api/admin/config` | 系统配置 |

## 项目结构

```
api-relay/
├── app/
│   ├── api/
│   │   ├── admin/     # 管理 API
│   │   └── v1/        # OpenAI 兼容接口
│   ├── core/          # 核心 (auth, jwt, middleware)
│   ├── models/        # SQLAlchemy 模型
│   ├── relay/         # 请求转发 (proxy, stream)
│   ├── services/      # 业务逻辑 (channel, quota)
│   ├── workers/       # 后台任务 (log, payload)
│   ├── config.py      # 配置加载
│   ├── database.py    # 数据库初始化
│   ├── http_client.py # HTTP 客户端
│   ├── redis.py       # Redis (预留)
│   └── main.py        # 入口
├── config.yaml        # 配置文件
└── requirements.txt   # 依赖
```

## License

MIT
