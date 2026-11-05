# MXReady 真实仓库迁移案例（2026-11-05）

本轮材料补上了此前缺失的三类证据：真实仓库的阻断项诊断、一个可构建仓库的“修复→重扫→真机复验”闭环，以及 runner 的否定路径。全部结论都来自本机固定提交的离线克隆与沐曦 C500 容器实测。文中引用的报告、补丁与 runner 结果均已随仓库提交，可直接核验。

## 环境

| 项目 | 实测值 |
| --- | --- |
| GPU | MetaX C500，65536 MiB |
| KMD / MACA | 3.8.30 / 3.3.0.15 |
| mx-smi | 2.2.9 |
| PyTorch | 2.8.0+metax3.3.0.2 |
| Python | 3.10.10（镜像标签声明的 3.12 / 3.3.0.4 与实测不符） |
| 工具链 | `/opt/maca/tools/cu-bridge`，只有 `cucc`，无 `nvcc`、无 `include/cub` |

## 案例 A：bitsandbytes 触发真实阻断项（静态）

- 仓库：`https://github.com/bitsandbytes-foundation/bitsandbytes`，固定提交 `a616886cacf86701514f0cb1d6be760f967481c0`。
- 结果：`static_status: blocked`，共 27 条发现，其中 **7 个 blocker / 10 个 warning / 10 个 info**，CLI 退出码 2。
- 阻断项分布：`MXR-PTX-001` 4 条（内联 PTX，集中在 4-bit GEMM 的 `mma.sync` 内核）、`MXR-WARP-001` 3 条（`threadIdx.x & 31`、`threadIdx.x / 32` 的 32 线程束假设）。
- 命中文件：`csrc/gemm_4bit_simt.cu`、`csrc/gemm_4bit_sm75.cu`、`csrc/gemm_4bit_sm80.cu`、`csrc/gemm_4bit_mma.cuh`。
- 意义：这些不是风格问题，而是 MXMACA 上无法直接编译或语义不成立的代码；工具在克隆阶段即可拦截，避免把无效仓库送进真机队列。

证据：[`examples/reports/bitsandbytes.md`](../examples/reports/bitsandbytes.md)、[`bitsandbytes.json`](../examples/reports/bitsandbytes.json)。

## 案例 B：causal-conv1d 修复后真机通过（闭环）

- 仓库：`https://github.com/Dao-AILab/causal-conv1d`，固定提交 `cd81f0413cad2fc1e6f17e785ac39f59aae690cd`。
- 初始扫描：10 条发现，0 blocker / 6 warning / 4 info，其中 `MXR-ARCH-002` 指向 `setup.py` 里硬编码的 `sm_75/sm_80/sm_87/sm_90...` 架构列表，`MXR-PATH-001` 指向 CI 脚本里的 `/usr/local/cuda`。
- 修复补丁（`dist/work/causal-conv1d-maca.patch`）：
  1. `setup.py` 仅在 `$CUDA_HOME/bin/nvcc` 存在时执行 NVIDIA 版本检查；
  2. 删除硬编码 `-gencode arch=compute_*,code=sm_*`，改由 PyTorch `BuildExtension` 生成目标平台参数；
  3. 无 `nvcc` 时不再传 `--ptxas-options=-v`、`-lineinfo`、`--threads`。
- 重扫：10 → 9 条发现，warning 6 → 5，`MXR-ARCH-002` 消失；其余 warning（内核语义、intrinsic、CI 路径）保留并如实记录。
- 真机：在 C500 上以补丁构建出 `causal_conv1d-1.7.0` wheel（约 17 MB），导入成功；随后 `git checkout -- setup.py` 恢复干净 checkout，再由 runner 验证。
- runner 结果：`overall_status: passed`；5 项环境检查全部通过；`causal-conv1d-cuda-smoke` 用仓库自带的 `causal_conv1d_ref` / `causal_conv1d_update_ref` 对比前向与更新内核，耗时 11.8 s，通过。
- Python 兼容性：runner 去掉 `datetime.UTC`（3.11+）后，直接在镜像自带 Python 3.10.10 上运行，未依赖 `python3.12`。

证据：

- [`examples/verification/causal-conv1d/result.json`](../examples/verification/causal-conv1d/result.json)、[`mxready.yml`](../examples/verification/causal-conv1d/mxready.yml)、[`commands.json`](../examples/verification/causal-conv1d/commands.json)
- [`examples/reports/causal-conv1d.md`](../examples/reports/causal-conv1d.md)（修复前）
- [`examples/reports/causal-conv1d-patched.md`](../examples/reports/causal-conv1d-patched.md)（修复后）
- [`examples/patches/causal-conv1d-maca.patch`](../examples/patches/causal-conv1d-maca.patch)

## 否定路径

在干净 checkout 中放入一个未跟踪文件后重新执行 runner：退出码 2，报错 `Repository is dirty; use a clean checkout`，且不生成 `result.json`。清理后仓库恢复干净。

证据：本轮 SSH 输出，runner 0.3.1。

## 案例 C：extension-cpp 基线（此前已完成）

- `pytorch/extension-cpp`，提交 `1c325b202ae5e11de3cefb9a65be28f47949edd4`，扫描 0 blocker / 0 warning / 4 info。
- 真机 `overall_status: passed`；smoke 10.9 s；probe 功能通过，1M float32 元素、100 次重复中位 0.074 ms。
- 证据：[`examples/verification/metax-verification-redacted.json`](../examples/verification/metax-verification-redacted.json)（runner 结果）、[`examples/hardware/extension-cpp-probe-result.json`](../examples/hardware/extension-cpp-probe-result.json)（probe）、[`examples/reports/pytorch-extension-cpp.json`](../examples/reports/pytorch-extension-cpp.json)（静态报告）。

## 边界与未完成项

- bitsandbytes 只做了静态诊断，未在 MXMACA 上编译；其 PTX/线程束假设需要代码级重写，补丁不是本轮范围。
- causal-conv1d 的构建补丁只用于本轮真机构建，未提交上游；验证记录绑定的是上游提交 + 临时补丁，仓库自身在验证时保持干净。
- runner 代码已可在 Python 3.10 运行，但发布 wheel 的 `requires-python` 仍为 `>=3.11`；镜像上使用 runner 需要源码目录或单独发布物。
- 环境行只有一条（Python 3.10.10 / MACA 3.3.0.15）；标签宣称的 Python 3.12 / MACA 3.3.0.4 尚无实测证据。
- 本轮在容器中卸载了镜像预装的 `causal_conv1d 1.5.0.post8+metax3.3.0.2torch2.8`，替换为本轮构建的 1.7.0；如需恢复预装版本需另行安装。
