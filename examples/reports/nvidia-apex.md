# MXReady 适配体检报告：apex

## 扫描元数据

| 字段 | 值 |
| --- | --- |
| 仓库 | https://github\.com/NVIDIA/apex |
| 提交 | `575968bc1f9127ccd61003a681472a83af4ff1a1` |
| MXReady 版本 | 0\.3\.0 |
| 规则集版本 | 4 |
| 规则集摘要 | sha256:badf12ad29ce6f7cff9e6f07b4df4034822fbe9773571cad6517d9c65325c531 |
| 扩展规则版本 | 无 |
| 分析配置 | \{'max\_findings': 10000, 'rule\_timeout\_seconds': 30, 'index\_max\_files': 10000, 'index\_max\_file\_bytes': 1048576, 'prefilter': 'on'\} |
| 扫描时间 | 2026\-10\-31T02:27:09\.616246\+00:00 |
| 静态状态 | `blocked` |
| 硬件验证状态 | `not-run` |

## 结果摘要

| 阻塞项 | 警告 | 提示 | 总计 |
| ---: | ---: | ---: | ---: |
| 12 | 65 | 140 | 217 |

## 阻塞项

### `MXR-PTX-001` — 检测内联 PTX 汇编

- 位置：`apex/contrib/csrc/group_norm/group_norm_nhwc.h`，第 40–44 行
- 分类：`ptx`
- 说明：内联汇编块嵌入的是 NVIDIA 虚拟 ISA（PTX）指令，MXMACA 后端不执行 PTX；这类代码可能固化 NVIDIA 指令语义。
- 建议：请逐处复核 asm 块对应的硬件能力，改用目标平台支持的内建函数或等价 C\+\+ 实现，并在沐曦环境验证功能与性能。
- 证据：

    asm volatile("red.release.gpu.global.add.s32 [%0], %1;" ::"l"(barrier), "r"(step));

- 参考：
  - [NVIDIA Inline PTX Assembly](https://docs.nvidia.com/cuda/inline-ptx-assembly/index.html)
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-PTX-001` — 检测内联 PTX 汇编

- 位置：`apex/contrib/csrc/group_norm/group_norm_nhwc_bwd_one_pass_kernel.cuh`，第 401–412 行
- 分类：`ptx`
- 说明：内联汇编块嵌入的是 NVIDIA 虚拟 ISA（PTX）指令，MXMACA 后端不执行 PTX；这类代码可能固化 NVIDIA 指令语义。
- 建议：请逐处复核 asm 块对应的硬件能力，改用目标平台支持的内建函数或等价 C\+\+ 实现，并在沐曦环境验证功能与性能。
- 证据：

    asm volatile("red.release.gpu.global.add.s32 [%0], 1;" ::"l"(barrier));

- 参考：
  - [NVIDIA Inline PTX Assembly](https://docs.nvidia.com/cuda/inline-ptx-assembly/index.html)
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-PTX-001` — 检测内联 PTX 汇编

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 86–129 行
- 分类：`ptx`
- 说明：内联汇编块嵌入的是 NVIDIA 虚拟 ISA（PTX）指令，MXMACA 后端不执行 PTX；这类代码可能固化 NVIDIA 指令语义。
- 建议：请逐处复核 asm 块对应的硬件能力，改用目标平台支持的内建函数或等价 C\+\+ 实现，并在沐曦环境验证功能与性能。
- 证据：

    asm volatile("atom.add.release.gpu.u32 %0,[%1],%2;"

- 参考：
  - [NVIDIA Inline PTX Assembly](https://docs.nvidia.com/cuda/inline-ptx-assembly/index.html)
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-WARP-001` — 检测硬编码 32 线程束假设

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 296–1187 行
- 分类：`warp`
- 说明：代码按 32 线程一组计算 lane 或定义线程束宽度常量；MXMACA 的线程束（wave）宽度为 64，这类算术可能编译通过但结果错位。
- 建议：请复核 lane 计算与掩码宽度，改用运行时查询的线程束宽度，并在沐曦环境用最小用例比对结果。
- 证据：

    if (threadIdx.x % 32 == 0) {

- 参考：
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-PTX-001` — 检测内联 PTX 汇编

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 62–669 行
- 分类：`ptx`
- 说明：内联汇编块嵌入的是 NVIDIA 虚拟 ISA（PTX）指令，MXMACA 后端不执行 PTX；这类代码可能固化 NVIDIA 指令语义。
- 建议：请逐处复核 asm 块对应的硬件能力，改用目标平台支持的内建函数或等价 C\+\+ 实现，并在沐曦环境验证功能与性能。
- 证据：

    asm volatile("cvt.rn.f16.f32 %0, %1;" : "=h"(lo) : "f"(src[2 * i + 0]));

- 参考：
  - [NVIDIA Inline PTX Assembly](https://docs.nvidia.com/cuda/inline-ptx-assembly/index.html)
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-WARP-001` — 检测硬编码 32 线程束假设

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 1245–2351 行
- 分类：`warp`
- 说明：代码按 32 线程一组计算 lane 或定义线程束宽度常量；MXMACA 的线程束（wave）宽度为 64，这类算术可能编译通过但结果错位。
- 建议：请复核 lane 计算与掩码宽度，改用运行时查询的线程束宽度，并在沐曦环境用最小用例比对结果。
- 证据：

    int lane_id = threadIdx.x &amp; 31;

- 参考：
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-PTX-001` — 检测内联 PTX 汇编

- 位置：`apex/contrib/csrc/layer_norm/ln_utils.cuh`，第 316–318 行
- 分类：`ptx`
- 说明：内联汇编块嵌入的是 NVIDIA 虚拟 ISA（PTX）指令，MXMACA 后端不执行 PTX；这类代码可能固化 NVIDIA 指令语义。
- 建议：请逐处复核 asm 块对应的硬件能力，改用目标平台支持的内建函数或等价 C\+\+ 实现，并在沐曦环境验证功能与性能。
- 证据：

    asm volatile("red.release.gpu.global.add.s32 [%0], %1;" ::"l"(barrier), "r"(step));

- 参考：
  - [NVIDIA Inline PTX Assembly](https://docs.nvidia.com/cuda/inline-ptx-assembly/index.html)
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-PTX-001` — 检测内联 PTX 汇编

- 位置：`apex/contrib/csrc/peer_memory/peer_memory_cuda.cu`，第 204–248 行
- 分类：`ptx`
- 说明：内联汇编块嵌入的是 NVIDIA 虚拟 ISA（PTX）指令，MXMACA 后端不执行 PTX；这类代码可能固化 NVIDIA 指令语义。
- 建议：请逐处复核 asm 块对应的硬件能力，改用目标平台支持的内建函数或等价 C\+\+ 实现，并在沐曦环境验证功能与性能。
- 证据：

    asm volatile("ld.volatile.global.v4.u32 {%0,%1,%2,%3}, [%4];"

- 参考：
  - [NVIDIA Inline PTX Assembly](https://docs.nvidia.com/cuda/inline-ptx-assembly/index.html)
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-PTX-001` — 检测内联 PTX 汇编

- 位置：`apex/contrib/csrc/transducer/philox.cuh`，第 70–87 行
- 分类：`ptx`
- 说明：内联汇编块嵌入的是 NVIDIA 虚拟 ISA（PTX）指令，MXMACA 后端不执行 PTX；这类代码可能固化 NVIDIA 指令语义。
- 建议：请逐处复核 asm 块对应的硬件能力，改用目标平台支持的内建函数或等价 C\+\+ 实现，并在沐曦环境验证功能与性能。
- 证据：

    asm("add.cc.u32      %0, %4, %8;\n\t"

- 参考：
  - [NVIDIA Inline PTX Assembly](https://docs.nvidia.com/cuda/inline-ptx-assembly/index.html)
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-WARP-001` — 检测硬编码 32 线程束假设

- 位置：`apex/contrib/csrc/xentropy/xentropy_kernel.cu`，第 169–215 行
- 分类：`warp`
- 说明：代码按 32 线程一组计算 lane 或定义线程束宽度常量；MXMACA 的线程束（wave）宽度为 64，这类算术可能编译通过但结果错位。
- 建议：请复核 lane 计算与掩码宽度，改用运行时查询的线程束宽度，并在沐曦环境用最小用例比对结果。
- 证据：

    int lane = threadIdx.x % 32;

- 参考：
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-WARP-001` — 检测硬编码 32 线程束假设

- 位置：`csrc/welford.cu`，第 36–37 行
- 分类：`warp`
- 说明：代码按 32 线程一组计算 lane 或定义线程束宽度常量；MXMACA 的线程束（wave）宽度为 64，这类算术可能编译通过但结果错位。
- 建议：请复核 lane 计算与掩码宽度，改用运行时查询的线程束宽度，并在沐曦环境用最小用例比对结果。
- 证据：

    #define WARP_SIZE 32

- 参考：
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-TOOLCHAIN-001` — 检测直接 nvcc 工具调用

- 位置：`setup.py`，第 65–65 行
- 分类：`toolchain`
- 说明：项目直接调用或固定指定 nvcc，迁移到 MXMACA/cu\-bridge 时工具入口与参数需要复核。
- 建议：请复核调用点，按 cu\-bridge 当前版本配置对应工具链，并在沐曦环境验证构建。
- 证据：

    raw_output = subprocess.check_output([cuda_dir + "/bin/nvcc", "-V"], universal_newlines=True)

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


## 警告

### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/bottleneck/bottleneck.py`，第 8–8 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex import check_cudnn_version_and_warn

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-002` — 检测 torch\.distributed NCCL 通信后端

- 位置：`apex/contrib/bottleneck/halo_exchangers.py`，第 102–102 行
- 分类：`communication`
- 说明：项目将分布式通信后端指定为 NCCL，迁移到沐曦环境需要确认通信库与后端的等价映射。
- 建议：请复核通信后端选择、初始化参数与多卡拓扑，并在沐曦多卡环境验证集合通信行为。
- 证据：

    # Create another global nccl communicator in addition to the one created by torch.distributed.init_process_group("nccl")

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/clip_grad/clip_grad.py`，第 10–10 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.multi_tensor_apply import multi_tensor_applier

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/conv_bias_relu/conv_bias_relu.py`，第 4–4 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex import check_cudnn_version_and_warn

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-LIBRARY-001` — 识别 cuBLAS / cuDNN / cuFFT / cuSPARSE / cuSOLVER 头文件

- 位置：`apex/contrib/csrc/bottleneck/bottleneck.cpp`，第 3–3 行
- 分类：`library`
- 说明：源码直接包含 NVIDIA 数学库头文件，目标环境需要由兼容层或等价库提供相应 API 映射。
- 建议：请复核实际使用的库 API 与链接配置，并结合 cu\-bridge 当前版本在沐曦环境验证编译与数值行为。
- 证据：

    #include &lt;cudnn_frontend.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-LIBRARY-001` — 识别 cuBLAS / cuDNN / cuFFT / cuSPARSE / cuSOLVER 头文件

- 位置：`apex/contrib/csrc/conv_bias_relu/conv_bias_relu.cpp`，第 3–3 行
- 分类：`library`
- 说明：源码直接包含 NVIDIA 数学库头文件，目标环境需要由兼容层或等价库提供相应 API 映射。
- 建议：请复核实际使用的库 API 与链接配置，并结合 cu\-bridge 当前版本在沐曦环境验证编译与数值行为。
- 证据：

    #include &lt;cudnn_frontend.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-LIBRARY-001` — 识别 cuBLAS / cuDNN / cuFFT / cuSPARSE / cuSOLVER 头文件

- 位置：`apex/contrib/csrc/cudnn_gbn/norm_sample.cpp`，第 26–30 行
- 分类：`library`
- 说明：源码直接包含 NVIDIA 数学库头文件，目标环境需要由兼容层或等价库提供相应 API 映射。
- 建议：请复核实际使用的库 API 与链接配置，并结合 cu\-bridge 当前版本在沐曦环境验证编译与数值行为。
- 证据：

    #include &lt;cudnn_frontend.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-LIBRARY-001` — 识别 cuBLAS / cuDNN / cuFFT / cuSPARSE / cuSOLVER 头文件

- 位置：`apex/contrib/csrc/cudnn_gbn/norm_sample.h`，第 29–30 行
- 分类：`library`
- 说明：源码直接包含 NVIDIA 数学库头文件，目标环境需要由兼容层或等价库提供相应 API 映射。
- 建议：请复核实际使用的库 API 与链接配置，并结合 cu\-bridge 当前版本在沐曦环境验证编译与数值行为。
- 证据：

    #include &lt;cudnn.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


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

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 195–596 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(BLOCK_DIM_X, BLOCKS_PER_SM) void gn_cuda_kernel(

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`，第 292–1202 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    frag_sum_per_channel[i].x += __shfl_xor_sync(FINAL_MASK, frag_sum_per_channel[i].x, mask, 32);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-LIBRARY-001` — 识别 cuBLAS / cuDNN / cuFFT / cuSPARSE / cuSOLVER 头文件

- 位置：`apex/contrib/csrc/groupbn/batch_norm.h`，第 28–29 行
- 分类：`library`
- 说明：源码直接包含 NVIDIA 数学库头文件，目标环境需要由兼容层或等价库提供相应 API 映射。
- 建议：请复核实际使用的库 API 与链接配置，并结合 cu\-bridge 当前版本在沐曦环境验证编译与数值行为。
- 证据：

    #include &lt;cudnn.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-LIBRARY-001` — 识别 cuBLAS / cuDNN / cuFFT / cuSPARSE / cuSOLVER 头文件

- 位置：`apex/contrib/csrc/groupbn/batch_norm_add_relu.h`，第 28–29 行
- 分类：`library`
- 说明：源码直接包含 NVIDIA 数学库头文件，目标环境需要由兼容层或等价库提供相应 API 映射。
- 建议：请复核实际使用的库 API 与链接配置，并结合 cu\-bridge 当前版本在沐曦环境验证编译与数值行为。
- 证据：

    #include &lt;cudnn.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 381–2366 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    x[i] += __shfl_sync(0xffffffffU, x[i], THREADS_PER_PIXEL + lane_id);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`，第 695–2187 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(THREADS_PER_CTA) void nhwc_batch_norm_fwd_inference(

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`apex/contrib/csrc/layer_norm/ln_bwd_kernels.cuh`，第 8–202 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

    __global__ __launch_bounds__(Ktraits::THREADS_PER_CTA) void ln_bwd_kernel(layer_norm::BwdParams params) {

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

- 位置：`apex/contrib/csrc/layer_norm/ln_utils.cuh`，第 82–532 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    return __shfl_xor_sync(uint32_t(-1), x, idx);

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


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/layer_norm/layer_norm.py`，第 5–5 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex._autocast_utils import _cast_if_autocast_enabled

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/nccl_allocator/nccl_allocator.py`，第 18–18 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex import deprecated_warning

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-001` — 检测 NCCL 环境变量覆盖

- 位置：`apex/contrib/nccl_allocator/nccl_allocator.py`，第 44–45 行
- 分类：`communication`
- 说明：项目覆盖了 NVIDIA NCCL 环境变量，多卡通信配置包含平台特定假设。
- 建议：请复核通信后端、环境变量和拓扑配置，并在沐曦多卡环境进行针对性验证。
- 证据：

    os.environ["NCCL_NVLS_ENABLE"] = "1"

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/openfold_triton/__init__.py`，第 14–25 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.openfold_triton._layer_norm_backward_kernels import (

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/openfold_triton/layer_norm.py`，第 9–17 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.openfold_triton._layer_norm_backward_kernels import (

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/openfold_triton/mha.py`，第 10–10 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.openfold_triton._mha_kernel import (

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/optimizers/distributed_fused_adam.py`，第 25–32 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib import nccl_allocator

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/optimizers/distributed_fused_lamb.py`，第 9–9 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.multi_tensor_apply import multi_tensor_applier

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/optimizers/fp16_optimizer.py`，第 3–3 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.multi_tensor_apply import multi_tensor_applier

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/optimizers/fused_adam.py`，第 6–6 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.multi_tensor_apply import multi_tensor_applier

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/optimizers/fused_lamb.py`，第 6–6 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.multi_tensor_apply import multi_tensor_applier

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/optimizers/fused_sgd.py`，第 6–6 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.multi_tensor_apply import multi_tensor_applier

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-TOOL-001` — 检测直接 nvidia\-smi 调用

- 位置：`apex/contrib/sparsity/permutation_search_kernels/permutation_utilities.py`，第 32–32 行
- 分类：`tool`
- 说明：项目直接调用 nvidia\-smi，设备发现或诊断流程依赖 NVIDIA 专用工具。
- 建议：请复核诊断逻辑并提供可替换工具入口，再在沐曦服务器验证设备信息采集。
- 证据：

    gpus_found = str(subprocess.check_output(["nvidia-smi", "-L"])).count("UUID")

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/torchsched/backend.py`，第 19–21 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.torchsched import config

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/torchsched/inductor/__init__.py`，第 3–3 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.torchsched.inductor.graph import patch_graph_lowering

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/torchsched/inductor/event.py`，第 20–21 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    import apex.contrib.torchsched.config as torchsched_config

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/torchsched/inductor/graph.py`，第 23–25 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.torchsched import config as torchsched_config

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/torchsched/inductor/scheduler.py`，第 26–32 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.torchsched import config

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/torchsched/inductor/wrapper.py`，第 27–39 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.torchsched import config

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/torchsched/passes/__init__.py`，第 5–5 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.torchsched.passes.pre_grad_passes import pre_grad_custom_pass

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/torchsched/passes/pre_grad_passes.py`，第 15–15 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.torchsched import config

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/distributed_testing/__init__.py`，第 3–3 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.distributed_testing.distributed_test_base import (

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/distributed_testing/distributed_test_base.py`，第 11–11 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.distributed_testing._ucc_util import HAS_UCC

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/fused_dense/fused_dense.py`，第 5–5 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex._autocast_utils import _cast_if_autocast_enabled

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/mlp/mlp.py`，第 8–8 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex._autocast_utils import _cast_if_autocast_enabled

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/normalization/fused_layer_norm.py`，第 10–10 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex._autocast_utils import _cast_if_autocast_enabled

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/optimizers/fused_adagrad.py`，第 3–3 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.multi_tensor_apply import multi_tensor_applier

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/optimizers/fused_adam.py`，第 3–3 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.multi_tensor_apply import multi_tensor_applier

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/optimizers/fused_lamb.py`，第 3–3 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.multi_tensor_apply import multi_tensor_applier

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/optimizers/fused_mixed_precision_lamb.py`，第 8–8 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.multi_tensor_apply import multi_tensor_applier

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/optimizers/fused_novograd.py`，第 3–3 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.multi_tensor_apply import multi_tensor_applier

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/optimizers/fused_sgd.py`，第 4–4 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.multi_tensor_apply import multi_tensor_applier

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-LIBRARY-001` — 识别 cuBLAS / cuDNN / cuFFT / cuSPARSE / cuSOLVER 头文件

- 位置：`csrc/fused_dense_cuda.cu`，第 10–15 行
- 分类：`library`
- 说明：源码直接包含 NVIDIA 数学库头文件，目标环境需要由兼容层或等价库提供相应 API 映射。
- 建议：请复核实际使用的库 API 与链接配置，并结合 cu\-bridge 当前版本在沐曦环境验证编译与数值行为。
- 证据：

    #include &lt;cublas_v2.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-LIBRARY-001` — 识别 cuBLAS / cuDNN / cuFFT / cuSPARSE / cuSOLVER 头文件

- 位置：`csrc/megatron/fused_weight_gradient_dense_16bit_prec_cuda.cu`，第 11–11 行
- 分类：`library`
- 说明：源码直接包含 NVIDIA 数学库头文件，目标环境需要由兼容层或等价库提供相应 API 映射。
- 建议：请复核实际使用的库 API 与链接配置，并结合 cu\-bridge 当前版本在沐曦环境验证编译与数值行为。
- 证据：

    #include &lt;cublas_v2.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-LIBRARY-001` — 识别 cuBLAS / cuDNN / cuFFT / cuSPARSE / cuSOLVER 头文件

- 位置：`csrc/megatron/fused_weight_gradient_dense_cuda.cu`，第 11–11 行
- 分类：`library`
- 说明：源码直接包含 NVIDIA 数学库头文件，目标环境需要由兼容层或等价库提供相应 API 映射。
- 建议：请复核实际使用的库 API 与链接配置，并结合 cu\-bridge 当前版本在沐曦环境验证编译与数值行为。
- 证据：

    #include &lt;cublas_v2.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


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


### `MXR-LIBRARY-001` — 识别 cuBLAS / cuDNN / cuFFT / cuSPARSE / cuSOLVER 头文件

- 位置：`csrc/mlp_cuda.cu`，第 10–15 行
- 分类：`library`
- 说明：源码直接包含 NVIDIA 数学库头文件，目标环境需要由兼容层或等价库提供相应 API 映射。
- 建议：请复核实际使用的库 API 与链接配置，并结合 cu\-bridge 当前版本在沐曦环境验证编译与数值行为。
- 证据：

    #include &lt;cublas_v2.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/type_shim.h`，第 291–333 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    for (int i = 16; i &gt;= lanes; i &gt;&gt;= 1) final = final + __shfl_down_sync(0xffffffff, final, i);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/welford.cu`，第 42–112 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

    for (int i = WARP_SIZE / 2; i &gt; 0; i &gt;&gt;= 1) val = val + __shfl_down_sync(0xffffffff, val, i);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-BUILD-001` — 检测 TORCH\_CUDA\_ARCH\_LIST 覆盖

- 位置：`setup.py`，第 130–140 行
- 分类：`build`
- 说明：项目显式覆盖 TORCH\_CUDA\_ARCH\_LIST，构建产物可能绑定 NVIDIA 架构列表。
- 建议：请复核 PyTorch 扩展的架构选择方式，移除不适用假设，并在 MXMACA 环境验证构建。
- 证据：

    os.environ["TORCH_CUDA_ARCH_LIST"] = "7.5;8.0;8.6;9.0;10.0;11.0;12.0"

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-ARCH-001` — 检测 CUDA gencode 参数

- 位置：`setup.py`，第 542–547 行
- 分类：`architecture`
- 说明：构建参数显式生成 NVIDIA compute/sm 目标，可能固化了设备架构假设。
- 建议：请复核目标架构参数，依据 MXMACA 工具链要求调整，并在沐曦设备验证生成物。
- 证据：

    "-gencode=arch=compute_90,code=sm_90",

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-ARCH-002` — 检测硬编码 sm 或 compute 架构

- 位置：`setup.py`，第 542–547 行
- 分类：`architecture`
- 说明：项目硬编码了 NVIDIA sm/compute 架构编号，需要确认目标编译器如何处理该配置。
- 建议：请复核架构列表是否可配置，并在 MXMACA 工具链上验证编译参数和运行结果。
- 证据：

    "-gencode=arch=compute_90,code=sm_90",

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


## 提示

### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/examples/gpu_direct_storage/benchmark_load.py`，第 3–3 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于示例路径：示例代码一般不随交付构建，已从 warning 降为提示。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    import apex.contrib.gpu_direct_storage as gds

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/examples/gpu_direct_storage/benchmark_save.py`，第 4–4 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于示例路径：示例代码一般不随交付构建，已从 warning 降为提示。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    import apex.contrib.gpu_direct_storage as gds

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/examples/gpu_direct_storage/example_load.py`，第 1–1 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于示例路径：示例代码一般不随交付构建，已从 warning 降为提示。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    import apex.contrib.gpu_direct_storage as gds

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/examples/gpu_direct_storage/example_save.py`，第 1–1 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于示例路径：示例代码一般不随交付构建，已从 warning 降为提示。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    import apex.contrib.gpu_direct_storage as gds

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/examples/nccl_allocator/allreduce.py`，第 6–6 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于示例路径：示例代码一般不随交付构建，已从 warning 降为提示。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib import nccl_allocator

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-002` — 检测 torch\.distributed NCCL 通信后端

- 位置：`apex/contrib/examples/nccl_allocator/allreduce.py`，第 17–17 行
- 分类：`communication`
- 说明：项目将分布式通信后端指定为 NCCL，迁移到沐曦环境需要确认通信库与后端的等价映射。（该命中位于示例路径：示例代码一般不随交付构建，已从 warning 降为提示。）
- 建议：请复核通信后端选择、初始化参数与多卡拓扑，并在沐曦多卡环境验证集合通信行为。
- 证据：

    dist.init_process_group(backend="nccl")

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/examples/nccl_allocator/cache.py`，第 4–4 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于示例路径：示例代码一般不随交付构建，已从 warning 降为提示。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib import nccl_allocator

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/examples/nccl_allocator/change_cuda_allocator.py`，第 3–3 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于示例路径：示例代码一般不随交付构建，已从 warning 降为提示。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib import nccl_allocator

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/examples/nccl_allocator/toy_ddp.py`，第 8–8 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于示例路径：示例代码一般不随交付构建，已从 warning 降为提示。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib import nccl_allocator

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-002` — 检测 torch\.distributed NCCL 通信后端

- 位置：`apex/contrib/examples/nccl_allocator/toy_ddp.py`，第 30–30 行
- 分类：`communication`
- 说明：项目将分布式通信后端指定为 NCCL，迁移到沐曦环境需要确认通信库与后端的等价映射。（该命中位于示例路径：示例代码一般不随交付构建，已从 warning 降为提示。）
- 建议：请复核通信后端选择、初始化参数与多卡拓扑，并在沐曦多卡环境验证集合通信行为。
- 证据：

    dist.init_process_group(backend="nccl")

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/sparsity/test/checkpointing_test_part1.py`，第 5–6 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.sparsity import ASP

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/sparsity/test/checkpointing_test_part2.py`，第 5–6 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.sparsity import ASP

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/sparsity/test/checkpointing_test_reference.py`，第 5–6 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.sparsity import ASP

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/sparsity/test/test_permutation_application.py`，第 4–4 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.sparsity.permutation_lib import Permutation

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/sparsity/test/toy_problem.py`，第 5–6 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.sparsity import ASP

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/bottleneck/test_bottleneck_module.py`，第 6–11 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.distributed_testing.distributed_test_base import NcclDistributedTestBase

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-002` — 检测 torch\.distributed NCCL 通信后端

- 位置：`apex/contrib/test/bottleneck/test_bottleneck_module.py`，第 228–228 行
- 分类：`communication`
- 说明：项目将分布式通信后端指定为 NCCL，迁移到沐曦环境需要确认通信库与后端的等价映射。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核通信后端选择、初始化参数与多卡拓扑，并在沐曦多卡环境验证集合通信行为。
- 证据：

    torch.distributed.init_process_group("nccl")

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/clip_grad/test_clip_grad.py`，第 8–8 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.clip_grad import clip_grad_norm_

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/conv_bias_relu/test_conv_bias_relu.py`，第 11–11 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.conv_bias_relu import (

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/cudnn_gbn/test_cudnn_gbn_with_two_gpus.py`，第 10–13 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.distributed_testing.distributed_test_base import NcclDistributedTestBase

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/focal_loss/test_focal_loss.py`，第 14–14 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.focal_loss import focal_loss

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/fused_dense/test_fused_dense.py`，第 10–10 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex import fused_dense

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/group_norm/test_group_norm.py`，第 18–19 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.group_norm import GroupNorm

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/index_mul_2d/test_index_mul_2d.py`，第 8–8 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.index_mul_2d import index_mul_2d

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/layer_norm/test_fast_layer_norm.py`，第 10–10 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.layer_norm.layer_norm import FastLayerNorm

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/openfold_triton/test_fused_adam_swa.py`，第 24–24 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.openfold_triton.fused_adam_swa import AdamMathType, FusedAdamSWA

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/openfold_triton/test_openfold_mha.py`，第 10–10 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.openfold_triton import AttnTri as openfold_attention_triton

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/openfold_triton/test_sync_triton_auto_tune_cache_across_gpus.py`，第 12–12 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.openfold_triton import (

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-002` — 检测 torch\.distributed NCCL 通信后端

- 位置：`apex/contrib/test/openfold_triton/test_sync_triton_auto_tune_cache_across_gpus.py`，第 59–60 行
- 分类：`communication`
- 说明：项目将分布式通信后端指定为 NCCL，迁移到沐曦环境需要确认通信库与后端的等价映射。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核通信后端选择、初始化参数与多卡拓扑，并在沐曦多卡环境验证集合通信行为。
- 证据：

    dist.init_process_group(
                "nccl",

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/optimizers/test_dist_adam.py`，第 13–16 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.optimizers.distributed_fused_adam import DistributedFusedAdam

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/optimizers/test_distributed_fused_lamb.py`，第 8–9 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.optimizers.distributed_fused_lamb import DistributedFusedLAMB

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/peer_memory/test_peer_halo_exchange_module.py`，第 7–10 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.distributed_testing.distributed_test_base import NcclDistributedTestBase

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-002` — 检测 torch\.distributed NCCL 通信后端

- 位置：`apex/contrib/test/peer_memory/test_peer_halo_exchange_module.py`，第 267–267 行
- 分类：`communication`
- 说明：项目将分布式通信后端指定为 NCCL，迁移到沐曦环境需要确认通信库与后端的等价映射。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核通信后端选择、初始化参数与多卡拓扑，并在沐曦多卡环境验证集合通信行为。
- 证据：

    torch.distributed.init_process_group("nccl")

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/transducer/test_transducer_joint.py`，第 7–8 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.transducer import TransducerJoint

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/transducer/test_transducer_loss.py`，第 7–8 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib.transducer import TransducerLoss

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`apex/contrib/test/xentropy/test_label_smoothing.py`，第 10–10 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.contrib import xentropy as label_smoothing

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`examples/dcgan/main_amp.py`，第 15–15 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于示例路径：示例代码一般不随交付构建，已从 warning 降为提示。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex import amp

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-002` — 检测 torch\.distributed NCCL 通信后端

- 位置：`examples/imagenet/main_amp.py`，第 117–117 行
- 分类：`communication`
- 说明：项目将分布式通信后端指定为 NCCL，迁移到沐曦环境需要确认通信库与后端的等价映射。（该命中位于示例路径：示例代码一般不随交付构建，已从 warning 降为提示。）
- 建议：请复核通信后端选择、初始化参数与多卡拓扑，并在沐曦多卡环境验证集合通信行为。
- 证据：

    torch.distributed.init_process_group(backend='nccl',

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`examples/imagenet/main_amp.py`，第 137–137 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于示例路径：示例代码一般不随交付构建，已从 warning 降为提示。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    import apex

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`examples/simple/distributed/distributed_data_parallel.py`，第 7–9 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于示例路径：示例代码一般不随交付构建，已从 warning 降为提示。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.parallel import DistributedDataParallel

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-002` — 检测 torch\.distributed NCCL 通信后端

- 位置：`examples/simple/distributed/distributed_data_parallel.py`，第 29–29 行
- 分类：`communication`
- 说明：项目将分布式通信后端指定为 NCCL，迁移到沐曦环境需要确认通信库与后端的等价映射。（该命中位于示例路径：示例代码一般不随交付构建，已从 warning 降为提示。）
- 建议：请复核通信后端选择、初始化参数与多卡拓扑，并在沐曦多卡环境验证集合通信行为。
- 证据：

    torch.distributed.init_process_group(backend='nccl',

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`tests/L0/run_fused_layer_norm/test_fused_layer_norm.py`，第 8–8 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.normalization import FusedLayerNorm, FusedRMSNorm, MixedFusedLayerNorm, MixedFusedRMSNorm

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`tests/L0/run_mlp/test_mlp.py`，第 12–12 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.mlp import MLP

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`tests/L0/run_optimizers/test_adam.py`，第 9–9 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    import apex

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`tests/L0/run_optimizers/test_fused_novograd.py`，第 8–8 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    import apex

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`tests/L0/run_optimizers/test_fused_optimizer.py`，第 7–7 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    import apex

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`tests/L0/run_optimizers/test_lamb.py`，第 8–9 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    import apex

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`tests/L1/common/main_amp.py`，第 18–203 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.fp16_utils import *

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-002` — 检测 torch\.distributed NCCL 通信后端

- 位置：`tests/L1/common/main_amp.py`，第 189–189 行
- 分类：`communication`
- 说明：项目将分布式通信后端指定为 NCCL，迁移到沐曦环境需要确认通信库与后端的等价映射。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核通信后端选择、初始化参数与多卡拓扑，并在沐曦多卡环境验证集合通信行为。
- 证据：

    torch.distributed.init_process_group(backend="nccl", init_method="env://")

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`tests/distributed/DDP/ddp_race_condition_test.py`，第 5–5 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.parallel import DistributedDataParallel as DDP

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-002` — 检测 torch\.distributed NCCL 通信后端

- 位置：`tests/distributed/DDP/ddp_race_condition_test.py`，第 19–19 行
- 分类：`communication`
- 说明：项目将分布式通信后端指定为 NCCL，迁移到沐曦环境需要确认通信库与后端的等价映射。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核通信后端选择、初始化参数与多卡拓扑，并在沐曦多卡环境验证集合通信行为。
- 证据：

    torch.distributed.init_process_group(backend="nccl", init_method="env://")

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`tests/distributed/amp_master_params/amp_master_params.py`，第 7–9 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.parallel import DistributedDataParallel

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-002` — 检测 torch\.distributed NCCL 通信后端

- 位置：`tests/distributed/amp_master_params/amp_master_params.py`，第 29–29 行
- 分类：`communication`
- 说明：项目将分布式通信后端指定为 NCCL，迁移到沐曦环境需要确认通信库与后端的等价映射。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核通信后端选择、初始化参数与多卡拓扑，并在沐曦多卡环境验证集合通信行为。
- 证据：

    torch.distributed.init_process_group(backend="nccl", init_method="env://")

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`tests/distributed/synced_batchnorm/python_single_gpu_unit_test.py`，第 62–62 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.parallel.sync_batchnorm import SyncBatchNorm

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`tests/distributed/synced_batchnorm/single_gpu_unit_test.py`，第 4–4 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    import apex

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`tests/distributed/synced_batchnorm/test_batchnorm1d.py`，第 3–3 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    import apex

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`tests/distributed/synced_batchnorm/test_groups.py`，第 9–31 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    import apex

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-002` — 检测 torch\.distributed NCCL 通信后端

- 位置：`tests/distributed/synced_batchnorm/test_groups.py`，第 49–49 行
- 分类：`communication`
- 说明：项目将分布式通信后端指定为 NCCL，迁移到沐曦环境需要确认通信库与后端的等价映射。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核通信后端选择、初始化参数与多卡拓扑，并在沐曦多卡环境验证集合通信行为。
- 证据：

    torch.distributed.init_process_group(backend="nccl", init_method="env://")

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`tests/distributed/synced_batchnorm/two_gpu_test_different_batch_size.py`，第 6–6 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    from apex.parallel import SyncBatchNorm as ApexSyncBatchNorm

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-002` — 检测 torch\.distributed NCCL 通信后端

- 位置：`tests/distributed/synced_batchnorm/two_gpu_test_different_batch_size.py`，第 38–39 行
- 分类：`communication`
- 说明：项目将分布式通信后端指定为 NCCL，迁移到沐曦环境需要确认通信库与后端的等价映射。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核通信后端选择、初始化参数与多卡拓扑，并在沐曦多卡环境验证集合通信行为。
- 证据：

    torch.distributed.init_process_group(
        "nccl",

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEPENDENCY-005` — 检测 apex 依赖或导入

- 位置：`tests/distributed/synced_batchnorm/two_gpu_unit_test.py`，第 9–31 行
- 分类：`dependency`
- 说明：项目依赖或导入 apex，其混合精度与融合算子包含设备相关原生组件，需要单独确认目标平台版本。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
- 证据：

    import apex

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-COMM-002` — 检测 torch\.distributed NCCL 通信后端

- 位置：`tests/distributed/synced_batchnorm/two_gpu_unit_test.py`，第 40–40 行
- 分类：`communication`
- 说明：项目将分布式通信后端指定为 NCCL，迁移到沐曦环境需要确认通信库与后端的等价映射。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核通信后端选择、初始化参数与多卡拓扑，并在沐曦多卡环境验证集合通信行为。
- 证据：

    torch.distributed.init_process_group(backend="nccl", init_method="env://")

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-003` — 识别 PyTorch 自动混合精度用法

- 位置：`apex/_autocast_utils.py`，第 26–26 行
- 分类：`runtime`
- 说明：项目使用 PyTorch 自动混合精度，目标环境的半精度算子支持与缩放行为需要结合 MXMACA 版本验证。
- 建议：请复核混合精度路径与缩放器行为，并依据 MXMACA 性能指南在沐曦设备验证精度与性能。
- 证据：

    return torch.cuda.amp.autocast_mode._cast(args, torch.get_autocast_gpu_dtype())

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-003` — 识别 PyTorch 自动混合精度用法

- 位置：`apex/contrib/conv_bias_relu/conv_bias_relu.py`，第 11–89 行
- 分类：`runtime`
- 说明：项目使用 PyTorch 自动混合精度，目标环境的半精度算子支持与缩放行为需要结合 MXMACA 版本验证。
- 建议：请复核混合精度路径与缩放器行为，并依据 MXMACA 性能指南在沐曦设备验证精度与性能。
- 证据：

    @torch.amp.custom_fwd(cast_inputs=torch.half, device_type="cuda")

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEVICE-001` — 检测 CUDA 设备管理 API

- 位置：`apex/contrib/csrc/bottleneck/bottleneck.cpp`，第 60–60 行
- 分类：`runtime`
- 说明：源码调用 CUDA 设备管理 API，多设备枚举与选择逻辑包含平台假设。
- 建议：请复核设备选择与同步逻辑，并在沐曦环境验证设备枚举与上下文行为。
- 证据：

    cudaDeviceReset();

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEVICE-001` — 检测 CUDA 设备管理 API

- 位置：`apex/contrib/csrc/conv_bias_relu/conv_bias_relu.cpp`，第 66–66 行
- 分类：`runtime`
- 说明：源码调用 CUDA 设备管理 API，多设备枚举与选择逻辑包含平台假设。
- 建议：请复核设备选择与同步逻辑，并在沐曦环境验证设备枚举与上下文行为。
- 证据：

    cudaDeviceReset();

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-RUNTIME-001` — 检测 CUDA 数据拷贝与事件 Runtime API

- 位置：`apex/contrib/csrc/cudnn_gbn/norm_sample.cpp`，第 263–443 行
- 分类：`runtime`
- 说明：源码调用 CUDA 数据拷贝或事件 API，其同步语义与错误处理需要结合目标运行时确认。
- 建议：请复核拷贝路径、同步点与事件使用方式，并在沐曦环境验证数据一致性与性能。
- 证据：

    cudaMemsetAsync(peer_devPtrs[rank_id], 0, peer_size * 4, stream);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-MEMORY-001` — 检测 CUDA 显存管理 Runtime API

- 位置：`apex/contrib/csrc/group_norm/group_norm_nhwc.cpp`，第 599–980 行
- 分类：`runtime`
- 说明：源码调用 CUDA 显存管理 Runtime API，需要确认 cu\-bridge 对相应 API 的映射与行为差异。
- 建议：请复核显存分配/释放调用点与错误处理，并结合 cu\-bridge 当前版本在沐曦环境验证。
- 证据：

    CHECK_CUDA(cudaMalloc((void**)&amp;x_d, x_sz));

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-RUNTIME-001` — 检测 CUDA 数据拷贝与事件 Runtime API

- 位置：`apex/contrib/csrc/group_norm/group_norm_nhwc.cpp`，第 760–966 行
- 分类：`runtime`
- 说明：源码调用 CUDA 数据拷贝或事件 API，其同步语义与错误处理需要结合目标运行时确认。
- 建议：请复核拷贝路径、同步点与事件使用方式，并在沐曦环境验证数据一致性与性能。
- 证据：

    CHECK_CUDA(cudaMemcpyAsync(x_d, x_h, x_sz, cudaMemcpyHostToDevice, cudaStreamDefault));

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEVICE-001` — 检测 CUDA 设备管理 API

- 位置：`apex/contrib/csrc/group_norm/group_norm_nhwc.cpp`，第 912–998 行
- 分类：`runtime`
- 说明：源码调用 CUDA 设备管理 API，多设备枚举与选择逻辑包含平台假设。
- 建议：请复核设备选择与同步逻辑，并在沐曦环境验证设备枚举与上下文行为。
- 证据：

    CHECK_CUDA(cudaDeviceSynchronize());

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-STREAM-001` — 检测 CUDA 流（Stream）API

- 位置：`apex/contrib/csrc/group_norm/group_norm_nhwc.cpp`，第 934–934 行
- 分类：`runtime`
- 说明：源码调用 CUDA 流（Stream）API，流创建、同步与事件语义需要结合目标运行时确认。
- 建议：请复核流与事件的使用方式，并在沐曦环境验证并发与同步行为。
- 证据：

    CHECK_CUDA(cudaStreamSynchronize(cudaStreamDefault));

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-CUB-001` — 识别 CUB 用法

- 位置：`apex/contrib/csrc/group_norm/group_norm_nhwc_bwd_one_pass_kernel.cuh`，第 6–58 行
- 分类：`library`
- 说明：项目使用 CUB；MXMACA 提供 mcCUB 且对外 API 接口不变，通常无需改动源码。
- 建议：请复核 CUB 版本与 mcCUB 的对应关系，并在沐曦环境验证编译与结果。
- 证据：

    #include &lt;cub/cub.cuh&gt;

- 参考：
  - [MXMACA AI training manual](https://developer.metax-tech.com/api/client/document/preview/587/C500_AITrainningMaunal_CN.html)


### `MXR-CUB-001` — 识别 CUB 用法

- 位置：`apex/contrib/csrc/group_norm/group_norm_nhwc_bwd_two_pass.cu`，第 6–39 行
- 分类：`library`
- 说明：项目使用 CUB；MXMACA 提供 mcCUB 且对外 API 接口不变，通常无需改动源码。
- 建议：请复核 CUB 版本与 mcCUB 的对应关系，并在沐曦环境验证编译与结果。
- 证据：

    #include &lt;cub/cub.cuh&gt;

- 参考：
  - [MXMACA AI training manual](https://developer.metax-tech.com/api/client/document/preview/587/C500_AITrainningMaunal_CN.html)


### `MXR-CUB-001` — 识别 CUB 用法

- 位置：`apex/contrib/csrc/group_norm/group_norm_nhwc_fwd_one_pass_kernel.cuh`，第 6–58 行
- 分类：`library`
- 说明：项目使用 CUB；MXMACA 提供 mcCUB 且对外 API 接口不变，通常无需改动源码。
- 建议：请复核 CUB 版本与 mcCUB 的对应关系，并在沐曦环境验证编译与结果。
- 证据：

    #include &lt;cub/cub.cuh&gt;

- 参考：
  - [MXMACA AI training manual](https://developer.metax-tech.com/api/client/document/preview/587/C500_AITrainningMaunal_CN.html)


### `MXR-CUB-001` — 识别 CUB 用法

- 位置：`apex/contrib/csrc/group_norm/group_norm_nhwc_fwd_two_pass.cu`，第 6–32 行
- 分类：`library`
- 说明：项目使用 CUB；MXMACA 提供 mcCUB 且对外 API 接口不变，通常无需改动源码。
- 建议：请复核 CUB 版本与 mcCUB 的对应关系，并在沐曦环境验证编译与结果。
- 证据：

    #include &lt;cub/cub.cuh&gt;

- 参考：
  - [MXMACA AI training manual](https://developer.metax-tech.com/api/client/document/preview/587/C500_AITrainningMaunal_CN.html)


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


### `MXR-DEVICE-001` — 检测 CUDA 设备管理 API

- 位置：`apex/contrib/csrc/group_norm_v2/gn_utils.cpp`，第 13–13 行
- 分类：`runtime`
- 说明：源码调用 CUDA 设备管理 API，多设备枚举与选择逻辑包含平台假设。
- 建议：请复核设备选择与同步逻辑，并在沐曦环境验证设备枚举与上下文行为。
- 证据：

    CUDA_CHECK(cudaGetDeviceCount(&amp;count));

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


### `MXR-DEVICE-001` — 检测 CUDA 设备管理 API

- 位置：`apex/contrib/csrc/groupbn/batch_norm.cu`，第 262–270 行
- 分类：`runtime`
- 说明：源码调用 CUDA 设备管理 API，多设备枚举与选择逻辑包含平台假设。
- 建议：请复核设备选择与同步逻辑，并在沐曦环境验证设备枚举与上下文行为。
- 证据：

    cudaGetDevice(&amp;device_id);

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


### `MXR-DEVICE-001` — 检测 CUDA 设备管理 API

- 位置：`apex/contrib/csrc/groupbn/batch_norm_add_relu.cu`，第 271–279 行
- 分类：`runtime`
- 说明：源码调用 CUDA 设备管理 API，多设备枚举与选择逻辑包含平台假设。
- 建议：请复核设备选择与同步逻辑，并在沐曦环境验证设备枚举与上下文行为。
- 证据：

    cudaGetDevice(&amp;device_id);

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


### `MXR-MEMORY-001` — 检测 CUDA 显存管理 Runtime API

- 位置：`apex/contrib/csrc/peer_memory/peer_memory_cuda.cu`，第 30–325 行
- 分类：`runtime`
- 说明：源码调用 CUDA 显存管理 Runtime API，需要确认 cu\-bridge 对相应 API 的映射与行为差异。
- 建议：请复核显存分配/释放调用点与错误处理，并结合 cu\-bridge 当前版本在沐曦环境验证。
- 证据：

    cudaFree(ptr);

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-RUNTIME-001` — 检测 CUDA 数据拷贝与事件 Runtime API

- 位置：`apex/contrib/csrc/peer_memory/peer_memory_cuda.cu`，第 321–327 行
- 分类：`runtime`
- 说明：源码调用 CUDA 数据拷贝或事件 API，其同步语义与错误处理需要结合目标运行时确认。
- 建议：请复核拷贝路径、同步点与事件使用方式，并在沐曦环境验证数据一致性与性能。
- 证据：

    cudaMemset(ptr, 0, size);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEVICE-001` — 检测 CUDA 设备管理 API

- 位置：`apex/contrib/csrc/peer_memory/peer_memory_cuda.cu`，第 488–488 行
- 分类：`runtime`
- 说明：源码调用 CUDA 设备管理 API，多设备枚举与选择逻辑包含平台假设。
- 建议：请复核设备选择与同步逻辑，并在沐曦环境验证设备枚举与上下文行为。
- 证据：

    cudaGetDevice(&amp;device);

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


### `MXR-PYTORCH-003` — 识别 PyTorch 自动混合精度用法

- 位置：`apex/contrib/cudnn_gbn/batch_norm.py`，第 5–5 行
- 分类：`runtime`
- 说明：项目使用 PyTorch 自动混合精度，目标环境的半精度算子支持与缩放行为需要结合 MXMACA 版本验证。
- 建议：请复核混合精度路径与缩放器行为，并依据 MXMACA 性能指南在沐曦设备验证精度与性能。
- 证据：

    from torch.cuda.amp import custom_bwd, custom_fwd

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-003` — 识别 PyTorch 自动混合精度用法

- 位置：`apex/contrib/layer_norm/layer_norm.py`，第 41–41 行
- 分类：`runtime`
- 说明：项目使用 PyTorch 自动混合精度，目标环境的半精度算子支持与缩放行为需要结合 MXMACA 版本验证。
- 建议：请复核混合精度路径与缩放器行为，并依据 MXMACA 性能指南在沐曦设备验证精度与性能。
- 证据：

    with torch.amp.autocast("cuda", enabled=False):

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-003` — 识别 PyTorch 自动混合精度用法

- 位置：`apex/contrib/optimizers/distributed_fused_adam.py`，第 2310–2398 行
- 分类：`runtime`
- 说明：项目使用 PyTorch 自动混合精度，目标环境的半精度算子支持与缩放行为需要结合 MXMACA 版本验证。
- 建议：请复核混合精度路径与缩放器行为，并依据 MXMACA 性能指南在沐曦设备验证精度与性能。
- 证据：

    grad_scaler: torch.cuda.amp.GradScaler | None = None,

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-MEMORY-001` — 检测 CUDA 显存管理 Runtime API

- 位置：`apex/contrib/sparsity/permutation_search_kernels/CUDA_kernels/permutation_search_kernels.cu`，第 97–591 行
- 分类：`runtime`
- 说明：源码调用 CUDA 显存管理 Runtime API，需要确认 cu\-bridge 对相应 API 的映射与行为差异。
- 建议：请复核显存分配/释放调用点与错误处理，并结合 cu\-bridge 当前版本在沐曦环境验证。
- 证据：

    cudaFree(*dmatrix);

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-RUNTIME-001` — 检测 CUDA 数据拷贝与事件 Runtime API

- 位置：`apex/contrib/sparsity/permutation_search_kernels/CUDA_kernels/permutation_search_kernels.cu`，第 166–618 行
- 分类：`runtime`
- 说明：源码调用 CUDA 数据拷贝或事件 API，其同步语义与错误处理需要结合目标运行时确认。
- 建议：请复核拷贝路径、同步点与事件使用方式，并在沐曦环境验证数据一致性与性能。
- 证据：

    gpuErrchk(cudaMemcpy(d_permutations, permutations, num_permutations * group_width * 4 * sizeof(unsigned int),

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEVICE-001` — 检测 CUDA 设备管理 API

- 位置：`apex/contrib/sparsity/permutation_search_kernels/CUDA_kernels/permutation_search_kernels.cu`，第 179–616 行
- 分类：`runtime`
- 说明：源码调用 CUDA 设备管理 API，多设备枚举与选择逻辑包含平台假设。
- 建议：请复核设备选择与同步逻辑，并在沐曦环境验证设备枚举与上下文行为。
- 证据：

    gpuErrchk(cudaDeviceSynchronize());

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-003` — 识别 PyTorch 自动混合精度用法

- 位置：`apex/contrib/test/conv_bias_relu/test_conv_bias_relu.py`，第 109–221 行
- 分类：`runtime`
- 说明：项目使用 PyTorch 自动混合精度，目标环境的半精度算子支持与缩放行为需要结合 MXMACA 版本验证。
- 建议：请复核混合精度路径与缩放器行为，并依据 MXMACA 性能指南在沐曦设备验证精度与性能。
- 证据：

    with torch.amp.autocast("cuda", dtype=torch.half):

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-003` — 识别 PyTorch 自动混合精度用法

- 位置：`apex/contrib/test/cudnn_gbn/test_cudnn_gbn_with_two_gpus.py`，第 136–136 行
- 分类：`runtime`
- 说明：项目使用 PyTorch 自动混合精度，目标环境的半精度算子支持与缩放行为需要结合 MXMACA 版本验证。
- 建议：请复核混合精度路径与缩放器行为，并依据 MXMACA 性能指南在沐曦设备验证精度与性能。
- 证据：

    with torch.amp.autocast("cuda"):

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-003` — 识别 PyTorch 自动混合精度用法

- 位置：`apex/contrib/test/layer_norm/test_fast_layer_norm.py`，第 280–280 行
- 分类：`runtime`
- 说明：项目使用 PyTorch 自动混合精度，目标环境的半精度算子支持与缩放行为需要结合 MXMACA 版本验证。
- 建议：请复核混合精度路径与缩放器行为，并依据 MXMACA 性能指南在沐曦设备验证精度与性能。
- 证据：

    with torch.amp.autocast("cuda", enabled=True, dtype=dtype):

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-003` — 识别 PyTorch 自动混合精度用法

- 位置：`apex/contrib/test/optimizers/test_dist_adam.py`，第 464–465 行
- 分类：`runtime`
- 说明：项目使用 PyTorch 自动混合精度，目标环境的半精度算子支持与缩放行为需要结合 MXMACA 版本验证。
- 建议：请复核混合精度路径与缩放器行为，并依据 MXMACA 性能指南在沐曦设备验证精度与性能。
- 证据：

    ref_scaler = torch.amp.GradScaler("cuda", **grad_scaler_args)

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-003` — 识别 PyTorch 自动混合精度用法

- 位置：`apex/contrib/test/optimizers/test_distributed_fused_lamb.py`，第 4–87 行
- 分类：`runtime`
- 说明：项目使用 PyTorch 自动混合精度，目标环境的半精度算子支持与缩放行为需要结合 MXMACA 版本验证。
- 建议：请复核混合精度路径与缩放器行为，并依据 MXMACA 性能指南在沐曦设备验证精度与性能。
- 证据：

    from torch.cuda.amp import GradScaler

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-003` — 识别 PyTorch 自动混合精度用法

- 位置：`apex/fused_dense/fused_dense.py`，第 63–75 行
- 分类：`runtime`
- 说明：项目使用 PyTorch 自动混合精度，目标环境的半精度算子支持与缩放行为需要结合 MXMACA 版本验证。
- 建议：请复核混合精度路径与缩放器行为，并依据 MXMACA 性能指南在沐曦设备验证精度与性能。
- 证据：

    with torch.amp.autocast("cuda", enabled=False):

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-003` — 识别 PyTorch 自动混合精度用法

- 位置：`apex/normalization/fused_layer_norm.py`，第 674–720 行
- 分类：`runtime`
- 说明：项目使用 PyTorch 自动混合精度，目标环境的半精度算子支持与缩放行为需要结合 MXMACA 版本验证。
- 建议：请复核混合精度路径与缩放器行为，并依据 MXMACA 性能指南在沐曦设备验证精度与性能。
- 证据：

    with torch.amp.autocast("cuda", enabled=False):

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
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


### `MXR-RUNTIME-001` — 检测 CUDA 数据拷贝与事件 Runtime API

- 位置：`csrc/mlp_cuda.cu`，第 1171–1211 行
- 分类：`runtime`
- 说明：源码调用 CUDA 数据拷贝或事件 API，其同步语义与错误处理需要结合目标运行时确认。
- 建议：请复核拷贝路径、同步点与事件使用方式，并在沐曦环境验证数据一致性与性能。
- 证据：

    cudaMemsetAsync(semaphores, 0, semaphore_size, stream);

- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEVICE-001` — 检测 CUDA 设备管理 API

- 位置：`csrc/multi_tensor_axpby_kernel.cu`，第 121–121 行
- 分类：`runtime`
- 说明：源码调用 CUDA 设备管理 API，多设备枚举与选择逻辑包含平台假设。
- 建议：请复核设备选择与同步逻辑，并在沐曦环境验证设备枚举与上下文行为。
- 证据：

    // AT_CUDA_CHECK(cudaDeviceSynchronize());

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEVICE-001` — 检测 CUDA 设备管理 API

- 位置：`csrc/multi_tensor_l2norm_kernel.cu`，第 322–426 行
- 分类：`runtime`
- 说明：源码调用 CUDA 设备管理 API，多设备枚举与选择逻辑包含平台假设。
- 建议：请复核设备选择与同步逻辑，并在沐曦环境验证设备枚举与上下文行为。
- 证据：

    // AT_CUDA_CHECK(cudaDeviceSynchronize());

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEVICE-001` — 检测 CUDA 设备管理 API

- 位置：`csrc/multi_tensor_l2norm_kernel_mp.cu`，第 153–153 行
- 分类：`runtime`
- 说明：源码调用 CUDA 设备管理 API，多设备枚举与选择逻辑包含平台假设。
- 建议：请复核设备选择与同步逻辑，并在沐曦环境验证设备枚举与上下文行为。
- 证据：

    // AT_CUDA_CHECK(cudaDeviceSynchronize());

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEVICE-001` — 检测 CUDA 设备管理 API

- 位置：`csrc/multi_tensor_l2norm_scale_kernel.cu`，第 238–238 行
- 分类：`runtime`
- 说明：源码调用 CUDA 设备管理 API，多设备枚举与选择逻辑包含平台假设。
- 建议：请复核设备选择与同步逻辑，并在沐曦环境验证设备枚举与上下文行为。
- 证据：

    // AT_CUDA_CHECK(cudaDeviceSynchronize());

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEVICE-001` — 检测 CUDA 设备管理 API

- 位置：`csrc/multi_tensor_lamb_stage_1.cu`，第 119–119 行
- 分类：`runtime`
- 说明：源码调用 CUDA 设备管理 API，多设备枚举与选择逻辑包含平台假设。
- 建议：请复核设备选择与同步逻辑，并在沐曦环境验证设备枚举与上下文行为。
- 证据：

    // AT_CUDA_CHECK(cudaDeviceSynchronize());

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEVICE-001` — 检测 CUDA 设备管理 API

- 位置：`csrc/multi_tensor_lamb_stage_2.cu`，第 95–95 行
- 分类：`runtime`
- 说明：源码调用 CUDA 设备管理 API，多设备枚举与选择逻辑包含平台假设。
- 建议：请复核设备选择与同步逻辑，并在沐曦环境验证设备枚举与上下文行为。
- 证据：

    // AT_CUDA_CHECK(cudaDeviceSynchronize());

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-DEVICE-001` — 检测 CUDA 设备管理 API

- 位置：`csrc/multi_tensor_scale_kernel.cu`，第 110–110 行
- 分类：`runtime`
- 说明：源码调用 CUDA 设备管理 API，多设备枚举与选择逻辑包含平台假设。
- 建议：请复核设备选择与同步逻辑，并在沐曦环境验证设备枚举与上下文行为。
- 证据：

    // AT_CUDA_CHECK(cudaDeviceSynchronize());

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


### `MXR-PYTORCH-003` — 识别 PyTorch 自动混合精度用法

- 位置：`examples/imagenet/main_amp.py`，第 151–323 行
- 分类：`runtime`
- 说明：项目使用 PyTorch 自动混合精度，目标环境的半精度算子支持与缩放行为需要结合 MXMACA 版本验证。
- 建议：请复核混合精度路径与缩放器行为，并依据 MXMACA 性能指南在沐曦设备验证精度与性能。
- 证据：

    scaler = torch.amp.GradScaler("cuda")

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 175–828 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

    CUDAExtension(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-002` — 识别 PyTorch JIT 原生扩展

- 位置：`setup.py`，第 818–818 行
- 分类：`pytorch\-extension`
- 说明：项目使用 torch\.utils\.cpp\_extension\.load 在运行时编译扩展，执行环境必须具备完整工具链。
- 建议：请复核 JIT 源码、缓存、编译参数与依赖，并在 MXMACA 环境验证首次和重复加载。
- 证据：

    _nccl_version_getter = load(

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


### `MXR-PYTORCH-003` — 识别 PyTorch 自动混合精度用法

- 位置：`tests/L0/run_fused_layer_norm/test_fused_layer_norm.py`，第 500–543 行
- 分类：`runtime`
- 说明：项目使用 PyTorch 自动混合精度，目标环境的半精度算子支持与缩放行为需要结合 MXMACA 版本验证。
- 建议：请复核混合精度路径与缩放器行为，并依据 MXMACA 性能指南在沐曦设备验证精度与性能。
- 证据：

    with torch.amp.autocast("cuda", dtype=dtype):

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-003` — 识别 PyTorch 自动混合精度用法

- 位置：`tests/L0/run_mlp/test_mlp.py`，第 79–79 行
- 分类：`runtime`
- 说明：项目使用 PyTorch 自动混合精度，目标环境的半精度算子支持与缩放行为需要结合 MXMACA 版本验证。
- 建议：请复核混合精度路径与缩放器行为，并依据 MXMACA 性能指南在沐曦设备验证精度与性能。
- 证据：

    with torch.cuda.amp.autocast_mode.autocast(enabled=enable_autocast):

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-003` — 识别 PyTorch 自动混合精度用法

- 位置：`tests/L0/run_optimizers/test_adam.py`，第 66–193 行
- 分类：`runtime`
- 说明：项目使用 PyTorch 自动混合精度，目标环境的半精度算子支持与缩放行为需要结合 MXMACA 版本验证。
- 建议：请复核混合精度路径与缩放器行为，并依据 MXMACA 性能指南在沐曦设备验证精度与性能。
- 证据：

    scaler = torch.amp.GradScaler("cuda", enabled=True)

- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-PYTORCH-002` — 识别 PyTorch JIT 原生扩展

- 位置：`tests/distributed/synced_batchnorm/single_gpu_unit_test.py`，第 13–13 行
- 分类：`pytorch\-extension`
- 说明：项目使用 torch\.utils\.cpp\_extension\.load 在运行时编译扩展，执行环境必须具备完整工具链。
- 建议：请复核 JIT 源码、缓存、编译参数与依赖，并在 MXMACA 环境验证首次和重复加载。
- 证据：

    syncbn = load(name="syncbn", sources=["../../csrc/syncbn.cpp", "../../csrc/welford.cu"])

- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


## 迁移清单

- [ ] `MXR-PTX-001` 检测内联 PTX 汇编：请逐处复核 asm 块对应的硬件能力，改用目标平台支持的内建函数或等价 C\+\+ 实现，并在沐曦环境验证功能与性能。
  - 涉及文件：`apex/contrib/csrc/group_norm/group_norm_nhwc.h`、`apex/contrib/csrc/group_norm/group_norm_nhwc_bwd_one_pass_kernel.cuh`、`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`、`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`、`apex/contrib/csrc/layer_norm/ln_utils.cuh`、`apex/contrib/csrc/peer_memory/peer_memory_cuda.cu`、`apex/contrib/csrc/transducer/philox.cuh`
- [ ] `MXR-WARP-001` 检测硬编码 32 线程束假设：请复核 lane 计算与掩码宽度，改用运行时查询的线程束宽度，并在沐曦环境用最小用例比对结果。
  - 涉及文件：`apex/contrib/csrc/group_norm_v2/gn_cuda_kernel.cuh`、`apex/contrib/csrc/groupbn/nhwc_batch_norm_kernel.h`、`apex/contrib/csrc/xentropy/xentropy_kernel.cu`、`csrc/welford.cu`
- [ ] `MXR-TOOLCHAIN-001` 检测直接 nvcc 工具调用：请复核调用点，按 cu\-bridge 当前版本配置对应工具链，并在沐曦环境验证构建。
  - 涉及文件：`setup.py`
- [ ] `MXR-DEPENDENCY-005` 检测 apex 依赖或导入：请复核 apex 版本、算子覆盖与混合精度路径，并在沐曦环境验证导入与核心功能。
  - 涉及文件：`apex/contrib/bottleneck/bottleneck.py`、`apex/contrib/clip_grad/clip_grad.py`、`apex/contrib/conv_bias_relu/conv_bias_relu.py`、`apex/contrib/layer_norm/layer_norm.py`、`apex/contrib/nccl_allocator/nccl_allocator.py`、`apex/contrib/openfold_triton/__init__.py`、`apex/contrib/openfold_triton/layer_norm.py`、`apex/contrib/openfold_triton/mha.py`、`apex/contrib/optimizers/distributed_fused_adam.py`、`apex/contrib/optimizers/distributed_fused_lamb.py`、`apex/contrib/optimizers/fp16_optimizer.py`、`apex/contrib/optimizers/fused_adam.py`、`apex/contrib/optimizers/fused_lamb.py`、`apex/contrib/optimizers/fused_sgd.py`、`apex/contrib/torchsched/backend.py`、`apex/contrib/torchsched/inductor/__init__.py`、`apex/contrib/torchsched/inductor/event.py`、`apex/contrib/torchsched/inductor/graph.py`、`apex/contrib/torchsched/inductor/scheduler.py`、`apex/contrib/torchsched/inductor/wrapper.py`、`apex/contrib/torchsched/passes/__init__.py`、`apex/contrib/torchsched/passes/pre_grad_passes.py`、`apex/distributed_testing/__init__.py`、`apex/distributed_testing/distributed_test_base.py`、`apex/fused_dense/fused_dense.py`、`apex/mlp/mlp.py`、`apex/normalization/fused_layer_norm.py`、`apex/optimizers/fused_adagrad.py`、`apex/optimizers/fused_adam.py`、`apex/optimizers/fused_lamb.py`、`apex/optimizers/fused_mixed_precision_lamb.py`、`apex/optimizers/fused_novograd.py`、`apex/optimizers/fused_sgd.py`
- [ ] `MXR-COMM-002` 检测 torch\.distributed NCCL 通信后端：请复核通信后端选择、初始化参数与多卡拓扑，并在沐曦多卡环境验证集合通信行为。
  - 涉及文件：`apex/contrib/bottleneck/halo_exchangers.py`
- [ ] `MXR-LIBRARY-001` 识别 cuBLAS / cuDNN / cuFFT / cuSPARSE / cuSOLVER 头文件：请复核实际使用的库 API 与链接配置，并结合 cu\-bridge 当前版本在沐曦环境验证编译与数值行为。
  - 涉及文件：`apex/contrib/csrc/bottleneck/bottleneck.cpp`、`apex/contrib/csrc/conv_bias_relu/conv_bias_relu.cpp`、`apex/contrib/csrc/cudnn_gbn/norm_sample.cpp`、`apex/contrib/csrc/cudnn_gbn/norm_sample.h`、`apex/contrib/csrc/groupbn/batch_norm.h`、`apex/contrib/csrc/groupbn/batch_norm_add_relu.h`、`csrc/fused_dense_cuda.cu`、`csrc/megatron/fused_weight_gradient_dense_16bit_prec_cuda.cu`、`csrc/megatron/fused_weight_gradient_dense_cuda.cu`、`csrc/mlp_cuda.cu`
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

- `PATH_CONTEXT_DEMOTION`：示例路径上的 MXR\-COMM\-002（4 个文件）；MXR\-DEPENDENCY\-005（11 个文件） 已封顶为提示，不参与静态状态判定；文件仍被扫描，结论可逐条复核。
- `PATH_CONTEXT_DEMOTION`：测试/夹具路径上的 MXR\-COMM\-002（9 个文件）；MXR\-DEPENDENCY\-005（38 个文件） 已封顶为提示，不参与静态状态判定；文件仍被扫描，结论可逐条复核。

## 说明

静态扫描不能替代真实沐曦 GPU 上的构建、功能和性能验证，也不能作为项目安全性或完整兼容性的证明。
