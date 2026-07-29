# MXReady 设计规格

- 日期：2026-07-29
- 状态：已确认，待实施
- 目标版本：MVP
- 开源许可证：Apache-2.0

## 1. 项目概述

MXReady 是面向公开开源项目的沐曦 MXMACA 适配体检平台。用户提交 GitHub 或 Gitee 仓库地址后，平台对源码进行静态检查，定位 CUDA、PyTorch 扩展、CMake、依赖版本和 NVIDIA 专属配置中的迁移风险，并生成带代码证据、严重级别、迁移建议和参考链接的报告。

对于需要真实硬件验证的项目，平台生成一个可下载的远程测试包。用户在沐曦 GPU 服务器上审阅并手动执行测试，再将结构化结果上传至平台。只有静态检查和真实硬件验证均满足要求时，项目报告才可显示“适配通过”。

MXReady 不尝试成为 CUDA 到 MXMACA 的自动翻译器。它与 cu-bridge 等迁移工具互补，主要负责迁移前体检、验证准备、结果归档和面向开发者的可读报告。

## 2. 目标用户

第一版服务以下用户：

- 希望评估开源 PyTorch CUDA 扩展迁移成本的开发者；
- 需要快速定位 MXMACA 适配阻塞项的项目维护者；
- 正在学习国产 GPU 适配、但缺少完整迁移经验的学生；
- 需要生成可复现适配报告的社区导师或评审人员。

## 3. MVP 成功标准

MVP 达到以下条件即视为完成：

1. 内置至少 20 条具有公开文档来源的检查规则；
2. 能扫描 GitHub 和 Gitee 上的公开 Python + PyTorch CUDA 扩展项目；
3. 完成至少 3 个真实公开项目的静态扫描报告；
4. 支持 JSON、Markdown、网页报告和 SVG 徽章；
5. 提供可下载、可审阅、可手动执行的远程验证包；
6. 保存至少 1 次真实沐曦 GPU 验证记录；
7. 提供 Apache-2.0 许可证、中文 README、贡献指南和规则编写指南；
8. 尝试向至少 1 个被扫描项目提交适配 PR，PR 是否合并不影响 MVP 完成状态。

## 4. 范围

### 4.1 MVP 包含

- GitHub 和 Gitee 公开仓库的 HTTPS 地址输入；
- 指定默认分支或一个合法分支、标签、提交引用；
- 仓库浅克隆和提交哈希记录；
- Python 依赖文件解析；
- PyTorch CUDA 扩展使用方式识别；
- CMake 和常见构建脚本检查；
- `.py`、`.toml`、`.txt`、`.cmake`、`.cu`、`.cuh`、`.cc`、`.cpp`、`.h`、`.hpp`、`.sh` 文件的规则扫描；
- 代码位置、证据、严重级别、说明、建议和参考资料展示；
- 迁移清单生成；
- 远程验证清单和测试包生成；
- 远程结果 JSON 上传、校验和展示；
- SVG 状态徽章；
- 单用户、无需登录的本地或受控演示部署。

### 4.2 MVP 不包含

- 自动修改或提交被扫描项目的源码；
- 在 MXReady Web 服务器上执行被扫描仓库的代码；
- 自动登录、调度或控制远程 GPU 服务器；
- 保存 SSH 密钥、访问令牌或私有仓库凭据；
- 自动安装 GPU 驱动、MXMACA、Docker 或其他系统软件；
- 私有仓库扫描；
- 任意 CUDA 项目的完整兼容性证明；
- 大模型性能压测或多机多卡测试；
- 用户系统、团队权限、计费和公共 SaaS 级多租户能力；
- 用不透明的模型自动生成迁移结论。

## 5. 用户流程

1. 用户输入公开 GitHub 或 Gitee 仓库地址，可选填引用；
2. 后端校验地址、创建扫描任务并返回任务编号；
3. 仓库获取器执行受限浅克隆，记录规范化地址和提交哈希；
4. 文件索引器过滤二进制、生成物、依赖目录和超限文件；
5. 结构化解析器读取依赖文件和构建配置；
6. 规则引擎对候选文件执行检查；
7. 报告服务汇总阻塞项、警告和提示，生成迁移清单；
8. 用户浏览报告并下载远程验证包；
9. 用户在沐曦服务器上审阅清单并手动运行验证器；
10. 验证器输出带项目提交、工具版本和环境指纹的 JSON；
11. 用户上传结果，后端校验其真实性边界和新鲜度；
12. 报告更新硬件验证状态，并提供 Markdown、JSON 和 SVG 输出。

## 6. 技术架构

项目采用单仓库，主要目录如下：

```text
mxready/
├── backend/          # FastAPI API、任务管理、扫描和报告
├── frontend/         # React + TypeScript + Vite
├── rules/            # YAML 检查规则
├── runner/           # 沐曦远程验证器
├── tests/
│   └── fixtures/     # 本地模拟仓库、日志和远程结果
├── docs/             # 使用、贡献、规则和架构文档
├── data/             # 本地运行时 SQLite 与报告目录，不提交数据库
├── LICENSE
└── README.md
```

### 6.1 前端

前端使用 React、TypeScript 和 Vite，职责包括：

- 仓库地址和引用输入；
- 扫描状态轮询；
- 任务错误展示；
- 报告摘要、筛选和逐条证据展示；
- 迁移清单展示；
- 远程验证包下载；
- 验证结果上传；
- Markdown、JSON 和 SVG 输出入口。

前端不负责判断兼容性，也不在浏览器中克隆或扫描仓库。所有结论均来自后端的版本化报告数据。

### 6.2 API 与任务管理

后端使用 Python 和 FastAPI。MVP 不引入 Redis、Celery或独立消息队列，使用进程内受控后台任务和 SQLite 持久化任务状态。

任务状态固定为：

- `queued`
- `cloning`
- `indexing`
- `analyzing`
- `completed`
- `failed`

服务重启时，未完成任务标记为失败并给出可重新扫描的原因，不尝试恢复不确定的子进程。

### 6.3 仓库获取器

仓库获取器只接受：

- `https://github.com/<owner>/<repo>`；
- `https://gitee.com/<owner>/<repo>`。

它使用参数数组而非 Shell 字符串启动 Git，执行单分支、有限历史的浅克隆。默认安全限制为：

- 克隆超时：60 秒；
- 下载后仓库大小：50 MiB；
- 纳入索引的文件数：10,000；
- 单个文本文件大小：1 MiB；
- 禁止子模块初始化；
- 禁止 Git LFS 自动下载；
- 禁止 URL 中携带用户名、密码或令牌。

超过限制时任务失败，并向用户显示具体限制。临时目录在任务结束后清理。

### 6.4 文件索引器

文件索引器只读取允许的文本扩展名，并默认排除：

- `.git`；
- `node_modules`；
- `vendor`；
- `third_party` 中超限内容；
- `dist`、`build`、`target`；
- Python 虚拟环境；
- 模型权重、归档和其他二进制文件；
- 压缩、混淆或无法按 UTF-8/常见文本编码安全读取的内容。

每个索引项包含相对路径、文件大小、内容哈希和按需加载的文本内容。

### 6.5 结构化解析器

结构化解析器提供可独立测试的解析单元：

- `requirements*.txt` 依赖解析；
- `pyproject.toml` 依赖与构建后端解析；
- `setup.py` 和 `setup.cfg` 的保守静态识别；
- `CMakeLists.txt` 和 `.cmake` 的关键构建配置识别；
- PyTorch `CUDAExtension`、`CppExtension` 和即时编译调用识别；
- Shell 脚本中的硬编码工具和目录识别。

解析器不执行 Python、CMake 或 Shell 文件。无法静态确定的动态配置会产生“需人工确认”提示，而不是猜测结果。

### 6.6 规则引擎

规则存储为 YAML。规则结构至少包含：

```yaml
id: MXR-PYTORCH-001
title: 检测硬编码 CUDA_HOME
category: pytorch-extension
severity: warning
file_globs:
  - "**/*.py"
patterns:
  - type: regex
    expression: "CUDA_HOME\\s*="
message: 项目显式覆盖 CUDA_HOME，迁移时可能绕过 MXMACA 工具链配置。
recommendation: 使用可配置路径，并在 MXMACA 环境中验证 cu-bridge 工具链变量。
references:
  - title: cu-bridge 项目文档
    url: https://gitee.com/metax-maca/cu-bridge
```

严重级别固定为：

- `blocker`：已知会阻止当前适配流程，必须处理或获得人工豁免；
- `warning`：存在较高迁移风险，需要验证；
- `info`：迁移时值得关注，但本身不代表失败。

规则引擎输出文件、起止行、证据摘要、规则版本和置信类型。MVP 不给出百分制兼容分数，避免制造虚假精度。

### 6.7 报告服务

报告由同一个版本化数据模型渲染为：

- 网页；
- JSON；
- Markdown；
- SVG 徽章。

报告头部必须包含：

- 仓库规范化地址；
- 扫描提交哈希；
- 扫描时间；
- MXReady 版本；
- 规则集版本；
- 静态检查状态；
- 远程验证状态。

徽章状态为：

- `static-passed`
- `warnings`
- `blocked`
- `verified`
- `verification-stale`
- `scan-failed`

只有与相同提交哈希关联的成功远程验证，才能产生 `verified` 徽章。

### 6.8 远程验证器

远程验证器是独立的 Python 命令行工具，不依赖 Web 服务持续在线。测试包包含：

- `mxready.yml` 验证清单；
- 验证器入口；
- JSON Schema；
- 使用和安全说明。

验证器分两阶段：

1. `inspect`：只采集操作系统、Python、MXMACA、PyTorch、设备可见性和项目提交信息；
2. `run`：先展示将要执行的命令，获得用户明确确认后，再运行清单中的构建或测试命令。

验证器不使用 `sudo`，不安装软件，不修改驱动，不上传完整环境变量，不收集主机名、用户名、令牌或模型数据。日志经过敏感字段过滤，输出固定 Schema 的 JSON 文件。

## 7. 核心数据模型

### 7.1 ScanJob

- `id`
- `repo_url`
- `requested_ref`
- `resolved_commit`
- `status`
- `stage_message`
- `created_at`
- `updated_at`
- `failure_code`
- `failure_message`

### 7.2 Finding

- `rule_id`
- `rule_version`
- `severity`
- `category`
- `title`
- `relative_path`
- `line_start`
- `line_end`
- `evidence`
- `message`
- `recommendation`
- `references`

### 7.3 ScanReport

- `schema_version`
- `scan_id`
- `repository`
- `tool_version`
- `ruleset_version`
- `summary`
- `findings`
- `migration_checklist`
- `static_status`
- `verification_status`

### 7.4 VerificationRun

- `schema_version`
- `scan_id`
- `repository_commit`
- `runner_version`
- `environment_fingerprint`
- `checks`
- `commands`
- `started_at`
- `finished_at`
- `overall_status`

## 8. API 设计

MVP API 如下：

- `POST /api/scans`：创建扫描任务；
- `GET /api/scans/{scan_id}`：读取状态和基础信息；
- `GET /api/scans/{scan_id}/report`：读取结构化报告；
- `GET /api/scans/{scan_id}/report.md`：下载 Markdown 报告；
- `GET /api/scans/{scan_id}/report.json`：下载 JSON 报告；
- `GET /api/scans/{scan_id}/badge.svg`：获取状态徽章；
- `GET /api/scans/{scan_id}/verification-bundle`：下载远程验证包；
- `POST /api/scans/{scan_id}/verification-runs`：上传验证结果；
- `GET /api/rules`：读取公开规则目录；
- `GET /api/health`：服务健康检查。

创建扫描请求只包含 `repo_url` 和可选 `ref`。API 不接受任意 Git 参数、Shell 命令或服务器路径。

## 9. 错误处理

面向用户的失败使用稳定错误代码，至少包括：

- `INVALID_REPOSITORY_URL`
- `UNSUPPORTED_REPOSITORY_HOST`
- `REPOSITORY_NOT_FOUND`
- `REPOSITORY_ACCESS_DENIED`
- `CLONE_TIMEOUT`
- `REPOSITORY_TOO_LARGE`
- `TOO_MANY_FILES`
- `UNSUPPORTED_TEXT_ENCODING`
- `RULESET_INVALID`
- `SCAN_INTERNAL_ERROR`
- `VERIFICATION_SCHEMA_INVALID`
- `VERIFICATION_COMMIT_MISMATCH`
- `VERIFICATION_STALE`

单个文件读取失败或单条非关键规则失败时，扫描继续进行，并在报告元数据中记录分析警告。规则集本身无法加载、仓库身份无法确定或报告无法持久化时，任务整体失败。

所有异常对用户返回可行动的说明；服务端日志保留关联任务编号和技术细节，但不回显本地绝对路径、凭据或完整敏感日志。

## 10. 安全边界

MVP 采用以下安全原则：

- Web 服务只做静态读取，绝不执行仓库代码；
- 仅允许两个固定公共代码托管域名；
- Git 子进程使用参数数组、固定环境和超时；
- 禁止私有网络地址、任意 URL 和本地路径输入；
- 对文件数量、大小、类型和读取时间设置上限；
- 报告中的源码证据限制长度并进行 HTML 转义；
- 上传 JSON 设置体积上限并按 Schema 校验；
- 远程验证命令在用户控制的服务器上执行，执行前完整展示；
- 不承诺静态扫描可以证明项目安全或完全兼容；
- 公共部署前必须增加反滥用限流，MVP 默认定位为本地或受控演示环境。

## 11. 测试策略

### 11.1 规则测试

每条规则至少包含：

- 一个应命中的最小样例；
- 一个相似但不应命中的反例；
- 期望严重级别、文件和行号；
- 规则文档来源校验。

### 11.2 后端单元测试

覆盖：

- 仓库 URL 规范化和拒绝逻辑；
- 文件限制；
- 依赖和构建文件解析；
- 规则匹配与去重；
- 严重级别汇总；
- 报告状态计算；
- 远程结果 Schema、新鲜度和提交匹配判断；
- SVG 内容转义。

### 11.3 后端集成测试

使用本地 Git fixture，不访问互联网，覆盖：

- 创建扫描；
- 任务状态变化；
- 完整扫描；
- 报告输出；
- 验证包生成；
- 验证结果上传；
- 失败状态和稳定错误码。

### 11.4 前端测试

覆盖：

- 无效输入；
- 扫描进行中；
- 扫描失败；
- 含阻塞项和警告的报告；
- 静态通过但尚未硬件验证；
- 硬件验证成功和结果过期；
- 报告筛选、下载和上传交互。

### 11.5 远程验证器测试

使用模拟命令输出验证：

- 无 MXMACA 环境；
- PyTorch 无法发现设备；
- 冒烟测试成功；
- 项目测试失败；
- 超时；
- 日志脱敏；
- JSON Schema 合规。

最终使用真实沐曦 GPU 完成至少一次端到端验证，并在仓库中保存去敏后的可复现报告。

## 12. 开发里程碑

### 里程碑 1：项目骨架与数据契约

- 建立前后端、规则和验证器目录；
- 定义 Pydantic 模型和 JSON Schema；
- 建立 SQLite 任务存储；
- 完成基础 CI、格式化和测试命令。

### 里程碑 2：离线扫描内核

- 完成文件索引器；
- 完成依赖和构建解析器；
- 完成 YAML 规则加载和匹配；
- 使用本地 fixture 输出 JSON 报告。

### 里程碑 3：受限公开仓库扫描

- 完成 URL 校验和浅克隆；
- 加入超时、文件和体积限制；
- 完成后台任务状态和错误码；
- 扫描 GitHub/Gitee 测试仓库。

### 里程碑 4：网页报告

- 完成仓库提交页面和任务进度；
- 完成报告摘要、筛选、证据和建议；
- 完成 Markdown、JSON 和 SVG 输出。

### 里程碑 5：远程验证

- 生成验证清单和测试包；
- 完成环境采集、用户确认、命令运行和日志脱敏；
- 完成结果上传、提交匹配和过期判断。

### 里程碑 6：申报材料

- 扩充至 20 条规则；
- 完成 3 个真实项目报告；
- 完成一次真实沐曦 GPU 验证；
- 完善 README、演示材料、贡献文档和规则指南；
- 选择一个项目准备并提交适配 PR。

## 13. 可维护性约束

- 每个模块只有一个主要职责；
- API、报告和验证结果均有独立版本号；
- 规则数据与执行引擎分离；
- 解析器不得通过执行配置文件获取信息；
- 所有外部进程都必须具有超时和受控参数；
- 业务状态计算集中在后端，前端只负责展示；
- GPU 不可用时，除真实硬件验证外的测试仍可全部通过；
- 未经新一轮设计评审，不在 MVP 中加入自动修复、账号系统、私有仓库或云端 GPU 调度。

## 14. 已确认决策

- 项目名称使用 MXReady；
- 首版聚焦 Python + PyTorch CUDA 扩展；
- 前端使用 React + TypeScript + Vite；
- 后端使用 FastAPI；
- 持久化使用 SQLite；
- 规则使用 YAML；
- 报告不使用百分制兼容分数；
- Web 服务不执行仓库代码；
- 远程验证由用户手动触发；
- 第一阶段开发不依赖真实 GPU；
- 真实沐曦验证是最终独立里程碑。
