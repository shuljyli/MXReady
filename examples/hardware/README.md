# 沐曦真机验证样板：extension-cpp

当前状态：`pytorch/extension-cpp` 已完成一次脱敏真机验证，结果见
`examples/verification/metax-verification-redacted.json` 与 `extension-cpp-probe-result.json`；
`acceptance-template.json` 仍是模板字段，不得当作通过证据，不上传为 runner result.json。

1. 选择并记录 https://github.com/pytorch/extension-cpp 的完整提交，审阅源码及项目构建说明。
   在用户控制的沐曦服务器上准备该提交的干净 checkout，记录 OS、GPU、驱动、MXMACA、
   cu-bridge、Python、PyTorch 的准确版本。工具链版本必须按官方文档配套。
2. **构建**：人工执行该提交支持的构建命令（例如项目文档中的 wheel 构建），保留实际
   命令、退出码、完整日志与 wheel 摘要。安装是人工环境准备步骤，不能绕过 runner 的
   包管理器禁用规则。构建成功只填 build，不填写 functional/performance 通过。
3. **功能与计时**：先审阅 `extension_cpp_probe.py`。它针对提供
   `extension_cpp.ops.mymuladd(a, b, c)` 的项目版本；若所选版本 API 不同，先调整并记录
   probe 的文件摘要。原有测试也应执行，不能用四个浮点数值样例替代完整测试集。
4. 将验证包、probe 和输出目录置于 checkout 外，将以下参数数组作为人工审阅的
   `project_commands` 写入验证包 manifest（路径和设备名须替换）：

   ```json
   ["python", "/path/to/extension_cpp_probe.py", "--expected-device", "实际沐曦设备名称片段", "--output", "/path/to/evidence/probe.json"]
   ```

   在目标服务器运行 `python -m mxready_runner run --manifest /path/to/bundle/mxready.yml
   --repo-dir /path/to/checkout --output /path/to/evidence/result.json`，按提示确认。
   runner 会核对 Git 提交及干净状态，probe 会核对设备名称。设备名称匹配并非硬件认证。
5. **性能**：记录输入、dtype、预热、重复次数与统计，另行执行相同工作负载的基线。
   probe 的 `measured` 仅代表获得测量值，验收阈值应事先确定，不能自动写为 passed。
6. 填写 `acceptance-template.json`，把构建、功能、性能和 runner 结果分别关联，计算日志
   SHA-256 并人工检查脱敏。缺项保持 not-run，失败保留原日志；不要覆盖失败记录。

参考：[PyTorch 扩展构建](https://docs.pytorch.org/docs/stable/cpp_extension.html)、
[数值比较](https://docs.pytorch.org/docs/stable/testing.html)、
[异步计时](https://docs.pytorch.org/docs/stable/notes/cuda.html)、
[cu-bridge 版本说明](https://gitee.com/metax-maca/cu-bridge/blob/master/README.md)。
