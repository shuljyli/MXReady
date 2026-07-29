# MXReady 适配体检报告：flash\-attention

## 扫描元数据

| 字段 | 值 |
| --- | --- |
| 仓库 | https://github\.com/Dao\-AILab/flash\-attention |
| 提交 | `c75d019dea9d910312974417bc28f190dfdda6d9` |
| MXReady 版本 | 0\.1\.0 |
| 规则集版本 | 1 |
| 扫描时间 | 2026\-07\-29T19:13:47\.789611\+00:00 |
| 静态状态 | `blocked` |
| 硬件验证状态 | `not-run` |

## 结果摘要

| 阻塞项 | 警告 | 提示 | 总计 |
| ---: | ---: | ---: | ---: |
| 5 | 124 | 10 | 139 |

## 阻塞项

### `MXR-TOOLCHAIN-001` — 检测直接 nvcc 工具调用

- 位置：`csrc/fused_dense_lib/setup.py`，第 11–11 行
- 分类：`toolchain`
- 说明：项目直接调用或固定指定 nvcc，迁移到 MXMACA/cu\-bridge 时工具入口与参数需要复核。
- 建议：请复核调用点，按 cu\-bridge 当前版本配置对应工具链，并在沐曦环境验证构建。
- 证据：

    raw_output = subprocess.check_output([cuda_dir + "/bin/nvcc", "-V"], universal_newlines=True)

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-TOOLCHAIN-001` — 检测直接 nvcc 工具调用

- 位置：`csrc/layer_norm/setup.py`，第 17–17 行
- 分类：`toolchain`
- 说明：项目直接调用或固定指定 nvcc，迁移到 MXMACA/cu\-bridge 时工具入口与参数需要复核。
- 建议：请复核调用点，按 cu\-bridge 当前版本配置对应工具链，并在沐曦环境验证构建。
- 证据：

    raw_output = subprocess.check_output([cuda_dir + "/bin/nvcc", "-V"], universal_newlines=True)

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-TOOLCHAIN-001` — 检测直接 nvcc 工具调用

- 位置：`hopper/setup.py`，第 191–191 行
- 分类：`toolchain`
- 说明：项目直接调用或固定指定 nvcc，迁移到 MXMACA/cu\-bridge 时工具入口与参数需要复核。
- 建议：请复核调用点，按 cu\-bridge 当前版本配置对应工具链，并在沐曦环境验证构建。
- 证据：

    nvcc = _join_cuda_home('bin', 'nvcc')

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-TOOLCHAIN-001` — 检测直接 nvcc 工具调用

- 位置：`hopper/setup.py`，第 339–339 行
- 分类：`toolchain`
- 说明：项目直接调用或固定指定 nvcc，迁移到 MXMACA/cu\-bridge 时工具入口与参数需要复核。
- 建议：请复核调用点，按 cu\-bridge 当前版本配置对应工具链，并在沐曦环境验证构建。
- 证据：

    raw_output = subprocess.check_output([cuda_dir + "/bin/nvcc", "-V"], universal_newlines=True)

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-TOOLCHAIN-001` — 检测直接 nvcc 工具调用

- 位置：`setup.py`，第 93–93 行
- 分类：`toolchain`
- 说明：项目直接调用或固定指定 nvcc，迁移到 MXMACA/cu\-bridge 时工具入口与参数需要复核。
- 建议：请复核调用点，按 cu\-bridge 当前版本配置对应工具链，并在沐曦环境验证构建。
- 证据：

    raw_output = subprocess.check_output([cuda_dir + "/bin/nvcc", "-V"], universal_newlines=True)

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


## 警告

### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`benchmarks/tune_ex2_emu.py`，第 86–86 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    is_sm103 = sm &gt;= 103 and sm &lt;= 103  # sm_103 to sm_103f

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/flash_attn/src/utils.h`，第 117–117 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    x = op(x, __shfl_xor_sync(uint32_t(-1), x, OFFSET));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/flash_attn/src/utils.h`，第 128–128 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    x = op(x, __shfl_xor_sync(uint32_t(-1), x, 1));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`csrc/layer_norm/ln_bwd_kernels.cuh`，第 11–11 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(Ktraits::THREADS_PER_CTA)

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`csrc/layer_norm/ln_bwd_kernels.cuh`，第 302–302 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(Kernel_traits::THREADS_PER_CTA)

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`csrc/layer_norm/ln_fwd_kernels.cuh`，第 20–20 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(Ktraits::THREADS_PER_CTA)

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`csrc/layer_norm/ln_parallel_residual_bwd_kernels.cuh`，第 12–12 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(Ktraits::THREADS_PER_CTA)

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`csrc/layer_norm/ln_parallel_residual_bwd_kernels.cuh`，第 294–294 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(Kernel_traits::THREADS_PER_CTA)

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`csrc/layer_norm/ln_parallel_residual_fwd_kernels.cuh`，第 20–20 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(Ktraits::THREADS_PER_CTA)

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/layer_norm/ln_utils.cuh`，第 125–125 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    return __shfl_xor_sync(uint32_t(-1), x, idx);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/layer_norm/ln_utils.cuh`，第 135–135 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    return __shfl_down_sync(uint32_t(-1), x, idx);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/layer_norm/ln_utils.cuh`，第 597–597 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    m_a = __shfl_sync(uint32_t(-1), m_a, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/layer_norm/ln_utils.cuh`，第 598–598 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    m2_a = __shfl_sync(uint32_t(-1), m2_a, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-BUILD-001` — 检测 TORCH\_CUDA\_ARCH\_LIST 覆盖

- 位置：`csrc/layer_norm/setup.py`，第 77–77 行
- 分类：`build`
- 说明：项目显式覆盖 TORCH\_CUDA\_ARCH\_LIST，构建产物可能绑定 NVIDIA 架构列表。
- 建议：请复核 PyTorch 扩展的架构选择方式，移除不适用假设，并在 MXMACA 环境验证构建。
- 证据：

    os.environ["TORCH_CUDA_ARCH_LIST"] = "6.0;6.1;6.2;7.0;7.5;8.0;8.6;9.0"

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-BUILD-001` — 检测 TORCH\_CUDA\_ARCH\_LIST 覆盖

- 位置：`csrc/layer_norm/setup.py`，第 79–79 行
- 分类：`build`
- 说明：项目显式覆盖 TORCH\_CUDA\_ARCH\_LIST，构建产物可能绑定 NVIDIA 架构列表。
- 建议：请复核 PyTorch 扩展的架构选择方式，移除不适用假设，并在 MXMACA 环境验证构建。
- 证据：

    os.environ["TORCH_CUDA_ARCH_LIST"] = "6.0;6.1;6.2;7.0;7.5;8.0;8.6"

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-BUILD-001` — 检测 TORCH\_CUDA\_ARCH\_LIST 覆盖

- 位置：`csrc/layer_norm/setup.py`，第 81–81 行
- 分类：`build`
- 说明：项目显式覆盖 TORCH\_CUDA\_ARCH\_LIST，构建产物可能绑定 NVIDIA 架构列表。
- 建议：请复核 PyTorch 扩展的架构选择方式，移除不适用假设，并在 MXMACA 环境验证构建。
- 证据：

    os.environ["TORCH_CUDA_ARCH_LIST"] = "6.0;6.1;6.2;7.0;7.5;8.0"

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-BUILD-001` — 检测 TORCH\_CUDA\_ARCH\_LIST 覆盖

- 位置：`csrc/layer_norm/setup.py`，第 83–83 行
- 分类：`build`
- 说明：项目显式覆盖 TORCH\_CUDA\_ARCH\_LIST，构建产物可能绑定 NVIDIA 架构列表。
- 建议：请复核 PyTorch 扩展的架构选择方式，移除不适用假设，并在 MXMACA 环境验证构建。
- 证据：

    os.environ["TORCH_CUDA_ARCH_LIST"] = "6.0;6.1;6.2;7.0;7.5"

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`csrc/layer_norm/setup.py`，第 107–107 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    cc_flag.append("arch=compute_70,code=sm_70")

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`csrc/layer_norm/setup.py`，第 109–109 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    cc_flag.append("arch=compute_80,code=sm_80")

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`csrc/layer_norm/setup.py`，第 112–112 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    cc_flag.append("arch=compute_90,code=sm_90")

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-PATH-001` — 检测硬编码 CUDA 安装路径

- 位置：`flash_attn/cute/cute_dsl_ptxas.py`，第 4–4 行
- 分类：`path`
- 说明：项目硬编码了 /usr/local/cuda，可能绕过 MXMACA/cu\-bridge 提供的工具链路径。
- 建议：请将路径改为可配置项，复核 cu\-bridge 环境变量，并在沐曦服务器验证解析结果。
- 证据：

    CUTE_DSL_PTXAS_PATH    - Path to ptxas (e.g., /usr/local/cuda/bin/ptxas)

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/flash_bwd.py`，第 146–146 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    smem_capacity = utils_basic.get_smem_capacity_in_bytes("sm_80")

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/flash_bwd_mla_dk_sm100.py`，第 107–107 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    self.arch = "sm_100"

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/flash_bwd_mla_dq_dqv_sm100.py`，第 74–74 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    self.arch = "sm_100"

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/flash_bwd_sm100.py`，第 172–172 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    self.tmem_alloc_cols = cute.arch.get_max_tmem_alloc_cols("sm_100")

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/flash_bwd_sm120.py`，第 52–52 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    smem_capacity = utils_basic.get_smem_capacity_in_bytes("sm_120")

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/flash_fwd.py`，第 169–169 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    smem_capacity = utils_basic.get_smem_capacity_in_bytes("sm_80")

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/flash_fwd.py`，第 658–658 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    self.use_tma_O = Arch.sm_90 &lt;= self.arch &lt; Arch.sm_120

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/flash_fwd_sm100.py`，第 225–225 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    # The flag gates ex2 emulation; sm_103 (B300) has fast hardware ex2 and later

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/flash_fwd_sm100.py`，第 286–286 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    self.tmem_alloc_cols = cute.arch.get_max_tmem_alloc_cols("sm_100")

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/flash_fwd_sm100.py`，第 1214–1214 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    tmem.allocate(cute.arch.get_max_tmem_alloc_cols("sm_100"))

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/flash_fwd_sm120.py`，第 19–19 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    self.arch = Arch.sm_80

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/flash_fwd_sm120.py`，第 56–56 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    smem_capacity = utils_basic.get_smem_capacity_in_bytes("sm_120")

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/flash_fwd_sm90.py`，第 225–225 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    self.use_tma_Q = self.arch &gt;= Arch.sm_90 and not (

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/interface.py`，第 69–69 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    """Parse arch string (e.g. 'sm_80', 'sm_90a', '80', '100') to int (e.g. 80, 90, 100)."""

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/interface.py`，第 82–82 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    Override with FLASH_ATTENTION_ARCH (e.g. 'sm_80' or '80') to select which

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/interface.py`，第 87–87 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    FLASH_ATTENTION_ARCH=sm_80  (kernel selection)

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`flash_attn/cute/interface.py`，第 88–88 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    CUTE_DSL_ARCH=sm_80         (compilation target)

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/epilogue_bwd.hpp`，第 212–212 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int warp_idx_sync = __shfl_sync(0xffffffff, thread_idx / cutlass::NumThreadsPerWarp, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/epilogue_fwd.hpp`，第 279–279 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int warp_group_idx = __shfl_sync(0xFFFFFFFF, thread_idx / cutlass::NumThreadsPerWarpGroup, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/epilogue_fwd.hpp`，第 317–317 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int warp_idx_sync = __shfl_sync(0xffffffff, thread_idx / cutlass::NumThreadsPerWarp, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/flash_bwd_kernel_sm90.h`，第 214–214 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int warp_idx_in_warpgroup = __shfl_sync(0xffffffff, (threadIdx.x / 32) % 4, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/flash_fwd_kernel_sm90.h`，第 318–318 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int warp_idx_in_warpgroup = __shfl_sync(0xffffffff, (threadIdx.x / 32) % 4, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/flash_prepare_scheduler.cu`，第 87–87 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int next_cu_seqlen = __shfl_down_sync(0xffffffff, cur_cu_seqlen, 1);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/flash_prepare_scheduler.cu`，第 104–104 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int next_cu_seqlen = __shfl_down_sync(0xffffffff, cur_cu_seqlen, 1);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/flash_prepare_scheduler.cu`，第 112–112 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int next_cu_seqlen_new = __shfl_down_sync(0xffffffff, cur_cu_seqlen_new, 1);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/flash_prepare_scheduler.cu`，第 150–150 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    total_blocks += __shfl_down_sync(0xffffffff, total_blocks, i);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/mainloop_bwd_sm80.hpp`，第 761–761 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    else return __shfl_sync(0xffffffff, tLSErLSE(mi / 8), (mi % 8) * 4 + (thread_idx % 4));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/mainloop_bwd_sm80.hpp`，第 796–796 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    else return __shfl_sync(0xffffffff, tLSErdPsum(mi / 8), (mi % 8) * 4 + (thread_idx % 4));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/mainloop_bwd_sm90_tma_gmma_ws.hpp`，第 674–674 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int warp_idx_in_warpgroup = __shfl_sync(0xffffffff, (threadIdx.x / 32) % 4, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/mainloop_bwd_sm90_tma_gmma_ws.hpp`，第 742–742 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int warp_group_idx = __shfl_sync(0xFFFFFFFF, thread_idx / cutlass::NumThreadsPerWarpGroup, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/mainloop_bwd_sm90_tma_gmma_ws.hpp`，第 864–864 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    else return __shfl_sync(0xffffffff, tLSErLSE(mi / 8), (mi % 8) * 4 + (thread_idx % 4));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/mainloop_bwd_sm90_tma_gmma_ws.hpp`，第 889–889 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    else return __shfl_sync(0xffffffff, tLSErdPsum(mi / 8), (mi % 8) * 4 + (thread_idx % 4));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/mainloop_fwd_sm90_tma_gmma_ws.hpp`，第 795–795 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int warp_idx_in_warpgroup = __shfl_sync(0xffffffff, (threadIdx.x / 32) % 4, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/mainloop_fwd_sm90_tma_gmma_ws.hpp`，第 900–900 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int warp_idx_in_warpgroup = __shfl_sync(0xffffffff, (threadIdx.x / 32) % 4, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/mainloop_fwd_sm90_tma_gmma_ws.hpp`，第 1018–1018 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int warp_group_idx = __shfl_sync(0xFFFFFFFF, thread_idx / cutlass::NumThreadsPerWarpGroup, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/mainloop_fwd_sm90_tma_gmma_ws.hpp`，第 1387–1387 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int warp_group_idx = __shfl_sync(0xFFFFFFFF, thread_idx / cutlass::NumThreadsPerWarpGroup, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/mainloop_fwd_sm90_tma_gmma_ws.hpp`，第 1517–1517 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int warp_idx_in_warpgroup = __shfl_sync(0xffffffff, (threadIdx.x / 32) % 4, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/mask.h`，第 94–94 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    :  __shfl_sync(0xffffffff, mma_m_idx, m % kMmaThreadsPerRow, kMmaThreadsPerRow);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/mask.h`，第 111–111 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    :  __shfl_sync(0xffffffff, mma_m_idx, m % kMmaThreadsPerRow, kMmaThreadsPerRow);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/pack_gqa.h`，第 108–108 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    Element const* q_ptr = reinterpret_cast&lt;Element const*&gt;(__shfl_sync(0xffffffff, reinterpret_cast&lt;uint64_t&gt;(tPrQPtr(m / kGmemThreadsPerRow)), m % kGmemThreadsPerRow, kGmemThreadsPerRow));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/pack_gqa.h`，第 152–152 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    float* ptr_LSE_cur = reinterpret_cast&lt;float*&gt;(__shfl_sync(0xffffffff, reinterpret_cast&lt;uint64_t&gt;(tPrLSEPtr[0]), mi % kMmaThreadsPerRow, kMmaThreadsPerRow));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/pack_gqa.h`，第 185–185 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    Element* o_ptr = reinterpret_cast&lt;Element*&gt;(__shfl_sync(0xffffffff, reinterpret_cast&lt;uint64_t&gt;(tPrOPtr(m / kGmemThreadsPerRow)), m % kGmemThreadsPerRow, kGmemThreadsPerRow));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/pack_gqa.h`，第 238–238 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    Element* o_ptr = reinterpret_cast&lt;Element*&gt;(__shfl_sync(0xffffffff, reinterpret_cast&lt;uint64_t&gt;(tPrOPtr[0]), m % kMmaThreadsPerRow, kMmaThreadsPerRow));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/paged_kv.h`，第 233–233 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    Element const* k_ptr = reinterpret_cast&lt;Element const*&gt;(__shfl_sync(0xffffffff, reinterpret_cast&lt;uint64_t&gt;(tPrKPtr(m / kGmemThreadsPerRow)), (m % kGmemThreadsPerRow), kGmemThreadsPerRow));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/paged_kv.h`，第 270–270 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    Element const* v_ptr = reinterpret_cast&lt;Element const*&gt;(__shfl_sync(0xffffffff, reinterpret_cast&lt;uint64_t&gt;(tPrVPtr(m / kGmemThreadsPerRow)), m % kGmemThreadsPerRow, kGmemThreadsPerRow));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/paged_kv.h`，第 304–304 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    Element* k_ptr = reinterpret_cast&lt;Element*&gt;(__shfl_sync(0xffffffff, reinterpret_cast&lt;uint64_t&gt;(tPrKPtr(m / kGmemThreadsPerRow)), (m % kGmemThreadsPerRow), kGmemThreadsPerRow));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/paged_kv.h`，第 335–335 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    Element* v_ptr = reinterpret_cast&lt;Element*&gt;(__shfl_sync(0xffffffff, reinterpret_cast&lt;uint64_t&gt;(tPrVPtr(m / kGmemThreadsPerRow)), m % kGmemThreadsPerRow, kGmemThreadsPerRow));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/rotary.h`，第 246–246 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    Element const* cos_ptr = reinterpret_cast&lt;Element const*&gt;(__shfl_sync(0xffffffff, reinterpret_cast&lt;uint64_t&gt;(tPrCosPtr(m / kGmemThreadsPerRow)), m % kGmemThreadsPerRow, kGmemThreadsPerRow));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/rotary.h`，第 247–247 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    Element const* sin_ptr = reinterpret_cast&lt;Element const*&gt;(__shfl_sync(0xffffffff, reinterpret_cast&lt;uint64_t&gt;(tPrSinPtr(m / kGmemThreadsPerRow)), m % kGmemThreadsPerRow, kGmemThreadsPerRow));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/rotary.h`，第 389–389 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    Element* k_ptr = reinterpret_cast&lt;Element*&gt;(__shfl_sync(0xffffffff, reinterpret_cast&lt;uint64_t&gt;(tPrKPtr(m / kGmemThreadsPerRow)), (m % kGmemThreadsPerRow), kGmemThreadsPerRow));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/rotary.h`，第 453–453 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    Element* k_ptr = reinterpret_cast&lt;Element*&gt;(__shfl_sync(0xffffffff, reinterpret_cast&lt;uint64_t&gt;(tPrKPtr(m / kGmemThreadsPerRow)), (m % kGmemThreadsPerRow), kGmemThreadsPerRow));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-001` — 检测 CUDA gencode 参数

- 位置：`hopper/setup.py`，第 75–75 行
- 分类：`architecture`
- 说明：构建参数显式生成 NVIDIA compute/sm 目标，可能固化了设备架构假设。
- 建议：请复核目标架构参数，依据 MXMACA 工具链要求调整，并在沐曦设备验证生成物。
- 证据：

    # "-gencode arch=compute_sm90a,code=sm_90a" to files ending in '_sm90.cu',

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-001` — 检测 CUDA gencode 参数

- 位置：`hopper/setup.py`，第 76–76 行
- 分类：`architecture`
- 说明：构建参数显式生成 NVIDIA compute/sm 目标，可能固化了设备架构假设。
- 建议：请复核目标架构参数，依据 MXMACA 工具链要求调整，并在沐曦设备验证生成物。
- 证据：

    # and pass "-gencode arch=compute_sm80,code=sm_80" to files ending in '_sm80.cu'

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`hopper/setup.py`，第 76–76 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    # and pass "-gencode arch=compute_sm80,code=sm_80" to files ending in '_sm80.cu'

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`hopper/setup.py`，第 206–206 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    cuda_post_cflags_sm80 = [s if s != 'arch=compute_90a,code=sm_90a' else 'arch=compute_80,code=sm_80' for s in cuda_post_cflags]

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`hopper/setup.py`，第 208–208 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    cuda_post_cflags_sm80_sm90 = cuda_post_cflags + ['-gencode', 'arch=compute_80,code=sm_80']

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-PATH-001` — 检测硬编码 CUDA 安装路径

- 位置：`hopper/setup.py`，第 511–511 行
- 分类：`path`
- 说明：项目硬编码了 /usr/local/cuda，可能绕过 MXMACA/cu\-bridge 提供的工具链路径。
- 建议：请将路径改为可配置项，复核 cu\-bridge 环境变量，并在沐曦服务器验证解析结果。
- 证据：

    # CUDA 13.0+ uses system nvcc and CCCL headers are in /usr/local/cuda/include/cccl/

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/tile_scheduler.hpp`，第 348–348 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int new_tile_idx = __shfl_sync(0xffffffff, current_work.tile_idx, 0 /*lane*/);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/tile_scheduler.hpp`，第 611–611 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int next_cu_seqlen = __shfl_down_sync(0xffffffff, cur_cu_seqlen, 1);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/tile_scheduler.hpp`，第 642–642 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int m_blocks_in_group = __shfl_sync(0xffffffff, num_m_blocks_cumulative, cutlass::NumThreadsPerWarp - 1);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/tile_scheduler.hpp`，第 645–645 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    // int group_end_tile = current_work.tile_idx - current_work.block - current_bidh * __shfl_sync(0xffffffff, num_split_m_blocks, 0 /*lane*/) + m_blocks_in_group * params.num_head;  // Same for all lanes

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/tile_scheduler.hpp`，第 648–648 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    //     group_end_tile -= current_split_idx * __shfl_sync(0xffffffff, num_m_blocks, 0 /*lane*/);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/tile_scheduler.hpp`，第 669–669 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    m_blocks_in_group = __shfl_sync(0xffffffff, num_m_blocks_cumulative, cutlass::NumThreadsPerWarp - 1);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/tile_scheduler.hpp`，第 678–678 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int batch_idx_in_group = __popc(__ballot_sync(0xffffffff, group_start_tile + num_m_blocks_cumulative * params.num_head &lt;= next_tile_idx));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/tile_scheduler.hpp`，第 681–681 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    num_m_blocks = __shfl_sync(0xffffffff, num_m_blocks, batch_idx_in_group);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/tile_scheduler.hpp`，第 682–682 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    if constexpr (Split) { num_splits = __shfl_sync(0xffffffff, num_splits, batch_idx_in_group); }

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/tile_scheduler.hpp`，第 683–683 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    group_start_tile += (batch_idx_in_group == 0 ? 0 : __shfl_sync(0xffffffff, num_m_blocks_cumulative, batch_idx_in_group - 1)) * params.num_head;

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/tile_scheduler.hpp`，第 796–796 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    int new_tile_idx = __shfl_sync(0xffffffff, current_work.tile_idx, 0 /*lane*/);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/tile_scheduler.hpp`，第 797–797 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    WorkTileInfo work_info = {__shfl_sync(0xffffffff, current_work.tile_idx, 1 /*lane*/), current_work.block, current_work.bidh, current_work.bidb};

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/utils.h`，第 84–84 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    x = op(x, __shfl_xor_sync(uint32_t(-1), x, OFFSET));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/utils.h`，第 95–95 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    x = op(x, __shfl_xor_sync(uint32_t(-1), x, 1));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/utils.h`，第 478–478 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    upper0 = __shfl_sync(uint32_t(-1), upper0, upper_map[quad_idx], 4);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/utils.h`，第 479–479 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    // lower0 = __shfl_sync(uint32_t(-1), lower0, lower_map[quad_idx], 4);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/utils.h`，第 480–480 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    lower0 = __shfl_sync(uint32_t(-1), lower0, upper_map[quad_idx] ^ 1, 4);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/utils.h`，第 559–559 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    upper0 = __shfl_sync(uint32_t(-1), upper0, upper_map[quad_idx], 4);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/utils.h`，第 560–560 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    // lower0 = __shfl_sync(uint32_t(-1), lower0, lower_map[quad_idx], 4);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/utils.h`，第 561–561 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    lower0 = __shfl_sync(uint32_t(-1), lower0, upper_map[quad_idx] ^ 2, 4);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/utils.h`，第 597–597 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    T partial_sum = __shfl_up_sync(0xffffffff, val, i);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/utils.h`，第 607–607 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    return __shfl_sync(0xffffffff, val, src_lane);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/utils.h`，第 612–612 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    return __shfl_sync(0xffffffff, val, cutlass::NumThreadsPerWarp - 1);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/utils.h`，第 616–616 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    return __popc(__ballot_sync(0xffffffff, cond));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`hopper/utils.h`，第 623–623 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    return __shfl_sync(0xffffffff, a, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-001` — 检测 CUDA gencode 参数

- 位置：`setup.py`，第 103–103 行
- 分类：`architecture`
- 说明：构建参数显式生成 NVIDIA compute/sm 目标，可能固化了设备架构假设。
- 建议：请复核目标架构参数，依据 MXMACA 工具链要求调整，并在沐曦设备验证生成物。
- 证据：

    Adds -gencode flags based on nvcc capabilities:

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 104–104 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    - sm_80/90 (regular)

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 105–105 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    - sm_100/120 on CUDA &gt;= 12.8

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 112–112 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    cc_flag += ["-gencode", "arch=compute_80,code=sm_80"]

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 116–116 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    cc_flag += ["-gencode", "arch=compute_90,code=sm_90"]

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 123–123 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    cc_flag += ["-gencode", "arch=compute_100f,code=sm_100"]

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 125–125 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    cc_flag += ["-gencode", "arch=compute_100,code=sm_100"]

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 128–128 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    # sm_120 is supported in CUDA 12.8/12.9+ toolkits

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 130–130 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    cc_flag += ["-gencode", "arch=compute_120f,code=sm_120"]

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 132–132 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    cc_flag += ["-gencode", "arch=compute_120,code=sm_120"]

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 135–135 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    # Thor rename: 12.9 uses sm_101; 13.0+ uses sm_110

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 138–138 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    cc_flag += ["-gencode", "arch=compute_110f,code=sm_110"]

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 140–140 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    # Provide Thor support for CUDA 12.9 via sm_101

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 142–142 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    cc_flag += ["-gencode", "arch=compute_101,code=sm_101"]

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-001` — 检测 CUDA gencode 参数

- 位置：`setup.py`，第 300–300 行
- 分类：`architecture`
- 说明：构建参数显式生成 NVIDIA compute/sm 目标，可能固化了设备架构假设。
- 建议：请复核目标架构参数，依据 MXMACA 工具链要求调整，并在沐曦设备验证生成物。
- 证据：

    # Build -gencode (regular + PTX + family-specific 'f' when available)

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`tests/cute/test_flash_attn.py`，第 477–477 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    # for sm_100/110, so this path needs coverage. Trigger requires

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-COMM-001` — 检测 NCCL 环境变量覆盖

- 位置：`tests/models/test_baichuan.py`，第 363–364 行
- 分类：`communication`
- 说明：项目覆盖了 NVIDIA NCCL 环境变量，多卡通信配置包含平台特定假设。
- 建议：请复核通信后端、环境变量和拓扑配置，并在沐曦多卡环境进行针对性验证。
- 证据：

    os.environ["NCCL_ASYNC_ERROR_HANDLING"] = "0"

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-001` — 检测 NCCL 环境变量覆盖

- 位置：`tests/models/test_falcon.py`，第 312–313 行
- 分类：`communication`
- 说明：项目覆盖了 NVIDIA NCCL 环境变量，多卡通信配置包含平台特定假设。
- 建议：请复核通信后端、环境变量和拓扑配置，并在沐曦多卡环境进行针对性验证。
- 证据：

    os.environ["NCCL_ASYNC_ERROR_HANDLING"] = "0"

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-001` — 检测 NCCL 环境变量覆盖

- 位置：`tests/models/test_gpt_generation_parallel.py`，第 39–40 行
- 分类：`communication`
- 说明：项目覆盖了 NVIDIA NCCL 环境变量，多卡通信配置包含平台特定假设。
- 建议：请复核通信后端、环境变量和拓扑配置，并在沐曦多卡环境进行针对性验证。
- 证据：

    os.environ["NCCL_ASYNC_ERROR_HANDLING"] = "0"

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-001` — 检测 NCCL 环境变量覆盖

- 位置：`tests/models/test_llama.py`，第 428–429 行
- 分类：`communication`
- 说明：项目覆盖了 NVIDIA NCCL 环境变量，多卡通信配置包含平台特定假设。
- 建议：请复核通信后端、环境变量和拓扑配置，并在沐曦多卡环境进行针对性验证。
- 证据：

    os.environ["NCCL_ASYNC_ERROR_HANDLING"] = "0"

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-TOOL-001` — 检测直接 nvidia\-smi 调用

- 位置：`tools/ci/run_fa4_ci.py`，第 79–79 行
- 分类：`tool`
- 说明：项目直接调用 nvidia\-smi，设备发现或诊断流程依赖 NVIDIA 专用工具。
- 建议：请复核诊断逻辑并提供可替换工具入口，再在沐曦服务器验证设备信息采集。
- 证据：

    out = subprocess.run(["nvidia-smi"], check=True, capture_output=True, text=True).stdout

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


## 提示

### `MXR-HEADER-002` — 识别 cuda\.h 驱动头文件

- 位置：`csrc/flash_attn/src/flash.h`，第 8–9 行
- 分类：`header`
- 说明：源码直接包含 CUDA Driver 头文件，需要核对所用 Driver API 的目标映射。
- 建议：请复核 Driver API 调用范围，并结合 cu\-bridge 文档在沐曦环境验证编译与行为。
- 证据：

    #include &lt;cuda.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/flash_attn/src/hardware_info.h`，第 10–10 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include "cuda_runtime.h"

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/fused_dense_lib/fused_dense_cuda.cu`，第 12–12 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`csrc/fused_dense_lib/setup.py`，第 30–30 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`csrc/layer_norm/setup.py`，第 115–115 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-HEADER-002` — 识别 cuda\.h 驱动头文件

- 位置：`hopper/flash.h`，第 6–7 行
- 分类：`header`
- 说明：源码直接包含 CUDA Driver 头文件，需要核对所用 Driver API 的目标映射。
- 建议：请复核 Driver API 调用范围，并结合 cu\-bridge 文档在沐曦环境验证编译与行为。
- 证据：

    #include &lt;cuda.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`hopper/flash_api_stable.cpp`，第 26–27 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`hopper/setup.py`，第 692–692 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 347–347 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 603–603 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


## 迁移清单

- [ ] `MXR-TOOLCHAIN-001` 检测直接 nvcc 工具调用：请复核调用点，按 cu\-bridge 当前版本配置对应工具链，并在沐曦环境验证构建。
  - 涉及文件：`csrc/fused_dense_lib/setup.py`、`csrc/layer_norm/setup.py`、`hopper/setup.py`、`setup.py`
- [ ] `MXR-ARCH-002` 检测硬编码 sm 或 compute 架构：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
  - 涉及文件：`benchmarks/tune_ex2_emu.py`、`csrc/layer_norm/setup.py`、`flash_attn/cute/flash_bwd.py`、`flash_attn/cute/flash_bwd_mla_dk_sm100.py`、`flash_attn/cute/flash_bwd_mla_dq_dqv_sm100.py`、`flash_attn/cute/flash_bwd_sm100.py`、`flash_attn/cute/flash_bwd_sm120.py`、`flash_attn/cute/flash_fwd.py`、`flash_attn/cute/flash_fwd_sm100.py`、`flash_attn/cute/flash_fwd_sm120.py`、`flash_attn/cute/flash_fwd_sm90.py`、`flash_attn/cute/interface.py`、`hopper/setup.py`、`setup.py`、`tests/cute/test_flash_attn.py`
- [ ] `MXR-INTRINSIC-001` 检测 CUDA warp 同步内建函数：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
  - 涉及文件：`csrc/flash_attn/src/utils.h`、`csrc/layer_norm/ln_utils.cuh`、`hopper/epilogue_bwd.hpp`、`hopper/epilogue_fwd.hpp`、`hopper/flash_bwd_kernel_sm90.h`、`hopper/flash_fwd_kernel_sm90.h`、`hopper/flash_prepare_scheduler.cu`、`hopper/mainloop_bwd_sm80.hpp`、`hopper/mainloop_bwd_sm90_tma_gmma_ws.hpp`、`hopper/mainloop_fwd_sm90_tma_gmma_ws.hpp`、`hopper/mask.h`、`hopper/pack_gqa.h`、`hopper/paged_kv.h`、`hopper/rotary.h`、`hopper/tile_scheduler.hpp`、`hopper/utils.h`
- [ ] `MXR-KERNEL-001` 检测 \_\_launch\_bounds\_\_ 调优假设：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
  - 涉及文件：`csrc/layer_norm/ln_bwd_kernels.cuh`、`csrc/layer_norm/ln_fwd_kernels.cuh`、`csrc/layer_norm/ln_parallel_residual_bwd_kernels.cuh`、`csrc/layer_norm/ln_parallel_residual_fwd_kernels.cuh`
- [ ] `MXR-BUILD-001` 检测 TORCH\_CUDA\_ARCH\_LIST 覆盖：请复核 PyTorch 扩展的架构选择方式，移除不适用假设，并在 MXMACA 环境验证构建。
  - 涉及文件：`csrc/layer_norm/setup.py`
- [ ] `MXR-PATH-001` 检测硬编码 CUDA 安装路径：请将路径改为可配置项，复核 cu\-bridge 环境变量，并在沐曦服务器验证解析结果。
  - 涉及文件：`flash_attn/cute/cute_dsl_ptxas.py`、`hopper/setup.py`
- [ ] `MXR-ARCH-001` 检测 CUDA gencode 参数：请复核目标架构参数，依据 MXMACA 工具链要求调整，并在沐曦设备验证生成物。
  - 涉及文件：`hopper/setup.py`、`setup.py`
- [ ] `MXR-COMM-001` 检测 NCCL 环境变量覆盖：请复核通信后端、环境变量和拓扑配置，并在沐曦多卡环境进行针对性验证。
  - 涉及文件：`tests/models/test_baichuan.py`、`tests/models/test_falcon.py`、`tests/models/test_gpt_generation_parallel.py`、`tests/models/test_llama.py`
- [ ] `MXR-TOOL-001` 检测直接 nvidia\-smi 调用：请复核诊断逻辑并提供可替换工具入口，再在沐曦服务器验证设备信息采集。
  - 涉及文件：`tools/ci/run_fa4_ci.py`

## 分析警告

无。

## 说明

静态扫描不能替代真实沐曦 GPU 上的构建、功能和性能验证，也不能作为项目安全性或完整兼容性的证明。
