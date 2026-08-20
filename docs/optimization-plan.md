# MXReady 修改优化计划书

- 日期：2026-08-01（v2，整合部署与可运维性评审意见）
- 项目：MXReady（沐曦种子计划参与项目）
- 当前环境：Windows 本地开发，即将申请沐曦 GPU 服务器做真机验证
- 文档目的：记录扫描发现的问题、优先级排序的修改方案、服务器测试准备清单与里程碑安排

## 1. 项目现状评估

### 1.1 完成度

MXReady MVP 设计规格中的 16 个实施任务已全部提交，代码结构完整：

| 模块 | 状态 |
| --- | --- |
| FastAPI 后端（扫描、报告、验证） | 已完成，263 个 Python 测试通过 |
| React + Vite 前端 | 已完成，23 个前端测试通过，构建产物存在 |
| 30 条 YAML 检查规则 | 已完成，正反例夹具齐全 |
| 独立 runner 验证包 | 已完成，支持 inspect / run 两阶段 |
| 3 个公开项目报告 | extension-cpp（passed）、apex（blocked 1）、flash-attention（blocked 5） |
| Apex 上游补丁 | 已编写并本地测试，未提交 PR |
| 真机沐曦验证 | **pending**，等待服务器 |

### 1.2 本机验证记录（2026-08-01）

- Python 后端测试：`204 passed`（使用干净 `--basetemp` 时全部通过）；
- 前端测试：`12 passed`；
- 前端构建：`dist/` 存在，可打包为单部署单元；
- 本机 venv Python 版本为 3.14.2，与项目声明（3.11）不一致。

## 2. 问题清单与修改建议（统一优先级）

### 2.1 P0 —— 立即修复

> **执行记录（2026-08-01）**：P0-1 ✅ 已改依赖 `httpx2` → `httpx` 并卸载 httpx2；P0-2 ✅ 已删 `.pytest-temp/` 并加入 `.gitignore`；P0-3 ✅ 根因是 `%TEMP%\pytest-of-21995` 目录 ACL 异常（提权进程创建、普通权限无法删除），已通过把 pytest basetemp 固定到 `.pytest-temp`（gitignore）根治，后端 204 测试、前端 12 测试全绿；P0-4 ⏳ 待用户自行安装 Python 3.11 后重建 venv（不代装环境）。

**P0-1 依赖声明错误：`httpx2` 是不需要的第三方包**

- 位置：[pyproject.toml](../pyproject.toml#L21)
- 现象：dev 依赖声明 `"httpx2>=2,<3"`，本机同时装入了 `httpx2 2.9.1` 与真正需要的 `httpx 0.28.1`；
- 分析：`httpx2` 是冷门/存疑的 PyPI 包，代码中没有任何 `import httpx`（测试走 `fastapi.testclient.TestClient`），真正被使用的是 `httpx`（由 starlette 传递安装）。声明 `httpx2` 既不必要，也存在供应链卫生隐患；
- 目标：改为 `"httpx>=0.27,<1"`，并 `pip uninstall httpx2` 验证测试仍通过。

**P0-2 `.pytest-temp/` 未跟踪目录污染工作区**

- 位置：仓库根目录 `.pytest-temp/`（约 60+ 个测试残留目录，`git status` 显示为 `??`）；
- 目标：删除该目录，并在 `.gitignore` 中追加 `.pytest-temp/`，防止再次提交。

**P0-3 Windows 下 pytest 默认临时目录 PermissionError**

- 现象：不带 `--basetemp` 运行 pytest 时，`%TEMP%\pytest-of-21995` 报 `PermissionError: [WinError 5] 拒绝访问`，导致 124 个用例 ERROR；指定干净 `--basetemp` 后全部通过；
- 分析：Windows 特有现象，通常由被中断的 pytest 运行残留、杀毒软件锁定或目录权限异常引起；
- 目标：清理 `%TEMP%\pytest-of-*` 残留目录；在 README 增加 Windows 故障排查说明。

**P0-4 Python 版本不一致**

- 现象：本机 venv 使用 Python 3.14.2，项目声明 `requires-python = ">=3.11"`、CI 使用 3.11；
- 风险：3.14 较新，PyTorch / 其他依赖在申请到的沐曦服务器上大概率按 3.10/3.11 提供，本地与服务器行为可能不一致；
- 目标：本机重建 venv 时统一到 Python 3.11（与 CI、服务器对齐）。

### 2.2 P1 —— 高优先级（部署与可运维性、服务器准备）

> **执行记录（2026-08-01）**：P1-2 ✅ 配置支持 `MXREADY_*` 环境变量注入（`Settings.from_env()`）+ `.env.example` + 4 个配置测试；P1-5 ✅ 新增 JSON 结构化日志（stdout、级别可控、URL 凭据/令牌/用户目录自动脱敏）并接入扫描关键路径 INFO 日志，6 个日志测试；P1-1 ✅ Dockerfile（多阶段）+ docker-compose + .dockerignore + README Docker 章节（本机无 Docker，构建验证交由 CI 的 docker job）；P1-3 ✅ CI 扩展为 Python 3.11/3.12 × ubuntu/windows 矩阵 + pip-audit + 前端 typecheck + docker build job；P1-8 ✅ docs/deployment.md（裸机/systemd/Docker/nginx/备份/日志/安全边界）。回归：后端 213 测试、前端 12 测试、ruff 全绿。⏳ P1-4（备份/迁移）、P1-6（服务器交接脚本+Linux 演练）、P1-7（报告聚合）未实施。

> **执行记录（2026-08-02）**：P1-4 ✅ SQLite 在线备份（`source.backup`）+ WAL + `user_version` 顺序迁移 + 保留期自动清理（4 个新存储测试）；P1-6 ✅ 服务器交接脚本三件套（`checkout-commit.sh` / `run-inspect.sh` / `pre-upload-check.sh`）+ CI 新增 `server-handover-scripts` job（`bash -n` 语法检查）+ 交接 README 跨平台 CRLF 说明；P1-7 ✅ 同规则同文件命中聚合（`count` 字段累加）+ `top_blockers` 优先复核清单（聚合正反例与端到端测试）。⏳ P1-6 剩余：Linux 真机演练留待服务器窗口期。

**P1-1 Docker 容器化部署（关键）**

- 现状问题：项目 README 提到"前端与 FastAPI 服务可打包为同一个部署单元"，但没有任何 Dockerfile 或 docker-compose.yml；本地 Windows 开发，后续需迁移到 Linux 服务器跑测试与演示；
- 设计约束说明：MVP 设计规格中"不包含 Docker 编排"指平台不替用户在远程 GPU 服务器安装 Docker；将 MXReady 自身容器化用于演示部署不违反该条，但需要同步更新 README 与设计规格中的相关表述（见"6. 风险与红线"决策更新）；
- 建议操作：
  1. 创建 `Dockerfile`（多阶段构建）：
     - 阶段一：`node:22-alpine` 构建前端静态资源；
     - 阶段二：`python:3.11-slim` 运行 FastAPI，安装 git（运行时依赖），使用非 root 用户；
  2. 创建 `docker-compose.yml`：定义 mxready 服务，挂载 data 目录持久化 SQLite，映射 8000 端口；nginx 反向代理为可选服务；
  3. 创建 `.dockerignore`：排除 `.pytest-temp/`、`node_modules/`、`.venv/`、`.git/` 等；
  4. README 补充 Docker 部署文档（配合 P1-8 的 `docs/deployment.md`）。

**P1-2 配置管理系统重构（12-factor）**

- 现状问题：[config.py](../backend/mxready/config.py) 是纯 dataclass 硬编码，路径写死为相对路径 `Path("data")`、`Path("rules/v1")`，服务器部署时无法通过环境变量覆盖；
- 建议操作：
  1. 给 `Settings` 增加 `from_env()` 类方法，读取 `MXREADY_DATA_DIR`、`MXREADY_RULES_DIR`、`MXREADY_TEMP_DIR`、`MXREADY_FRONTEND_DIR`、`MXREADY_HOST`、`MXREADY_PORT`、`MXREADY_LOG_LEVEL` 等环境变量，保留合理默认值；
  2. 创建 `.env.example` 模板供部署参考；
  3. TOML/YAML 配置文件加载降为可选（P3），MVP 阶段环境变量 + `.env` 足够，避免过度设计；
- 注意：host/port 同时会经 uvicorn 命令行指定，需在文档中说明两者的优先级与推荐用法。

**P1-3 CI/CD 增强**

- 现状问题：[ci.yml](../.github/workflows/ci.yml) 只在 `ubuntu-latest` 运行，未覆盖本地 Windows 开发环境；
- 建议操作：
  1. 使用 `strategy.matrix`：`os: [ubuntu-latest, windows-latest]`，`python-version: ["3.11", "3.12"]`；Windows job 使用干净 basetemp；
  2. 增加 Docker 镜像构建验证 job（`docker build` 至少能通过）；
  3. 增加依赖安全扫描 `pip-audit`（先安装进 dev 依赖或单独步骤）；
  4. 前端把 `tsc -b` 类型检查单独列为 lint 步骤（目前只在 build 内隐式执行）。

**P1-4 数据持久化与备份**

- 现状问题：SQLite 单文件存储在 `data/mxready.db`，无自动备份机制；
- 建议操作：
  1. 利用 SQLite `backup` API 提供定时备份（如每日 `.db.bak`），WAL 模式已启用，可配合定期 checkpoint；
  2. 数据清理策略 `scan_retention_days`：**默认不启用**，因为扫描记录是申报证据的一部分；仅在显式配置时按天清理，且清理前必须可导出归档；
  3. 数据库迁移机制：MVP schema 简单，不建议引入 alembic；采用轻量"schema 版本表 + 启动时顺序迁移函数"，为未来变更做准备。

**P1-5 日志系统完善**

- 现状问题：代码有 `logging.getLogger(__name__)` 但无统一 handler / formatter / 级别控制；
- 建议操作：
  1. `create_app()` 中配置统一日志：JSON 结构化输出（便于服务器日志收集）、级别由 `MXREADY_LOG_LEVEL` 控制、区分访问日志与业务日志；
  2. 关键路径补 INFO 日志：扫描开始/结束、Git 获取、阶段切换、验证上传、异常；
  3. 敏感信息脱敏：仓库 URL、临时路径等写入日志前过滤（复用 runner 中 `redact.py` 的同类逻辑，注意不直接 import runner 模块）。

**P1-6 真机验证"服务器工作手册"脚本化 + 跨平台演练**

- 现状：`examples/verification/README.md` 的 SOP 已很完整，但全部是人工复制粘贴命令；ZIP 在 Windows 生成、Linux 服务器解压，跨平台未验证；
- 建议操作：
  1. 在交接目录提供只读辅助脚本：`checkout-commit.sh`（锁定提交并校验）、`run-inspect.sh`（自动 inspect + 摘要）、`pre-upload-check.sh`（扫描 result.json 残留的主机名/用户名/绝对路径/敏感键）；脚本不修改驱动、不安装软件，保持 runner 安全边界；
  2. 在本地用 WSL 或 Docker（Linux 容器）完整演练第 3~6 步，把结果记入 `docs/application-evidence.md`，提前排除换行符/权限/路径问题。

**P1-7 报告噪音治理**

- 现象：flash-attention 报告 124 条 warning、64 条 info，apex 78 条 warning，评审阅读负担大；
- 建议操作（按收益排序）：
  1. 同一规则在同一文件多次命中时聚合为一条（记录命中数）——先写"聚合语义"的反例测试；
  2. 报告顶部增加"Top 阻塞项 / 需优先复核清单"，按 severity 与受影响文件数排序；
  3. 每条 finding 的 `references` 增加"文档版本/日期"字段，便于评审追溯；
  4. 高频规则提供"每文件最多 N 条"的防刷阈值，避免单个文件刷爆计数。

**P1-8 部署方案文档**

- 建议操作：新增 `docs/deployment.md`，覆盖生产启动命令（uvicorn 多 worker 或进程管理器）、反向代理（nginx/caddy）与静态托管、`data/` 目录显式化与备份、Docker 部署步骤。

### 2.3 P2 —— 中优先级

> **执行记录（2026-08-02）**：P2-1 ✅ 自定义进程内滑动窗口限流中间件（按 IP，默认关闭、`MXREADY_RATE_LIMIT_ENABLED` 开启）+ 请求体 Content-Length 上限中间件 + 并发扫描上限（数据库统计 active job，超出直接 429），新增 6 个中间件测试；P2-2 ✅ `scripts/dev.ps1` + `make.ps1` + `Makefile` 统一 `install` / `dev` / `test` / `lint` / `build`；P2-3 ✅ 前端 ErrorBoundary + 报告骨架屏 + 键盘可访问性（方向键筛选导航、FindingCard Enter/Space 折叠、焦点管理）+ 移动端响应式，前端测试 20 个 + `npm run build` 通过；P2-4 ✅ 新增规则（含 MXR-DOCKER-001，Dockerfile/kernel.cu 正反例夹具）+ 规则 schema 增加 `updated` / `confidence` + `MXREADY_EXTRA_RULES_DIR` 自定义规则目录；P2-5 ✅ `allowed_hosts` 可配置（默认仍为 github.com + gitee.com，URL 规范化与无凭据校验保持）；P2-6 ✅ `docs/api.md` 中文 API 手册（含 curl 示例）。回归：后端 + runner 246 个测试、前端 20 个测试、ruff 全绿。⏳ P2-3 可选：openapi-typescript 从 OpenAPI 生成类型（计划书列为可选，未实施）。

**P2-1 API 限流与防护**

- 现状：设计文档已声明"公共部署前必须增加反滥用限流"；
- 建议操作：
  1. 引入轻量限流：`slowapi` 或自定义进程内 token bucket，至少限制"每 IP 每分钟扫描创建次数"与"验证上传次数"；默认关闭、环境变量开启；
  2. 通用请求体大小限制中间件：注意验证上传已有 1 MiB 上限，扫描创建请求体很小，补充一个整体上限即可（FastAPI 无内置 `maximum_request_size` 参数，需自写中间件或依赖）；
  3. 并发扫描数限制：通过数据库统计 `queued/cloning/indexing/analyzing` 状态的 job 数，超出上限直接 429。

**P2-2 Windows 开发体验优化**

- 建议操作：
  1. 创建 `scripts/dev.ps1` 一键启动前后端；
  2. 创建 `Makefile`（Linux/macOS）与 `make.ps1`（Windows），统一 `install` / `dev` / `test` / `lint` / `build`；
  3. 检查代码中 `Path` 均使用 `pathlib`，不硬编码 `/` 或 `\`（当前实现已满足，仅补测试覆盖）；
  4. 若出现仅 Linux 可跑的用例，用 `pytest.mark` 标记并在 `pyproject.toml` 配置 skip，而不是注释掉测试。

**P2-3 前端改进**

- 建议操作：
  1. 添加 `ErrorBoundary` 包裹各功能区域，防止单一组件崩溃导致白屏；
  2. 报告加载时展示骨架屏而非空白；
  3. 键盘可访问性：筛选按钮组方向键导航、FindingCard 展开/折叠支持 Enter/Space、视图切换焦点管理；
  4. 响应式优化：移动端（<768px）布局调整、表格窄屏横向滚动；
  5. 类型安全：考虑用 `openapi-typescript` 从后端 OpenAPI 生成类型，避免 `api/types.ts` 与 Pydantic 模型漂移。

**P2-4 规则引擎增强**

- 建议操作：
  1. 新增规则（每条走"正例 + 相似反例 + 一手参考"流程）：
     - `MXR-DOCKER-001`（info/warning）：检测 Dockerfile 中 NVIDIA 基础镜像或 `nvidia-docker` 相关配置——价值高，可直接实施；
     - `MXR-MEMORY-001`（info）：`cudaMalloc`/`cudaFree` 显存管理 API——参考 cu-bridge 映射表后定级；
     - `MXR-STREAM-001`（info）：`cudaStream` 系列 API——同上；
     - `MXR-DEVICE-001`（info）：`cudaSetDevice`/`cudaGetDevice` 设备管理 API——同上；
     - `MXR-KERNEL-002`（info）：`__syncthreads()` block 级同步是 CUDA 标准特性、cu-bridge 通常支持，定级不宜高于 info，需先验证映射文档再实施；
     - `MXR-BUILD-002`（存疑，暂缓）：`CUDA_VISIBLE_DEVICES` 不是 NVIDIA 专属变量，MXMACA 也用于设备索引，命中价值低，需先确认目标平台行为再决定是否立项；
  2. 支持 `MXREADY_EXTRA_RULES_DIR` 环境变量追加自定义规则目录（与 P1-2 配置重构联动）；
  3. 规则 schema 增加 `updated`（日期）与 `confidence`（documented / needs-review）字段，为 v2 与审计做准备；
  4. CI 中输出每条规则的命中/误报统计（配合测试夹具统计）。

**P2-5 代码托管平台扩展**

- 现状：白名单只允许 `github.com` 与 `gitee.com`；
- 建议操作：`Settings` 增加 `allowed_hosts` 可配置列表，默认保持 `github.com` + `gitee.com`，内部部署时经环境变量显式扩展；任何扩展都必须维持 URL 规范化、无凭据、无私有地址等既有校验。

**P2-6 中文 API 手册**

- 建议操作：新增 `docs/api.md`，给出每个端点的 curl 示例与中文说明，方便申报材料与服务器验收。

### 2.4 P3 —— 低优先级

> **执行记录（2026-08-02）**：P3-1 ✅ locust 压力测试脚本（`tests/load/locustfile.py`：health / rules / scan 三类负载，429 视为预期防护行为）+ `tests/load/serve_mock.py`（mock Git 直接复制本地夹具仓库，免公网依赖），端到端验证 mock 扫描链路成功（202 → completed → report 200）；`pyproject.toml` 新增 `load` 可选依赖组（`pip install -e ".[load]"`）。⏳ P3-1 剩余：实机压测待用户自行安装 load 依赖后运行 `python tests/load/serve_mock.py` + `locust`（不代装环境）。

**P3-1 测试增强**

- 建议操作：
  1. Windows 兼容性测试：已由 P1-3 的 CI 矩阵覆盖，补充路径处理与 git 命令的断言即可；
  2. 压力测试：使用 `locust` 添加基本并发扫描负载脚本（本地 fixture + mock Git，不依赖公网）；
  3. TOML/YAML 配置文件加载（如确需）——见 P1-2 备注。

## 3. 修改优化实施计划（按顺序执行）

| # | 任务 | 涉及文件 | 验证方式 | 优先级 |
| --- | --- | --- | --- | --- |
| 1 | 修正 `httpx2` → `httpx` 依赖 | `pyproject.toml` | `pip install -e ".[dev]"` 后 `pytest` 全绿；`pip uninstall httpx2` | P0 |
| 2 | 清理 `.pytest-temp/` 并加入 `.gitignore` | `.gitignore`、删除目录 | `git status` 干净 | P0 |
| 3 | 清理 `%TEMP%\pytest-of-*`，README 增加 Windows 故障排查 | `README.md` | 无 `--basetemp` 直接 `pytest` 通过 | P0 |
| 4 | Python 版本统一到 3.11 | 本机 venv 重建 | `python --version` 输出 3.11 | P0 |
| 5 | `Settings.from_env()` 环境变量注入 + `.env.example` | `backend/mxready/config.py`、新文件 `.env.example` | 新增配置读取测试；不同 env 组合下 app 启动 | P1 |
| 6 | 统一日志配置（JSON、级别、脱敏） | `backend/mxready/app.py`、`logging` 配置模块 | 日志输出断言（含脱敏） | P1 |
| 7 | SQLite 备份 + schema 版本表 + 可选 retention | `backend/mxready/storage.py`、`config.py` | 备份/迁移测试 | P1 |
| 8 | Dockerfile + docker-compose + .dockerignore | 新文件 | `docker build` 通过并启动冒烟；`docker compose up` 后可访问 `/api/health` | P1 |
| 9 | CI 矩阵（windows）+ pip-audit + 前端 tsc lint + Docker build job | `.github/workflows/ci.yml`、`frontend/package.json` | Actions 全绿 | P1 |
| 10 | 服务器交接辅助脚本 + Linux 容器演练 | `examples/verification/`、交接记录 | 演练记录写入 `docs/application-evidence.md` | P1 |
| 11 | 报告聚合与 Top 清单 | `backend/mxready/models.py`、`reporting/`、`api/scans.py` | 先写聚合测试，再重新生成示例报告 | P1 |
| 12 | 进程内限流 + 请求体上限 + 并发扫描上限 | `backend/mxready/api/`、`config.py` | 新增限流测试；默认关闭 | P2 |
| 13 | `docs/deployment.md` 部署文档 | 新文档 | 按文档复现 Docker/裸机两种部署 | P1 |
| 14 | 规则 schema 增加 `updated` / `confidence` + 自定义规则目录 | `rules/v1/core.yml`、`rule_loader.py`、`config.py` | 规则加载测试 | P2 |
| 15 | 新规则（DOCKER-001 先行，其余按映射表） | `rules/`、测试夹具 | 每条规则正反例 + 参考来源 | P2 |
| 16 | Windows 开发脚本（dev.ps1 / Makefile / make.ps1） | `scripts/` | 本机一键命令可用 | P2 |
| 17 | 前端 ErrorBoundary / 骨架屏 / 可访问性 / 响应式 | `frontend/src/` | `npm test` + `npm run build` | P2 |
| 18 | `allowed_hosts` 可配置（默认不变） | `config.py`、`repository/identity.py` | URL 校验测试 | P2 |
| 19 | `docs/api.md` 中文 API 手册 | 新文档 | 按文档复现 curl | P2 |
| 20 | 规则命中/误报统计 + locust 压力脚本 | CI、`tests/`、新脚本 | CI 输出统计；本机冒烟 | P3 |

## 4. 服务器测试准备清单（申请到服务器后）

按以下顺序执行，避免在窗口期返工：

1. **环境核对（申请时确认）**：GPU 型号、驱动 / MXMACA / cu-bridge / PyTorch 精确版本、是否允许编译小型 PyTorch 扩展、是否可联网；
2. **提交锁定**：按 `examples/verification/README.md` 第 2 步 `git fetch --depth 1` 固定 `1c325b202ae5e11de3cefb9a65be28f47949edd4`，`rev-parse HEAD` 必须一致；
3. **inspect 先行**：解压验证包，先跑 `mxready_runner inspect`，确认 `mx-smi` 与 `pytorch-device` 均 passed，失败即停止并保存脱敏日志；
4. **人工构建**：`pip install --no-build-isolation -e ./extension_cpp`，不使用 sudo；
5. **审阅并补充 smoke command**：确认 `project_commands` 只创建小张量、调用算子、比较结果；
6. **run + 人工确认**：输入精确 `yes`，核对 `overall_status == passed` 与提交一致；
7. **脱敏后带回**：人工检查 result.json 中的主机名、用户名、绝对 home 路径、内网 IP、token 等，只保存脱敏副本为 `examples/verification/metax-verification-redacted.json`；
8. **上传与归档**：在报告页上传副本，导出更新报告；把验证记录写入 `docs/application-evidence.md`；
9. **上游 PR（授权后）**：真机 smoke 通过后，先提交 Apex 补丁 PR，再考虑 extension-cpp 的最小文档 PR。

## 5. 里程碑安排

- **里程碑 A（本周，纯本地）**：完成 P0-1 ~ P0-4 与 P1-2（配置重构），本机后端/前端测试全绿，工作区干净；
- **里程碑 B（申请服务器前）**：完成 P1-1 / P1-3 / P1-6 / P1-8（Docker 化、CI 矩阵、交接脚本 + Linux 演练、部署文档），保证服务器窗口期不浪费；
- **里程碑 C（真机验证期间）**：按第 4 节清单完成验证，产出 `metax-verification-redacted.json`；
- **里程碑 D（验证后）**：完成 P1-4 / P1-5 / P1-7 与 P2/P3 项，提交上游 PR，更新申报材料。

## 6. 风险与红线

**决策更新（需随实施同步修改 README 与设计规格）**

- 采纳：为 MXReady 自身增加 Docker 容器化（仅用于演示/测试部署，非远程 GPU 服务器编排），README"MVP 不包含 Docker 编排"的表述同步更新为"不包含对远程 GPU 服务器上的项目进行 Docker 编排"；
- 采纳：配置支持环境变量注入（12-factor），默认值与 MVP 一致；
- 采纳：CI 覆盖 Windows + 多 Python 版本，并引入依赖安全扫描。

**保持不变的红线**

- 不放松任何安全限制（克隆 50 MiB / 10,000 文件 / 60 秒超时 / 默认仅两个托管域名）换取扫描通过；
- 不伪造真机验证结果：在拿到真实沐曦服务器结果前，报告保持 `verified` 以外状态；
- 聚合规则、限流、迁移等任何行为变更，都必须先写失败测试再改实现；
- 数据清理（retention）默认关闭，避免误删申报证据；
- 所有外部 PR 创建与提交需单独授权。

## 7. 验证命令（每次改动后回归）

```powershell
# 后端（Windows 若遇 tmp 权限错误，追加 --basetemp=$env:TEMP\mxr-pt）
.\.venv\Scripts\python.exe -m ruff check backend runner scripts tests
.\.venv\Scripts\python.exe -m pytest --cov=mxready --cov=mxready_runner --cov-fail-under=80

# 前端
cd frontend
npm test
npm run build

# Docker（P1-1 已实现）
docker build -t mxready .
docker compose up -d
# 打开 http://127.0.0.1:8000/api/health 验证
```

## 8. 执行记录（2026-08-03）：文档与仓库维护

- ✅ README 重写：新增三平台（Windows / Linux / macOS）一键启动入口表格（`dev.ps1` / `dev.sh`）、命令入口总表、`MXREADY_*` 配置对照表（修正：监听地址由 uvicorn 控制，无 `MXREADY_HOST/PORT`）、文档导航表；规则数更正为 24 条；
- ✅ 新增 `scripts/dev.sh`：Linux / macOS 一键启动前后端，与 `dev.ps1` 参数对齐（`--skip-frontend` / `--skip-backend`）；尚未在 Linux / macOS 真机验证（Windows 本机无 bash），语法与行为待 CI / 服务器确认；
- ✅ 文档一致性修正：`docs/application-evidence.md` 注明三份公开报告由 20 条规则生成、规则集 v1 已扩至 24 条（新增均为 info 级）；`docs/deployment.md` 环境变量表扩至 12 项并更新限流说明；本计划书完成度表格刷新为 246 后端测试 / 20 前端测试 / 24 条规则；
- ✅ 主要贡献人：README「主要贡献人」章节与 `pyproject.toml` `authors` 均记录为 `shuli-陆家勇`；
- ✅ GitHub 仓库设置同步：仓库描述（MXReady：静态检查 PyTorch CUDA 扩展向 MetaX MXMACA 迁移的就绪度）+ 6 个 Topics（pytorch / cuda / mxmaca / static-analysis / fastapi / python）；
- ✅ README 新增「当前进度」章节，**明确标注尚未本地验证项**：Docker 构建与启动未在本机实跑（无 Docker，仅 CI 验证）、`dev.sh` 未在 Linux / macOS 验证、Python 3.11 venv 未重建复测（当前 3.14.2）、真机沐曦 GPU 验证 pending；
- 回归状态：上述均为文档 / 仓库元数据改动，不影响代码；后端 246 测试、前端 20 测试、ruff 全绿结论保持有效。

## 9. 执行记录（2026-08-13）：竞态修复与规则版本治理

- ✅ 修复前端报告加载竞态（P0）：`frontend/src/App.tsx` 轮询 effect 的清理函数与取报告共用 `cancelled` 标志，扫描完成后切换视图会立即置位该标志，导致真实网络下取回的报告被丢弃、页面永久停在骨架屏。修复方式：取报告拆为独立 effect（依赖 `view.kind === "report-loading"`），与轮询 effect 各自维护取消标志；顺带修复 `initialJob` 为 completed / failed 时永远卡在进度页的缺口，并把 `visibleError` 区分轮询（`POLLING_FAILED`）与取报告（`REPORT_LOAD_FAILED`）两个阶段。新增回归测试（报告在视图切换后才 resolve 时仍须渲染），已验证旧代码下该测试必挂、新代码通过；
- ✅ 规则集版本治理：`rules/v1/manifest.yml` 的 `ruleset_version` 由 `"1"` 升为 `"2"`（24→30 条规则的语义变更，写入每份报告保证可复现）；同步更新 `test_rule_loader.py` / `test_scan_api.py` 中的版本断言与 `docs/rules.md` 清单示例；
- ✅ 前端规则数动态化：`App.tsx` 不再硬编码规则数量（此前 20/24/30 反复失配的根因），改为挂载时通过 `GET /api/rules` 拉取（`api/client.ts` 新增 `getRules()`），请求失败时头部优雅降级；新增前端断言测试；
- ✅ 事实层修补：`docs/rules.md` 事实清单补上缺失的 `imports_apex`；`test_facts.py` 新增 `imports_apex` 正反例直接测试与 shell 注释剥离测试（此前删除该 flag 无测试会红）；`facts.py` 的 `_extract_shell` 先剥离 `#` 注释再匹配，消除注释中 nvcc / nvidia-smi / CUDA_HOME / `/usr/local/cuda` 的误报，与 `_extract_cmake` 对齐；
- ✅ 验证包再生成：`examples/verification/pytorch-extension-cpp-verification.zip` 按当前代码重新生成（新增 `project-commands.example.json` 模板），两次构建 SHA-256 一致验证确定性；`docs/application-evidence.md` 的大小与 SHA-256 已同步（10,095 字节 / `255747681b…`）；
- ✅ 仓库卫生：`.gitignore` 增加 `.zcode/`；`.gitattributes` 增加 `*.sh text eol=lf`（防止 Windows 检出后 CRLF 导致服务器 bad interpreter）；
- ✅ 维护者笔名统一：README「主要贡献人」与 `pyproject.toml` `authors` 由 `shuli-陆家勇` 更新为笔名 `shuli-黍黎`（`shuli` 即笔名拼音）；2026-08-03 的历史执行记录保留当时原文，不改写；
- 回归状态：后端 + runner **263 个测试通过**（覆盖率 90.86%，80 门槛通过）、ruff 全绿、前端 **23 个测试通过**、`tsc -b` 与 `npm run build` 通过。

> 说明：评估曾建议把 MXR-PATH-001 / TOOL-001 / TOOLCHAIN-001 三条 regex 规则改为 fact 模式，经核实不可行——fact 提取面远窄于 regex（不含 `.py` 的 subprocess 调用、不含 `.cmake/.toml/.cfg` 覆盖），转换会降低召回，故保留 regex 规则，仅修复事实层自身的误报与文档缺失。
