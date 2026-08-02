# MXReady API 手册（中文）

MXReady 提供 HTTP API 供前端与自动化脚本调用。本文档覆盖全部公开端点，含 curl 示例与错误码约定，可用于申报材料与服务器验收。

## 通用约定

- 基础地址：本地开发默认 `http://127.0.0.1:8000`，生产环境以实际部署为准（见 `docs/deployment.md`）。
- 内容类型：请求体与响应体均为 JSON（UTF-8），上传验证结果必须显式携带 `Content-Type: application/json`。
- 时间格式：ISO 8601（含 UTC 偏移），例如 `2026-08-02T10:00:00+00:00`。
- 错误格式：所有非 2xx 响应统一为：

```json
{
  "error": {
    "code": "错误码",
    "message": "人类可读说明",
    "details": {}
  }
}
```

### 错误码一览

| HTTP 状态 | 错误码 | 含义 |
| --- | --- | --- |
| 400 | `INVALID_REPOSITORY_URL` | 仓库地址不是合法的公开 HTTPS 地址 |
| 400 | `UNSUPPORTED_REPOSITORY_HOST` | 仓库主机不在白名单（默认 GitHub / Gitee） |
| 400 | `INVALID_GIT_REF` | ref 参数格式不安全或超长 |
| 400 | `INVALID_REQUEST` | 请求体或路径参数校验失败 |
| 404 | `SCAN_NOT_FOUND` | 扫描任务不存在 |
| 409 | `SCAN_NOT_COMPLETED` | 扫描尚未完成，报告不可用 |
| 409 | `VERIFICATION_COMMIT_MISMATCH` | 验证结果的提交与报告不一致 |
| 413 | `REQUEST_TOO_LARGE` | 请求体超过全局上限（`MXREADY_MAX_REQUEST_BYTES`） |
| 413 | `UPLOAD_TOO_LARGE` | 验证结果超过 1 MiB |
| 422 | `VERIFICATION_SCHEMA_INVALID` | 验证结果不是 `application/json` |
| 429 | `RATE_LIMITED` | 超过每 IP 限流阈值（`MXREADY_RATE_LIMIT_ENABLED` 开启时） |
| 429 | `SCAN_LIMIT_REACHED` | 并发扫描任务数达到上限（`MXREADY_MAX_CONCURRENT_SCANS`） |

## 1. 健康检查

### `GET /api/health`

返回服务版本，用于探活与部署验证。

```bash
curl -s http://127.0.0.1:8000/api/health
```

```json
{ "status": "ok", "version": "0.1.0" }
```

## 2. 规则目录

### `GET /api/rules`

返回当前加载的规则集（版本 + 规则清单）。`MXREADY_EXTRA_RULES_DIR` 配置的自定义规则也会合并进该清单。

```bash
curl -s http://127.0.0.1:8000/api/rules | python -m json.tool
```

响应结构：

- `version`：规则集版本（如 `"1"`）；
- `rules[]`：每条规则包含 `id` / `version` / `title` / `category` / `severity`（blocker / warning / info）/ `file_globs` / `patterns` / `message` / `recommendation` / `references` / `updated` / `confidence`。

## 3. 创建扫描

### `POST /api/scans`

提交仓库地址（可选 ref），服务立即返回排队中的扫描任务；实际扫描在后台执行。

```bash
curl -s -X POST http://127.0.0.1:8000/api/scans \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/pytorch/extension-cpp.git", "ref": null}'
```

请求体：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `repo_url` | string | 是 | 公开仓库 HTTPS 地址（仅允许白名单主机、无凭据） |
| `ref` | string | 否 | 分支 / 标签 / 40 位提交号，最长 200 字符 |

成功返回 `202 Accepted`：

```json
{
  "id": "2f9a1c1e-...-...-...",
  "repo_url": "https://github.com/pytorch/extension-cpp",
  "requested_ref": null,
  "resolved_commit": null,
  "status": "queued",
  "stage_message": "Waiting to start",
  "created_at": "2026-08-02T10:00:00+00:00",
  "updated_at": "2026-08-02T10:00:00+00:00",
  "failure_code": null,
  "failure_message": null
}
```

## 4. 查询扫描任务

### `GET /api/scans/{scan_id}`

`scan_id` 为创建扫描时返回的 UUID。轮询 `status` 字段即可观察进度：`queued → cloning → indexing → analyzing → completed | failed`。

```bash
curl -s http://127.0.0.1:8000/api/scans/2f9a1c1e-0000-0000-0000-000000000000
```

## 5. 获取报告

### `GET /api/scans/{scan_id}/report`

返回结构化扫描报告（JSON）。扫描未完成时返回 `409 SCAN_NOT_COMPLETED`。

```bash
curl -s http://127.0.0.1:8000/api/scans/2f9a1c1e-0000-0000-0000-000000000000/report \
  | python -m json.tool
```

关键字段：

| 字段 | 说明 |
| --- | --- |
| `schema_version` | 报告 schema 版本，当前 `"1.0"` |
| `repository` | 仓库快照：`provider` / `owner` / `name` / `url` / `commit` |
| `tool_version` / `ruleset_version` | 工具与规则集版本 |
| `summary` | 统计：`total_count` / `blocker_count` / `warning_count` / `info_count` / `top_blockers`（优先复核清单） |
| `findings[]` | 每条含 `rule_id` / `severity` / `category` / `relative_path` / `line_start` / `line_end` / `evidence` / `message` / `recommendation` / `references` / `count`（同规则同文件聚合命中数） |
| `migration_checklist[]` | 按规则分组的迁移待办清单 |
| `analysis_warnings[]` | 索引阶段警告（如文件过大被跳过），与 findings 分离 |
| `static_status` | `passed` / `warnings` / `blocked` / `failed` |
| `verification_status` | `not-run` / `verified` / `failed` / `stale` |

### `GET /api/scans/{scan_id}/report.md`

下载 Markdown 版报告（`Content-Disposition: attachment`）。

### `GET /api/scans/{scan_id}/report.json`

下载 JSON 版报告文件。

### `GET /api/scans/{scan_id}/badge.svg`

获取徽章 SVG（`Cache-Control: no-store`），可直接嵌入 README。

## 6. 下载验证包

### `GET /api/scans/{scan_id}/verification-bundle`

下载与该报告匹配的验证 ZIP（含 `mxready.yml`、`SECURITY.md`、只读 runner），用于在沐曦服务器上执行真机验证。

```bash
curl -sL -o verification.zip \
  http://127.0.0.1:8000/api/scans/2f9a1c1e-0000-0000-0000-000000000000/verification-bundle
```

## 7. 上传验证结果

### `POST /api/scans/{scan_id}/verification-runs`

上传 runner 生成的 `result.json`（脱敏后）内容，服务校验提交一致性后更新报告状态。

```bash
curl -s -X POST \
  http://127.0.0.1:8000/api/scans/2f9a1c1e-0000-0000-0000-000000000000/verification-runs \
  -H "Content-Type: application/json" \
  --data-binary @result.json
```

约束：

- 必须携带 `Content-Type: application/json`，否则 `422 VERIFICATION_SCHEMA_INVALID`；
- 请求体上限 1 MiB，超出返回 `413 UPLOAD_TOO_LARGE`；
- `repository_commit` 必须与报告中的提交一致，否则 `409 VERIFICATION_COMMIT_MISMATCH`；
- `checks` 必须包含 `mx-smi` 与 `pytorch-device`；
- `started_at` 不得晚于服务器时间 10 分钟以上，结果有效期 30 天。

成功返回 `200`，`verification_status` 更新为 `verified` / `failed` / `stale`。

## 8. 防护行为说明（部署时）

- 限流：`MXREADY_RATE_LIMIT_ENABLED=true` 时，按客户端 IP 限制写操作频率（默认每 IP 每分钟 20 次，`MXREADY_RATE_LIMIT_PER_MINUTE` 可调），超限返回 `429 RATE_LIMITED`；
- 请求体上限：`MXREADY_MAX_REQUEST_BYTES` 全局限制（默认 1 MiB），验证结果上传走端点自身的 1 MiB 校验（错误码 `UPLOAD_TOO_LARGE`）；
- 并发扫描上限：`MXREADY_MAX_CONCURRENT_SCANS`（默认 2），超过返回 `429 SCAN_LIMIT_REACHED`；
- 数据保留：`MXREADY_SCAN_RETENTION_DAYS`（默认 0 = 不清理，保护申报证据）。

更多部署参数见 `.env.example` 与 `docs/deployment.md`。
