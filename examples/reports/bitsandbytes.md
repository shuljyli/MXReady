# MXReady 适配体检报告：bitsandbytes

## 扫描元数据

| 字段 | 值 |
| --- | --- |
| 仓库 | https://github\.com/bitsandbytes\-foundation/bitsandbytes |
| 提交 | `a616886cacf86701514f0cb1d6be760f967481c0` |
| MXReady 版本 | 0\.3\.1 |
| 规则集版本 | 4 |
| 规则集摘要 | sha256:badf12ad29ce6f7cff9e6f07b4df4034822fbe9773571cad6517d9c65325c531 |
| 扩展规则版本 | 无 |
| 分析配置 | \{'max\_findings': 10000, 'rule\_timeout\_seconds': 30, 'index\_max\_files': 10000, 'index\_max\_file\_bytes': 1048576, 'prefilter': 'on'\} |
| 扫描时间 | 2026\-11\-05T07:05:59\.211603\+00:00 |
| 静态状态 | `blocked` |
| 硬件验证状态 | `not-run` |

## 结果摘要

| 阻塞项 | 警告 | 提示 | 总计 |
| ---: | ---: | ---: | ---: |
| 7 | 10 | 10 | 27 |

## 扫描范围

分析文件：148；字节：1702772；排除目录：1（未遍历内容）。
文件类型：\{'\.cpp': 4, '\.cu': 6, '\.cuh': 10, '\.h': 4, '\.md': 24, '\.py': 79, '\.sh': 4, '\.toml': 2, '\.txt': 1, '\.yaml': 1, '\.yml': 13\}
跳过原因：\{'UNSUPPORTED\_FILE\_TYPE': 37\}

仅表示支持的文件类型与限制内的扫描范围，不是完整仓库覆盖率。

## 阻塞项

### `MXR-PTX-001` — 检测内联 PTX 汇编

- 位置：`csrc/gemm_4bit_mma.cuh`，第 45–117 行
- 分类：`ptx`
- 说明：内联汇编块嵌入的是 NVIDIA 虚拟 ISA（PTX）指令，MXMACA 后端不执行 PTX；这类代码可能固化 NVIDIA 指令语义。
- 建议：请逐处复核 asm 块对应的硬件能力，改用目标平台支持的内建函数或等价 C\+\+ 实现，并在沐曦环境验证功能与性能。
- 证据：

- 第 45–45 行

    asm("cvt.rn.bf16x2.f32 %0, %1, %2;" : "=r"(result) : "f"(hi), "f"(lo));

- 第 107–107 行

    asm volatile("st.global.cs.b32 [%0], %1;" :: "l"(&amp;C[m0 * N + n0]), "r"(c01));

- 第 117–117 行

    asm volatile("st.global.cs.b32 [%0], %1;" :: "l"(&amp;C[m1 * N + n0]), "r"(c23));


- 参考：
  - [NVIDIA Inline PTX Assembly](https://docs.nvidia.com/cuda/inline-ptx-assembly/index.html)
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-WARP-001` — 检测硬编码 32 线程束假设

- 位置：`csrc/gemm_4bit_simt.cu`，第 138–138 行
- 分类：`warp`
- 说明：代码按 32 线程一组计算 lane 或定义线程束宽度常量；MXMACA 的线程束（wave）宽度为 64，这类算术可能编译通过但结果错位。
- 建议：请复核 lane 计算与掩码宽度，改用运行时查询的线程束宽度，并在沐曦环境用最小用例比对结果。
- 证据：

- 第 138–138 行

    const int lane_id = threadIdx.x &amp; 31;


- 参考：
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-PTX-001` — 检测内联 PTX 汇编

- 位置：`csrc/gemm_4bit_simt.cu`，第 286–408 行
- 分类：`ptx`
- 说明：内联汇编块嵌入的是 NVIDIA 虚拟 ISA（PTX）指令，MXMACA 后端不执行 PTX；这类代码可能固化 NVIDIA 指令语义。
- 建议：请逐处复核 asm 块对应的硬件能力，改用目标平台支持的内建函数或等价 C\+\+ 实现，并在沐曦环境验证功能与性能。
- 证据：

- 第 286–287 行

    asm volatile(
                    "ld.global.cs.v4.u32 {%0,%1,%2,%3}, [%4];\n"

- 第 407–408 行

    asm volatile(
                                "ld.global.ca.v4.u32 {%0,%1,%2,%3}, [%4];\n"


- 参考：
  - [NVIDIA Inline PTX Assembly](https://docs.nvidia.com/cuda/inline-ptx-assembly/index.html)
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-PTX-001` — 检测内联 PTX 汇编

- 位置：`csrc/gemm_4bit_sm75.cu`，第 34–248 行
- 分类：`ptx`
- 说明：内联汇编块嵌入的是 NVIDIA 虚拟 ISA（PTX）指令，MXMACA 后端不执行 PTX；这类代码可能固化 NVIDIA 指令语义。
- 建议：请逐处复核 asm 块对应的硬件能力，改用目标平台支持的内建函数或等价 C\+\+ 实现，并在沐曦环境验证功能与性能。
- 证据：

- 第 34–35 行

    asm volatile(
            "mma.sync.aligned.m16n8k8.row.col.f32.f16.f16.f32 "

- 第 50–51 行

    asm volatile(
            "ldmatrix.sync.aligned.m8n8.x2.shared.b16 {%0,%1}, [%2];\n"

- 第 64–65 行

    asm volatile(
            "ldmatrix.sync.aligned.m8n8.x1.shared.b16 {%0}, [%1];\n"

- 第 187–188 行

    asm volatile(
                        "ld.global.ca.v4.u32 {%0,%1,%2,%3}, [%4];\n"

- 第 231–232 行

    asm volatile(
                            "ld.global.cs.v4.u32 {%0,%1,%2,%3}, [%4];\n"

- 第 247–248 行

    asm volatile(
                            "ld.global.cs.v2.u32 {%0,%1}, [%2];\n"


- 参考：
  - [NVIDIA Inline PTX Assembly](https://docs.nvidia.com/cuda/inline-ptx-assembly/index.html)
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-WARP-001` — 检测硬编码 32 线程束假设

- 位置：`csrc/gemm_4bit_sm75.cu`，第 147–148 行
- 分类：`warp`
- 说明：代码按 32 线程一组计算 lane 或定义线程束宽度常量；MXMACA 的线程束（wave）宽度为 64，这类算术可能编译通过但结果错位。
- 建议：请复核 lane 计算与掩码宽度，改用运行时查询的线程束宽度，并在沐曦环境用最小用例比对结果。
- 证据：

- 第 147–147 行

    const int warp_id = threadIdx.x / 32;

- 第 148–148 行

    const int lane_id = threadIdx.x % 32;


- 参考：
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-PTX-001` — 检测内联 PTX 汇编

- 位置：`csrc/gemm_4bit_sm80.cu`，第 34–402 行
- 分类：`ptx`
- 说明：内联汇编块嵌入的是 NVIDIA 虚拟 ISA（PTX）指令，MXMACA 后端不执行 PTX；这类代码可能固化 NVIDIA 指令语义。
- 建议：请逐处复核 asm 块对应的硬件能力，改用目标平台支持的内建函数或等价 C\+\+ 实现，并在沐曦环境验证功能与性能。
- 证据：

- 第 34–35 行

    asm volatile(
                "mma.sync.aligned.m16n8k16.row.col.f32.bf16.bf16.f32 "

- 第 44–45 行

    asm volatile(
                "mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32 "

- 第 69–70 行

    asm volatile(
            "ldmatrix.sync.aligned.m8n8.x4.shared.b16 {%0,%1,%2,%3}, [%4];\n"

- 第 89–90 行

    asm volatile(
            "ldmatrix.sync.aligned.m8n8.x2.shared.b16 {%0,%1}, [%2];\n"

- 第 257–258 行

    asm volatile(
                        "ld.global.ca.v4.u32 {%0,%1,%2,%3}, [%4];\n"

- 第 318–319 行

    asm volatile(
                            "ld.global.cs.v4.u32 {%0,%1,%2,%3},   [%16];\n"

- 第 356–357 行

    asm volatile(
                            "ld.global.cs.v4.u32 {%0,%1,%2,%3}, [%8];\n"

- 第 385–386 行

    asm volatile(
                            "ld.global.cs.v4.u32 {%0,%1,%2,%3}, [%4];\n"

- 第 401–402 行

    asm volatile(
                            "ld.global.cs.v2.u32 {%0,%1}, [%2];\n"


- 参考：
  - [NVIDIA Inline PTX Assembly](https://docs.nvidia.com/cuda/inline-ptx-assembly/index.html)
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


### `MXR-WARP-001` — 检测硬编码 32 线程束假设

- 位置：`csrc/gemm_4bit_sm80.cu`，第 215–216 行
- 分类：`warp`
- 说明：代码按 32 线程一组计算 lane 或定义线程束宽度常量；MXMACA 的线程束（wave）宽度为 64，这类算术可能编译通过但结果错位。
- 建议：请复核 lane 计算与掩码宽度，改用运行时查询的线程束宽度，并在沐曦环境用最小用例比对结果。
- 证据：

- 第 215–215 行

    const int warp_id = threadIdx.x / 32;

- 第 216–216 行

    const int lane_id = threadIdx.x % 32;


- 参考：
  - [MXMACA runtime API guide](https://developer.metax-tech.com/api/client/document/preview/567/C500_RuntimeAPIProgrammingGuide_CN.html)


## 警告

### `MXR-CMAKE-002` — 检测 CMake FindCUDAToolkit

- 位置：`CMakeLists.txt`，第 138–138 行
- 分类：`cmake`
- 说明：工程显式查找 NVIDIA CUDAToolkit，其搜索路径和导入目标带有工具链假设。
- 建议：请复核 CUDAToolkit\_ROOT、导入目标和链接库，并在 cu\-bridge 环境验证 CMake 配置。
- 证据：

- 第 138–138 行

    find_package(CUDAToolkit REQUIRED)


- 参考：
  - [CMake FindCUDAToolkit](https://cmake.org/cmake/help/latest/module/FindCUDAToolkit.html)


### `MXR-LIBRARY-001` — 识别 cuBLAS / cuDNN / cuFFT / cuSPARSE / cuSOLVER 头文件

- 位置：`csrc/compat.cuh`，第 181–183 行
- 分类：`library`
- 说明：源码直接包含 NVIDIA 数学库头文件，目标环境需要由兼容层或等价库提供相应 API 映射。
- 建议：请复核实际使用的库 API 与链接配置，并结合 cu\-bridge 当前版本在沐曦环境验证编译与数值行为。
- 证据：

- 第 181–182 行

    #include &lt;cublasLt.h&gt;

- 第 183–183 行

    #include &lt;cublas_v2.h&gt;


- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/gemm_4bit_simt.cu`，第 88–348 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

- 第 88–88 行

    v += __shfl_down_sync(BNB_FULL_WARP_MASK, v, offset, 32);

- 第 328–328 行

    b_dq[j * 2] = __shfl_sync(BNB_FULL_WARP_MASK, my_lut_f32_shfl, byte &gt;&gt; 4, 32) * scale_f;

- 第 329–329 行

    b_dq[j * 2 + 1] = __shfl_sync(BNB_FULL_WARP_MASK, my_lut_f32_shfl, byte &amp; 0x0f, 32) * scale_f;

- 第 347–347 行

    hi = __shfl_sync(BNB_FULL_WARP_MASK, my_lut_u32, byte &gt;&gt; 4, 32);

- 第 348–348 行

    lo = __shfl_sync(BNB_FULL_WARP_MASK, my_lut_u32, byte &amp; 0x0f, 32);


- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`csrc/gemm_4bit_simt.cu`，第 110–110 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

- 第 110–110 行

    __global__ void __launch_bounds__(WARPS_PER_BLOCK * 32) gemm_4bit_simt(


- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`csrc/gemm_4bit_sm75.cu`，第 98–98 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

- 第 98–98 行

    __global__ void __launch_bounds__(CTA_SIZE) gemm_4bit_sm75_m16n8k8(


- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/gemm_4bit_sm75.cu`，第 220–221 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

- 第 220–220 行

    const float hi = __shfl_sync(0xffffffff, my_lut_f32, byte &gt;&gt; 4);

- 第 221–221 行

    const float lo = __shfl_sync(0xffffffff, my_lut_f32, byte &amp; 0x0f);


- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`csrc/gemm_4bit_sm80.cu`，第 128–128 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

- 第 128–128 行

    __global__ void __launch_bounds__(CTA_SIZE) gemm_4bit_sm80_m16n8k16(


- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/gemm_4bit_sm80.cu`，第 302–303 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

- 第 302–302 行

    const float hi = __shfl_sync(0xffffffff, my_lut_f32, byte &gt;&gt; 4);

- 第 303–303 行

    const float lo = __shfl_sync(0xffffffff, my_lut_f32, byte &amp; 0x0f);


- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`csrc/kernels.cu`，第 270–1332 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

- 第 270–270 行

    //__launch_bounds__(TH, 4)

- 第 532–532 行

    __launch_bounds__(BLOCK_SIZE / NUM_VALS, 1) __global__ void kPreconditionOptimizer32bit2State(

- 第 606–606 行

    __launch_bounds__(TH, 1) __global__ void kOptimizer32bit2State(

- 第 730–730 行

    __launch_bounds__(BLOCK_SIZE / NUM_VALS, 1) __global__ void kPreconditionOptimizer32bit1State(

- 第 807–807 行

    __launch_bounds__(TH, 1) __global__ void kOptimizer32bit1State(

- 第 915–915 行

    __launch_bounds__(256, 3) __global__ void kOptimizerStatic8bit2StateBlockwise(

- 第 1153–1153 行

    __launch_bounds__(256, 3) __global__ void kOptimizerStatic8bit1StateBlockwise(

- 第 1332–1332 行

    __launch_bounds__(1024, BNB_MAX_THREADS_PER_SM / 1024) __global__


- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-DEPENDENCY-002` — 检测 bitsandbytes 依赖

- 位置：`pyproject.toml`，第 61–61 行
- 分类：`dependency`
- 说明：bitsandbytes 包含原生 GPU 组件和设备相关构建逻辑，需要单独确认目标平台版本。
- 建议：请复核依赖版本、预编译包来源和算子覆盖，并在沐曦环境验证导入与核心功能。
- 证据：

- 第 61–61 行

    "bitsandbytes[test]",


- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


## 提示

### `MXR-TEST-001` — 检测 CUDA 可用性静默跳过测试

- 位置：`tests/test_functional.py`，第 461–730 行
- 分类：`test`
- 说明：测试在 torch\.cuda 不可用时静默跳过，迁移到沐曦环境后可能因环境未配置而跳过，造成验证通过的假象。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核跳过条件，并在真机环境手动运行核心 CUDA 测试以确认实际覆盖。
- 证据：

- 第 461–461 行

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA is required")

- 第 730–730 行

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA is required")


- 参考：
  - [pytest skipif documentation](https://docs.pytest.org/)
  - [unittest skipUnless documentation](https://docs.python.org/3/library/unittest.html)


### `MXR-CMAKE-001` — 识别 CMake CUDA 语言

- 位置：`CMakeLists.txt`，第 137–137 行
- 分类：`cmake`
- 说明：CMake 项目启用了 CUDA 语言，目标环境需要提供与工程探测逻辑匹配的编译器。
- 建议：请复核 CMake 工具链选择和语言探测结果，并在 MXMACA/cu\-bridge 环境验证配置阶段。
- 证据：

- 第 137–137 行

    enable_language(CUDA) # This will fail if CUDA is not found


- 参考：
  - [CMake FindCUDAToolkit](https://cmake.org/cmake/help/latest/module/FindCUDAToolkit.html)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/compat.cuh`，第 44–44 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

- 第 44–44 行

    #include &lt;cuda_runtime.h&gt;


- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-MEMORY-001` — 检测 CUDA 显存管理 Runtime API

- 位置：`csrc/compat.cuh`，第 70–71 行
- 分类：`runtime`
- 说明：源码调用 CUDA 显存管理 Runtime API，需要确认 cu\-bridge 对相应 API 的映射与行为差异。
- 建议：请复核显存分配/释放调用点与错误处理，并结合 cu\-bridge 当前版本在沐曦环境验证。
- 证据：

- 第 70–70 行

    #define BNB_DEVICE_MALLOC(p, s) cudaMalloc(p, s)

- 第 71–71 行

    #define BNB_DEVICE_FREE(p) cudaFree(p)


- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-RUNTIME-001` — 检测 CUDA 数据拷贝与事件 Runtime API

- 位置：`csrc/compat.cuh`，第 72–72 行
- 分类：`runtime`
- 说明：源码调用 CUDA 数据拷贝或事件 API，其同步语义与错误处理需要结合目标运行时确认。
- 建议：请复核拷贝路径、同步点与事件使用方式，并在沐曦环境验证数据一致性与性能。
- 证据：

- 第 72–72 行

    #define BNB_DEVICE_MEMSET(p, v, s) cudaMemset(p, v, s)


- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-CUB-001` — 识别 CUB 用法

- 位置：`csrc/compat_device.cuh`，第 18–49 行
- 分类：`library`
- 说明：项目使用 CUB；MXMACA 提供 mcCUB 且对外 API 接口不变，通常无需改动源码。
- 建议：请复核 CUB 版本与 mcCUB 的对应关系，并在沐曦环境验证编译与结果。
- 证据：

- 第 18–19 行

    #include &lt;cub/block/block_discontinuity.cuh&gt;

- 第 20–20 行

    #include &lt;cub/block/block_load.cuh&gt;

- 第 21–21 行

    #include &lt;cub/block/block_radix_sort.cuh&gt;

- 第 22–22 行

    #include &lt;cub/block/block_reduce.cuh&gt;

- 第 23–23 行

    #include &lt;cub/block/block_store.cuh&gt;

- 第 24–24 行

    #include &lt;cub/cub.cuh&gt;

- 第 25–25 行

    #include &lt;cub/warp/warp_reduce.cuh&gt;

- 第 41–41 行

    // CCCL 2.8.2+ moved to cuda::maximum&lt;&gt;{}, older versions use cub::Max()

- 第 47–47 行

    #define BNB_MAX_OP cub::Max()

- 第 49–49 行

    #define BNB_SUM_OP cub::Sum()


- 参考：
  - [MXMACA AI training manual](https://developer.metax-tech.com/api/client/document/preview/587/C500_AITrainningMaunal_CN.html)


### `MXR-DEVICE-001` — 检测 CUDA 设备管理 API

- 位置：`csrc/gemm_4bit.cu`，第 21–21 行
- 分类：`runtime`
- 说明：源码调用 CUDA 设备管理 API，多设备枚举与选择逻辑包含平台假设。
- 建议：请复核设备选择与同步逻辑，并在沐曦环境验证设备枚举与上下文行为。
- 证据：

- 第 21–21 行

    cudaGetDevice(&amp;dev);


- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/gemm_4bit_sm75.cuh`，第 7–7 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

- 第 7–7 行

    #include &lt;cuda_runtime.h&gt;


- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`csrc/gemm_4bit_sm80.cuh`，第 7–7 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

- 第 7–7 行

    #include &lt;cuda_runtime.h&gt;


- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-MEMORY-001` — 检测 CUDA 显存管理 Runtime API

- 位置：`csrc/pythonInterface.cpp`，第 559–559 行
- 分类：`runtime`
- 说明：源码调用 CUDA 显存管理 Runtime API，需要确认 cu\-bridge 对相应 API 的映射与行为差异。
- 建议：请复核显存分配/释放调用点与错误处理，并结合 cu\-bridge 当前版本在沐曦环境验证。
- 证据：

- 第 559–559 行

    CUDA_CHECK_RETURN(cudaMallocManaged(&amp;ptr, bytes, cudaMemAttachHost));


- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


## 迁移清单

- [ ] `MXR-PTX-001` 检测内联 PTX 汇编：请逐处复核 asm 块对应的硬件能力，改用目标平台支持的内建函数或等价 C\+\+ 实现，并在沐曦环境验证功能与性能。
  - 涉及文件：`csrc/gemm_4bit_mma.cuh`、`csrc/gemm_4bit_simt.cu`、`csrc/gemm_4bit_sm75.cu`、`csrc/gemm_4bit_sm80.cu`
- [ ] `MXR-WARP-001` 检测硬编码 32 线程束假设：请复核 lane 计算与掩码宽度，改用运行时查询的线程束宽度，并在沐曦环境用最小用例比对结果。
  - 涉及文件：`csrc/gemm_4bit_simt.cu`、`csrc/gemm_4bit_sm75.cu`、`csrc/gemm_4bit_sm80.cu`
- [ ] `MXR-CMAKE-002` 检测 CMake FindCUDAToolkit：请复核 CUDAToolkit\_ROOT、导入目标和链接库，并在 cu\-bridge 环境验证 CMake 配置。
  - 涉及文件：`CMakeLists.txt`
- [ ] `MXR-LIBRARY-001` 识别 cuBLAS / cuDNN / cuFFT / cuSPARSE / cuSOLVER 头文件：请复核实际使用的库 API 与链接配置，并结合 cu\-bridge 当前版本在沐曦环境验证编译与数值行为。
  - 涉及文件：`csrc/compat.cuh`
- [ ] `MXR-INTRINSIC-001` 检测 CUDA warp 同步内建函数：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
  - 涉及文件：`csrc/gemm_4bit_simt.cu`、`csrc/gemm_4bit_sm75.cu`、`csrc/gemm_4bit_sm80.cu`
- [ ] `MXR-KERNEL-001` 检测 \_\_launch\_bounds\_\_ 调优假设：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
  - 涉及文件：`csrc/gemm_4bit_simt.cu`、`csrc/gemm_4bit_sm75.cu`、`csrc/gemm_4bit_sm80.cu`、`csrc/kernels.cu`
- [ ] `MXR-DEPENDENCY-002` 检测 bitsandbytes 依赖：请复核依赖版本、预编译包来源和算子覆盖，并在沐曦环境验证导入与核心功能。
  - 涉及文件：`pyproject.toml`

## 分析警告

- `PATH_CONTEXT_DEMOTION`：测试/夹具路径上的 MXR\-TEST\-001（1 个文件） 已封顶为提示，不参与静态状态判定；文件仍被扫描，结论可逐条复核。

## 说明

静态扫描不能替代真实沐曦 GPU 上的构建、功能和性能验证，也不能作为项目安全性或完整兼容性的证明。
