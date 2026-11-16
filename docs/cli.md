# MXReady 命令行使用

`mxready`、`mxready-scan`、`mxready-scan-public`、`mxready-build-bundle`、`mxready-scan-batch`、`mxready-mcp`
与 `mxready-runner` 随安装包和开发环境提供（安装方式见[安装与发布方案](installation.md)）。
本地 CLI 只用于开发者信任的本地目录；公开 Web API 不接受本地路径。
所有命令只读分析被扫描代码，不导入、安装、构建或执行它；分析边界与 Web 服务一致。

## 全屏交互终端（mxready）

这是一个持续命令输入的终端工作区：中间滚动查看输出与建议，底部输入命令，右侧显示项目、
任务和最近报告；终端变窄时侧栏自动隐藏。使用确定的扫描命令，不接入语言模型。

```bash
# 安装终端可选依赖（Web / 单次 CLI 不需要它）
python -m pip install "mxready[tui]"
mxready
mxready /path/to/project --output-dir ./reports
# 源码开发环境（Windows 使用 .venv\Scripts\python.exe）
python -m pip install -e ".[dev]"
.venv/bin/python -m mxready
```

已有开发环境需重新安装以注册新增入口。启动时项目目录默认为当前目录；在界面内输入：

| 命令 | 用途 |
| --- | --- |
| `/scan [目录] [--repo-url URL] [--commit SHA]` | 扫描本地项目，目录默认 `.`，身份默认读取 origin / HEAD |
| `/public <URL> [--ref 分支/标签/提交]` | 扫描公开 GitHub / Gitee 仓库 |
| `/batch <清单文件或URL>` | 批量扫描，清单沿用下方 `mxready-scan-batch` 格式 |
| `/report [JSON路径]` | 打开报告，默认最近一次结果 |
| `/findings [页码]` | 每页五项发现、证据和建议 |
| `/bundle [JSON路径]` | 生成验证 ZIP，默认最近一次报告 |
| `/output [目录]` | 查看或设置后续任务的输出目录 |
| `/help` | 查看全部命令 |
| `/clear` | 清空屏幕，保留文件与命令历史 |
| `/cancel` | 取消当前任务并终止子进程树 |
| `/quit` | 停止运行中任务并退出 |

直接输入目录或 HTTPS URL 也可以开始扫描。带空格的路径请加引号，如
`/scan "C:\source code\extension"`。相对命令路径以启动时的项目目录为基准，`~` 展开为用户目录；
启动参数 `--output-dir` 的相对路径以启动命令所在目录为基准。
无 Git 身份的本地目录需要显式传入仓库 URL 与 40 位提交。这里的命令只调用现有扫描器，
不支持任意 shell 命令，不会安装依赖、构建或执行被扫描项目代码。

键盘操作：输入 `/` 显示命令建议，↑↓ 选择、Tab 补全；无建议时 ↑↓ 浏览本次会话的命令历史。
Enter 执行命令，Ctrl+P 打开可搜索命令面板，PgUp/PgDn 滚动结果，Esc 收起建议。
Ctrl+C 中断当前任务（空闲时清空输入），Ctrl+L 清屏，Ctrl+Q 退出。
命令历史仅保留在本次进程内。扫描在后台子进程中执行，界面可继续操作；一次只运行一个任务，
重复提交会提示等待或取消，不自动重试。取消不回滚已生成的文件；再次扫描会创建新目录。

默认报告与安装目录分离：macOS 为 `~/Library/Application Support/MXReady/reports`，
Linux 为 `${XDG_DATA_HOME:-~/.local/share}/mxready/reports`，Windows 为
`%LOCALAPPDATA%\MXReady\reports`；`MXREADY_DATA_DIR` 可覆盖数据目录，`--output-dir` 优先。
每次扫描与验证 ZIP 使用独立的 `scan-<ID>`、`public-<ID>`、`batch-<ID>` 或 `bundle-<ID>`
子目录，保留旧文件。本地扫描仍使用原有的独占文件与扫描 ID 规则。
终端输出最多显示 256 KiB，达到上限后继续排空子进程输出，完整发现保存在报告文件中。

JSON 报告最多读取 20 MiB，兼容缺少 coverage / occurrences 的旧报告；来源文本中的终端控制字符
会转义，Rich 标记作为普通文本显示。硬件状态标为“导出时快照”：JSON 不含验证执行时间，
无法据此重新计算有效期，当前状态需从持有验证记录的 Web 服务读取。
终端扫描文件与 Web 数据库分开，结果不会自动出现在 Web 历史里。生成验证包不会运行 runner。

全屏入口要求 stdin / stdout 为终端。CI、管道与脚本请继续使用下方单次命令；
`mxready --help` 与 `mxready --version` 可在非交互环境使用，且无需安装 Textual。

## 离线 fixture 扫描（mxready-scan）

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

命令生成 `<仓库>-<commit12>.json`、`.md`、`.svg` 和 `.sarif`。每次扫描具有独立的扫描 ID；
任一种同名输出已存在时，四个文件统一改用 `<仓库>-<commit12>-<scan_id无连字符>`，保留旧文件。
终端会打印本次实际文件名。退出码为：`0` 表示通过或仅有警告，`2` 表示存在阻塞项，`1` 表示操作失败。

在 Git 仓库目录中运行时可省略 `--repo-url` 与 `--commit`，命令默认读取 `origin` 地址与当前 `HEAD`（SSH 形式的 `origin` 会转换为 HTTPS 地址）；探测不到时会在报错信息里指明需要显式传入的参数。

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

## 公开仓库证据与验证包（mxready-scan-public / mxready-build-bundle）

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

生成清单默认不含项目命令（ZIP 内附 `project-commands.example.json` 模板，需人工审阅并替换为实际 smoke 命令后填入清单）。请先阅读 [真机验证交接](../examples/verification/README.md)，再在自己控制的沐曦服务器上人工补充并执行命令。

## 批量评估多个仓库（mxready-scan-batch）

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

输入方式请按场景选择：Web 支持单仓和每批最多 10 个公开仓库 URL，提供进度、失败项新建重试与汇总 JSON；本地目录使用 `mxready-scan`，大型清单使用上述批量 CLI。Web 批量在文本框逐行输入，不上传清单文件或源码 ZIP。
验证 runner 生成的 `result.json` 是真机验证结果，不是待扫描的源码输入。

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
| `get_report` | 按 `scan_id` 读取报告，支持 `cursor` 分页、`severity` 和 `file` 筛选 |
| `get_scan` | 查询原任务的进度或失败原因，不重复创建扫描 |
| `list_rules` | 列出内置规则，可按 `category` / `severity` 过滤 |
| `explain_rule` | 返回单条规则的判据、建议与一手引用 |

边界与 CLI 完全一致：仅接受公开 GitHub / Gitee 仓库、不执行被扫描代码、结果绑定到具体提交。
静态结论仍然不是真机验证结论——`verification_status` 保持 `not-run`，除非上传了同提交的
沐曦 GPU 验证结果。在 Web 的“MCP 接入”页可生成并复制 stdio 配置；MCP 与 Web 互相读取
报告时需显式共用同一本地数据目录。

## 远程验证 runner

`mxready-runner` 是只依赖标准库的真机验证 CLI，见 [runner 指南](runner.md) 与
[真机验证交接](../examples/verification/README.md)。
