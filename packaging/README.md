# 发布安装模板

此目录只保存安装模板，不保存构建产物或虚拟环境。

- `install.py`：三平台共享的 wheel 校验、独立 `.venv` 创建与 pip 安装逻辑。
- `windows/`：Windows PowerShell 5.1+ 的安装和启动入口，保持 ASCII 源码。
- `unix/`：Linux/macOS 的 Bash 安装和启动入口。

`scripts/build_release.py` 把这些模板、wheel、许可证与安装说明组合为三平台 ZIP，
统一输出至被 Git 忽略的 `dist/`。模板不需要复制进 Python 包。
使用及维护流程见 [安装与发布方案](../docs/installation.md)。
