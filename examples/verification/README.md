# MetaX 真机验证交接

本目录目前只有为 `pytorch/extension-cpp` 生成的安全默认验证 ZIP。真实结果文件尚不存在；只有在授权的沐曦服务器上运行、人工脱敏并核对提交后，才应新增 `metax-verification-redacted.json`。

## 1. 核对环境

请向服务器提供方确认：

- GPU 型号；
- 驱动、MXMACA、cu-bridge 与 PyTorch 的精确版本；
- 当前 PyTorch 是否按该 MXMACA 版本提供；
- 是否允许在临时目录编译一个小型 PyTorch C++/CUDA 扩展。

不要在未知来源的生产主机上运行验证包。

## 2. 获取固定源码

在远程服务器的临时工作目录执行：

```bash
git init extension-cpp
cd extension-cpp
git remote add origin https://github.com/pytorch/extension-cpp.git
git fetch --depth 1 origin 1c325b202ae5e11de3cefb9a65be28f47949edd4
git checkout --detach FETCH_HEAD
git rev-parse HEAD
```

最后一条必须输出：

```text
1c325b202ae5e11de3cefb9a65be28f47949edd4
```

若服务器不能联网，应在本地从同一提交制作源码包并通过受控方式上传。

## 3. 解压并先做只读检查

把 `pytorch-extension-cpp-verification.zip` 上传到源码目录的上一级，然后在仓库根目录解压：

```bash
python -m zipfile -e ../pytorch-extension-cpp-verification.zip .
cat SECURITY.md
python -m mxready_runner inspect --manifest mxready.yml --output inspect.json
```

打开 `inspect.json`，确认 `mx-smi` 和 `pytorch-device` 均为 `passed`。任意检查失败或不可用时先停止，保存脱敏后的错误信息，不要硬改结果。

## 4. 手工构建项目

runner 故意禁止包管理器，因此构建必须在 runner 外由操作者明确执行：

```bash
python -m pip install --no-build-isolation -e ./extension_cpp
```

这一步应使用服务器提供方认可的 MXMACA/cu-bridge/PyTorch 环境。不要使用 `sudo`，不要更换系统驱动。

## 5. 审阅并加入单卡 smoke command

打开 `mxready.yml`，把空的 `project_commands` 替换为：

```json
"project_commands": [
  {
    "id": "extension-cpp-cuda-smoke",
    "command": [
      "python",
      "-c",
      "import torch, extension_cpp; a=torch.randn(1024, device='cuda'); b=torch.randn(1024, device='cuda'); actual=extension_cpp.ops.mymuladd(a, b, 1.0); torch.testing.assert_close(actual, a * b + 1.0); print('MXReady extension_cpp CUDA smoke passed')"
    ],
    "timeout_seconds": 120
  }
]
```

确认代码只创建两个小张量、调用一个已构建算子并比较结果，不下载数据、不修改驱动。

## 6. 运行并人工确认

```bash
python -m mxready_runner run --manifest mxready.yml --output result.json
```

runner 会列出项目命令。再次核对后输入精确的 `yes`。成功标准：

- 所有环境检查为 `passed`；
- `extension-cpp-cuda-smoke` 为 `passed`；
- `overall_status` 为 `passed`；
- `repository_commit` 与上面的 40 位提交完全一致。

## 7. 脱敏后带回

人工检查 `result.json` 中的：

- 主机名、用户名和绝对 home 路径；
- 内网 IP、代理地址和镜像仓库地址；
- token、password、secret、key、authorization；
- 与验证无关的环境变量或内部资产信息。

只将脱敏后的副本保存为：

```text
examples/verification/metax-verification-redacted.json
```

然后在 MXReady 报告页上传该副本。不要修改提交号、状态或失败结果来制造 `verified`。

## 8. 脚本化辅助（可选，只读）

交接目录提供三个只读辅助脚本，与第 2/3/7 步一一对应；它们不修改驱动、不安装软件、不触碰验证结果：

| 步骤 | 脚本 | 作用 |
| --- | --- | --- |
| 2 | `checkout-commit.sh` | 锁定提交并校验 `rev-parse HEAD` 与期望提交一致，不一致即退出 |
| 3 | `run-inspect.sh` | 自动解压验证包、展示 `SECURITY.md`、运行 inspect 并输出检查摘要 |
| 7 | `pre-upload-check.sh` | 扫描 `result.json` 中的 home 路径、内网地址、敏感键与主机名残留 |

上传到服务器后先执行 `chmod +x checkout-commit.sh run-inspect.sh pre-upload-check.sh`，再按需运行。脚本默认值对应 `pytorch/extension-cpp` 与固定提交 `1c325b202ae5e11de3cefb9a65be28f47949edd4`，可通过 `MXREADY_REPO` / `MXREADY_COMMIT` 环境变量调整。

> 跨平台注意：本仓库在 GitHub Actions 中对三个脚本执行 `bash -n` 语法检查（job `server-handover-scripts`）。Windows 本机生成的脚本若报 "bad interpreter"，请用 `dos2unix` 或 `sed -i 's/\r$//'` 去除 CRLF 后再在服务器运行。


