# MXReady 部署文档

本文档覆盖 MXReady Web 服务的两种部署方式（裸机、Docker），以及数据持久化、日志、反向代理等生产注意事项。

## 1. 前置条件

- Python 3.11+（建议与 CI 一致使用 3.11）；
- Node.js 22（仅构建前端时使用，Docker 部署无需本机安装）；
- `git` 命令可用（扫描仓库的运行时依赖）；
- 服务器可访问公网（扫描时克隆托管仓库）。

## 2. 环境变量

全部配置项通过 `MXREADY_*` 环境变量注入（12-factor），未设置时使用默认值。模板见 `.env.example`。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MXREADY_DATA_DIR` | `data` | SQLite 数据库所在目录 |
| `MXREADY_RULES_DIR` | `rules/v1` | YAML 规则集目录 |
| `MXREADY_TEMP_DIR` | `data/tmp` | 扫描临时目录（克隆仓库用） |
| `MXREADY_FRONTEND_DIR` | `frontend/dist` | 前端构建产物目录 |
| `MXREADY_LOG_LEVEL` | `INFO` | 日志级别：`DEBUG`/`INFO`/`WARNING`/`ERROR` |

> 监听地址与端口由 uvicorn 的 `--host` / `--port` 或环境变量 `UVICORN_HOST` / `UVICORN_PORT` 控制（uvicorn 自身读取），不要在 `MXREADY_*` 中重复配置。

## 3. 裸机部署

```bash
python3.11 -m venv .venv
. .venv/bin/activate
pip install .
npm --prefix frontend ci && npm --prefix frontend run build   # 构建前端
export MXREADY_DATA_DIR=/srv/mxready/data
uvicorn mxready.app:create_app --factory --host 0.0.0.0 --port 8000 --workers 2
```

- 首次启动会在 `MXREADY_DATA_DIR` 下自动创建 `mxready.db`；
- 生产建议加反向代理（见第 5 节），并为 `/assets` 启用长缓存（服务已返回 `Cache-Control: immutable`）。

### systemd 示例（Linux 服务器）

```ini
[Unit]
Description=MXReady
After=network.target

[Service]
User=mxready
WorkingDirectory=/srv/mxready
EnvironmentFile=/srv/mxready/.env
ExecStart=/srv/mxready/.venv/bin/uvicorn mxready.app:create_app --factory --host 127.0.0.1 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## 4. Docker 部署

仓库提供多阶段 `Dockerfile` 与 `docker-compose.yml`（仅用于 MXReady 自身的演示/测试部署，不涉及远程 GPU 服务器的 Docker 编排）。

```bash
docker compose up -d --build
curl http://127.0.0.1:8000/api/health   # {"status":"ok",...}
```

- 镜像以非 root 用户 `mxready` 运行；
- SQLite 数据经命名卷 `mxready-data` 持久化到 `/app/data`；
- 日志级别：`MXREADY_LOG_LEVEL=DEBUG docker compose up -d`。

## 5. 反向代理（可选）

```nginx
server {
    listen 80;
    server_name mxready.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;   # 扫描任务可能耗时较长
    }
}
```

## 6. 数据目录与备份

- `MXREADY_DATA_DIR/mxready.db` 为 SQLite 单文件库，WAL 模式已启用；
- 备份：对运行中的 SQLite 应使用 `sqlite3 mxready.db ".backup 'mxready.bak'"`，不要直接复制主库文件；
- 建议 cron 每日备份并保留近 N 天：
  ```bash
  0 2 * * * sqlite3 /srv/mxready/data/mxready.db ".backup '/srv/backups/mxready-$(date +\%F).bak'"
  ```
- 扫描记录是申报/审计证据，项目默认**不自动清理**历史记录。

## 7. 日志

- 业务日志（`mxready` 命名空间）为单行 JSON 结构：`{ts, level, logger, message, ...extra}`；
- 访问日志由 uvicorn 输出（文本格式），与业务日志分离；
- 日志中的 URL 明文凭据、`*_TOKEN/*_PASSWORD/*_KEY` 赋值、用户目录、常见令牌前缀会被自动脱敏；
- 通过 `MXREADY_LOG_LEVEL` 控制级别，生产建议 `INFO`。

## 8. 常见问题

| 现象 | 处理 |
| --- | --- |
| Windows 本地 pytest 报 `PermissionError` | 项目已固定 basetemp，若仍有问题见 README「Windows 常见问题」 |
| 容器内无法写 `data` 目录 | 确认命名卷 `mxready-data` 已挂载，首次挂载会继承镜像中 `/app/data` 的 `mxready` 归属 |
| 反向代理下扫描超时 | 调大 `proxy_read_timeout`（克隆大仓库可能超过默认 60 秒） |
| 想改用本地 .env 文件 | 进程环境变量注入即可，无需额外解析库；`docker compose --env-file .env up` 会注入 compose 中的占位变量 |

## 9. 安全边界（部署时保持）

- 仓库白名单默认仅 `github.com` 与 `gitee.com`（URL 规范化、无凭据、无私有地址校验均生效）；
- 克隆限制：单仓库 50 MiB、10,000 文件、60 秒超时；
- 验证上传限制 1 MiB；
- 如需公网部署，请先完成 API 限流（见 `docs/optimization-plan.md` P2-1）。
