# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与
[语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.2.1] - 2026-10-26

### Changed

- 前端整体替换为浅色工作台：精简仓库输入首页，重新设计扫描进度、异常恢复、
  迁移报告、导出与真机验证界面，继续独立展示静态与硬件状态。
- 优化移动端单列布局、长路径与代码显示、键盘焦点和文件选择反馈；保留刷新恢复、
  轮询重试、严重级别筛选及验证结果校验，未更改 API 契约或 runner 行为。
- 首页使用本地生成并优化的芯片插画，通过 Vite 打包到安装版支持的 assets 目录，
  无需外部图片或字体服务。

### Fixed

- 修复 Windows 安装 ZIP 在 cp1252 等旧代码页下安装到含中文路径时，pip 打印路径
  触发 `UnicodeEncodeError` 并退出失败的问题：安装器为 pip 显式设置 UTF-8 输出编码，
  恢复三平台发布安装冒烟工作流。

## [0.2.0] - 2026-10-25

### Added

- Windows、Linux、macOS 安装 ZIP 与包含网页的通用 wheel/sdist 构建入口；安装模板位于
  `packaging/`，构建产物统一位于 Git 忽略的 `dist/`，提供 SHA-256 清单和离线依赖安装选项。
- `mxready-serve` 安装后启动入口，默认监听本机地址并使用各系统的用户数据目录；
  发布包可直接提供完整界面，保留 `MXREADY_FRONTEND_DIR` 覆盖方式。
- 三平台 Python 3.11/3.12 发布包安装、HTTP、扫描与标准库 runner 冒烟工作流，
  以及安装、升级、卸载和构建文档。
- `setup.py` 依赖声明面的事实提取：保守解析 `install_requires` / `setup_requires` /
  `tests_require` / `extras_require` 中的字面量字符串（依据 PyMigBench 等迁移语料，
  CUDA 扩展项目的依赖最常声明在 setup.py），不求值任何表达式。
- `mxready-scan` 与 `mxready-scan-public` 终端直接输出极简检查结果：一行状态与
  阻断/警告/提示计数、按严重程度排序的命中列表（最多 5 条，其余指向报告文件）、
  报告文件位置；输出仅使用 GBK 可编码字符，兼容 Windows 传统代码页管道。
- `mxready-scan-batch` 批量评估入口：接收清单文件或直接 URL，逐仓复用安全获取与
  只读分析管线，生成每仓报告与 `batch-summary.csv` / `batch-summary.md` 汇总总表，
  单仓失败不中断批量；退出码区分全部通过、存在阻塞与存在失败。

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
- 规则正则评估引入字面量预过滤（Hyperscan NSDI'19 与 Russ Cox trigram 分解思路）：
  从每条正则保守提取"命中必含"的子串，字面量不出现的文件跳过正则扫描；30 条 regex
  规则中 25 条被覆盖，实测合成语料扫描时间减半，且与全量扫描结果逐项一致（含等价性测试）。
- 事实提取层按文件缓存行列表并复用 `IndexedFile` 行偏移，位置去重改为集合判定；
  重型 Python 构建文件的事实提取实测约 9 倍加速。
- 限流器滑动窗口桶周期清扫过期 IP，避免公网环境大量一次性 IP 导致内存无界增长。

### Fixed

- 修复 `mxready-scan` 在 cp1252 等无法编码中文的旧代码页下输出 `UnicodeEncodeError`
  的问题：按 `sys.stdout.encoding` 检测，不可编码时回退为纯 ASCII 摘要。
- 修复 Windows mypy 对 POSIX 进程组 API 的平台分支判定，并在本地类型检查入口增加跨平台目标检查。
- Docker CI 健康检查对启动阶段连接重置等错误执行有总时限的重试，保留未就绪时的失败结果。
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

[Unreleased]: https://github.com/shuljyli/MXReady/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/shuljyli/MXReady/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/shuljyli/MXReady/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/shuljyli/MXReady/releases/tag/v0.1.0
