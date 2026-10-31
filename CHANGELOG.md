# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与
[语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Changed

- 同步中英文 README：明确 Web、本地目录和批量 CLI 的输入边界，补充英文批量扫描与 MCP 用法，避免覆盖率数字随测试变化而过期。

## [0.3.1] - 2026-10-31

补丁版本：补全发布验收与安全边界，新增可选 MCP 接口与七份本地化 README。0.x 阶段对外契约仍可能调整，
接口与报告字段在 1.0 之前不承诺向后兼容。

沐曦真机验证已完成——在 MetaX C500（Kernel Mode Driver 3.8.30、MACA 3.3.0.15）上以
PyTorch 2.8.0+metax3.3.0.2 / Python 3.10.10 对 `pytorch/extension-cpp` 的提交
`1c325b202ae5e11de3cefb9a65be28f47949edd4` 执行 runner：`inspect` 五项环境检查与单卡
smoke 全部 `passed`。该结果只覆盖上述提交与该服务器环境，静态检查结论仍不代表项目已兼容
MXMACA；正式版本将在后续发布。

### Added

- 发布安装冒烟保留候选 ZIP 摘要、命令/退出码、日志及结果，检查系统默认用户数据路径和报告重启持久化；
  发布矩阵增加缺依赖失败检查及无包索引安装，明确进程故障、旧库升级与真机验收门槛。
- `examples/reports/nvidia-apex`：第一份处于 `blocked` 状态的公开项目示例报告
  （`NVIDIA/apex` @ `575968bc1f91`，阻断 12 · 警告 65 · 提示 140）。此前该目录只有一份全绿报告，
  4 条发现都是 `info`——材料里从没出现过“这个工具真的抓到问题”的证据。12 条阻断逐条核对为真阳性：
  `#define WARP_SIZE 32`、`int lane_id = threadIdx.x & 31;`、
  `asm volatile("red.release.gpu.global.add.s32 ...")`、以及 `setup.py` 里直接调 `nvcc` 探测版本。
  其中两条能编译通过但会在 64 宽度的 wave 上算出错误结果，正是只能靠静态检查拦住的静默缺陷。
- `SECURITY.md`：说明漏洞报告走 GitHub Security Advisories，并界定范围（越出只读扫描边界、
  绕过主机白名单与体积限制、验证清单命令注入、报告或日志泄漏凭据与主机信息）与非范围
  （误报、没有兼容性结论、被扫描项目自身的漏洞）。
- 可选 `mxready-mcp`：把扫描、报告与规则查询暴露为 4 个 MCP 工具（`scan_repository` /
  `get_report` / `list_rules` / `explain_rule`），供支持 Model Context Protocol 的编码 Agent
  在改代码前取得可核验的迁移事实，而不是凭模型记忆猜测 CUDA 与 MXMACA 的差异。`mcp` 单独放在
  可选依赖组（`.[mcp]`），核心运行时依赖仍是 4 个；stdio 传输下日志强制写 stderr，stdout 只承载
  协议消息——这条边界由实际握手验证，不靠约定。

### Fixed

- 修复 0.3.0 版本重置时对 `frontend/package-lock.json` 的全局替换误伤：`gensync`、
  `@rolldown/pluginutils`、`@types/estree`、`min-indent` 的依赖版本、`BlueOak-1.0.0`
  许可证标识和 Node 引擎范围都被错误改写成 `0.3.0` 相关值，导致 `npm ci` 报
  `No matching version found for @types/estree@^0.3.0`。lockfile 已恢复为正确解析结果，
  只保留根项目的版本号变更；`npm ci`、`npm run typecheck`、`npm test` 与 Docker 构建同步恢复。
- 自扫描把本仓库判成"阻塞"：22 条 `blocker` 全部出自测试夹具与文档描述。三处修复后，
  干净检出（`git archive HEAD`）的自扫描结果为 **0 blocker / 1 warning / 72 info**。
  - `scanning/path_context.py`：按**完整路径段**判定文件角色（`tests` / `fixtures` /
    `examples` / `docs` / `benchmarks`，不做子串匹配，`contest/`、`latest/` 不受影响），
    非交付路径上的 `blocker` / `warning` 封顶为 `info`。文件仍被索引、仍出现在报告里，
    降级在 `Finding.message` 与 `analysis_warnings`（`PATH_CONTEXT_DEMOTION`，按角色聚合、
    含规则 ID 与文件数）双重留痕。
  - `scanning/python_source.py`：命中若**完整**落在 Python 文档字符串内降为 `info`——
    文档里写 `subprocess.run(["nvcc", ...])` 作为反例，不等于代码这样写了。普通字符串
    字面量**不**豁免（`os.system("nvcc main.cu")` 仍报 `blocker`），Python 解析失败一律不豁免。
  - `scanning/indexer.py`：整目录跳过测试运行器与基准框架的临时目录（`.pytest*`、
    `.benchmarks`）。那是夹具的运行时副本，不属于仓库内容，且每次运行内容都会漂移。
- 路径上下文先于工具链画像生效，避免对一条已是 `info` 的 finding 追加"从 blocker 降为
  warning"这种错误说明（`test_path_demotion_runs_before_toolchain_profile` 守着这条）。
- 发布工作流在本机只装 `.[dev]` 时 `mypy` 报 `mcp.server.fastmcp` 的 `import-not-found`：
  为可选依赖 `mcp.*` 增加类型检查豁免，核心与开发安装不再被迫装上 MCP SDK。

### Changed

- README 的工程状态数字改成不易漂移的写法：`pytest` 用例从写死的“477 条”改为“当前 490 余条”，
  覆盖率从 90% 改为实测的 89%。加入 MCP 测试后这两个数已经过期，而版本一致性测试守得住版本号与
  产物名，守不住用例数和覆盖率——同类问题在这个仓库已经发生过两次。
- README 中文与英文版开头改成直白叙述：先说清“代码从 NVIDIA 搬到沐曦会坏在哪、这个工具帮你找出来”，
  术语留给后面的技术章节，不再用“迁移准备度体检”“可解释的静态规则”这类堆叠名词开门。
- 新增日语、韩语、西班牙语、葡萄牙语（巴西）、法语、德语、俄语七份精简 README，九份文档顶部统一
  语言切换。多语言版刻意不写规则条数与版本号——这些数字改一次要人工同步九处，CI 校验不到，
  而仓库已经因为写死数字漂移过两次；需要细节的一律指向中文与英文主文档。英文主文档同步补上 MCP 能力。
- README 与功能矩阵的规则数从“30 条”更正为实际的 35 条（规则集 v4 早已是 35 条／49 条模式）。
- `docs/rules.md` 增补"路径上下文与文档字符串"一节，说明两处降级的判据、留痕方式与豁免边界。

## [0.3.0] - 2026-10-31

第三个预览版本。工程链路、发布链路与开源治理补全，规则引擎的正确性缺陷修复，
并新增四类迁移阻塞项规则。0.x 阶段对外契约仍可能调整，接口与报告字段在 1.0 之前
不承诺向后兼容。

验证范围：Windows / Linux / macOS 已完成源码测试与三平台安装包安装、启动验证；
沐曦真机验证已完成——在 MetaX C500（Kernel Mode Driver 3.8.30、MACA 3.3.0.15）
上以 PyTorch 2.8.0+metax3.3.0.2 / Python 3.10.10 对 `pytorch/extension-cpp` 的提交
`1c325b202ae5e11de3cefb9a65be28f47949edd4` 执行 0.3.0 runner：`inspect` 的五项
环境检查全部 `passed`，`mx-smi` 与 `torch.cuda` 均指向同一块 C500；构建
`extension_cpp` 后单卡 smoke 命令通过，`overall_status` 为 `passed`。该结果只覆盖
上述提交与那台服务器的环境组合，静态检查结论仍不代表项目已兼容 MXMACA。

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
- 新增四类迁移阻塞项规则，规则集升至 v3（34 条规则 / 48 条模式）：`MXR-PTX-001` 内联 PTX `asm`、
  `MXR-WARP-001` 按 32 硬编码的线程束算术（两者记为 `blocker`），`MXR-THRUST-001` / `MXR-CUB-001`
  登记 Thrust/CUB 用法（`info`，沐曦 mcThrust / mcCUB 提供 API 不变的 wrapper）。
  线程束宽度属于"能编译但结果错"的静默缺陷，静态检查是唯一能在 CI 阶段拦住它的手段。
- `docs/rules.md` 增加"严重度口径"与"覆盖边界"两节：前者把 blocker/warning/info 对齐到
  SYCLomatic 的 High/Medium/Low 人力分档并给出判级硬规则，后者显式列出不做 AST、不构建带来的盲区。
- 新增 `MXR-TOOLCHAIN-002`（info）与工具链画像，规则集升至 v4（35 条规则 / 49 条模式）：
  从 `make_maca` / `cmake_maca` / `cucc` / `CUCC_PATH` / `CUCC_CMAKE_ENTRY` / `cu-bridge`
  路径识别已接入 cu-bridge 的项目。识别到之后，声明式构建文件（`Makefile` / `*.mk` /
  `CMakeLists.txt` / `*.cmake`）里的 `NVCC = nvcc` 由 blocker 降为 warning——cu-bridge
  在构建期接管这些调用，继续报阻塞等于把已迁移项目判成未迁移。`.py` / `.sh` 里的
  `nvcc` 调用保持 blocker，因为它可能绕过 `make_maca` 注入的 `PATH`。降级会在 finding
  的 message 与 `analysis_warnings` 里双重留痕，不做静默处理。
- `scripts/optimize_docs_images.py`：把 `docs/design` 下的设计图转成 WebP，按内容分档编码——真实
  页面截图用无损（逐像素与 PNG 一致），渲染插画用 q92 有损（PSNR 44–46 dB）。分辨率一律不动：
  这些图含可读的 UI 文字，降采样是不可逆损失，而 WebP 本身已能收回绝大部分体积。`--check`
  用于确认目录里不再残留 PNG。Pillow 只进 `dev` 依赖组，产品代码不引用它。

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
- 六张设计图由 PNG 改为 WebP，合计 3065 KB 降至 463 KB（−85%）。两张 1536×1024 的生成概念图各约
  1.2 MB，是仓库字节的主要来源——PNG 存连续色调插画本就低效，同一批像素用有损 WebP 只需 85 KB。
  受控内容整体由 3.95 MB 降到约 1.4 MB，`git clone` 与 CI checkout 同步变轻。

### Removed

- 移除 `docs/design/frontend-refresh/prompts.md`（7.5 KB）与 `browser-check-results.json`（1.3 KB）
  两份过程产物。插画提示词是 `frontend/src/assets/mx-chip.webp` 的复现依据，已并入
  `docs/frontend-redesign.md` 的折叠小节；两张概念图的提示词不再保留，因为图已归档、页面由真实
  React 实现，不存在重新生成的场景。浏览器检查的 23 条明细已由 `docs/frontend-redesign.md` 的
  验收表覆盖，原文件又缺少提交与机器信息，无法据此复现，故只留结论、不留原始快照。

### Fixed

- 发布安装冒烟的资源检查不再硬编码"恰好 30 条规则"，改为至少 35 条的下界断言，
  避免规则集扩充后三平台发布任务被误判失败；英文 README 的规则数同步修正为 35 条。
- 修复 `Makefile` / `*.mk` 完全不在扫描范围导致的**假绿灯**：索引器白名单只收
  `CMakeLists.txt` 与 `Dockerfile`，34 条规则的作用域也没有一条包含 Makefile，
  两层叠加使 `NVCC = nvcc` 这类最典型的阻塞项完全不可见。实测一个只有
  `Makefile` + `main.cu` 的仓库返回 `passed`。
  这对沐曦场景尤其致命——cu-bridge 的官方入口 `make_maca` 本身就是 make 包装器，
  cu-bridge 生态的主战场正是 Makefile。
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
- 修正 `README.md` 中"34 条规则"的过期计数（规则集在 v4 已增至 35 条）：该处改为不写具体条数并
  指向 `docs/rules.md`。版本一致性测试守住了版本号与产物名，但规则条数不在其覆盖范围内——
  写死的数字每扩一条规则都要人工同步，漏改不会被任何门禁拦住。

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

[Unreleased]: https://github.com/shuljyli/MXReady/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/shuljyli/MXReady/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/shuljyli/MXReady/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/shuljyli/MXReady/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/shuljyli/MXReady/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/shuljyli/MXReady/releases/tag/v0.1.0
