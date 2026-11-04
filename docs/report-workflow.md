# 从扫描到整改与验证

## 完整命中与扫描范围

JSON `findings[].occurrences` 保存每次命中的行号与证据，`count` 保留聚合次数。
Web 按需展开全部命中并链接到报告固定提交；Markdown 与 SARIF 同步导出这些位置。
旧报告无 occurrences 时仅显示原有聚合证据，不虚构丢失的位置。

`coverage` 记录分析文件数量、字节数、文件类型、跳过原因和排除目录数量。
目录排除后不会遍历其内部，因此不能把统计解释为整个仓库的文件覆盖率。
符号链接、非支持文件类型、二进制、超限和不可读取文件不参与分析。
无可分析文件时提供 `NO_ANALYZABLE_SOURCE` 警告；零命中不是兼容性证明。
旧报告 coverage 为 null，需重新扫描才能补齐。

## 比较整改效果

按规则 ID 与文件路径匹配聚合发现，显示新增、消失、保留以及级别/次数变化。
级别和次数变化可同时发生，两个类别不是互斥分组。
路径重命名会体现为新增/消失；证据变化不会直接视为新增发现。
规则、工具或配置发生变化时仍提示分析条件不同，不能把差异全部归于整改。

## 在实际代码版本上运行验证

把验证包放在待测仓库外，确认仓库 HEAD 为报告中的提交，然后执行：

```sh
python -m mxready_runner run --manifest /path/to/bundle/mxready.yml \
  --repo-dir /path/to/checkout --output /path/to/bundle/result.json
```

项目命令仍逐项展示并要求输入 yes。执行前后均检查实际 HEAD、仓库根目录及
Git 工作区状态（包含未跟踪文件和子模块状态）；不一致或脏工作区拒绝生成成功结果。
命令以指定仓库根目录为 cwd 执行。测试产生的文件应由项目合理配置 gitignore。
结果新增 `repository_state`，记录实际提交、工作目录与干净状态。共享前检查本机路径。
校验失败退出 2，不覆盖结果文件；请使用新的输出文件名，避免误传旧结果。
Git 检查无法防止运行期间有其他进程改动后又还原代码，不能作为可信执行证明。
`inspect` 和没有项目命令的 `run` 仅检查环境，repository_state 为 null。
旧结果仍可读取；未记录状态不代表已核对源码。

## SARIF 与 CI

Web 可下载 `/api/scans/{scan_id}/report.sarif`；`mxready-scan`、公开仓库与批量 CLI
会在报告目录同时生成 `.sarif`。采用 SARIF 2.1.0，每个命中位置一个结果，
blocker/warning/info 对应 error/warning/note，附带提交与扫描范围。
旧聚合报告只导出保留下来的位置，并标记 occurrencesComplete=false。

复制 [GitHub Actions 模板](../examples/ci/mxready.yml) 到目标仓库的工作流目录，
设置仓库变量 `MXREADY_REF` 为包含本功能且已审核的 MXReady 完整提交 SHA。
模板在目标源码目录外安装扫描器，不安装或执行待扫描项目。扫描退出 2 时先上传
报告，再令检查失败；退出 1 是扫描失败。SARIF 上传需要该仓库启用 Code scanning
及相应权限；上传受限时可下载 workflow artifact，在支持 SARIF 的工具中查看。
参见 [GitHub SARIF 上传说明](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/integrate-with-existing-tools/upload-sarif-file)。

SARIF 是静态迁移风险信息，不是漏洞认证或硬件验证。此模板需在使用方仓库实际运行
验证权限与平台接入；本地测试不会证明 GitHub 已接收报告。
