# MXReady 种子计划申报证据

本页记录可复现的本地成果、人工复核结论，以及仍需真实沐曦 GPU 才能完成的验收项。它不是沐曦官方兼容性声明。

## 当前结论

截至 2026-07-29，MXReady 已用同一版 20 条规则扫描三个公开 CUDA 扩展项目，并将报告固定到 40 位 Git 提交。`pytorch/extension-cpp` 是首个真机候选：源码小、没有静态 blocker、不下载模型权重，适合在一张远程 GPU 上完成最小构建和算子正确性验证。

真实硬件验证仍为 **pending**。仓库中没有 `metax-verification-redacted.json`，因为目前没有可证明来源的沐曦服务器结果。

## 三个公开项目

| 项目 | 固定提交 | 静态状态 | blocker | warning | info |
| --- | --- | --- | ---: | ---: | ---: |
| [pytorch/extension-cpp](https://github.com/pytorch/extension-cpp) | `1c325b202ae5e11de3cefb9a65be28f47949edd4` | `passed` | 0 | 0 | 4 |
| [NVIDIA/apex](https://github.com/NVIDIA/apex) | `6424da3b4faa6c8f062da4a48c424fff3f02d42d` | `blocked` | 1 | 78 | 64 |
| [Dao-AILab/flash-attention](https://github.com/Dao-AILab/flash-attention) | `c75d019dea9d910312974417bc28f190dfdda6d9` | `blocked` | 5 | 124 | 10 |

报告位于 [`examples/reports`](../examples/reports)。发现数是规则命中的源码位置数，不是兼容概率，也不代表同等数量的独立缺陷。

### 复现命令

先安装项目：

```bash
python -m pip install -e ".[dev]"
```

再从仓库根目录运行：

```bash
mxready-scan-public https://github.com/pytorch/extension-cpp --ref 1c325b202ae5e11de3cefb9a65be28f47949edd4 --label pytorch-extension-cpp --output examples/reports --work-dir data/public-scan-work

mxready-scan-public https://github.com/NVIDIA/apex --ref 6424da3b4faa6c8f062da4a48c424fff3f02d42d --label apex --output examples/reports --work-dir data/public-scan-work

mxready-scan-public https://github.com/Dao-AILab/flash-attention --ref c75d019dea9d910312974417bc28f190dfdda6d9 --label flash-attention --output examples/reports --work-dir data/public-scan-work
```

命令优先使用受限浅克隆。GitHub 的 Git 传输超时或内部失败时，证据命令才使用 GitHub API 与 codeload 的提交锁定归档后备路径。API 元数据请求和归档下载各自具有 60 秒总时限；压缩下载与展开内容受 50 MiB 限制；目录、符号链接和普通文件都计入 10,000 条归档成员上限。

## blocker 人工复核

所有 blocker 已逐条查看证据：

- Apex 的 1 条 blocker 是 `setup.py` 直接运行 `$CUDA_HOME/bin/nvcc -V`，属于真实工具链迁移点。
- FlashAttention 的 4 条 blocker 是不同构建入口直接运行 `$CUDA_HOME/bin/nvcc -V`。
- FlashAttention 的另 1 条 blocker 把编译器固定为 `_join_cuda_home("bin", "nvcc")`，同样需要在目标工具链复核。

初次扫描还把 `nvcc = _join_rocm_home("bin", "hipcc")` 错判成命令调用。该误报已通过“相似反例先失败”的测试收紧，重新扫描后 blocker 从 6 降为 5；真正的 `nvcc` 固定入口仍保留。

## 真机候选与验证包

选择 `pytorch/extension-cpp` 的原因：

- 没有未解决的静态 blocker；
- 仅包含小型 C++/CUDA 自定义算子；
- 不依赖模型权重或数据集；
- 一张 GPU 即可运行；
- 可以用一个约 120 秒的 CUDA `mymuladd` smoke command 验证构建产物。

验证包：

- 文件：[`examples/verification/pytorch-extension-cpp-verification.zip`](../examples/verification/pytorch-extension-cpp-verification.zip)
- 固定提交：`1c325b202ae5e11de3cefb9a65be28f47949edd4`
- 大小：9,671 字节
- SHA-256：`078df24e33bf41bc9f8ff396ea32e2dc6af4376ccbb0d20e4c481b5214c51bd1`
- 默认 `project_commands`：空；必须人工审阅后添加

生成命令：

```bash
mxready-build-bundle examples/reports/pytorch-extension-cpp.json \
  --output examples/verification/pytorch-extension-cpp-verification.zip
```

完整服务器步骤、清单片段和脱敏要求见 [`examples/verification/README.md`](../examples/verification/README.md)。

## 远程算力申请清单

建议申请一次 2 小时窗口，实际 GPU 占用目标不超过 30 分钟：

- 1 张可用的沐曦 GPU；
- 官方建议的 MXMACA、cu-bridge 与 PyTorch 组合；
- Python 3.11+、Git、C/C++ 构建工具和允许编译 PyTorch 扩展的环境；
- 至少 10 GiB 临时磁盘；
- 告知 GPU 型号、驱动/MXMACA/cu-bridge/PyTorch 版本；
- 若服务器禁止公网，提前上传固定提交源码包和验证 ZIP；
- 允许带走经过人工脱敏的 `result.json`，不带走主机名、用户名、令牌或内部地址。

验收目标：

1. `mx-smi` 与 PyTorch 设备检查通过；
2. `extension_cpp` 在指定 MXMACA 环境构建成功；
3. CUDA `mymuladd` 与 PyTorch 参考结果一致；
4. 结果绑定同一提交并在上传前完成脱敏；
5. 失败也保留可公开的最小日志和迁移清单。

## 上游补丁候选

已针对 Apex 固定提交 `6424da3b4faa6c8f062da4a48c424fff3f02d42d` 编写 [`apex-configurable-nvcc.patch`](../examples/patches/apex-configurable-nvcc.patch)。补丁让工具链版本探测支持通过 `APEX_NVCC` 指定兼容编译器，同时保持 `$CUDA_HOME/bin/nvcc` 为默认路径。

本地复核结果：

- 3 个新增单元测试通过；
- 两个新增 Python 文件通过 Ruff，4 个改动 Python 文件通过无缓存语法编译；
- `git diff --check` 与 `git apply --check --cached` 通过；
- 同一源码的 MXReady 结果从 1 blocker / 78 warnings / 64 info 变为 0 blockers / 78 warnings / 64 info。

补丁完整复现步骤见 [`examples/patches/README.md`](../examples/patches/README.md)。其状态为 **authored / locally tested / not submitted**，只处理硬编码编译器探测，不声称 Apex 已兼容沐曦 GPU。

拟议 PR 标题（未提交）：

> Allow overriding the CUDA compiler used for version detection

拟议 PR 正文：

```markdown
## Summary

- add an `APEX_NVCC` override for the compiler used by CUDA toolkit version detection
- preserve `$CUDA_HOME/bin/nvcc` as the default
- document the override and cover the default, explicit, and empty-value cases

## Motivation

CUDA-compatible toolchains do not always expose their compiler at
`$CUDA_HOME/bin/nvcc`. A separate executable override lets those environments
reuse Apex's existing version check without changing toolkit include or library
paths.

## Testing

- `python -m unittest discover -s tests/L0/run_build_utils -v`
- Ruff on the two new Python files
- syntax compilation of all four changed Python files

This change only makes compiler discovery configurable. It does not claim
hardware compatibility with any non-CUDA platform.
```

真机 smoke test 通过后，仍可为 `pytorch/extension-cpp` 准备一个只记录可复现环境、命令和结果的最小文档 PR。任何外部 PR 的创建或提交都需要单独授权。
