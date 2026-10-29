# MXReady 规则开发指南

规则集位于 `src/mxready/resources/rules/v1/`，由 `manifest.yml` 固定版本与加载顺序。规则是受信任的项目代码，应和 Python 代码一样接受评审；用户提交的仓库不能提供或覆盖规则。

## 清单文件

```yaml
schema_version: "1.0"
ruleset_version: "2"
rule_files:
  - core.yml
```

- `schema_version`：清单契约版本，目前只能为 `"1.0"`；
- `ruleset_version`：写入每份报告的规则集版本；
- `rule_files`：相对文件名列表，只允许安全的 `.yml`/`.yaml` 文件名，不能重复或包含路径。

每个规则文件最大 1 MiB，必须解析为非空规则数组。

## 规则字段

```yaml
- id: MXR-TOOLCHAIN-001
  version: 1
  title: 检测直接 nvcc 工具调用
  category: toolchain
  severity: blocker
  file_globs: ["**/*.py", "**/*.sh"]
  patterns:
    - type: regex
      expression: '\bnvcc\b'
      flags: [IGNORECASE]
  message: 说明为什么这个模式值得复核。
  recommendation: 给出可执行的复核与验证动作。
  references:
    - title: MetaX-MACA cu-bridge
      url: https://gitee.com/metax-maca/cu-bridge
```

| 字段 | 约束 |
| --- | --- |
| `id` | `MXR-[A-Z]+-[0-9]{3}`，全规则集唯一 |
| `version` | 大于等于 1；语义变化时递增 |
| `title` | 非空、面向用户的简短标题 |
| `category` | 小写字母开头，只含小写字母、数字、连字符 |
| `severity` | `blocker`、`warning` 或 `info` |
| `file_globs` | 非空、安全、去重的正斜杠相对 glob |
| `patterns` | 一个或多个 `regex`、`dependency`、`fact` 模式 |
| `message` | 解释检测到的代码事实，不下无证据的确定性结论 |
| `recommendation` | 明确要求复核、迁移或真机验证的下一步 |
| `references` | 至少一个公开 HTTPS 一手资料链接 |

严重级别建议：

- `blocker`：若不处理，常常无法进入目标工具链构建阶段；
- `warning`：存在平台假设或依赖风险，需要人工复核；
- `info`：识别项目形态或迁移入口，不代表错误。

## 三种模式

### `regex`

对匹配 `file_globs` 的已索引文本做 Python 正则搜索。

```yaml
- type: regex
  expression: '\bfind_package\s*\(\s*CUDAToolkit\b'
  flags: [IGNORECASE]
```

- 表达式必须非空且不超过 1,000 字符；
- 支持 `ASCII`、`DOTALL`、`IGNORECASE`、`MULTILINE`、`VERBOSE`；
- flags 不能重复；
- 正则应尽量锚定调用上下文，避免仅匹配一个常见单词；
- 匹配证据最多保留 240 字符。

引擎会从表达式中提取"命中必然包含"的必需字面量做预过滤，判定不可能命中的文件直接跳过、
不进入正则。提取是保守的：拿不出字面量（或依赖的内部解析接口不可用）时退化为全量扫描，
**跳过的集合只会更小，结论与全量扫描完全一致**。

由此有两条约束：

- 大小写请用 `flags: [IGNORECASE]` 声明，不要写内联 `(?i)` 或 `(?i:...)`。内联写法只对作用域
  局部生效，而规则读者通常只看 `flags`，容易误判整条规则的大小写语义；
- 表达式尽量包含至少 3 个字符的固定字面量（如 `nvcc`、`find_package`）。只有短分支或纯字符类
  的表达式无法预过滤，在大仓库上会明显变慢。多分支 `(?:a|b)` 要求**每个**分支都能给出字面量，
  否则整条规则放弃预过滤——这是为了保证零漏报。

### `dependency`

匹配从 `pyproject.toml`、Poetry 配置、`requirements*.txt` 以及 `setup.py` 静态提取并规范化的依赖名。
`setup.py` 只读取 `install_requires` / `setup_requires` / `tests_require` / `extras_require` 中的
字面量字符串（列表或元组写法均可），变量等动态值不求值、不采集。

```yaml
- type: dependency
  name: flash-attn
```

依赖名按 Python 包名规则把 `-`、`_`、`.` 统一处理；不要在该模式中写版本条件。

### `fact`

匹配解析器产生的布尔或字符串事实。

```yaml
- type: fact
  name: uses_torch_cuda_extension
  equals: true
```

当前布尔事实包括：

- `imports_apex`
- `imports_tensorrt`
- `invokes_nvcc_directly`
- `invokes_nvidia_smi`
- `references_cuda_home`
- `uses_cmake_cuda_language`
- `uses_cmake_cuda_package`
- `uses_cmake_torch_package`
- `uses_hardcoded_cuda_path`
- `uses_torch_cpp_extension`
- `uses_torch_cpp_extension_load`
- `uses_torch_cuda_extension`

新增事实需要先在 `facts.py` 中实现保守的静态提取和独立测试。

## 证据与去重

每条 finding 固定包含规则 ID/版本、严重级别、类别、相对路径、起止行、原始行证据、说明、建议和参考资料。相同规则、文件、起始行与证据只保留一次，最终结果按严重级别、路径、行号和规则 ID 稳定排序。

不要在证据里拼接仓库外数据，也不要执行预处理器、Python 导入或构建系统来“获得更多事实”。

## 一手资料政策

优先级如下：

1. MXMACA、cu-bridge、沐曦性能调优指南等维护者资料；
2. PyTorch、CMake、CUDA 等上游官方文档；
3. 对应开源项目自己的仓库文档。

参考链接必须直接支持规则所陈述的技术事实。规则措辞应使用“需要复核”“可能固化假设”“请在目标环境验证”，不能把静态命中冒充硬件测试结论。

## 测试要求

在 `tests/fixtures/repositories/rule_cases/` 添加最小代码，并在 `tests/backend/test_core_rules.py` 中加入：

- 正例：只包含触发该规则所需的最少文本；
- 相似反例：例如注释、普通字符串、近似依赖名或无调用上下文的工具名；
- 预期严重级别；
- 主资料 URL。

先运行测试观察失败，再改 YAML 或事实提取器：

```bash
python -m pytest tests/backend/test_core_rules.py tests/backend/test_rule_engine.py -v
python -m ruff check src scripts tests packaging
```

最后必须运行全量质量门，避免规则相互影响。
