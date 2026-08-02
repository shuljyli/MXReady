# MXReady

[![CI](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml/badge.svg)](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml)

MXReady 是一个面向 Python、PyTorch CUDA 扩展项目的**迁移准备度体检工具**。在申请稀缺的沐曦 GPU 算力之前，它用可解释的静态规则定位 CUDA 工具链、架构参数、原生依赖和构建配置中值得复核的迁移风险，并生成固定到具体 Git 提交的报告与远程验证包。

> MXReady 是社区原型，不是沐曦官方兼容性认证。静态检查通过不等于项目已经兼容 MXMACA；最终结论仍需要在相同提交和受控的沐曦 GPU 环境中验证。

## 当前能力

- 接收 GitHub、Gitee 的公开 HTTPS 仓库，以及可选的分支、标签或 40 位提交；
- 扫描 Python、C/C++、CUDA、CMake、Shell、TOML、YAML 等受支持文本文件；
- 提供 **24 条首批规则**（`MXR-*`），每条结果包含文件、行号、证据、建议和权威参考；
- 输出 JSON、Markdown、SVG 徽章与标准库远程验证包；
- 明确区分静态状态与真机验证状态；
- 提供只读本地目录 CLI，便于离线回归和生成申报材料；
- React 单页界面与 FastAPI 服务可打包为同一个部署单元。

MVP 不包含私有仓库、自动修改源码、远程 GPU 服务器的 Docker 编排、云 GPU 调度、用户系统或百分比"兼容分数"。

## 架构

```text
React/Vite UI
      │ /api
      ▼
FastAPI ── SQLite
   │
   ├─ 受限 Git 获取 ── 只读文件索引 ── YAML 规则引擎
   ├─ JSON / Markdown / SVG 报告
   └─ 验证 ZIP ◀── 在用户控制的沐曦主机运行 ── result.json
```

Web 服务从不导入、安装、构建或执行被扫描仓库中的代码。远程 runner 只在用户控制的机器运行，并要求在执行项目命令前人工确认。

## 快速开始（三平台统一命令入口）

### 环境要求

- Python 3.11 或更高版本；
- Git；
- Node.js 22 或更高版本（只在开发或构建前端时需要）。

### 一键安装

| 平台 | 命令 |
| --- | --- |
| Windows (PowerShell) | `.\scripts\make.ps1 install` |
| Linux / macOS | `make install` |

`install` 会创建 `.venv`、安装后端与开发依赖（`pip install -e ".[dev]"`）、执行 `npm ci`。

### 一键启动（前后端同时）

| 平台 | 命令 | 可选参数 |
| --- | --- | --- |
| Windows (PowerShell) | `.\scripts\dev.ps1` | `-SkipFrontend` / `-SkipBackend` |
| Linux / macOS | `./scripts/dev.sh` | `--skip-frontend` / `--skip-backend` |

`dev.ps1` / `dev.sh` 会同时启动：

- 前端 Vite 开发服务器：<http://localhost:5173>（开发代理把 `/api` 转发到后端）；
- 后端 FastAPI：<http://127.0.0.1:8000>（`--reload` 热重载）。

打开 <http://127.0.0.1:8000> 即可使用完整界面。如果暂时不构建前端，服务仍会以 API-only 模式启动，API 文档位于 `/docs`，中文接口手册见 [docs/api.md](docs/api.md)。

### 命令入口总表

统一 `install` / `dev` / `test` / `lint` / `build` / `frontend` / `clean`：

| 目标 | Windows (PowerShell) | Linux / macOS | 作用 |
| --- | --- | --- | --- |
| 安装依赖 | `.\scripts\make.ps1 install` | `make install` | venv + 后端依赖 + `npm ci` |
| 启动后端 | `.\scripts\make.ps1 dev` | `make dev` | uvicorn `--reload`，端口 8000 |
| 启动前端 | `.\scripts\make.ps1 frontend` | `make frontend` | Vite dev，端口 5173 |
| 运行测试 | `.\scripts\make.ps1 test` | `make test` | 后端 pytest（含覆盖率门槛） |
| 代码检查 | `.\scripts\make.ps1 lint` | `make lint` | ruff 检查 backend / runner / scripts / tests |
| 构建前端 | `.\scripts\make.ps1 build` | `make build` | `npm run build` 产出 `frontend/dist` |
| 清理 | `.\scripts\make.ps1 clean` | `make clean` | 删除 `.pytest-temp` |

> **Windows 常见问题**：本仓库已在 [pyproject.toml](pyproject.toml) 中将 pytest 临时目录固定到项目本地 `.pytest-temp/`（已加入 `.gitignore`），因此正常测试不会写入 `%TEMP%\pytest-of-*`。
>
> 若你看到 `%TEMP%\pytest-of-<用户名>` 报 `PermissionError`，通常是某个提权终端运行 pytest 时创建了带异常权限的残留目录。该目录普通权限无法删除，可改用固定 basetemp 运行（无需处理僵尸目录）：
>
> ```powershell
> .\.venv\Scripts\python.exe -m pytest --basetemp="$env:TEMP\mxr-pytest"
> ```
>
> 若确要清理僵尸目录，请在**管理员 PowerShell** 中执行：
>
> ```powershell
> takeown /f "$env:TEMP\pytest-of-*" /r /d y
> icacls "$env:TEMP\pytest-of-*" /grant "$env:USERNAME:(OI)(CI)F" /t /c
> Remove-Item -Recurse -Force "$env:TEMP\pytest-of-*"
> ```

## Docker 部署

MXReady 自带多阶段 [Dockerfile](Dockerfile) 与 [docker-compose.yml](docker-compose.yml)，用于自身的演示/测试部署（不涉及远程 GPU 服务器的 Docker 编排）。

```bash
docker compose up -d --build
# 打开 http://127.0.0.1:8000 ，健康检查：curl http://127.0.0.1:8000/api/health
```

- 镜像以非 root 用户 `mxready` 运行，SQLite 数据经命名卷 `mxready-data` 持久化到 `/app/data`；
- 全部配置项通过 `MXREADY_*` 环境变量注入（见 [.env.example](.env.example)），例如：

```bash
MXREADY_LOG_LEVEL=DEBUG docker compose up -d
```

- 手动构建：`docker build -t mxready . && docker run -p 8000:8000 mxready`
- 完整部署方案（裸机 / systemd / nginx / 备份 / 日志）见 [docs/deployment.md](docs/deployment.md)。

## 配置

后端配置支持 12-factor 风格的环境变量注入（见 [backend/mxready/config.py](backend/mxready/config.py)），常用项：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MXREADY_DATA_DIR` | `data` | SQLite 数据目录 |
| `MXREADY_RULES_DIR` | `rules/v1` | 规则目录 |
| `MXREADY_TEMP_DIR` | `data/tmp` | 克隆与索引临时目录 |
| `MXREADY_FRONTEND_DIR` | `frontend/dist` | 前端静态资源目录 |
| `MXREADY_LOG_LEVEL` | `INFO` | 日志级别 |
| `MXREADY_ALLOWED_HOSTS` | `github.com,gitee.com` | 允许的代码托管平台白名单 |
| `MXREADY_EXTRA_RULES_DIR` | 未设置 | 追加的自定义规则目录 |
| `MXREADY_SCAN_RETENTION_DAYS` | `0` | 扫描记录保留天数（0 = 不自动清理，保护申报证据） |
| `MXREADY_RATE_LIMIT_ENABLED` | 关闭 | 按 IP 的滑动窗口限流开关 |
| `MXREADY_RATE_LIMIT_PER_MINUTE` | `20` | 每 IP 每分钟请求上限 |
| `MXREADY_MAX_CONCURRENT_SCANS` | `2` | 并发扫描上限（0 表示不限制） |
| `MXREADY_MAX_REQUEST_BYTES` | `1048576` | 请求体大小上限 |

> 监听地址与端口由 uvicorn 的 `--host` / `--port`（或 `UVICORN_HOST` / `UVICORN_PORT`）控制，不在 `MXREADY_*` 中重复配置。完整模板见 [.env.example](.env.example)。

## 离线 fixture 扫描

本地 CLI 只用于开发者信任的本地目录；公开 Web API 不接受本地路径。

```bash
mxready-scan tests/fixtures/repositories/cuda_extension \
  --repo-url https://github.com/example/cuda-extension \
  --commit dddddddddddddddddddddddddddddddddddddddd \
  --output data/reports
```

PowerShell 单行写法：

```powershell
mxready-scan tests/fixtures/repositories/cuda_extension --repo-url https://github.com/example/cuda-extension --commit dddddddddddddddddddddddddddddddddddddddd --output data/reports
```

命令生成 `<仓库>-<commit12>.json`、`.md` 和 `.svg`。退出码为：`0` 表示通过或仅有警告，`2` 表示存在阻塞项，`1` 表示操作失败。

## 公开仓库证据与验证包

需要生成固定文件名的申报证据时，可使用同一套主机白名单、Git 限制和只读分析器：

```bash
mxready-scan-public https://github.com/pytorch/extension-cpp \
  --ref 1c325b202ae5e11de3cefb9a65be28f47949edd4 \
  --label pytorch-extension-cpp \
  --output examples/reports
```

GitHub 的 Git 传输超时或内部失败时，该本地证据命令可以改用提交锁定的安全归档；每个 HTTP 请求有 60 秒总时限，压缩与展开后的内容受 50 MiB 限制，归档中的目录和符号链接也计入 10,000 条目上限。Web API 仍使用受限 Git 获取路径。

从 JSON 报告生成安全默认验证 ZIP：

```bash
mxready-build-bundle examples/reports/pytorch-extension-cpp.json \
  --output examples/verification/pytorch-extension-cpp-verification.zip
```

生成清单默认不含项目命令。请先阅读 [申报证据](docs/application-evidence.md) 与 [真机验证交接](examples/verification/README.md)，再在自己控制的沐曦服务器上人工补充并执行命令。服务器窗口期的执行清单见 [修改优化计划书](docs/optimization-plan.md) 第 4 节。

## 状态含义

| 状态 | 含义 |
| --- | --- |
| `passed` | 未命中阻塞项或警告，仍需真机验证 |
| `warnings` | 有需要人工复核的迁移风险 |
| `blocked` | 有应在申请远程算力前处理的阻塞项 |
| `not-run` | 尚未上传沐曦环境验证结果 |
| `verified` | 相同提交的 `mx-smi` 与 PyTorch 设备检查通过，全部环境检查成功且结果不超过 30 天；不等同于完整项目认证 |
| `failed` | 验证命令失败 |
| `stale` | 验证结果超过 30 天，需要重新运行 |

报告故意不提供百分比兼容分数，因为规则命中数不能代表项目兼容概率。

## 测试

```bash
python -m ruff check backend runner scripts tests
python -m pytest --cov=mxready --cov=mxready_runner --cov-fail-under=80

cd frontend
npm test
npm run build
```

压力测试脚本（locust，本地 mock Git、不依赖公网）见 [tests/load/](tests/load/)，先执行 `pip install -e ".[load]"`，再运行 `python tests/load/serve_mock.py` 与 `locust`。

## 文档导航

| 文档 | 内容 |
| --- | --- |
| [docs/deployment.md](docs/deployment.md) | 生产部署：裸机 / systemd / Docker / nginx / 备份 / 日志 |
| [docs/api.md](docs/api.md) | 中文 API 手册（含 curl 示例） |
| [docs/security.md](docs/security.md) | 安全模型 |
| [docs/rules.md](docs/rules.md) | 规则开发指南 |
| [docs/runner.md](docs/runner.md) | 远程验证 runner 指南 |
| [docs/application-evidence.md](docs/application-evidence.md) | 申报证据与可复现验证 |
| [docs/optimization-plan.md](docs/optimization-plan.md) | 修改优化计划书（P0~P3 执行记录） |
| [examples/verification/README.md](examples/verification/README.md) | 真机验证交接 SOP |

## 安全边界

- 仅允许 `github.com` 与 `gitee.com` 的公开 HTTPS 仓库（`MXREADY_ALLOWED_HOSTS` 可扩展，但维持 URL 规范化、无凭据、无私有地址校验）；
- Git 不读取凭据、不弹出登录提示、不下载 LFS 对象、不初始化子模块；
- Git 获取超时 60 秒；归档后备路径的每个 HTTP 请求也有 60 秒总时限；仓库最多 50 MiB、10,000 个文件或归档条目；
- 单个索引文本文件最多 1 MiB，不跟随符号链接；
- Web 扫描不执行仓库代码；
- 验证结果最多 1 MiB，使用严格版本化模型并绑定扫描提交；
- runner 不使用 `sudo`、不安装软件、不修改驱动，命令以参数数组和 `shell=False` 执行；
- 公共部署前应开启 `MXREADY_RATE_LIMIT_ENABLED` 限流（按 IP 滑动窗口）与请求体大小限制。

部署前请完整阅读 [安全模型](docs/security.md) 与 [runner 指南](docs/runner.md)。

## 参与贡献

新规则必须同时提供正例、相似反例和一手技术资料。请阅读：

- [贡献指南](CONTRIBUTING.md)
- [规则开发指南](docs/rules.md)
- [远程验证指南](docs/runner.md)
- [安全模型](docs/security.md)

## MVP 路线图

1. 用三个公开 CUDA 扩展项目生成可复现报告并校正规则精度；
2. 申请沐曦远程服务器，完成至少一次相同提交的脱敏验证；
3. 选择一个上游项目提交小范围、可评审的迁移 PR；
4. 根据真实适配反馈扩充规则与最小验证模板。

## 许可证

本项目采用 [Apache License 2.0](LICENSE)。
