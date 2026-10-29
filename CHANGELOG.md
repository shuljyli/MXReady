# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与
[语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.3.0] - 2026-10-29

第三个预览版本。工程链路、发布链路与开源治理补全，规则引擎的正确性缺陷修复，
并新增四类迁移阻塞项规则。0.x 阶段对外契约仍可能调整，接口与报告字段在 1.0 之前
不承诺向后兼容。

### Added

- `MXREADY_PREFILTER_MODE`（`auto` / `off`）与 `Settings.prefilter_mode`：预过滤的应急止血开关，
  关闭后只影响耗时、不影响结论；取值拼错时回退 `auto`，不会阻止启动。
- 报告新增 `analysis_config.prefilter`，记录预过滤的**实际生效状态**（`on` / `off` / `unavailable`），
  以便区分"配置关闭"与"内部解析接口不可用而降级"；旧报告缺少该字段仍可解析。
- `scripts/bench_prefilter.py`：逐规则对比预过滤与完整正则的成本、可跳过文件数，并校验两种模式的
  命中集合一致；输出不含时间戳，两次运行可直接 diff。
- `scripts/release_notes.py`：从 CHANGELOG 渲染 GitHub Release 正文，缺对应版本小节时直接失败，
  避免"版本号升了但没写变更记录"的发布。
- 打包补齐 PEP 561 `py.typed` 标记（`mxready` 与 `mxready_runner`），下游类型检查可直接使用本项目的注解。
- 版本一致性测试：`pyproject`、两个包的 `__version__`、前端 `package.json` 与 lockfile、README 徽章与
  四个安装包名、安装与接口文档中的示例、CHANGELOG 小节必须同源，任一处漂移即测试失败。
- 新增四类迁移阻塞项规则，规则集升至 v3（34 条规则 / 49 条模式）：`MXR-PTX-001` 内联 PTX `asm`、
  `MXR-WARP-001` 按 32 硬编码的线程束算术（两者记为 `blocker`），`MXR-THRUST-001` / `MXR-CUB-001`
  登记 Thrust/CUB 用法（`info`，沐曦 mcThrust / mcCUB 提供 API 不变的 wrapper）。
  线程束宽度属于"能编译但结果错"的静默缺陷，静态检查是唯一能在 CI 阶段拦住它的手段。
- `docs/rules.md` 增加"严重度口径"与"覆盖边界"两节：前者把 blocker/warning/info 对齐到
  SYCLomatic 的 High/Medium/Low 人力分档并给出判级硬规则，后者显式列出不做 AST、不构建带来的盲区。

### Changed

- 发布工作流在打 tag 时创建 GitHub Release 并挂载三平台 ZIP、wheel、sdist 与 `SHA256SUMS.txt`。
  此前只上传 workflow artifact，Release 页面始终为空；同一 tag 重跑改为覆盖附件。
- 覆盖率改按 branch 口径统计（90%），并排除 `__main__` 守卫；仅统计语句会掩盖"分支只走一半"。
- CI 矩阵由 3.11/3.12 扩到 3.11/3.12/3.13，classifier 同步；此前声明 `>=3.11` 却只测到 3.12。
- `mypy` 纳入 `packaging/`（此前 `install.py` 完全未受类型检查），并新增 `ruff format --check` 门禁。
- `ci.yml` 增加 `concurrency` 分组，连续推送时取消被取代的运行。
- 规则正则的必需字面量预过滤改为按"或"组织（OR-of-AND）的候选集，分支型规则也能参与过滤，
  提取覆盖率由 25/30 提升到 29/30；仅 `MXR-ARCH-002`（`(?:sm|compute)` 两支都过短）仍需全量扫描。
  在 613 文件 / 2 MiB 的真实语料上，规则评估 278 ms 降至 153 ms（约 1.96×），命中结论逐条一致。
- 折叠视图缓存加 48 MiB 字节上限，超限后只计算不缓存：预过滤需要按文件折叠文本，
  无上限缓存会让整仓常驻内存翻倍，而淘汰旧项只会让后续文件反复重算，故选择"停止累积"。
- `pyproject.toml` 依赖行号定位由"逐依赖扫描全部行"改为整篇折叠后一次查找 + 行首偏移查表，
  500 条依赖的文件上单文件耗时由 5.1 ms 降至 1.8 ms；行号口径与 `str.splitlines()` 严格一致。

### Fixed

- 修复内联 `(?i)` / `(?i:...)` 未反映到字面量大小写语义，导致预过滤跳过本应命中的文件（漏报）：
  字面量现在携带所处作用域的 effective flags，`(?i:AB)cd` 只把 `AB` 视为忽略大小写。
- 修复 `str.casefold()` 与 `re.IGNORECASE` 在土耳其语 I 家族（`I` `i` `İ` `ı`）上不同构导致的漏报：
  折叠未命中时，若文件或字面量含分歧码位则放行给完整正则确认。
- 修复 `re._parser` 在模块加载期硬导入、私有 API 一旦变更就让扫描整体失败的问题：改为惰性探测
  加行为探针（不判版本号），不可用时自动退化为全量扫描并只记一次 WARNING。
- 修复 CMake 中已被注释掉的 `# set(CUDA_HOME ...)` 被计为真实 CUDA 路径引用的问题。
- 修复 `setup.py` 以元组声明依赖（如 `install_requires=("torch",)`）时整条漏采的问题。
- 修复 `MXR-COMM-001` 首条正则的二次回溯（ReDoS）：`[^\]\n]*` 与 `[A-Z0-9_]+` 字符集重叠且缺少
  终止符，攻击者可构造 `os.environ["NCCL_` 加长串使其达到 O(n²)——120 KB 单行耗时 19.2 s，
  端到端 68.7 ms 涨到 5221 ms。改用前瞻替代一个消耗型量词后回到线性，命中结果不变。
  注意协作式预算只在文件之间检查，单次 `finditer` 内部无法抢占，因此这类缺陷不能只靠超时兜底。
- 修正 `docs/rules.md` 与 PR 模板中指向已移除 `backend/`、`runner/` 目录的 lint 命令。

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
- 修复 Windows 安装脚本优先使用 `py -3` 时可能选中矩阵之外的新版 Python，导致
  `PyYAML` 没有可用二进制 wheel 而安装失败的问题：`install.ps1` 支持 `PYTHON`
  环境变量指定解释器，发布安装冒烟显式传入矩阵 Python。

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

[Unreleased]: https://github.com/shuljyli/MXReady/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/shuljyli/MXReady/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/shuljyli/MXReady/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/shuljyli/MXReady/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/shuljyli/MXReady/releases/tag/v0.1.0
