# MXReady

[![CI](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml/badge.svg)](https://github.com/shuljyli/MXReady/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.0.1-blue)](CHANGELOG.md)
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
- 输出 JSON、Markdown、SVG 徽章和可打印的 HTML 报告（浏览器打印转 PDF），以及一个只依赖标准库的远程验证包；
- 静态结论和真机验证结论分开显示，不混在一起；
- 提供只读的本地目录 CLI，便于离线回归和生成示例报告；
- 可选 `mxready-mcp`：把扫描、任务状态、报告与规则查询暴露为 5 个 MCP 工具，供支持 Model Context Protocol 的编码 Agent 调用；
- React 单页界面与 FastAPI 服务可以打包成同一个部署单元。

网页界面提供“源码体检”“批量扫描”“扫描历史”“迁移进度”“规则库”“MCP 接入”和“命令行使用”页面；
报告支持优先文件定位、分页检索、对比分享、人工复核清单与 HTML 打印导出。MCP 与 Web 互相读取
报告时需显式共用同一本地数据目录。

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

另外两个固定提交的案例补上了阻断与修复闭环两侧的证据：

- [`bitsandbytes`](https://github.com/bitsandbytes-foundation/bitsandbytes)（`a616886`）：27 条发现、7 条阻断，
  报告见 [examples/reports/bitsandbytes.md](examples/reports/bitsandbytes.md)。
- [`causal-conv1d`](https://github.com/Dao-AILab/causal-conv1d)（`cd81f04`）：按报告修复后发现数下降、
  在 MetaX C500 上真机验证全部 `passed`，详见 [迁移案例记录](docs/migration-case-2026-11.md)。

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
| 报告输出：JSON / Markdown / HTML / SVG 徽章 | 可用 | 契约测试 + `generate_contracts.py --check` |
| 迁移进度仪表盘（跨仓库聚合、阻塞项趋势） | 可用 | 后端聚合测试 + Vitest |
| 远程验证包与标准库 runner | 可用 | 安装包回归 + 安全边界测试 |
| 三平台安装 ZIP 与含网页的 wheel/sdist | 可用 | 发布工作流在 Windows / Linux / macOS 实际安装并启动 |
| React 单页界面 | 可用 | Vitest + TypeScript 严格模式 |
| 批量评估（`mxready-scan-batch`） | 可用 | CLI 回归 |
| MCP 工具（`mxready-mcp`，需 `.[mcp]`） | 可用 | 后端测试 + 实际 stdio 握手 |
| 真机沐曦 GPU 验证 | 已完成两次脱敏验证（MetaX C500：`pytorch/extension-cpp` @ `1c325b2`、`causal-conv1d` @ `cd81f04`） | runner `inspect` 五项环境检查与单卡 smoke 全部 `passed`；causal-conv1d 的构建使用了未提交上游的临时补丁，其他项目仍需各自验证 |

工程状态：`ruff`、`mypy`、契约校验与 `pytest` 全绿（540 余条用例，分支覆盖率 90%）；
CI 覆盖 Python 3.11 / 3.12 / 3.13 × Windows / Linux / macOS，另有 Python 3.10 的 runner 作业。

## 已知限制

- **不提供兼容性结论**。所有输出止步于静态风险提示与人工复核建议；"已在沐曦环境验证"必须绑定到具体提交、
  在受控沐曦 GPU 上跑出 `verified` 结果，且不超过 30 天。
- **规则精度尚未用大规模真实项目统计**。正反例来自受控夹具并在公开仓库上复核（0 误报），
  系统性误报率与漏报率仍需更多真实项目统计，见[规则说明](docs/rules.md)。
- **真机验证结果有 30 天有效期**，过期后报告状态转为 `stale`，需要重新上传。
- **MVP 边界**：不支持私有仓库、不自动修改源码、不做云 GPU 调度、无用户系统、不给百分比兼容分数。

> 公开项目示例报告见 [examples/reports](examples/reports)：`pytorch-extension-cpp` 全部通过（4 条提示），
> `nvidia-apex`（12 条阻断）与 `bitsandbytes`（7 条阻断）为阻塞状态，`causal-conv1d` 保留修复前/后两份。
> 放在一起是为了说明报告会真的判绿，也会真的判红。远程验证流程见
> [examples/verification/README.md](examples/verification/README.md)。

## 安装与启动

普通使用者直接安装包含网页的发布包即可，无需 Node.js，也无需安装 PyTorch 或 GPU 驱动；
三平台均需预装 **Python 3.11+（含 pip/venv）和 Git**，首次安装默认联网下载 Python 依赖。

| 平台 | 安装包 | 完整解压后，在包目录中执行 |
| --- | --- | --- |
| Windows 10/11 | `mxready-1.0.1-windows.zip` | PowerShell：`.\install.ps1`，然后 `.\start.ps1` |
| Linux | `mxready-1.0.1-linux.zip` | `bash install.sh`，然后 `bash start.sh` |
| macOS（Apple Silicon / Intel） | `mxready-1.0.1-macos.zip` | `bash install.sh`，然后 `bash start.sh` |
| 自行管理 Python 环境 | PyPI 上的 `mxready` | `python -m pip install mxready`，然后 `mxready-serve` |
| 已有 Python 环境 | `mxready-1.0.1-py3-none-any.whl` | 在专用 venv 中 `python -m pip install <wheel路径>`，然后 `mxready-serve` |

启动后打开 <http://127.0.0.1:8000>，终端中按 `Ctrl+C` 停止服务。ZIP 是 Python 应用安装包，
不附带 Python/Git，也不是原生 EXE、DMG 或系统包管理器安装程序。已发布的附件见
[GitHub Releases](https://github.com/shuljyli/MXReady/releases)；离线准备、摘要校验、升级、
卸载与 Windows 问题排查见 [安装与发布方案](docs/installation.md)。

维护者构建安装包：安装开发依赖后执行 `make release`（Windows：`.\scripts\make.ps1 release`），
产物在 Git 忽略的 `dist/`。服务器部署（裸机 / systemd / Docker / nginx）与 `MXREADY_*` 配置项
见 [部署文档](docs/deployment.md) 与 [.env.example](.env.example)。

### 源码开发

环境要求：Python 3.11+、Git、Node.js 22+（仅开发/构建前端时需要）。

```bash
make install                # 创建 .venv、安装开发依赖、npm ci（Windows：.\scripts\make.ps1 install）
bash ./scripts/dev.sh       # 前后端一键启动（Windows：.\scripts\dev.ps1）
```

`dev.sh` / `dev.ps1` 同时启动前端 <http://localhost:5173>（`/api` 代理到后端）与后端
<http://127.0.0.1:8000>（`--reload` 热重载）。开发模式请打开 5173；后端在已有
`frontend/dist` 时提供完整界面，API 文档位于 `/docs`，中文接口手册见 [docs/api.md](docs/api.md)。

统一命令入口（`install` / `dev` / `frontend` / `test` / `lint` / `typecheck` / `build` / `release` / `clean`）：

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

## 命令行工具

`mxready-scan`（本地目录）、`mxready-scan-public`（公开仓库证据）、`mxready-build-bundle`（验证包）、
`mxready-scan-batch`（批量评估）与 `mxready-mcp`（供编码 Agent）的详细用法与退出码约定见
[命令行使用](docs/cli.md)。所有 CLI 只读分析，不执行被扫描代码。

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

压力测试脚本（locust，本地 mock Git、不依赖公网）见 [tests/load/](tests/load/)。

## 文档导航

| 文档 | 内容 |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | 目录层级、依赖方向、任务生命周期与包资源约定 |
| [docs/deployment.md](docs/deployment.md) | 生产部署：裸机 / systemd / Docker / nginx / 备份 / 日志 / 配置项 |
| [docs/api.md](docs/api.md) | 中文 API 手册（含 curl 示例） |
| [docs/cli.md](docs/cli.md) | 命令行工具与 MCP 详细用法 |
| [docs/installation.md](docs/installation.md) | 三平台安装包、离线准备、升级、发布构建与 Windows 排查 |
| [docs/report-workflow.md](docs/report-workflow.md) | 完整命中、扫描范围、报告对比、SARIF 与 CI 接入 |
| [docs/security.md](docs/security.md) | 安全模型 |
| [docs/rules.md](docs/rules.md) | 规则开发指南 |
| [docs/runner.md](docs/runner.md) | 远程验证 runner 指南 |
| [docs/migration-case-2026-11.md](docs/migration-case-2026-11.md) | 真实仓库案例：阻断诊断、修复与真机复验 |
| [examples/verification/README.md](examples/verification/README.md) | 真机验证交接 SOP |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更记录 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献流程与质量门 |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | 社区行为准则 |

## 安全边界

- 仅允许 `github.com` 与 `gitee.com` 的公开 HTTPS 仓库；Git 不读取凭据、不下载 LFS、不初始化子模块，获取有超时与体积/条目上限；
- Web 扫描从不执行仓库代码；验证结果上限 1 MiB 并绑定扫描提交；
- runner 不使用 `sudo`、不安装软件，命令以 `shell=False` 执行，项目命令执行前要求人工确认；
- 公共部署前应开启限流与请求体大小限制。

部署前请完整阅读 [安全模型](docs/security.md) 与 [runner 指南](docs/runner.md)。

## 参与贡献

新规则必须同时提供正例、相似反例和一手技术资料。请阅读：

- [贡献指南](CONTRIBUTING.md)
- [规则开发指南](docs/rules.md)
- [远程验证指南](docs/runner.md)
- [安全模型](docs/security.md)

## MVP 路线图

1. 用三个公开 CUDA 扩展项目生成可复现报告并校正规则精度；
2. 在更多公开项目上完成相同提交的脱敏真机验证（已完成 `pytorch/extension-cpp` @ `1c325b2` 与 `causal-conv1d` @ `cd81f04`）；
3. 选择一个上游项目提交小范围、可评审的迁移 PR；
4. 根据真实适配反馈扩充规则与最小验证模板。

## 主要贡献人

- **shuli-黍黎** —— 项目发起人与主要开发者。

## 许可证

本项目采用 [Apache License 2.0](LICENSE) 许可证。欢迎在遵守许可证条款的前提下使用、修改和分发。

## 联系方式

问题、建议与合作欢迎提交 GitHub Issue，或邮件联系：

- shuli_ljy@outlook.com
- 2199553510@qq.com
