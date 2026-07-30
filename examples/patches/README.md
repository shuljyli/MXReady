# Apex 上游补丁候选

本目录保存可独立评审的上游补丁草案，不代表 NVIDIA、沐曦或 MXReady 已认证 Apex 兼容性，也没有向外部仓库提交。

## `apex-configurable-nvcc.patch`

- 上游仓库：<https://github.com/NVIDIA/apex>
- 基准提交：`6424da3b4faa6c8f062da4a48c424fff3f02d42d`
- 目的：让 CUDA 工具链版本探测可通过 `APEX_NVCC` 指定兼容编译器，同时保持 `$CUDA_HOME/bin/nvcc` 为默认值。
- 范围：仅修改编译器版本探测入口、文档和单元测试；不声称处理内核、架构参数、通信库或真机运行兼容性。
- 状态：**authored / locally tested / not submitted**。

在固定提交的干净检出中检查并应用：

```bash
git apply --check /path/to/apex-configurable-nvcc.patch
git apply /path/to/apex-configurable-nvcc.patch
python -m unittest discover -s tests/L0/run_build_utils -v
```

本地验证记录（2026-07-29）：

- 3 个新增单元测试通过；
- 两个新增 Python 文件通过 Ruff；
- 4 个改动 Python 文件通过无缓存语法编译；
- `git diff --check` 通过；
- 对同一源码运行 MXReady，blocker 从 1 降为 0，warning 仍为 78，info 仍为 64。

最后一项只证明补丁消除了“硬编码调用 `$CUDA_HOME/bin/nvcc -V`”这一静态阻断项，不证明 Apex 已在沐曦 GPU 上构建或运行成功。

拟议但未提交的上游 PR 标题和正文记录在
[`docs/application-evidence.md`](../../docs/application-evidence.md#上游补丁候选)。
