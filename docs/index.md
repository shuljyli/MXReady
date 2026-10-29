# MXReady 文档索引

> English readers: detailed documentation is currently written in Chinese, but every command and code
> sample is language-neutral. Start from [README.en.md](../README.en.md).

## 按角色选择路径

| 你想做的事 | 从这里开始 | 接着看 |
| --- | --- | --- |
| 在自己的项目上跑一次体检 | [README 快速开始](../README.md) | [示例报告](../examples/reports/pytorch-extension-cpp.md) |
| 把 MXReady 部署成常驻服务 | [部署文档](deployment.md) | [安全模型](security.md) |
| 在沐曦主机上做真机验证 | [runner 指南](runner.md) | [交接 SOP](../examples/verification/README.md) |
| 新增或修改检查规则 | [规则开发指南](rules.md) | [架构说明](architecture.md) |
| 集成 API 或写前端 | [API 手册](api.md) | [契约生成](../README.md) |
| 打发布包 / 排查安装问题 | [安装与发布方案](installation.md) | [变更记录](../CHANGELOG.md) |

## 文档清单

| 文档 | 内容 |
| --- | --- |
| [architecture.md](architecture.md) | 目录层级、依赖方向、任务生命周期、包资源约定 |
| [api.md](api.md) | HTTP API 手册，含 `curl` 示例 |
| [deployment.md](deployment.md) | 裸机 / systemd / Docker / nginx / 备份 / 日志 |
| [installation.md](installation.md) | 三平台安装包、离线准备、升级与发布构建 |
| [rules.md](rules.md) | 规则 YAML 结构、三种匹配模式、预过滤契约、正反例要求 |
| [runner.md](runner.md) | 远程验证 runner 的命令白名单、确认流程与结果格式 |
| [security.md](security.md) | 威胁模型与安全边界 |
| [frontend-redesign.md](frontend-redesign.md) | 前端设计与交互决策记录 |
| [design/](design/) | 设计稿与视觉资产 |

## 一页内的技术事实

- **规则数**：30 条（`MXR-*`），两条阻塞级、十八条警告级、十条提示级。
- **静态与硬件状态严格分离**：报告的 `static_status` 与 `verification_status` 互不推导，
  真机验证结果有 30 天有效期，过期转为 `stale`。
- **不给百分比兼容分数**：规则命中数是风险提示，不是兼容概率。
- **Web 扫描永不执行仓库代码**：只读索引 + YAML 规则，远程 runner 单独运行且需人工确认。
- **质量门**：`ruff check`、`ruff format --check`、`mypy`、契约校验、`pytest`（分支覆盖率门槛 80%）。
- **安装包不含 Python 与 Git**：ZIP 是 Python 应用安装包，不是原生 EXE / DMG / 系统包管理器包。

## 术语

| 术语 | 含义 |
| --- | --- |
| 规则（rule） | 一条 `MXR-<类别>-<三位编号>` 的 YAML 检查项 |
| 事实（fact） | 从仓库静态提取的布尔或字符串特征，供 `fact` 类规则消费 |
| 证据（evidence） | 命中位置所在的原始代码行，最多保留 240 字符 |
| 验证包（verification bundle） | 绑定扫描提交、在用户控制的沐曦主机上执行的 ZIP |
| 预过滤（prefilter） | 从正则提取"命中必然包含"的字面量，跳过不可能命中的文件；零漏报 |
