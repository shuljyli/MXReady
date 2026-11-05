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

## `causal-conv1d-maca.patch`

- 上游仓库：<https://github.com/Dao-AILab/causal-conv1d>
- 基准提交：`cd81f0413cad2fc1e6f17e785ac39f59aae690cd`
- 目的：让 `setup.py` 在只有 cu-bridge `cucc`、没有 `nvcc` 的 MXMACA 环境里完成构建——仅在 `$CUDA_HOME/bin/nvcc` 存在时做 NVIDIA 版本检查，删除硬编码的 `-gencode` 架构列表，改由 PyTorch `BuildExtension` 生成目标平台参数。
- 范围：仅修改构建脚本的编译器探测与架构参数；不改内核源码，也不声称 `MXR-KERNEL-001`、`MXR-INTRINSIC-001` 等警告已消除。
- 状态：**authored / built on MetaX C500 / not submitted upstream**。

在固定提交的干净检出中检查并应用：

```bash
git apply --check /path/to/causal-conv1d-maca.patch
git apply /path/to/causal-conv1d-maca.patch
CAUSAL_CONV1D_FORCE_BUILD=TRUE python -m pip install --no-build-isolation .
```

本地与真机验证记录（2026-11-05）：

- 重扫发现 10 → 9，warning 6 → 5，`MXR-ARCH-002` 消失；
- 在 MetaX C500（MACA 3.3.0.15、PyTorch 2.8.0+metax3.3.0.2）构建出 `causal_conv1d-1.7.0` wheel（约 17 MB）；
- 恢复干净 checkout 后 runner `overall_status: passed`，五项环境检查与单卡 smoke 全部通过。

补丁只在验证时临时应用；runner 验证的仓库保持上游提交与干净状态。结论只覆盖该提交与该环境，未提交上游。

拟议但未提交的上游 PR 标题与正文可直接参照本目录中的补丁文件。
