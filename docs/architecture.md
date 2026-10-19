# MXReady 架构与目录约定

MXReady 使用模块化单体，扫描服务只做静态分析；标准库 runner 在用户控制的主机执行审阅后的命令。

```text
src/
  mxready/
    api/             HTTP 契约、路由和请求防护
    cli/             三个扫描、报告与验证包命令入口
    services/        扫描编排、心跳和 SQLite 队列消费者
    persistence/     SQLite 适配器、顺序迁移和租约原子操作
    repository/      URL/ref 校验、受限 Git 与归档获取
    scanning/        文件索引、事实提取、规则加载与评估
    reporting/       Markdown 与 SVG 输出
    verification/    验证结果校验与自包含 ZIP
    resources/
      rules/v1/      随 wheel/sdist 发布的默认规则
      schemas/       生成的版本化验证结果 schema
    app.py           应用组合与生命周期
    config.py        环境变量配置
    models.py        后端领域模型和对外契约
  mxready_runner/
    contracts.py     环境检查约定，供后端和 runner 共用
    process.py       参数数组执行、采集上限与超时处理
    schema.py        标准库清单校验与结果对象
frontend/src/
  api/               HTTP 客户端与生成的响应类型
  hooks/             扫描状态、恢复与轮询生命周期
  components/        展示与表单组件
scripts/             开发运维入口、契约生成工具
tests/
  backend/           后端单元与接口回归
  runner/            标准库 runner 与进程边界回归
  integration/       sdist/wheel 和离开源码目录后的冒烟
  fixtures/          受控测试输入
  load/              本地 mock Git 压测
docs/                开发与部署文档
examples/            固定提交的证据与真机交接材料
```

## 依赖方向

API 和 CLI 调用应用服务或分析器；扫描器依赖领域模型，不依赖 HTTP。
应用服务负责工作流，通过 SQLite 适配器保存状态。runner 不导入 Web 包，也不依赖 Pydantic、
FastAPI 或 PyYAML。后端读取 runner 的 `contracts.py` 和包资源来构建可离线运行的 ZIP。

命令实现从 `scripts.*` 移入 `mxready.cli.*`，对外的 `mxready-scan`、
`mxready-scan-public`、`mxready-build-bundle`、`mxready-runner` 名称保持一致。
直接导入旧 `mxready.storage` 的内部代码应改为 `mxready.persistence.sqlite`。

## 扫描任务生命周期

提交接口只在 SQLite 中创建 `queued` 记录并返回 202。每个 API 进程拥有固定数量的消费者线程，
消费者读取队列并用条件 UPDATE 原子领取任务，写入随机执行令牌和租约，随后开始受限 Git 获取。
心跳每隔租约时长的三分之一续租。阶段更新、报告写入和失败写入均校验令牌及未过期租约。

启动进程不再清空活跃任务。消费者定期把租约过期的执行标为 `SCAN_INTERRUPTED`，要求用户重新扫描；
未领取的队列任务继续执行。历史数据库中的无租约执行也按中断处理。失去租约的执行不能再覆盖状态。
正常退出会等待当前任务和心跳结束；异常退出后的临时目录可能残留，运维清理必须避开活跃任务。

这是单机、共享本地 SQLite 数据库的持久队列，没有独立进程的 CPU/内存隔离。
多个 API 进程必须使用相同本地数据库、规则与配置；不要通过网络文件系统跨主机共享 SQLite。
`MAX_CONCURRENT_SCANS` 限制排队与执行中的总准入数量，`SCAN_WORKER_THREADS` 控制每进程消费者数量。
进程内 IP 限流仍按进程计数，多进程部署应在代理层设置统一限流。

## 报告、契约与资源

验证记录保存原始执行时间，读取报告时推导当前 `verified` / `stale` 状态；不会改写历史结果。
原先下载到本地的文件不会自动变化，需要重新下载。静态状态仍与硬件验证状态分开。

报告记录完整合并规则的 SHA-256、扩展规则版本和分析参数。旧报告缺少这些可选字段时仍可读取。
规则引擎限制唯一命中数，并在模式、文件和命中边界检查时间预算；时间预算不保证中断单次阻塞的正则调用。
文件索引保存行偏移，命中行号通过二分定位。

修改模型后运行 `make contracts` 或 `.\scripts\make.ps1 contracts`，同步生成 TypeScript 响应类型和
验证结果 JSON Schema；CI 执行 `python scripts/generate_contracts.py --check`。
JSON Schema 描述结构约束，状态一致性、提交绑定、必需硬件检查和有效期仍由后端语义校验负责。

默认规则与 schema 通过包资源读取，工作目录不影响默认规则选择。显式设置 `MXREADY_RULES_DIR`
仍可覆盖默认目录。前端静态文件通过 `MXREADY_FRONTEND_DIR` 部署，未提供时为 API-only 模式。
