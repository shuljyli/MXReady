# 远程验证 runner

MXReady Web 服务不接触 GPU，也不执行被扫描项目。它生成一个自包含 ZIP，供用户下载到自己控制的沐曦服务器上审阅和运行。

## ZIP 内容

```text
mxready.yml
SECURITY.md
project-commands.example.json
mxready_runner/
schemas/verification-result-v1.json
```

`mxready.yml` 使用 JSON 语法，因此既是合法 YAML，也能由 Python 标准库 `json` 读取。它固定包含扫描 ID、仓库 URL、40 位提交、runner 版本、环境检查和可选项目命令。`project-commands.example.json` 是项目命令的参考模板，默认清单不含项目命令；需要项目验证时，把模板中的占位内容替换为实际 smoke 命令后填入 `mxready.yml` 的 `project_commands`（见 [examples/verification/README.md](../examples/verification/README.md) 第 5 步）。

runner 只要求 Python 3.11+，不依赖 PyYAML、Pydantic 或其他第三方包。

## `inspect` 与 `run`

解压后先阅读 `SECURITY.md` 和 `mxready.yml`，再执行环境检查：

```bash
python -m mxready_runner inspect \
  --manifest mxready.yml \
  --output result.json
```

`inspect` 只运行清单里的固定环境检查，不运行 `project_commands`。当前生成包检查：

- `uname -a`
- `python --version`
- `mx-smi --version`
- `mx-smi`
- PyTorch 版本、`torch.cuda.is_available()`、设备数量与首设备名称

所有配置的环境检查都会运行并写入结果；任意一项 `failed` 或 `unavailable` 都会使最终状态为 `failed`。PyTorch 检查只有在 `torch.cuda.is_available()` 为真且至少发现一个设备时才通过。`pytorch-device` 会额外输出首设备名称，用于与 `mx-smi` 输出的 GPU 型号人工交叉核对：确认 `torch.cuda` 指向的是同一块沐曦设备，而不是混卡环境中的其他设备或误装的 NVIDIA 版 PyTorch。

如清单经过人工补充并包含项目命令，可使用：

```bash
python -m mxready_runner run \
  --manifest mxready.yml \
  --output result.json
```

`run` 会先列出项目命令，只有交互输入精确的 `yes` 才会执行。Web 生成的 MVP 清单默认不包含项目命令，因此成功结果证明的是相同提交所对应验证包的沐曦环境检查，不是完整项目功能或性能认证。

## 命令安全

清单只接受参数数组，不接受 shell 字符串。runner 会拒绝：

- 空命令；
- `sudo`；
- 常见包管理器或安装命令；
- 把重定向/管道/控制符作为可执行程序；
- 小于 1 秒或大于 600 秒的超时；
- 含控制字符或超长参数的命令。

执行使用 `subprocess.run(..., shell=False)`、逐命令超时和捕获输出。runner 不提升权限、不安装软件、不更改 GPU 驱动，也不主动联网或上传结果。

## `result.json`

结果契约为 `schema_version: "1.0"`，包含：

- 扫描 ID 与仓库提交；
- runner 版本；
- 环境指纹；
- 每项环境检查和项目命令的状态、返回码、耗时、stdout/stderr；
- UTC 开始/结束时间；
- `passed`、`failed` 或 `cancelled` 总状态。

每个 stdout/stderr 最多 16 KiB。输出会对常见 `TOKEN`、`PASSWORD`、`SECRET`、`KEY`、`AUTHORIZATION` 赋值及主目录用户名做脱敏，但自动脱敏不可能覆盖所有敏感格式。

## 上传前检查

1. 确认 `scan_id` 和 `repository_commit` 对应当前报告；
2. 人工打开 `result.json`，删除或遮盖仍可能敏感的信息；
3. 确认文件不超过 1 MiB；
4. 通过报告页上传 `.json` 文件。

服务端会严格拒绝未知字段、错误类型、重复 ID、矛盾状态、不同提交、不同扫描 ID 和过大的文件。只有 `mx-smi` 与 `pytorch-device` 两项都通过的成功结果才能标记为 `verified`；成功结果超过 30 天会标记为 `stale`。

## 常见退出码

| 命令结果 | 退出码 |
| --- | ---: |
| 全部通过 | 0 |
| 有命令失败 | 1 |
| 用户取消或清单/文件错误 | 2 |

一个固定到真实公开提交、但尚未执行真机验证的完整示例见 [`examples/verification/README.md`](../examples/verification/README.md)。
