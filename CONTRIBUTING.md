# 参与 MXReady

感谢你帮助改善国产 GPU 迁移工具链。MXReady 优先接受范围小、证据明确、可离线验证的贡献。

## 开发流程

1. 从最新 `main` 创建短生命周期分支；
2. 先添加能失败的测试，再实现功能或修复；
3. 保持 Web 扫描的“永不执行仓库代码”边界；
4. 运行完整质量门；
5. 在 PR 中说明问题、证据、测试结果和对外契约变化。

```bash
python -m ruff check backend runner scripts tests
python -m pytest --cov=mxready --cov=mxready_runner --cov-fail-under=80
cd frontend
npm test
npm run build
```

## 贡献规则

每条新规则必须包含：

- 稳定且不重复的 `MXR-<类别>-<三位编号>`；
- 一份会命中的最小正例；
- 一份语义相近但不应命中的反例；
- 对真实项目误报风险的说明；
- 至少一个一手资料链接，例如 MXMACA/cu-bridge、PyTorch、CMake 或 CUDA 官方文档；
- 面向人工复核的措辞，不得把静态模式描述为确定的不兼容。

不要仅引用博客、搜索结果页或无法追溯的二手结论。完整字段约束见 [docs/rules.md](docs/rules.md)。

## 安全变更

涉及仓库获取、路径处理、文件读取、命令执行、上传、HTML/SVG/Markdown 输出的变更，必须增加对应安全回归测试。不要为了扫描更多项目而放宽硬限制；若确需改变限制，请单独提案并解释威胁模型。

runner 的命令白名单、人工确认、`shell=False`、超时、脱敏和输出上限属于安全契约，不能在普通功能 PR 中绕过。

## 文档与界面

- 对用户可见的静态状态和硬件状态必须始终分开；
- 不得引入百分比兼容分数；
- 中英文术语首次出现时应清楚解释；
- UI 变更需要可访问名称、键盘行为和响应式测试；
- 文档中的命令必须与当前 CLI/API 实现一致。

## 提交信息

推荐使用简短的约定式前缀，例如：

```text
feat: add CMake architecture rule
fix: avoid matching commented compiler flags
docs: explain verification result expiry
test: cover symlink traversal boundary
```

## 漏洞报告

请不要在公开 Issue 中粘贴密钥、访问令牌、私有仓库内容或可直接利用的细节。先按 [docs/security.md](docs/security.md) 中的披露流程联系维护者。
