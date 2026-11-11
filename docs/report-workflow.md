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

## 人工复核与整改示例

报告的“人工复核与误报反馈”按扫描 ID、规则和文件定位发现，每次保存追加一条记录，
支持确认、误报、暂缓，必须填写判断依据。记录分页读取并保留历史，不修改 finding、
静态结论、硬件结论或 CI 判断。服务实例内共享数据，目前无个人身份认证，不将记录
伪装成特定维护者签名。报告重新扫描后不自动继承复核结果，避免跨提交沿用错误判断。
接口：`GET/POST /api/scans/{scan_id}/reviews`；GET 必填 rule_id、relative_path，
默认每页 20 条、上限 50；POST 只允许报告中实际存在的发现，reason 上限 1000 字符。
可在人工确认误报后，把最小复现和相似反例补入规则回归集；反馈不会自动训练或修改规则。

每个发现提供所属类别的修改前后示例、适用条件与验证命令。它们不是对当前源码生成的
补丁，不能直接套用到不匹配的命中；内核和原语迁移需按目标工具链逐项分析。
示例命令仅供用户审阅后在受控环境执行，Web 不执行这些命令。

## 批量工作区

导航中的“批量扫描”支持每行 URL 加可选 ref，每批 1–10 项，逐项调用现有受限扫描队列。
批量记录保存在当前标签页 sessionStorage 中，刷新可恢复；关闭标签页或禁用存储后
仍可到服务端扫描历史找回已创建的任务。不是服务器端的跨设备批次管理。
每 5 秒顺序查询进度，连续 3 次查询失败后暂停该项，需手动恢复查询。
提交超时或服务器错误可能已经创建任务，界面不自动重提，应先核对扫描历史。
只有明确失败的提交或扫描可直接新建重试；旧任务保留，汇总 JSON 记录当前批次状态。

## 基线 CI 策略

```sh
mxready-scan /path/to/source --repo-url https://github.com/owner/project \
  --commit <实际完整提交> --output /path/to/reports \
  --baseline /path/to/trusted-baseline.json --fail-on new-blockers
```

默认仍是 all-blockers。new-blockers 比较同仓库的规则/文件组，仅新增 blocker、
由非 blocker 升级、或现有 blocker 次数增加时退出 2；原有 blocker 仍写入完整报告，
报告可能继续为 blocked，CI 策略通过不意味着项目兼容。
同一组中次数相同的证据替换不作为新增，文件重命名则视为新增；这不是逐字符差异分析。
缺基线、超过 20 MiB、非法 JSON、不同仓库、缺少规则摘要或分析配置/规则/工具条件不同
均退出 1，不能静默忽略。使用方应固定扫描器版本，不能以人工标注覆盖基线政策。

本地 `mxready-scan` 在分析前有界读取并校验基线参数，比较条件通过校验后才写当前报告。
基线与输出目录中的默认 JSON 同名时仍保留原文件；任一导出文件已存在，新的 JSON、Markdown、
SVG、SARIF 统一追加本次扫描 ID（不含连字符）。每次执行具有独立 ID，终端打印实际文件名。
基线缺失、内容无效、参数不配套或分析条件不一致时退出 1，不生成当前报告。

CI 模板可设置 `MXREADY_BASELINE_RUN` 为同仓库已审核历史运行的 ID，从其
`mxready-reports` artifact 下载唯一 JSON。未设置时仍检查全部 blocker；下载失败、
artifact 过期或存在多份 JSON 会失败。不要接受 PR 作者提供或修改的基线来批准该 PR。

## 真机验证与依赖

[真机样板](../examples/hardware/README.md) 分开记录构建、功能与性能。当前无沐曦设备，
交付模板和探针，没有真机通过结论。探针只覆盖选定算子及尺寸，不能代替完整项目测试。

开发依赖更新至 Vite 7.3.7、Vitest 4.1.12，并更新 source-map-js；本次安装后的
`npm audit` 为 0 条告警。这是当前锁文件和审计数据库的检查结果，不是长期无漏洞保证。
