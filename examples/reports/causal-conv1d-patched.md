# MXReady 适配体检报告：causal\-conv1d

## 扫描元数据

| 字段 | 值 |
| --- | --- |
| 仓库 | https://github\.com/Dao\-AILab/causal\-conv1d |
| 提交 | `cd81f0413cad2fc1e6f17e785ac39f59aae690cd` |
| MXReady 版本 | 0\.3\.1 |
| 规则集版本 | 4 |
| 规则集摘要 | sha256:badf12ad29ce6f7cff9e6f07b4df4034822fbe9773571cad6517d9c65325c531 |
| 扩展规则版本 | 无 |
| 分析配置 | \{'max\_findings': 10000, 'rule\_timeout\_seconds': 30, 'index\_max\_files': 10000, 'index\_max\_file\_bytes': 1048576, 'prefilter': 'on'\} |
| 扫描时间 | 2026\-11\-05T07:15:01\.957272\+00:00 |
| 静态状态 | `warnings` |
| 硬件验证状态 | `not-run` |

## 结果摘要

| 阻塞项 | 警告 | 提示 | 总计 |
| ---: | ---: | ---: | ---: |
| 0 | 5 | 4 | 9 |

## 扫描范围

分析文件：26；字节：198965；排除目录：1（未遍历内容）。
文件类型：\{'\.cpp': 1, '\.cu': 3, '\.h': 3, '\.md': 1, '\.py': 7, '\.sh': 4, '\.toml': 1, '\.yaml': 1, '\.yml': 5\}
跳过原因：\{'UNSUPPORTED\_FILE\_TYPE': 5\}

仅表示支持的文件类型与限制内的扫描范围，不是完整仓库覆盖率。

## 阻塞项

无。

## 警告

### `MXR-PATH-001` — 检测硬编码 CUDA 安装路径

- 位置：`.github/scripts/build.sh`，第 10–11 行
- 分类：`path`
- 说明：项目硬编码了 /usr/local/cuda，可能绕过 MXMACA/cu\-bridge 提供的工具链路径。
- 建议：请将路径改为可配置项，复核 cu\-bridge 环境变量，并在沐曦服务器验证解析结果。
- 证据：

- 第 10–10 行

    export PATH=/usr/local/cuda/bin:/usr/local/nvidia/bin:/usr/local/nvidia/lib64:$PATH

- 第 11–11 行

    export LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/cuda/lib64:$LD_LIBRARY_PATH


- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`csrc/causal_conv1d_bwd.cu`，第 54–330 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

- 第 54–54 行

    __global__ __launch_bounds__(Ktraits::kNThreads)

- 第 330–330 行

    __global__ __launch_bounds__(Ktraits::kNThreads)


- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-INTRINSIC-001` — 检测 CUDA warp 同步内建函数

- 位置：`csrc/causal_conv1d_common.h`，第 12–12 行
- 分类：`intrinsic`
- 说明：内核使用 warp 同步内建函数，其掩码、warp 宽度和硬件执行假设需要复核。
- 建议：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
- 证据：

- 第 12–12 行

    return __shfl_xor_sync(uint32_t(-1), val, offset);


- 参考：
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`csrc/causal_conv1d_fwd.cu`，第 47–206 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

- 第 47–47 行

    __global__ __launch_bounds__(Ktraits::kNThreads)

- 第 206–206 行

    __global__ __launch_bounds__(Ktraits::kNThreads)


- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


### `MXR-KERNEL-001` — 检测 \_\_launch\_bounds\_\_ 调优假设

- 位置：`csrc/causal_conv1d_update.cu`，第 24–24 行
- 分类：`kernel`
- 说明：内核使用 \_\_launch\_bounds\_\_ 固化线程和寄存器调优假设，目标架构的最佳配置可能不同。
- 建议：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
- 证据：

- 第 24–24 行

    __global__ __launch_bounds__(Ktraits::kNThreads)


- 参考：
  - [MXMACA performance tuning guide](https://gitee.com/metax-maca/mxmaca-performance-tuning-guide)
  - [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/)


## 提示

### `MXR-TEST-001` — 检测 CUDA 可用性静默跳过测试

- 位置：`tests/test_causal_conv1d.py`，第 714–750 行
- 分类：`test`
- 说明：测试在 torch\.cuda 不可用时静默跳过，迁移到沐曦环境后可能因环境未配置而跳过，造成验证通过的假象。（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的迁移风险，已从 warning 降为提示；若该夹具描述的正是交付行为，请另行复核。）
- 建议：请复核跳过条件，并在真机环境手动运行核心 CUDA 测试以确认实际覆盖。
- 证据：

- 第 714–714 行

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")

- 第 732–732 行

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")

- 第 750–750 行

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")


- 参考：
  - [pytest skipif documentation](https://docs.pytest.org/)
  - [unittest skipUnless documentation](https://docs.python.org/3/library/unittest.html)


### `MXR-CUB-001` — 识别 CUB 用法

- 位置：`csrc/causal_conv1d_bwd.cu`，第 10–323 行
- 分类：`library`
- 说明：项目使用 CUB；MXMACA 提供 mcCUB 且对外 API 接口不变，通常无需改动源码。
- 建议：请复核 CUB 版本与 mcCUB 的对应关系，并在沐曦环境验证编译与结果。
- 证据：

- 第 10–10 行

    #include &lt;cub/block/block_load.cuh&gt;

- 第 11–11 行

    #include &lt;cub/block/block_store.cuh&gt;

- 第 12–12 行

    #include &lt;cub/block/block_reduce.cuh&gt;

- 第 40–40 行

    using BlockLoadT = cub::BlockLoad&lt;input_t, kNThreads, kNElts, cub::BLOCK_LOAD_WARP_TRANSPOSE&gt;;

- 第 40–40 行

    using BlockLoadT = cub::BlockLoad&lt;input_t, kNThreads, kNElts, cub::BLOCK_LOAD_WARP_TRANSPOSE&gt;;

- 第 41–41 行

    using BlockLoadVecT = cub::BlockLoad&lt;vec_t, kNThreads, 1, cub::BLOCK_LOAD_DIRECT&gt;;

- 第 41–41 行

    using BlockLoadVecT = cub::BlockLoad&lt;vec_t, kNThreads, 1, cub::BLOCK_LOAD_DIRECT&gt;;

- 第 42–42 行

    using BlockStoreT = cub::BlockStore&lt;input_t, kNThreads, kNElts, cub::BLOCK_STORE_WARP_TRANSPOSE&gt;;

- 第 42–42 行

    using BlockStoreT = cub::BlockStore&lt;input_t, kNThreads, kNElts, cub::BLOCK_STORE_WARP_TRANSPOSE&gt;;

- 第 43–43 行

    using BlockStoreVecT = cub::BlockStore&lt;vec_t, kNThreads, 1, cub::BLOCK_STORE_DIRECT&gt;;

- 第 43–43 行

    using BlockStoreVecT = cub::BlockStore&lt;vec_t, kNThreads, 1, cub::BLOCK_STORE_DIRECT&gt;;

- 第 44–44 行

    using BlockReduceFloatT = cub::BlockReduce&lt;float, kNThreads&gt;;

- 第 322–322 行

    // using BlockLoadT = cub::BlockLoad&lt;input_t, kNThreads, kNItems, cub::BLOCK_LOAD_WARP_TRANSPOSE&gt;;

- 第 322–322 行

    // using BlockLoadT = cub::BlockLoad&lt;input_t, kNThreads, kNItems, cub::BLOCK_LOAD_WARP_TRANSPOSE&gt;;

- 第 323–323 行

    // using BlockStoreT = cub::BlockStore&lt;input_t, kNThreads, kNItems, cub::BLOCK_STORE_WARP_TRANSPOSE&gt;;

- 第 323–323 行

    // using BlockStoreT = cub::BlockStore&lt;input_t, kNThreads, kNItems, cub::BLOCK_STORE_WARP_TRANSPOSE&gt;;


- 参考：
  - [MXMACA AI training manual](https://developer.metax-tech.com/api/client/document/preview/587/C500_AITrainningMaunal_CN.html)


### `MXR-CUB-001` — 识别 CUB 用法

- 位置：`csrc/causal_conv1d_fwd.cu`，第 10–199 行
- 分类：`library`
- 说明：项目使用 CUB；MXMACA 提供 mcCUB 且对外 API 接口不变，通常无需改动源码。
- 建议：请复核 CUB 版本与 mcCUB 的对应关系，并在沐曦环境验证编译与结果。
- 证据：

- 第 10–10 行

    #include &lt;cub/block/block_load.cuh&gt;

- 第 11–11 行

    #include &lt;cub/block/block_store.cuh&gt;

- 第 35–35 行

    using BlockLoadT = cub::BlockLoad&lt;input_t, kNThreads, kNElts, cub::BLOCK_LOAD_WARP_TRANSPOSE&gt;;

- 第 35–35 行

    using BlockLoadT = cub::BlockLoad&lt;input_t, kNThreads, kNElts, cub::BLOCK_LOAD_WARP_TRANSPOSE&gt;;

- 第 36–36 行

    using BlockLoadVecT = cub::BlockLoad&lt;vec_t, kNThreads, 1, cub::BLOCK_LOAD_DIRECT&gt;;

- 第 36–36 行

    using BlockLoadVecT = cub::BlockLoad&lt;vec_t, kNThreads, 1, cub::BLOCK_LOAD_DIRECT&gt;;

- 第 37–37 行

    using BlockStoreT = cub::BlockStore&lt;input_t, kNThreads, kNElts, cub::BLOCK_STORE_WARP_TRANSPOSE&gt;;

- 第 37–37 行

    using BlockStoreT = cub::BlockStore&lt;input_t, kNThreads, kNElts, cub::BLOCK_STORE_WARP_TRANSPOSE&gt;;

- 第 38–38 行

    using BlockStoreVecT = cub::BlockStore&lt;vec_t, kNThreads, 1, cub::BLOCK_STORE_DIRECT&gt;;

- 第 38–38 行

    using BlockStoreVecT = cub::BlockStore&lt;vec_t, kNThreads, 1, cub::BLOCK_STORE_DIRECT&gt;;

- 第 198–198 行

    // using BlockLoadT = cub::BlockLoad&lt;input_t, kNThreads, kNItems, cub::BLOCK_LOAD_WARP_TRANSPOSE&gt;;

- 第 198–198 行

    // using BlockLoadT = cub::BlockLoad&lt;input_t, kNThreads, kNItems, cub::BLOCK_LOAD_WARP_TRANSPOSE&gt;;

- 第 199–199 行

    // using BlockStoreT = cub::BlockStore&lt;input_t, kNThreads, kNItems, cub::BLOCK_STORE_WARP_TRANSPOSE&gt;;

- 第 199–199 行

    // using BlockStoreT = cub::BlockStore&lt;input_t, kNThreads, kNItems, cub::BLOCK_STORE_WARP_TRANSPOSE&gt;;


- 参考：
  - [MXMACA AI training manual](https://developer.metax-tech.com/api/client/document/preview/587/C500_AITrainningMaunal_CN.html)


### `MXR-PYTORCH-001` — 识别 PyTorch CUDAExtension

- 位置：`setup.py`，第 219–219 行
- 分类：`pytorch\-extension`
- 说明：项目通过 PyTorch CUDAExtension 构建原生扩展，需要准备与目标工具链匹配的编译环境。
- 建议：请复核扩展源文件、编译参数与依赖库，并在 MXMACA PyTorch 环境完成最小构建验证。
- 证据：

- 第 219–219 行

    CUDAExtension(


- 参考：
  - [PyTorch C\+\+/CUDA extensions](https://docs.pytorch.org/docs/stable/cpp_extension.html)


## 迁移清单

- [ ] `MXR-PATH-001` 检测硬编码 CUDA 安装路径：请将路径改为可配置项，复核 cu\-bridge 环境变量，并在沐曦服务器验证解析结果。
  - 涉及文件：`.github/scripts/build.sh`
- [ ] `MXR-KERNEL-001` 检测 \_\_launch\_bounds\_\_ 调优假设：请复核线程块和资源约束，并依据 MXMACA 性能指南在沐曦设备重新验证调优参数。
  - 涉及文件：`csrc/causal_conv1d_bwd.cu`、`csrc/causal_conv1d_fwd.cu`、`csrc/causal_conv1d_update.cu`
- [ ] `MXR-INTRINSIC-001` 检测 CUDA warp 同步内建函数：请复核内建函数语义与 warp 假设，并依据性能指南在沐曦设备验证正确性和性能。
  - 涉及文件：`csrc/causal_conv1d_common.h`

## 分析警告

- `PATH_CONTEXT_DEMOTION`：测试/夹具路径上的 MXR\-TEST\-001（1 个文件） 已封顶为提示，不参与静态状态判定；文件仍被扫描，结论可逐条复核。

## 说明

静态扫描不能替代真实沐曦 GPU 上的构建、功能和性能验证，也不能作为项目安全性或完整兼容性的证明。
