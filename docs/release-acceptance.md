# 发布验收与证据

源码回归通过只证明对应测试执行成功。ZIP 安装、真实进程故障、历史数据库升级、沐曦硬件
分别验收；没有执行记录的项目保持待验证。工作流配置存在不表示已经执行通过。

## 固定候选产物

从确定的完整提交构建一次，将提交、构建命令/日志、版本、OS/架构、Python/Node 版本与
`SHA256SUMS.txt` 一并归档。后续六组安装测试和最终分发使用同一批产物。
依赖目前未锁定；同时保留安装后的 `pip freeze` 和离线 wheel 摘要，不能仅靠源码提交重现依赖。
更换产物后重新验收受影响项目。`--candidate-commit` 是声明的来源，必须由构建记录支持。

## 安装证据脚本

在对应系统、架构及 Python 版本上执行；每次使用新的证据目录：

```bash
python scripts/smoke_release.py --dist dist \
  --candidate-commit <完整提交> --evidence-dir dist/evidence-online
python -m pip download --only-binary=:all: --dest dist/wheelhouse \
  dist/mxready-0.1.0-py3-none-any.whl
python scripts/smoke_release.py --dist dist --wheelhouse dist/wheelhouse \
  --candidate-commit <完整提交> --evidence-dir dist/evidence-offline
```

Windows PowerShell 将续行反斜杠改为反引号，或将命令写成一行。
证据目录应位于 `dist/` 等 Git 忽略路径，不能重复覆盖旧记录。

脚本检查选中 ZIP 的 SHA-256 后，在源码外的中文/空格路径安装；检查包规则/schema、
只读本地扫描、生成验证 ZIP、标准库 runner 的 `--help`、网页与资源、健康接口及未知 API 404。
脚本通过隔离 HOME/USERPROFILE（Windows 使用隔离 LOCALAPPDATA）测试系统默认路径，
不设置 `MXREADY_DATA_DIR`/`MXREADY_TEMP_DIR`。预置一份本地扫描报告，启动及重启两次后从 API
读取并比较，检查数据库和报告保留；核对启动日志使用 `127.0.0.1`。
这是隔离用户配置下的默认路径检查，不代表真实用户权限和所有安装位置均已验证。

传入 `--wheelhouse` 时，先用不含依赖的原始 ZIP 执行离线安装并要求非零退出，随后删除
半成品 venv，补入依赖 wheel，再以 `--no-index` 全新安装。该检查禁用 pip 配置和缓存，
但没有切断操作系统网络；发布前还需 Windows/Linux 普通用户在真实断网环境各执行一次。
脚本不会调用 Node.js，但也没有隐藏系统上已有的 Node.js；无开发环境验收仍须单独记录。

`result.json` 记录状态、候选摘要、检查脚本摘要、环境、命令、退出码及未覆盖项；
失败时也写入结果并保留对应日志。服务退出码包含脚本主动终止产生的结果，整体通过状态取决于
HTTP/资源/报告断言。证据还包含扫描报告、schema、数据库及安装依赖清单。
`kind=release-installation-smoke` 的结果不是硬件 runner 的 `result.json`，不能上传为真机证据。

## 发布门槛

| 门槛 | 必需执行证据 | 阻断条件 |
| --- | --- | --- |
| 三平台 ZIP | 同一候选，Windows/Linux/macOS × Python 3.11/3.12 六组安装结果 | 任一组失败或缺记录 |
| 普通用户与离线 | Windows/Linux 各一次，无管理员权限、无 Node.js/开发环境，准备依赖后真实断网 | 默认目录不可写、缺依赖未明确失败、离线安装/本地扫描失败 |
| 进程故障 | 两个独立服务共享同机 SQLite，终止持有租约者，记录任务时间线及后续任务处理 | 活跃任务被另一进程启动清空、旧执行写入被接受、队列停滞或任务无明确终态 |
| 历史库升级 | 真实旧版本样本库及备份，候选升级后旧报告/30 天过期结果检查，恢复备份 | 数据丢失、迁移失败、API/徽章/下载状态不一致或备份不可恢复 |
| 沐曦环境 | 候选验证 ZIP 在目标主机 inspect，人工核对设备，审阅并上传结果 | mx-smi/PyTorch 检查失败、设备或扫描 ID/提交不匹配 |

前四项通过才可宣称三平台安装包完成正式验收；硬件未完成时明确标注“沐曦真机待验证”。
runner inspect 通过只说明环境检查通过；具体项目可运行还需人工配置并执行最小 smoke 命令。

## 进程故障与旧库验收记录

进程故障应记录两个服务 PID、端口、同一个数据库绝对路径、扫描 ID、领取时间、租约到期时间、
杀进程命令、恢复后的状态和日志。应先证实第二进程启动后仍保留另一进程的活跃租约。
当前策略是过期执行变为 `failed/SCAN_INTERRUPTED`，提示重新发起扫描；排队任务继续处理。
验收时显式检查旧令牌的 `save_report`/`update_job` 被拒绝，重新提交扫描并确认队列继续工作。
若要求同一任务自动重新执行，则属于尚未实现的行为，必须另行修改并验收。
刷新恢复、取消请求及失败后重试需另留浏览器操作证据；HTTP 冒烟不覆盖这些交互。

旧库必须注明产生它的旧版本和样本来源。停止旧服务后备份（活动库使用 SQLite backup API，
不要只复制主文件而漏掉 WAL），保留备份摘要；先在副本上升级，确认 `PRAGMA user_version`、
历史报告和数量，再检查超过 30 天结果在 report API、report.json、report.md、badge.svg 均为
`stale`。停止候选后恢复备份，用原版本读回确认。不要混用两个版本同时升级同一个库。
临时构造的旧 schema 与单元测试不能冒充真实历史样本升级证据；已下载文件无需自动变化。

每项记录提交、产物摘要、OS/架构/Python、命令、退出码、日志和结果文件。
缺真实旧库或目标硬件时明确保持待验收，不用源码测试填补对应门槛。
