## 变更说明

<!-- 说明改了什么，以及为什么需要这个改动。 -->

## 关联 Issue

<!-- 例如 Closes #123；无关联可写“无”。 -->

## 测试与验证

<!-- 列出实际执行的命令及结果，不要只写“测试通过”。 -->

- [ ] `python -m ruff check src scripts tests packaging`
- [ ] `python -m pytest --cov=mxready --cov=mxready_runner --cov-fail-under=80`
- [ ] `cd frontend && npm test && npm run build`（涉及前端时）

## 检查清单

- [ ] 新增行为有对应测试，规则类变更包含正例与相似反例
- [ ] 未放宽 Web 扫描“永不执行仓库代码”的安全边界
- [ ] 未引入百分比兼容分数，静态状态与硬件验证状态保持分离
- [ ] 文档中的命令与当前 CLI/API 实现一致
- [ ] 涉及用户可见变更时已更新 `CHANGELOG.md`

## 对外契约变化

<!-- 如有 API、规则 ID、报告格式或环境变量变化，请说明兼容性影响；没有则写“无”。 -->
