# MXReady 安装与发布方案

## 选择安装方式

| 使用场景 | 方案 | 使用者需要准备 |
| --- | --- | --- |
| Windows 10/11 | `mxready-0.3.1-windows.zip` | Python 3.11+（含 pip）、Git、PowerShell 5.1+ |
| Linux | `mxready-0.3.1-linux.zip` | Python 3.11+（含 venv/pip）、Git、Bash |
| macOS（Apple Silicon / Intel） | `mxready-0.3.1-macos.zip` | Python 3.11+（含 pip）、Git、Bash |
| 已有 Python 环境 / 自动化部署 | `mxready-0.3.1-py3-none-any.whl` | Python 3.11+、Git |
| 容器部署 | 仓库中的 Dockerfile / Compose | Docker Engine + Compose；桌面系统也可用 Docker Desktop |
| 开发与修改源码 | Git 源码 + 开发脚本 | Python 3.11+、Git、Node.js 22+ |

ZIP 是包含预构建网页与 Python wheel 的安装包。安装时创建包目录内的 `.venv`，
默认联网下载 Python 依赖；安装包不附带 Python、Git、GPU 驱动或完整离线依赖。
使用者无需 Node.js，也无需安装 PyTorch/CUDA/MXMACA 即可做静态扫描。
MXReady 的 wheel 自身为纯 Python、跨平台；依赖中的二进制 wheel 由 pip 根据当前系统和 CPU 选择。
若对应 Python/CPU 没有依赖 wheel，安装会明确失败，不会自动编译依赖。

这些包不是原生 `.exe`、`.msi`、`.deb`、`.rpm`、`.dmg` 或 `.app`，也没有系统代码签名。
Windows、Linux 和 macOS 包共享相同应用代码，区别是安装与启动入口。
建议先用 CI 覆盖的 Python 3.11/3.12；其他 Python 3.11+ 版本取决于依赖的支持情况。
沐曦硬件验证仍须在用户控制且配置好驱动的目标主机单独运行 runner。

## 获取与校验

维护者执行下文的构建命令后，在源码根目录的 `dist/` 获得三个 ZIP、通用 wheel、源码包及
`SHA256SUMS.txt`。发布到 GitHub 后可从
[Releases](https://github.com/shuljyli/MXReady/releases) 获取；若版本没有附件，应先自行构建。
CI 的 `Release packages` 工作流也提供打包产物下载，工作流不会自动创建公开 Release。

校验下载文件（把占位的文件名替换为实际 ZIP 名称）：

```powershell
Get-FileHash .\mxready-0.3.1-windows.zip -Algorithm SHA256
```

Linux 可在附件所在目录执行 `sha256sum -c SHA256SUMS.txt`，macOS 执行
`shasum -a 256 -c SHA256SUMS.txt`；这两个批量命令需要下载清单中的全部文件。
只下载一个 ZIP 时，单独计算该 ZIP 的 SHA-256 并对照清单对应行。
安装器还会校验包内 wheel 的摘要；摘要用于发现传输或解压损坏，不代替发布者签名。

## Windows 安装与启动

先确认 `py -3 --version`（或 `python --version`）为 3.11+，`git --version` 可用。
将 ZIP **完整解压**到当前用户可写的目录，例如 `C:\Users\你的用户名\Apps\`，进入解压目录：

```powershell
.\install.ps1
.\start.ps1
```

机器上有多个 Python 时，先执行 `$env:PYTHON = "C:\Python311\python.exe"` 指定解释器，
再运行 `.\install.ps1`。

若 Windows 拦截从网络下载的脚本，核对来源和摘要后，执行
`Unblock-File .\install.ps1` 与 `Unblock-File .\start.ps1`。
若执行策略仍阻止脚本，可以只为本次运行使用：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

也可以直接运行 `py -3 install.py`，再运行
`.\.venv\Scripts\python.exe -m mxready.cli.serve`。
安装过程不需要管理员权限。不要把解压目录放在只读的 `Program Files` 下。

## Linux 安装与启动

确认 `python3 --version` 为 3.11+、`git --version` 可用。Debian/Ubuntu 若缺少 venv，
由系统管理员安装对应版本的 `python3-venv`；其他发行版使用自己的包管理器。
完整解压 ZIP 到用户可写目录，进入该目录：

```bash
bash install.sh
bash start.sh
```

如果默认 `python3` 过旧，可显式选择已安装的版本：

```bash
PYTHON=python3.11 bash install.sh
```

不需要 `sudo pip`。有图形桌面时在浏览器中打开服务地址；服务器长期运行方案见部署文档。

## macOS 安装与启动

安装适合本机 CPU 的 Python 3.11+，并确认 `python3 --version` 与 `git --version` 可用。
Python 可从 [python.org](https://www.python.org/downloads/macos/) 安装，Git 可通过
Apple Command Line Tools 提供。完整解压到用户可写目录，例如 `~/Applications/`，进入目录：

```bash
bash install.sh
bash start.sh
```

Intel 与 Apple Silicon 使用同一个 macOS ZIP；pip 按所运行的 Python 架构选择依赖。
不要混用两种架构的虚拟环境，也不要复制其他电脑的 `.venv`。

## 使用、数据与升级

三平台启动后均打开 <http://127.0.0.1:8000>；健康检查为
<http://127.0.0.1:8000/api/health>。终端保持运行，`Ctrl+C` 停止服务。
端口被占用时，使用 `bash start.sh --port 8123` 或 `.\start.ps1 --port 8123`。
包目录可以包含空格、中文，但安装后不应移动整个目录：venv 的入口可能记住原路径。
需要移动时，在新位置重新运行安装脚本并重建 `.venv`。

`mxready-serve` 的默认数据库目录与程序目录分离：

| 平台 | 默认数据目录 |
| --- | --- |
| Windows | `%LOCALAPPDATA%\MXReady`（未设置时回退 `~/AppData/Local/MXReady`） |
| Linux | `${XDG_DATA_HOME:-~/.local/share}/mxready` |
| macOS | `~/Library/Application Support/MXReady` |

目录内包含 `mxready.db` 和扫描临时目录 `tmp/`。`--data-dir` 可以指定数据位置；
其次使用 `MXREADY_DATA_DIR`，最后使用上述系统默认值。`MXREADY_TEMP_DIR` 可单独覆盖临时目录。
升级前停止服务并备份数据库；把新版本解压到新目录、运行安装和启动脚本即可复用原有数据。
不要同时启动两个不同版本来升级同一个数据库。卸载时停止服务并删除安装目录，历史数据保留；
确认不再需要历史报告后再手动删除用户数据目录。

直接使用 `uvicorn mxready.app:create_app --factory` 时，数据目录仍默认是工作目录下的 `data/`，
方便现有开发与服务器配置继续使用。只有 `mxready-serve` 使用上述用户目录约定。
若从旧的源码启动方式迁移，先停止旧服务，再指定 `--data-dir` 指向原有 `data/` 的绝对路径。

环境变量配置见源码中的 `.env.example` 和部署文档；启动脚本不自动加载 `.env`。
默认监听 `127.0.0.1`。共享网络部署前按安全模型设置反向代理、访问控制与 TLS。

## wheel 安装与离线准备

已经维护 Python 环境的用户可以直接安装 wheel；推荐为 MXReady 建立专用 venv：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install ./mxready-0.3.1-py3-none-any.whl
.venv/bin/mxready-serve
```

Windows 将上面的 `python3` 改为 `py -3`、`.venv/bin/` 改为 `.venv\Scripts\`。
wheel 已包含网页、规则与验证 schema，无需重新构建网页。
普通 `python -m build` 从开发源码构建的包可能不含网页，完整分发请使用发布脚本。

如需离线安装，先在**相同操作系统、CPU 架构与 Python 版本**的联网机器上解压对应 ZIP，
进入解压目录，下载依赖 wheel：

```bash
python3 -m pip download --only-binary=:all: --dest packages ./packages/mxready-0.3.1-py3-none-any.whl
```

Windows 使用 `py -3 -m pip download`。将整个目录复制到离线机器，执行
`bash install.sh --offline` 或 `.\install.ps1 -Offline`。
目标机器仍需预装 Python（含 venv/pip）和 Git。运行本地目录扫描无需公网，
Web 公开仓库扫描仍需要访问 GitHub/Gitee；离线安装不意味着可离线克隆远程仓库。

## 维护者构建与目录约定

在安装开发依赖后执行：

```bash
make release
# Windows PowerShell
# .\scripts\make.ps1 release
```

底层入口是 `python scripts/build_release.py`，默认执行 `npm ci` 和 `npm run build`，
把前端复制到临时源码树的包资源中，再从 sdist 构建 wheel，最后组合三个 ZIP。
已在本次构建中完成前端构建时，可以传 `--skip-frontend-build`，复用 `frontend/dist/`。
构建器会检查 wheel 中是否包含全部网页资源。前端构建或 Python 打包失败时不输出本次新包。
输出位置可以通过 `--output <目录>` 调整；同名产物会被本次成功构建覆盖。

```text
packaging/                 受版本管理的安装模板
  install.py               共享安装逻辑
  windows/                 PowerShell 安装、启动脚本
  unix/                    Bash 安装、启动脚本
scripts/build_release.py   构建编排，不放业务逻辑
src/mxready/cli/serve.py    安装后的生产启动入口
docs/installation.md       安装、升级、离线与构建说明
dist/                      本地生成，Git 忽略
  mxready-0.3.1-windows.zip
  mxready-0.3.1-linux.zip
  mxready-0.3.1-macos.zip
  mxready-0.3.1-py3-none-any.whl
  mxready-0.3.1.tar.gz
  SHA256SUMS.txt
```

ZIP 内仅保留 `packages/`、安装/启动入口、共享安装器、安装说明、许可证和 wheel 摘要。
`.venv/` 安装时生成；用户数据库不放入发布包。不要提交 `dist/`、`build/`、下载依赖或虚拟环境。
源码目录中的 `src/mxready/resources/` 只保留受维护的规则与 schema；网页资源仅在临时打包目录中合并。

`.github/workflows/release.yml` 在 `v*` 标签或手动触发时构建，并在 Windows/Linux/macOS 上
解压对应 ZIP、运行安装入口，在源码目录之外检查网页、静态资源、规则与验证 ZIP。
通过后才上传构建附件；这不表示已经在所有 CPU、所有 Python 版本或沐曦真机上完成验证。

维护者的证据留存命令和逐项发布门槛见 [发布验收](release-acceptance.md)。
安装矩阵保留每组的在线和 `--no-index` 检查日志；后者不等于操作系统已断网。

服务器的 systemd、Docker、代理和备份方案见源码中的 `docs/deployment.md`；
完整安全约束见 `docs/security.md`；硬件验证流程见 `docs/runner.md`。
打包依据：[PyPA 打包指南](https://packaging.python.org/en/latest/tutorials/packaging-projects/)、
[setuptools 包资源说明](https://setuptools.pypa.io/en/latest/userguide/datafiles.html)。
