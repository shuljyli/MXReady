# MXReady

[![CI](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml/badge.svg)](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.3.1-blue)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)

**中文** | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt-BR.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Русский](README.ru.md)

你要把一段跑在 NVIDIA 显卡上的 PyTorch 代码搬到沐曦 GPU 上，但不知道会踩哪些坑。

MXReady 先把代码读一遍（只读，不运行），把可能出问题的地方列出来：哪里直接调了 NVIDIA 的编译器、哪里按“32 个线程一组”写死了（沐曦是 64）、哪里内联了 NVIDIA 专有的汇编、哪里依赖了跑不起来的库。每条都会说清楚是哪个文件、第几行、为什么有问题、建议怎么改。

它不替你改代码，也不给“兼容性百分比”这种数字——命中几条规则推不出兼容概率。静态检查通过只代表没发现明显问题，真正的结论要在沐曦的机器上跑出来。

> MXReady 是社区原型，不是沐曦官方兼容性认证。静态检查通过不等于项目已经兼容 MXMACA；最终结论仍需要在相同提交和受控的沐曦 GPU 环境中验证。

## 它能做什么

- 接收 GitHub、Gitee 的公开 HTTPS 仓库，可以指定分支、标签或 40 位提交；
- 扫描 Python、C/C++、CUDA、CMake、Shell、TOML、YAML 等文本文件；
- 内置 **35 条规则**（`MXR-*`），每条结果都带文件、行号、命中的代码、建议和权威参考；
- 测试、示例和文档里出现的命中只算提示：仍然列进报告，但不会让整个项目被判成阻塞；
- 输出 JSON、Markdown、SVG 徽章，以及一个只依赖标准库的远程验证包；
- 静态结论和真机验证结论分开显示，不混在一起；
- 提供只读的本地目录 CLI，便于离线回归和生成示例报告；
- 可选 `mxready-mcp`：把扫描、报告与规则查询暴露为 4 个 MCP 工具，供支持 Model Context Protocol 的编码 Agent 调用；
- React 单页界面与 FastAPI 服务可以打包成同一个部署单元。

MVP 不包含私有仓库、自动修改源码、远程 GPU 服务器的 Docker 编排、云 GPU 调度、用户系统或百分比"兼容分数"。

## 在真实项目上发现了什么

[`NVIDIA/apex`](https://github.com/NVIDIA/apex) 在提交 `575968bc1f9127ccd61003a681472a83af4ff1a1` 上的体检结果：
**阻断 12 · 警告 65 · 提示 140**。完整报告见 [examples/reports/nvidia-apex.md](examples/reports/nvidia-apex.md)。

12 条阻断里最有代表性的四条：

| 位置 | 命中 | 为什么在沐曦上会坏 |
| --- | --- | --- |
| `csrc/welford.cu:36` | `#define WARP_SIZE 32` | 线程束宽度写死 32，沐曦是 64 |
| `nhwc_batch_norm_kernel.h:1245` | `int lane_id = threadIdx.x & 31;` | lane 0 和 lane 32 会被算成同一条 lane |
| `group_norm_nhwc.h:40` | `asm volatile("red.release.gpu.global.add.s32 …")` | 内联 PTX 绑定 NVIDIA 后端 |
| `setup.py:65` | `subprocess.check_output([cuda_dir + "/bin/nvcc", "-V"])` | 直接调 `nvcc` 探测版本，沐曦环境里没有这个命令 |

四条里有两条**能编译通过**，但 lane 计算和线程束宽度在 64 宽度的 wave 上会算出错误结果，测试也未必覆盖得到；
另两条在沐曦上直接编不过。这两类问题都会让一次迁移拖上几周。

## 架构

```text
React/Vite UI
      │ /api
      ▼
FastAPI ── SQLite 持久任务队列与报告
   │
   ├─ 原子领取 / 租约心跳 ── 受限 Git 获取 ── 只读文件索引 ── YAML 规则引擎
   ├─ JSON / Markdown / SVG 报告
   └─ 验证 ZIP ◀── 在用户控制的沐曦主机运行 ── result.json
```

Web 服务从不导入、安装、构建或执行被扫描仓库中的代码。远程 runner 只在用户控制的机器运行，并要求在执行项目命令前人工确认。

Python 代码统一放在 `src/`；默认规则和验证 schema 随安装包发布。目录约定、任务队列和升级说明见
[架构说明](docs/architecture.md)。修改模型后使用 `make contracts` 同步生成接口契约。

## 功能矩阵

| 能力 | 状态 | 验证方式 |
| --- | --- | --- |
| 公开仓库静态扫描（GitHub / Gitee，可指定分支、标签或 40 位提交） | 可用 | 端到端测试 + 示例报告 |
| 35 条 `MXR-*` 检查规则 | 可用 | 每条规则含正例与相似反例夹具 |
| 报告输出：JSON / Markdown / SVG 徽章 | 可用 | 契约测试 + `generate_contracts.py --check` |
| 远程验证包与标准库 runner | 可用 | 安装包回归 + 安全边界测试 |
| 三平台安装 ZIP 与含网页的 wheel/sdist | 可用 | 发布工作流在 Windows / Linux / macOS 实际安装并启动 |
| React 单页界面 | 可用 | Vitest + TypeScript 严格模式 |
| 批量评估（`mxready-scan-batch`） | 可用 | CLI 回归 |
| MCP 工具（`mxready-mcp`，需 `.[mcp]`） | 可用 | 后端测试 + 实际 stdio 握手 |
| 真机沐曦 GPU 验证 | 已完成一次脱敏验证（MetaX C500，`pytorch/extension-cpp` @ `1c325b2`） | runner `inspect` 五项环境检查与单卡 smoke 全部 `passed`；其他项目仍需各自验证 |

工程状态：`ruff check`、`ruff format --check`、`mypy`、契约校验与 `pytest` 用例全绿（当前 490 余条），
分支覆盖率 89%（门槛 80%）；CI 覆盖 Python 3.11 / 3.12 / 3.13 × Windows / Linux / macOS。

## 已知限制

- **不提供兼容性结论**。所有输出止步于静态风险提示与人工复核建议；"已在沐曦环境验证"必须绑定到具体提交、
  在受控沐曦 GPU 上跑出 `verified` 结果，且不超过 30 天。
- **规则精度尚未用大规模真实项目统计**。内置规则集的正反例来自受控夹具，并在 `examples/reports` 的公开仓库上复核（0 误报）；系统性误报率与漏报率仍需在更多真实项目上统计。条目清单与判级口径见[规则说明](docs/rules.md)。
- **真机验证结果有 30 天有效期**，过期后报告状态转为 `stale`，需要重新上传。
- **MVP 边界**：不支持私有仓库、不自动修改源码、不做云 GPU 调度、无用户系统、不给百分比兼容分数。
- **环境要求**：安装包不附带 Python 与 Git，需预装 Python 3.11+ 与 Git。Docker 镜像的构建与启动由 CI 覆盖。
- **前端未配置 ESLint / Prettier**，以 TypeScript 严格模式与 Vitest 兜底。

> 公开项目示例报告见 [examples/reports](examples/reports)：`pytorch-extension-cpp` 全部通过（4 条提示），
> `nvidia-apex` 为阻断状态（12 条阻断）。两份放在一起是为了说明报告会真的判绿，也会真的判红。
> 远程验证流程见 [examples/verification/README.md](examples/verification/README.md)。

## 安装包（Windows / Linux / macOS）

普通使用者可直接安装包含网页的发布包，无需 Node.js，也无需安装 PyTorch 或 GPU 驱动。
三平台均需预装 **Python 3.11+（含 pip/venv）和 Git**；首次安装默认联网下载 Python 依赖。

| 平台 | 安装包 | 完整解压后，在包目录中执行 |
| --- | --- | --- |
| Windows 10/11 | `mxready-0.3.1-windows.zip` | PowerShell：`.\install.ps1`，然后 `.\start.ps1` |
| Linux | `mxready-0.3.1-linux.zip` | `bash install.sh`，然后 `bash start.sh` |
| macOS（Apple Silicon / Intel） | `mxready-0.3.1-macos.zip` | `bash install.sh`，然后 `bash start.sh` |
| 已有 Python 环境 | `mxready-0.3.1-py3-none-any.whl` | 在专用 venv 中 `python -m pip install <wheel路径>`，然后 `mxready-serve` |

启动后打开 <http://127.0.0.1:8000>，终端中按 `Ctrl+C` 停止服务。
安装器在解压目录创建 `.venv/`，数据库保存在系统用户数据目录，升级替换程序时可保留历史报告。
ZIP 为 Python 应用安装包，不附带 Python/Git，也不是原生 EXE、DMG 或系统包管理器安装程序。

本地构建后从 `dist/` 获取安装包；已公开发布的附件见
[GitHub Releases](https://github.com/shuljyli/MXReady/releases)。若对应版本没有附件，按下文自行构建，
或在 GitHub Actions 中手动运行 `Release packages` 下载构建附件。
离线依赖准备、摘要校验、三平台详细步骤、数据迁移和卸载见
[安装与发布方案](docs/installation.md)。服务器部署见 [部署文档](docs/deployment.md)。

### 维护者生成安装包

先安装开发依赖，再执行：

| 平台 | 命令 |
| --- | --- |
| Windows (PowerShell) | `.\scripts\make.ps1 release` |
| Linux / macOS | `make release` |

构建器会安装并构建前端，将网页合入临时 Python 包，生成三个平台 ZIP、通用 wheel、源码包和
`SHA256SUMS.txt`，统一放在 Git 忽略的 `dist/`。
发布工作流配置了 Python 3.11/3.12 × Windows/Linux/macOS 的实际安装与启动冒烟；
本地验证结果与目标系统 CI 结果应分别确认。

```text
packaging/                安装模板（共享安装器、Windows / Unix 入口）
scripts/build_release.py  发布构建编排
scripts/smoke_release.py  离开源码目录后的安装与 HTTP 冒烟
src/mxready/cli/          安装后的命令行入口，含 mxready-serve
docs/installation.md      安装、升级、离线与发布方案
dist/                    生成产物，不提交到仓库
```

## 源码开发（三平台统一命令入口）

### 环境要求

- Python 3.11 或更高版本；
- Git；
- Node.js 22 或更高版本（只在开发或构建前端时需要）。

### 安装开发依赖

| 平台 | 命令 |
| --- | --- |
| Windows (PowerShell) | `.\scripts\make.ps1 install` |
| Linux / macOS | `make install` |

`install` 会创建 `.venv`、安装后端与开发依赖（`pip install -e ".[dev]"`）、执行 `npm ci`。

### 一键启动（前后端同时）

| 平台 | 命令 | 可选参数 |
| --- | --- | --- |
| Windows (PowerShell) | `.\scripts\dev.ps1` | `-SkipFrontend` / `-SkipBackend` |
| Linux / macOS | `bash ./scripts/dev.sh` | `--skip-frontend` / `--skip-backend` |

`dev.ps1` / `dev.sh` 会同时启动：

- 前端 Vite 开发服务器：<http://localhost:5173>（开发代理把 `/api` 转发到后端）；
- 后端 FastAPI：<http://127.0.0.1:8000>（`--reload` 热重载）。

开发模式请打开 <http://localhost:5173>。后端的 <http://127.0.0.1:8000> 在已有 `frontend/dist` 时提供构建后的完整界面，否则以 API-only 模式启动；API 文档位于 `/docs`，中文接口手册见 [docs/api.md](docs/api.md)。

### 命令入口总表

统一 `install` / `dev` / `test` / `lint` / `typecheck` / `build` / `release` / `frontend` / `clean`：

| 目标 | Windows (PowerShell) | Linux / macOS | 作用 |
| --- | --- | --- | --- |
| 安装依赖 | `.\scripts\make.ps1 install` | `make install` | venv + 后端依赖 + `npm ci` |
| 启动后端 | `.\scripts\make.ps1 dev` | `make dev` | uvicorn `--reload`，端口 8000 |
| 启动前端 | `.\scripts\make.ps1 frontend` | `make frontend` | Vite dev，端口 5173 |
| 运行测试 | `.\scripts\make.ps1 test` | `make test` | 后端 pytest（含覆盖率门槛） |
| 代码检查 | `.\scripts\make.ps1 lint` | `make lint` | ruff 检查 src / scripts / tests / packaging |
| 类型检查 | `.\scripts\make.ps1 typecheck` | `make typecheck` | mypy 检查 src / scripts |
| 构建前端 | `.\scripts\make.ps1 build` | `make build` | `npm run build` 产出 `frontend/dist` |
| 生成安装包 | `.\scripts\make.ps1 release` | `make release` | 网页 + wheel/sdist + 三平台 ZIP，产出 `dist/` |
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

### Windows 安装问题排查

如果他人运行 `.\scripts\make.ps1 install` 时失败，按下面顺序检查：

1. **执行策略**：先运行 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`。
2. **Python**：`py -3.11 --version` 或 `python --version` 应显示 3.11+。没有 `py` 启动器时，在 <https://www.python.org/downloads/> 安装时勾选 “Add python.exe to PATH”。
3. **Node.js**：`node --version` 应为 20.19+ 或 22.12+，`npm --version` 可用；否则安装 Node.js 22 LTS。
4. **Git**：扫描功能依赖 `git --version` 可用。
5. **网络下载失败**：国内环境优先使用镜像：

   ```powershell
   $env:PIP_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
   .\.venv\Scripts\python.exe -m pip install -e ".[dev]"

   cd frontend
   npm ci --registry=https://registry.npmmirror.com
   cd ..
   ```

6. **重复安装**：`make.ps1 install` 可以安全重跑，会刷新 Python 可编辑安装并按锁文件重新执行 `npm ci`。
7. **PowerShell 兼容性**：入口脚本保持 ASCII 源码，可由 Windows PowerShell 5.1 和 PowerShell 7 直接解析；项目运行日志仍使用 UTF-8。

如果以上步骤仍失败，请让使用者把 `install` 的完整报错和 `py --version`、`node --version`、`npm --version`、`git --version` 输出一起发给项目维护者。

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

后端配置支持 12-factor 风格的环境变量注入（见 [src/mxready/config.py](src/mxready/config.py)），常用项：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MXREADY_DATA_DIR` | `data` | SQLite 数据目录 |
| `MXREADY_RULES_DIR` | 安装包内规则 | 可选覆盖规则目录 |
| `MXREADY_TEMP_DIR` | `data/tmp` | 克隆与索引临时目录 |
| `MXREADY_FRONTEND_DIR` | 发布包内网页；源码为 `frontend/dist` | 可覆盖前端静态资源目录 |
| `MXREADY_LOG_LEVEL` | `INFO` | 日志级别 |
| `MXREADY_ALLOWED_HOSTS` | `github.com,gitee.com` | 允许的代码托管平台白名单 |
| `MXREADY_EXTRA_RULES_DIR` | 未设置 | 追加的自定义规则目录 |
| `MXREADY_SCAN_RETENTION_DAYS` | `0` | 扫描记录保留天数（0 = 不自动清理，保留历史记录） |
| `MXREADY_RATE_LIMIT_ENABLED` | 关闭 | 按 IP 的滑动窗口限流开关 |
| `MXREADY_RATE_LIMIT_PER_MINUTE` | `20` | 每 IP 每分钟请求上限 |
| `MXREADY_MAX_CONCURRENT_SCANS` | `2` | 原子并发扫描上限（0 表示不限制） |
| `MXREADY_MAX_REQUEST_BYTES` | `1048576` | 按实际接收字节数执行的请求体上限 |
| `MXREADY_SCAN_WORKER_THREADS` | `2` | 每进程消费者线程数 |
| `MXREADY_TASK_LEASE_SECONDS` | `120` | 任务执行租约秒数，至少 3 |

> 监听地址与端口由 uvicorn 的 `--host` / `--port`（或 `UVICORN_HOST` / `UVICORN_PORT`）控制，不在 `MXREADY_*` 中重复配置。完整模板见 [.env.example](.env.example)。

`mxready-serve` 使用自身的 `--host` / `--port` 参数，数据默认保存在系统用户目录；
上表的 `data` 与 `data/tmp` 是直接使用 uvicorn 的默认值，详见 [安装方案](docs/installation.md)。

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

终端直接输出极简检查结果（命中按严重程度排序，最多列出 5 条，其余见报告文件）：

```text
MXReady: blocked | 阻断 1 · 警告 2 · 提示 3
  阻断 MXR-TOOLCHAIN-001 检测直接 nvcc 工具调用 (setup.py:5)
  警告 MXR-DEPENDENCY-001 检测 flash-attn 依赖 (requirements.txt:2)
  警告 MXR-PATH-001 检测硬编码 CUDA 安装路径 (setup.py:4 x2)
  提示 MXR-CMAKE-001 识别 CMake CUDA 语言 (CMakeLists.txt:2)
  提示 MXR-HEADER-001 识别 cuda_runtime.h 头文件 (csrc/kernel.cu:1)
  … 其余 1 项见报告文件
报告: cuda-extension-dddddddddddd.json / cuda-extension-dddddddddddd.md / cuda-extension-dddddddddddd.svg
```

## 公开仓库证据与验证包

需要生成固定文件名的公开报告时，可使用同一套主机白名单、Git 限制和只读分析器：

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

生成清单默认不含项目命令（ZIP 内附 `project-commands.example.json` 模板，需人工审阅并替换为实际 smoke 命令后填入清单）。请先阅读 [真机验证交接](examples/verification/README.md)，再在自己控制的沐曦服务器上人工补充并执行命令。

### 批量评估多个仓库

迁移评估通常面对一批仓库。`mxready-scan-batch` 接收清单文件（每行一个仓库，
可选分支/标签/40 位提交，`#` 注释）或直接传 URL，逐仓复用与单仓扫描相同的安全
获取与只读分析管线，输出每仓报告和汇总总表：

```bash
mxready-scan-batch repos.txt --output data/batch
# 或混合来源：mxready-scan-batch repos.txt https://github.com/pytorch/extension-cpp
```

```text
[1/3] pytorch/extension-cpp → warnings（阻断 0 · 警告 2 · 提示 1）
[2/3] example/missing-repo → 失败: REPOSITORY_NOT_FOUND: 未找到仓库或指定分支、标签、提交，请检查输入。
[3/3] example/cuda-ext → blocked（阻断 1 · 警告 2 · 提示 3）
汇总: 成功 2 · 失败 1（其中阻塞 1）
报告: data/batch/batch-summary.csv 与 data/batch/batch-summary.md
```

`batch-summary.csv`（UTF-8 BOM，Excel 可直接打开）逐仓记录提交、状态、三档计数、
主要规则与报告文件；`batch-summary.md` 生成带链接的汇总表，适合直接贴进评估结论。
退出码：`0` 全部成功且无阻塞，`2` 成功但存在阻塞仓库，`1` 存在扫描失败。

## MCP（供编码 Agent 调用）

`mxready-mcp` 把同一套扫描管线暴露为 Model Context Protocol 工具。它的用途是让编码 Agent
在动手改代码前拿到可核验的迁移事实，而不是凭模型记忆猜测 CUDA 与 MXMACA 的差异。

它依赖可选的 `mcp` 包，不在核心运行时依赖内：

```bash
python -m pip install -e ".[mcp]"
mxready-mcp
```

默认使用 stdio 传输；日志固定写 stderr，stdout 只承载协议消息。暴露的工具：

| 工具 | 作用 |
| --- | --- |
| `scan_repository` | 扫描公开仓库，在超时内返回按严重度排序的发现（含 file:line、证据与建议） |
| `get_report` | 按 `scan_id` 重新取回已完成的报告 |
| `list_rules` | 列出内置规则，可按 `category` / `severity` 过滤 |
| `explain_rule` | 返回单条规则的判据、建议与一手引用 |

边界与 CLI 完全一致：仅接受公开 GitHub / Gitee 仓库、不执行被扫描代码、结果绑定到具体提交。
静态结论仍然不是真机验证结论——`verification_status` 保持 `not-run`，除非上传了同提交的
沐曦 GPU 验证结果。

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
python -m ruff check src scripts tests packaging
python -m ruff format --check src scripts tests packaging
python -m mypy
python scripts/generate_contracts.py --check
python -m pytest --cov=mxready --cov=mxready_runner --cov-fail-under=80

cd frontend
npm test
npm run build
```

压力测试脚本（locust，本地 mock Git、不依赖公网）见 [tests/load/](tests/load/)，先执行 `pip install -e ".[load]"`，再运行 `python tests/load/serve_mock.py` 与 `locust`。

## 文档导航

| 文档 | 内容 |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | 目录层级、依赖方向、任务生命周期与包资源约定 |
| [docs/deployment.md](docs/deployment.md) | 生产部署：裸机 / systemd / Docker / nginx / 备份 / 日志 |
| [docs/api.md](docs/api.md) | 中文 API 手册（含 curl 示例） |
| [docs/installation.md](docs/installation.md) | 三平台安装包、离线准备、升级与发布构建 |
| [docs/security.md](docs/security.md) | 安全模型 |
| [docs/rules.md](docs/rules.md) | 规则开发指南 |
| [docs/runner.md](docs/runner.md) | 远程验证 runner 指南 |
| [examples/verification/README.md](examples/verification/README.md) | 真机验证交接 SOP |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更记录 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献流程与质量门 |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | 社区行为准则 |

## 安全边界

- 仅允许 `github.com` 与 `gitee.com` 的公开 HTTPS 仓库（`MXREADY_ALLOWED_HOSTS` 可扩展，但维持 URL 规范化、无凭据、无私有地址校验）；
- Git 不读取凭据、不弹出登录提示、不下载 LFS 对象、不初始化子模块；
- Git 获取超时 60 秒；克隆完成后的工作树最多 50 MiB、10,000 个文件；归档后备路径在下载及展开阶段分别执行 50 MiB、10,000 条目上限；
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
2. 在更多公开项目上完成相同提交的脱敏真机验证（已完成 `pytorch/extension-cpp` @ `1c325b2`）；
3. 选择一个上游项目提交小范围、可评审的迁移 PR；
4. 根据真实适配反馈扩充规则与最小验证模板。

## 主要贡献人

- **shuli-黍黎** —— 项目发起人与主要开发者。

## 许可证

本项目采用 [Apache License 2.0](LICENSE) 许可证。欢迎在遵守许可证条款的前提下使用、修改和分发。
