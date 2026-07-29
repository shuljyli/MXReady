# MXReady 适配体检报告：apex

## 扫描元数据

| 字段 | 值 |
| --- | --- |
| 仓库 | https://github\.com/NVIDIA/apex |
| 提交 | `6424da3b4faa6c8f062da4a48c424fff3f02d42d` |
| MXReady 版本 | 0\.1\.0 |
| 规则集版本 | 1 |
| 扫描时间 | 2026\-07\-29T19:12:42\.560205\+00:00 |
| 静态状态 | `blocked` |
| 硬件验证状态 | `not-run` |

## 结果摘要

| 阻塞项 | 警告 | 提示 | 总计 |
| ---: | ---: | ---: | ---: |
| 1 | 78 | 64 | 143 |

## 阻塞项

### `MXR-TOOLCHAIN-001` — 检测直接 nvcc 工具调用

- 位置：`setup.py`，第 66–66 行
- 分类：`toolchain`
- 说明：项目直接调用或固定指定 nvcc，迁移到 MXMACA/cu\-bridge 时工具入口与参数需要复核。
- 建议：请复核调用点，按 cu\-bridge 当前版本配置对应工具链，并在沐曦环境验证构建。
- 证据：

    raw_output = subprocess.check_output([cuda_dir + "/bin/nvcc", "-V"], universal_newlines=True)

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


## 警告

### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`apex/contrib/csrc/group_norm/group_norm_nhwc_bwd_one_pass_kernel.cuh`，第 19–19 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(THREADS_PER_BLOCK_) void group_norm_nhwc_bwd_one_pass_kernel(

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`apex/contrib/csrc/group_norm/group_norm_nhwc_fwd_one_pass_kernel.cuh`，第 19–19 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(THREADS_PER_BLOCK_) void group_norm_nhwc_fwd_one_pass_kernel(

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 195–195 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(BLOCK_DIM_X, BLOCKS_PER_SM) void gn_cuda_kernel(

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 292–292 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    frag_sum_per_channel[i].x += __shfl_xor_sync(FINAL_MASK, frag_sum_per_channel[i].x, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 293–293 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    frag_sum_per_channel[i].y += __shfl_xor_sync(FINAL_MASK, frag_sum_per_channel[i].y, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 324–324 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum.x += __shfl_xor_sync(FINAL_MASK, sum.x, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 325–325 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum.y += __shfl_xor_sync(FINAL_MASK, sum.y, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 366–366 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum_local_group.x += __shfl_xor_sync(FINAL_MASK, sum_local_group.x, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 367–367 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum_local_group.y += __shfl_xor_sync(FINAL_MASK, sum_local_group.y, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 411–411 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum_local_group.x += __shfl_xor_sync(FINAL_MASK, sum_local_group.x, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 412–412 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum_local_group.y += __shfl_xor_sync(FINAL_MASK, sum_local_group.y, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 512–512 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum_global_group.x += __shfl_xor_sync(FINAL_MASK, sum_global_group.x, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 513–513 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum_global_group.y += __shfl_xor_sync(FINAL_MASK, sum_global_group.y, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 596–596 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(BLOCK_DIM_X, BLOCKS_PER_SM) void gn_bwd_cuda_kernel(

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 777–777 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    frag_sum_per_channel[i].x += __shfl_xor_sync(FINAL_MASK, frag_sum_per_channel[i].x, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 778–778 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    frag_sum_per_channel[i].y += __shfl_xor_sync(FINAL_MASK, frag_sum_per_channel[i].y, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 823–823 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum.x += __shfl_xor_sync(FINAL_MASK, sum.x, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 824–824 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum.y += __shfl_xor_sync(FINAL_MASK, sum.y, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 865–865 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    dw_block += __shfl_xor_sync(FINAL_MASK, dw_block, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 866–866 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    db_block += __shfl_xor_sync(FINAL_MASK, db_block, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 902–902 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum_local_group.x += __shfl_xor_sync(FINAL_MASK, sum_local_group.x, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 903–903 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum_local_group.y += __shfl_xor_sync(FINAL_MASK, sum_local_group.y, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 947–947 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum_local_group.x += __shfl_xor_sync(FINAL_MASK, sum_local_group.x, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 948–948 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum_local_group.y += __shfl_xor_sync(FINAL_MASK, sum_local_group.y, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 1079–1079 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum_global_group.x += __shfl_xor_sync(FINAL_MASK, sum_global_group.x, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 1080–1080 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum_global_group.y += __shfl_xor_sync(FINAL_MASK, sum_global_group.y, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 1201–1201 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum_wgrad += __shfl_xor_sync((uint64_t(1) &lt;&lt; warp_num_pow2) - 1, sum_wgrad, mask, warp_num_pow2);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 1202–1202 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    sum_bgrad += __shfl_xor_sync((uint64_t(1) &lt;&lt; warp_num_pow2) - 1, sum_bgrad, mask, warp_num_pow2);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 381–381 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    x[i] += __shfl_sync(0xffffffffU, x[i], THREADS_PER_PIXEL + lane_id);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 407–407 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    x[i] += __shfl_sync(0xffffffffU, x[i], THREADS_PER_PIXEL + lane_id);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 484–484 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    x[i] += __shfl_sync(0xffffffffU, x[i], THREADS_PER_PIXEL + lane_id);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 485–485 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    x[i] += __shfl_sync(0xffffffffU, x[i], THREADS_PER_PIXEL * 2 + lane_id);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 511–511 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    x[i] += __shfl_sync(0xffffffffU, x[i], THREADS_PER_PIXEL + lane_id);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 512–512 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    x[i] += __shfl_sync(0xffffffffU, x[i], THREADS_PER_PIXEL * 2 + lane_id);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 695–695 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(THREADS_PER_CTA) void nhwc_batch_norm_fwd_inference(

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 816–816 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(THREADS_PER_CTA,

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 1249–1249 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    unsigned int local_relu_mask = __ballot_sync(0xFFFFFFFFU, rectified);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 1311–1311 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    unsigned int local_relu_mask = __ballot_sync(0xFFFFFFFFU, rectified);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 1466–1466 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(THREADS_PER_CTA,

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 1815–1815 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(THREADS_PER_CTA,

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 2187–2187 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(THREADS_PER_CTA,

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 2312–2312 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    rectified[j] = ((__shfl_sync(0xFFFFFFFFU, relu_mask[i], j) &amp; (1U &lt;&lt; lane_id)) != 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 2366–2366 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    rectified[j] = ((__shfl_sync(0xFFFFFFFFU, relu_mask, j) &amp; (1U &lt;&lt; lane_id)) != 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`apex/contrib/csrc/layer_norm/ln_bwd_kernels.cuh`，第 8–8 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(Ktraits::THREADS_PER_CTA) void ln_bwd_kernel(layer_norm::BwdParams params) {

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`apex/contrib/csrc/layer_norm/ln_bwd_kernels.cuh`，第 202–202 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(Kernel_traits::THREADS_PER_CTA) void ln_bwd_finalize_kernel(BwdParams params) {

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`apex/contrib/csrc/layer_norm/ln_fwd_kernels.cuh`，第 9–9 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(Ktraits::THREADS_PER_CTA) void ln_fwd_kernel(FwdParams params) {

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/layer_norm/ln_utils.cuh`，第 82–82 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    return __shfl_xor_sync(uint32_t(-1), x, idx);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/layer_norm/ln_utils.cuh`，第 92–92 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    return __shfl_down_sync(uint32_t(-1), x, idx);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/layer_norm/ln_utils.cuh`，第 531–531 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    m_a = __shfl_sync(uint32_t(-1), m_a, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/layer_norm/ln_utils.cuh`，第 532–532 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    m2_a = __shfl_sync(uint32_t(-1), m2_a, 0);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`apex/contrib/csrc/peer_memory/peer_memory_cuda.cu`，第 258–258 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __launch_bounds__(THREADS_PER_CTA)

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/transducer/transducer_joint_kernel.cu`，第 25–25 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    x += __shfl_down_sync(0xffffffff, x, offset, width);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-COMM-001` — 检测 NCCL 环境变量覆盖

- 位置：`apex/contrib/nccl_allocator/nccl_allocator.py`，第 37–37 行
- 分类：`communication`
- 说明：项目覆盖了 NVIDIA NCCL 环境变量，多卡通信配置包含平台特定假设。
- 建议：请复核通信后端、环境变量和拓扑配置，并在沐曦多卡环境进行针对性验证。
- 证据：

    os.environ["NCCL_NVLS_ENABLE"] = "1"

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-001` — 检测 NCCL 环境变量覆盖

- 位置：`apex/contrib/nccl_allocator/nccl_allocator.py`，第 38–38 行
- 分类：`communication`
- 说明：项目覆盖了 NVIDIA NCCL 环境变量，多卡通信配置包含平台特定假设。
- 建议：请复核通信后端、环境变量和拓扑配置，并在沐曦多卡环境进行针对性验证。
- 证据：

    os.environ["TORCH_NCCL_USE_TENSOR_REGISTER_ALLOCATOR_HOOK"] = "0"

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-TOOL-001` — 检测直接 nvidia\-smi 调用

- 位置：`apex/contrib/sparsity/permutation_search_kernels/permutation_utilities.py`，第 31–31 行
- 分类：`tool`
- 说明：项目直接调用 nvidia\-smi，设备发现或诊断流程依赖 NVIDIA 专用工具。
- 建议：请复核诊断逻辑并提供可替换工具入口，再在沐曦服务器验证设备信息采集。
- 证据：

    gpus_found = str(subprocess.check_output(["nvidia-smi", "-L"])).count("UUID")

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/megatron/generic_scaled_masked_softmax.h`，第 43–43 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    return __shfl_down_sync(mask, value, laneMask, width);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/megatron/scaled_masked_softmax.h`，第 82–82 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    return __shfl_xor_sync(mask, value, laneMask, width);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/megatron/scaled_upper_triang_masked_softmax.h`，第 105–105 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    return __shfl_xor_sync(mask, value, laneMask, width);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/type_shim.h`，第 291–291 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    for (int i = 16; i &gt;= lanes; i &gt;&gt;= 1) final = final + __shfl_down_sync(0xffffffff, final, i);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/type_shim.h`，第 333–333 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    for (int i = 16; i &gt;= lanes; i &gt;&gt;= 1) final = fmaxf(fabsf(final), fabsf(__shfl_down_sync(0xffffffff, final, i)));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/welford.cu`，第 42–42 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    for (int i = WARP_SIZE / 2; i &gt; 0; i &gt;&gt;= 1) val = val + __shfl_down_sync(0xffffffff, val, i);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/welford.cu`，第 110–110 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    auto num_new = __shfl_down_sync(0xffffffff, num, i);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/welford.cu`，第 111–111 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    auto mean_new = __shfl_down_sync(0xffffffff, mean, i);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/welford.cu`，第 112–112 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    auto m2n_new = __shfl_down_sync(0xffffffff, m2n, i);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-BUILD-001` — 检测 TORCH\_CUDA\_ARCH\_LIST 覆盖

- 位置：`setup.py`，第 131–131 行
- 分类：`build`
- 说明：项目显式覆盖 TORCH\_CUDA\_ARCH\_LIST，构建产物可能绑定 NVIDIA 架构列表。
- 建议：请复核 PyTorch 扩展的架构选择方式，移除不适用假设，并在 MXMACA 环境验证构建。
- 证据：

    os.environ["TORCH_CUDA_ARCH_LIST"] = "7.5;8.0;8.6;9.0;10.0;11.0;12.0"

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-BUILD-001` — 检测 TORCH\_CUDA\_ARCH\_LIST 覆盖

- 位置：`setup.py`，第 133–133 行
- 分类：`build`
- 说明：项目显式覆盖 TORCH\_CUDA\_ARCH\_LIST，构建产物可能绑定 NVIDIA 架构列表。
- 建议：请复核 PyTorch 扩展的架构选择方式，移除不适用假设，并在 MXMACA 环境验证构建。
- 证据：

    os.environ["TORCH_CUDA_ARCH_LIST"] = "7.0;7.5;8.0;8.6;9.0;10.0;12.0"

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-BUILD-001` — 检测 TORCH\_CUDA\_ARCH\_LIST 覆盖

- 位置：`setup.py`，第 135–135 行
- 分类：`build`
- 说明：项目显式覆盖 TORCH\_CUDA\_ARCH\_LIST，构建产物可能绑定 NVIDIA 架构列表。
- 建议：请复核 PyTorch 扩展的架构选择方式，移除不适用假设，并在 MXMACA 环境验证构建。
- 证据：

    os.environ["TORCH_CUDA_ARCH_LIST"] = "6.0;6.1;6.2;7.0;7.5;8.0;8.6;9.0"

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-BUILD-001` — 检测 TORCH\_CUDA\_ARCH\_LIST 覆盖

- 位置：`setup.py`，第 137–137 行
- 分类：`build`
- 说明：项目显式覆盖 TORCH\_CUDA\_ARCH\_LIST，构建产物可能绑定 NVIDIA 架构列表。
- 建议：请复核 PyTorch 扩展的架构选择方式，移除不适用假设，并在 MXMACA 环境验证构建。
- 证据：

    os.environ["TORCH_CUDA_ARCH_LIST"] = "6.0;6.1;6.2;7.0;7.5;8.0;8.6"

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-BUILD-001` — 检测 TORCH\_CUDA\_ARCH\_LIST 覆盖

- 位置：`setup.py`，第 139–139 行
- 分类：`build`
- 说明：项目显式覆盖 TORCH\_CUDA\_ARCH\_LIST，构建产物可能绑定 NVIDIA 架构列表。
- 建议：请复核 PyTorch 扩展的架构选择方式，移除不适用假设，并在 MXMACA 环境验证构建。
- 证据：

    os.environ["TORCH_CUDA_ARCH_LIST"] = "6.0;6.1;6.2;7.0;7.5;8.0"

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-BUILD-001` — 检测 TORCH\_CUDA\_ARCH\_LIST 覆盖

- 位置：`setup.py`，第 141–141 行
- 分类：`build`
- 说明：项目显式覆盖 TORCH\_CUDA\_ARCH\_LIST，构建产物可能绑定 NVIDIA 架构列表。
- 建议：请复核 PyTorch 扩展的架构选择方式，移除不适用假设，并在 MXMACA 环境验证构建。
- 证据：

    os.environ["TORCH_CUDA_ARCH_LIST"] = "6.0;6.1;6.2;7.0;7.5"

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-ARCH-001` — 检测 CUDA gencode 参数

- 位置：`setup.py`，第 545–545 行
- 分类：`architecture`
- 说明：构建参数显式生成 NVIDIA compute/sm 目标，可能固化了设备架构假设。
- 建议：请复核目标架构参数，依据 MXMACA 工具链要求调整，并在沐曦设备验证生成物。
- 证据：

    "-gencode=arch=compute_90,code=sm_90",

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 545–545 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    "-gencode=arch=compute_90,code=sm_90",

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-001` — 检测 CUDA gencode 参数

- 位置：`setup.py`，第 546–546 行
- 分类：`architecture`
- 说明：构建参数显式生成 NVIDIA compute/sm 目标，可能固化了设备架构假设。
- 建议：请复核目标架构参数，依据 MXMACA 工具链要求调整，并在沐曦设备验证生成物。
- 证据：

    "-gencode=arch=compute_100,code=sm_100",

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 546–546 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    "-gencode=arch=compute_100,code=sm_100",

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-001` — 检测 CUDA gencode 参数

- 位置：`setup.py`，第 547–547 行
- 分类：`architecture`
- 说明：构建参数显式生成 NVIDIA compute/sm 目标，可能固化了设备架构假设。
- 建议：请复核目标架构参数，依据 MXMACA 工具链要求调整，并在沐曦设备验证生成物。
- 证据：

    "-gencode=arch=compute_120,code=compute_120",

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 547–547 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    "-gencode=arch=compute_120,code=compute_120",

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-001` — 检测 CUDA gencode 参数

- 位置：`setup.py`，第 550–550 行
- 分类：`architecture`
- 说明：构建参数显式生成 NVIDIA compute/sm 目标，可能固化了设备架构假设。
- 建议：请复核目标架构参数，依据 MXMACA 工具链要求调整，并在沐曦设备验证生成物。
- 证据：

    arch_flags = ["-gencode=arch=compute_90,code=compute_90"]

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 550–550 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    arch_flags = ["-gencode=arch=compute_90,code=compute_90"]

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


## 提示

### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`apex/contrib/csrc/group_norm_v2/gn.hpp`，第 2–3 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda.cu`，第 3–3 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_host_template.cuh`，第 5–5 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`apex/contrib/csrc/group_norm_v2/gn_utils.hpp`，第 2–3 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-002` — 识别 cuda\.h 驱动头文件

- 位置：`apex/contrib/csrc/groupbn/batch_norm.cu`，第 4–4 行
- 分类：`header`
- 说明：源码直接包含 CUDA Driver 头文件，需要核对所用 Driver API 的目标映射。
- 建议：请复核 Driver API 调用范围，并结合 cu\-bridge 文档在沐曦环境验证编译与行为。
- 证据：

    #include &lt;cuda.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-002` — 识别 cuda\.h 驱动头文件

- 位置：`apex/contrib/csrc/groupbn/batch_norm_add_relu.cu`，第 4–4 行
- 分类：`header`
- 说明：源码直接包含 CUDA Driver 头文件，需要核对所用 Driver API 的目标映射。
- 建议：请复核 Driver API 调用范围，并结合 cu\-bridge 文档在沐曦环境验证编译与行为。
- 证据：

    #include &lt;cuda.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-002` — 识别 cuda\.h 驱动头文件

- 位置：`apex/contrib/csrc/groupbn/ipc.cu`，第 3–3 行
- 分类：`header`
- 说明：源码直接包含 CUDA Driver 头文件，需要核对所用 Driver API 的目标映射。
- 建议：请复核 Driver API 调用范围，并结合 cu\-bridge 文档在沐曦环境验证编译与行为。
- 证据：

    #include &lt;cuda.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-002` — 识别 cuda\.h 驱动头文件

- 位置：`apex/contrib/csrc/optimizers/fused_adam_cuda_kernel.cu`，第 1–1 行
- 分类：`header`
- 说明：源码直接包含 CUDA Driver 头文件，需要核对所用 Driver API 的目标映射。
- 建议：请复核 Driver API 调用范围，并结合 cu\-bridge 文档在沐曦环境验证编译与行为。
- 证据：

    #include &lt;cuda.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`apex/contrib/csrc/optimizers/fused_adam_cuda_kernel.cu`，第 2–2 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-002` — 识别 cuda\.h 驱动头文件

- 位置：`apex/contrib/csrc/transducer/transducer_joint_kernel.cu`，第 2–2 行
- 分类：`header`
- 说明：源码直接包含 CUDA Driver 头文件，需要核对所用 Driver API 的目标映射。
- 建议：请复核 Driver API 调用范围，并结合 cu\-bridge 文档在沐曦环境验证编译与行为。
- 证据：

    #include &lt;cuda.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`apex/contrib/csrc/transducer/transducer_joint_kernel.cu`，第 3–3 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-002` — 识别 cuda\.h 驱动头文件

- 位置：`apex/contrib/csrc/transducer/transducer_loss_kernel.cu`，第 4–4 行
- 分类：`header`
- 说明：源码直接包含 CUDA Driver 头文件，需要核对所用 Driver API 的目标映射。
- 建议：请复核 Driver API 调用范围，并结合 cu\-bridge 文档在沐曦环境验证编译与行为。
- 证据：

    #include &lt;cuda.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`apex/contrib/csrc/transducer/transducer_loss_kernel.cu`，第 5–5 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/fused_dense_cuda.cu`，第 11–11 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-002` — 识别 cuda\.h 驱动头文件

- 位置：`csrc/layer_norm_cuda_kernel.cu`，第 1–1 行
- 分类：`header`
- 说明：源码直接包含 CUDA Driver 头文件，需要核对所用 Driver API 的目标映射。
- 建议：请复核 Driver API 调用范围，并结合 cu\-bridge 文档在沐曦环境验证编译与行为。
- 证据：

    #include &lt;cuda.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/layer_norm_cuda_kernel.cu`，第 2–2 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/megatron/fused_rotary_positional_embedding.h`，第 22–22 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/megatron/fused_weight_gradient_dense_16bit_prec_cuda.cu`，第 12–12 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/megatron/fused_weight_gradient_dense_cuda.cu`，第 12–12 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-002` — 识别 cuda\.h 驱动头文件

- 位置：`csrc/megatron/generic_scaled_masked_softmax_cuda.cu`，第 19–19 行
- 分类：`header`
- 说明：源码直接包含 CUDA Driver 头文件，需要核对所用 Driver API 的目标映射。
- 建议：请复核 Driver API 调用范围，并结合 cu\-bridge 文档在沐曦环境验证编译与行为。
- 证据：

    #include &lt;cuda.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/megatron/generic_scaled_masked_softmax_cuda.cu`，第 22–22 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-002` — 识别 cuda\.h 驱动头文件

- 位置：`csrc/megatron/scaled_masked_softmax_cuda.cu`，第 19–19 行
- 分类：`header`
- 说明：源码直接包含 CUDA Driver 头文件，需要核对所用 Driver API 的目标映射。
- 建议：请复核 Driver API 调用范围，并结合 cu\-bridge 文档在沐曦环境验证编译与行为。
- 证据：

    #include &lt;cuda.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/megatron/scaled_masked_softmax_cuda.cu`，第 22–22 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-002` — 识别 cuda\.h 驱动头文件

- 位置：`csrc/megatron/scaled_softmax_cuda.cu`，第 19–19 行
- 分类：`header`
- 说明：源码直接包含 CUDA Driver 头文件，需要核对所用 Driver API 的目标映射。
- 建议：请复核 Driver API 调用范围，并结合 cu\-bridge 文档在沐曦环境验证编译与行为。
- 证据：

    #include &lt;cuda.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/megatron/scaled_softmax_cuda.cu`，第 22–22 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-002` — 识别 cuda\.h 驱动头文件

- 位置：`csrc/megatron/scaled_upper_triang_masked_softmax_cuda.cu`，第 19–19 行
- 分类：`header`
- 说明：源码直接包含 CUDA Driver 头文件，需要核对所用 Driver API 的目标映射。
- 建议：请复核 Driver API 调用范围，并结合 cu\-bridge 文档在沐曦环境验证编译与行为。
- 证据：

    #include &lt;cuda.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/megatron/scaled_upper_triang_masked_softmax_cuda.cu`，第 22–22 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/mlp_cuda.cu`，第 11–11 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/multi_tensor_sgd_kernel.cu`，第 6–6 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-002` — 识别 cuda\.h 驱动头文件

- 位置：`csrc/welford.cu`，第 4–4 行
- 分类：`header`
- 说明：源码直接包含 CUDA Driver 头文件，需要核对所用 Driver API 的目标映射。
- 建议：请复核 Driver API 调用范围，并结合 cu\-bridge 文档在沐曦环境验证编译与行为。
- 证据：

    #include &lt;cuda.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/welford.cu`，第 5–5 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 178–178 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 197–197 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 218–218 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 249–249 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 260–260 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 271–271 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 281–281 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 292–292 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 313–313 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 334–334 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 355–355 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 376–376 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 397–397 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 430–430 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 454–454 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 484–484 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 503–503 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 523–523 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 553–553 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 582–582 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 601–601 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 620–620 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 648–648 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 681–681 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 697–697 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 726–726 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 742–742 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 758–758 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 784–784 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 808–808 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-002` — 识别 PyTorch JIT 原生扩展

- 位置：`setup.py`，第 821–821 行
- 分类：`pytorch\-extension`
- 说明：项目使用 torch\.utils\.cpp\_extension\.load 在运行时编译扩展，执行环境必须具备完整工具链。
- 建议：请复核 JIT 源码、缓存、编译参数与依赖，并在 MXMACA 环境验证首次和重复加载。
- 证据：

    _nccl_version_getter = load(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 831–831 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-002` — 识别 PyTorch JIT 原生扩展

- 位置：`tests/distributed/synced_batchnorm/single_gpu_unit_test.py`，第 12–12 行
- 分类：`pytorch\-extension`
- 说明：项目使用 torch\.utils\.cpp\_extension\.load 在运行时编译扩展，执行环境必须具备完整工具链。
- 建议：请复核 JIT 源码、缓存、编译参数与依赖，并在 MXMACA 环境验证首次和重复加载。
- 证据：

    syncbn = load(name="syncbn", sources=["../../csrc/syncbn.cpp", "../../csrc/welford.cu"])

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


## 迁移清单

- [ ] `MXR-TOOLCHAIN-001` 检测直接 nvcc 工具调用：请复核调用点，按 cu\-bridge 当前版本配置对应工具链，并在沐曦环境验证构建。
  - 涉及文件：`setup.py`
- [ ] `MXR-KERNEL-001` 检测 \_\_launch\_bounds\_\_ 调优假设：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
  - 涉及文件：`apex/contrib/csrc/group_norm/group_norm_nhwc_bwd_one_pass_kernel.cuh`、`apex/contrib/csrc/group_norm/group_norm_nhwc_fwd_one_pass_kernel.cuh`、`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`、`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`、`apex/contrib/csrc/layer_norm/ln_bwd_kernels.cuh`、`apex/contrib/csrc/layer_norm/ln_fwd_kernels.cuh`、`apex/contrib/csrc/peer_memory/peer_memory_cuda.cu`
- [ ] `MXR-INTRINSIC-001` 检测 CUDA warp 同步内建函数：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
  - 涉及文件：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`、`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`、`apex/contrib/csrc/layer_norm/ln_utils.cuh`、`apex/contrib/csrc/transducer/transducer_joint_kernel.cu`、`csrc/megatron/generic_scaled_masked_softmax.h`、`csrc/megatron/scaled_masked_softmax.h`、`csrc/megatron/scaled_upper_triang_masked_softmax.h`、`csrc/type_shim.h`、`csrc/welford.cu`
- [ ] `MXR-COMM-001` 检测 NCCL 环境变量覆盖：请复核通信后端、环境变量和拓扑配置，并在沐曦多卡环境进行针对性验证。
  - 涉及文件：`apex/contrib/nccl_allocator/nccl_allocator.py`
- [ ] `MXR-TOOL-001` 检测直接 nvidia\-smi 调用：请复核诊断逻辑并提供可替换工具入口，再在沐曦服务器验证设备信息采集。
  - 涉及文件：`apex/contrib/sparsity/permutation_search_kernels/permutation_utilities.py`
- [ ] `MXR-BUILD-001` 检测 TORCH\_CUDA\_ARCH\_LIST 覆盖：请复核 PyTorch 扩展的架构选择方式，移除不适用假设，并在 MXMACA 环境验证构建。
  - 涉及文件：`setup.py`
- [ ] `MXR-ARCH-001` 检测 CUDA gencode 参数：请复核目标架构参数，依据 MXMACA 工具链要求调整，并在沐曦设备验证生成物。
  - 涉及文件：`setup.py`
- [ ] `MXR-ARCH-002` 检测硬编码 sm 或 compute 架构：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
  - 涉及文件：`setup.py`

## 分析警告

无。

## 说明

静态扫描不能替代真实沐曦 GPU 上的构建、功能和性能验证，也不能作为项目安全性或完整兼容性的证明。
