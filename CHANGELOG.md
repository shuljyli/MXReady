# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与
[语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Changed

- Python 代码统一为 `src/` 布局：Web 与 CLI 位于 `src/mxready/`，独立标准库 runner
  位于 `src/mxready_runner/`；SQLite 适配器移至 `mxready.persistence.sqlite`，开发脚本保留在
  `scripts/`。命令行入口名称与 HTTP 路由保持一致。
- 规则与验证 schema 作为包资源发布，CLI 与验证 ZIP 不再依赖源码根目录或当前工作目录。
- 扫描通过持久化 SQLite 队列、原子领取和可续期租约执行；增加状态与保留清理索引，清理只删除终态记录。
- 报告增加可选规则摘要、扩展规则版本和分析配置字段，旧报告仍可读取；Markdown 同步显示来源信息。
- TypeScript 响应类型与验证结果 JSON Schema 从后端模型生成，CI 检查生成物是否同步。
- 文件索引预计算行位置；规则评估增加 10,000 条唯一命中与 30 秒协作式预算，超限任务明确失败。
- 页面通过 URL 保存扫描 ID，支持刷新恢复、取消请求、15 秒请求超时及有限退避重试。

### Fixed

- 修复启动其他 API 进程时将活跃扫描误标为失败的问题；队列任务可在服务重启后继续领取。
- 修复验证结果仅在上传时检查有效期的问题；报告、徽章和下载内容读取时统一重算 30 天状态。
- 修复 wheel 缺失规则与 schema、安装后无法生成自包含验证 ZIP 的问题；增加 sdist/wheel 隔离冒烟测试。
- runner 在采集阶段限制每条输出流的保留量，持续排空超额日志，避免在截断前无限缓存输出。

## [0.1.0] - 2026-10-19

首次开源发布。

### Added

- 面向 Python / PyTorch CUDA 扩展项目的静态迁移准备度体检服务（FastAPI + React/Vite）。
- 30 条 `MXR-*` 检查规则，覆盖 CUDA 工具链、架构参数、Dockerfile、显存、Stream、Device、
  通信后端、数学库、测试跳过与混合精度等类别，并附带正反例夹具。
- JSON、Markdown 与 SVG 徽章报告输出，报告固定到具体 Git 提交。
- 只读本地目录 CLI（`mxready-scan`）与公开仓库报告命令（`mxready-scan-public`）。
- 仅依赖 Python 标准库的远程验证 runner，生成自包含验证 ZIP（`mxready-build-bundle`）。
- Docker 与裸机两种部署方式，配置通过 `MXREADY_*` 环境变量注入。
- GitHub Actions CI：Python 3.11/3.12 × Windows/Linux 测试、ruff 与 mypy 静态检查、覆盖率门槛、
  前端测试与构建、依赖漏洞扫描、镜像构建。

### Security

- Web 扫描路径永不执行被扫描仓库中的代码。
- 仓库地址主机白名单、受限 Git 获取、只读索引与上传结果严格校验。

[Unreleased]: https://github.com/shuljyli/MXReady/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/shuljyli/MXReady/releases/tag/v0.1.0
