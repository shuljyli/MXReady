# MXReady 适配体检报告：extension\-cpp

## 扫描元数据

| 字段 | 值 |
| --- | --- |
| 仓库 | https://github\.com/pytorch/extension\-cpp |
| 提交 | `1c325b202ae5e11de3cefb9a65be28f47949edd4` |
| MXReady 版本 | 0\.1\.0 |
| 规则集版本 | 1 |
| 扫描时间 | 2026\-07\-29T19:12:29\.351728\+00:00 |
| 静态状态 | `passed` |
| 硬件验证状态 | `not-run` |

## 结果摘要

| 阻塞项 | 警告 | 提示 | 总计 |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 4 | 4 |

## 阻塞项

无。

## 警告

无。

## 提示

### `MXR-HEADER-002` — 识别 cuda\.h 驱动头文件

- 位置：`extension_cpp/extension_cpp/csrc/cuda/muladd.cu`，第 4–5 行
- 分类：`header`
- 说明：源码直接包含 CUDA Driver 头文件，需要核对所用 Driver API 的目标映射。
- 建议：请复核 Driver API 调用范围，并结合 cu\-bridge 文档在沐曦环境验证编译与行为。
- 证据：

    #include &lt;cuda.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`extension_cpp/extension_cpp/csrc/cuda/muladd.cu`，第 6–6 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-002` — 识别 cuda\.h 驱动头文件

- 位置：`extension_cpp_stable/extension_cpp_stable/csrc/cuda/muladd.cu`，第 9–10 行
- 分类：`header`
- 说明：源码直接包含 CUDA Driver 头文件，需要核对所用 Driver API 的目标映射。
- 建议：请复核 Driver API 调用范围，并结合 cu\-bridge 文档在沐曦环境验证编译与行为。
- 证据：

    #include &lt;cuda.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


### `MXR-HEADER-001` — 识别 cuda\_runtime\.h 头文件

- 位置：`extension_cpp_stable/extension_cpp_stable/csrc/cuda/muladd.cu`，第 11–11 行
- 分类：`header`
- 说明：源码直接包含 CUDA Runtime 头文件，需要由目标兼容层和工具链提供相应映射。
- 建议：请复核使用到的 Runtime API，并结合 cu\-bridge 当前版本在沐曦环境验证编译与功能。
- 证据：

    #include &lt;cuda_runtime.h&gt;

- 参考：
  - [MetaX\-MACA cu\-bridge](https://gitee.com/metax-maca/cu-bridge)


## 迁移清单

当前没有由阻塞项或警告生成的迁移任务。

## 分析警告

无。

## 说明

静态扫描不能替代真实沐曦 GPU 上的构建、功能和性能验证，也不能作为项目安全性或完整兼容性的证明。
