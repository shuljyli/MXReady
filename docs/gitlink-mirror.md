# GitLink 镜像与同步

种子计划要求入选项目同步镜像至 GitLink。本文把这件事拆成三部分：一次性建镜像、每次发版的同步、
以及“哪些链接要改、哪些必须保持原样”的判断依据。

## 一、策略：单一权威源 + 只读镜像

**不改任何源码内容。** GitHub 是开发与 CI 的权威源，GitLink 是只读镜像。

理由很直接：仓库有 9 个语言版本的 README、CI 徽章、Release 链接和 `pyproject.toml` 里的项目地址。
如果为了镜像去改这些内容，就要维护两套事实，任何一次发版都会漂移。镜像的价值是“国内可达 + 合规”，
不是“第二套文档”。

由此推出三条规则：

1. GitLink 侧不接受 PR、不提 issue，`README` 里也不加“请到 GitLink 提问”这类入口；
2. 所有合并只发生在 GitHub，然后单向推送；
3. GitLink 上缺的东西（发版附件、仓库简介）靠手工补齐，不靠改源码。

需要先摆正预期：GitLink 是 CCF 官方指定的开源创新服务平台，用户以国内高校、科研机构与竞赛生态为主
（2025 年 CCF 公开数据：25 万用户、144 万托管项目）。它是**评审与合规意义上的镜像，不是流量入口**，
不要指望它带来新用户。

## 二、一次性建立镜像（用官方同步服务，不手工 push）

GitLink 提供「跨平台代码同步」服务（与蚂蚁 OceanBase 联合研发），基于 webhook 做 GitHub、Gitee 与
GitLink 之间的分支同步，最多支持三个平台。用它比每次手工 push 可靠，因为漏推会立刻表现为“镜像落后”，
而不会悄悄发生。

1. 在 GitLink 用「导入仓库」填入 `https://github.com/shuljyli/MXReady.git`，创建镜像仓。**不要**新建空仓
   再初始化 README——导入会连提交历史一起带过来，空仓则会产生一次无关历史的首次提交；
2. 进入仓库的「服务」标签，开通「跨平台代码同步」；
3. 填 GitHub 仓库地址，并提供一个 GitHub PAT（classic，勾 `repo` 权限）。**token 过期后同步会停止**，
   不是报错提醒，是静默不动，所以要在日历上记一次到期日；
4. 复制 GitLink 给出的 webhook 地址，到 GitHub 仓库 `Settings → Webhooks → Add webhook`：
   Content type 选 `application/json`，事件只勾 `push`，确认状态是激活；
5. 绑定分支 `main` ↔ `main`。**首次同步方向必须选 GitHub → GitLink**，因为首次同步会强推一次；
   方向选反会把 GitHub 主仓覆盖掉。

官方明确的三条限制，选型时要知道：

- 只支持**个人仓库**，组织仓库暂不支持同步；
- 只同步**分支**，标签（tag）和发行版（release）不跟；
- 不要在两边同时提交，webhook 双向触发会冲突。

如果导入或同步服务不可用，退回手动远端，效果等价但需要每次记得执行：

```bash
git remote add gitlink https://gitlink.org.cn/<你的用户名>/MXReady.git
git push gitlink main:main --tags
```

首次推送**不要用 `git push --mirror`**。`--mirror` 会把本地所有引用（含 `refs/remotes/`）一并推送，
并且在后续执行时会删除远端不存在的分支——镜像应当只增不改，这条命令的风险大于收益。

镜像建好后，在 GitLink 仓库设置里补齐元信息：

1. 默认分支确认为 `main`；
2. 仓库简介与 GitHub 的 description 保持一致：
   `面向 PyTorch CUDA 扩展的沐曦 MXMACA 迁移准备度静态体检工具`；
3. 补 topics：`cuda` `pytorch` `metax` `mxmaca` `migration` `static-analysis`；
4. 确认许可证被识别为 `Apache-2.0`（识别失败通常是 `LICENSE` 未被读到，检查默认分支）。

## 三、每次发版后的同步

分支由同步服务自动跟，剩下两件事必须手工补。

**标签。** 同步服务不推 tag，发版后单独推一次：

```bash
git push gitlink --tags
```

**发行版附件。** GitLink 没有与 GitHub Releases 对等的 API 同步机制，附件必须在「发行版」页手工上传：

```text
dist/mxready-<版本>-windows.zip
dist/mxready-<版本>-linux.zip
dist/mxready-<版本>-macos.zip
dist/mxready-<版本>-py3-none-any.whl
dist/mxready-<版本>.tar.gz
dist/SHA256SUMS.txt
```

上传后逐个核对摘要，不要直接相信上传成功提示：

```bash
sha256sum -c SHA256SUMS.txt
```

Windows 侧用 PowerShell：

```powershell
Get-FileHash .\mxready-1.0.0-windows.zip -Algorithm SHA256
```

## 四、链接盘点：只有两处需要判断

全仓库指向 `github.com/shuljyli/MXReady` 的位置共 6 个文件，逐个判定如下。

| 位置 | 内容 | 处理 |
| --- | --- | --- |
| `README.md` 第 3 行 | CI 徽章（GitHub Actions） | **保留**。GitLink 没有 Actions，徽章继续显示 GitHub 的构建状态，这是“CI 在 GitHub 跑”的如实表达，不是坏链 |
| `README.md` 第 115 行 | GitHub Releases 链接 | **保留**，但必须在 GitLink 发行版同步上传同样的附件，否则国内读者点过去要跨站 |
| `docs/installation.md` 第 29 行 | Releases 下载入口 | 同上，与 README 一并依赖 GitLink 发行版 |
| `README.en.md` 第 3 行 | 同上 CI 徽章 | 保留 |
| `pyproject.toml` | `Homepage` / `Repository` / `Issues` / `Changelog` | **保留 GitHub**。这四个字段是包元数据，指向唯一权威源；改成 GitLink 会让 `pip show` 把用户带到不收 issue 的镜像 |
| `CHANGELOG.md` | 各版本的 compare 链接 | 保留 |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | issue 入口 | 保留。GitLink 侧不使用 |

结论：**镜像不需要改一行代码或文档**。需要人工补的只有 GitLink 侧的仓库信息与发版附件。

## 五、验收清单

镜像建好后逐项确认，任何一项不过都不算完成：

- [ ] `git clone https://gitlink.org.cn/<用户名>/MXReady.git` 能成功，默认分支为 `main`
- [ ] `git ls-remote --tags gitlink` 与 `git ls-remote --tags origin` 的标签集合一致
- [ ] 克隆下来的仓库里 `pyproject.toml`、`src/mxready/resources/rules/v1/core.yml` 与 GitHub 一致
- [ ] 在克隆目录执行 `python -m pip install -e .` 后，`mxready-scan --help` 可用
- [ ] README 在 GitLink 页面渲染正常，相对链接（如 `docs/architecture.md`）不跳回 GitHub
- [ ] 发行版附件的 SHA256 与 `SHA256SUMS.txt` 一致
- [ ] 仓库页显示许可证 `Apache-2.0`

## 六、已知坑

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 首次推送被拒：`non-fast-forward` | 建仓时勾选了 README 初始化 | 删掉远端初始提交后重推，或改用新空仓库 |
| 默认分支是 `master` | 平台按旧约定初始化 | 在仓库设置里改回 `main`，否则 README 与徽章都不显示 |
| 徽章在 GitLink 不显示 | 外链图片被拦截或缓存 | 属正常降级，不影响仓库可用性；不要为此删掉徽章 |
| 两边历史分叉 | 有人在 GitLink 直接提交 | 只允许 GitHub → GitLink 单向；出现分叉时以 GitHub 为准，`git push --force-with-lease` 覆盖镜像 |
| 发版附件缺失 | 忘了手工上传 | 把“上传 GitLink 附件”写进发版检查表，与 `SHA256SUMS.txt` 一起核对 |

## 七、真机证据的位置

真机结果以脱敏形式入库，可直接核验：

- `examples/verification/metax-verification-redacted.json`：`pytorch/extension-cpp` @ `1c325b2`；
- `examples/verification/causal-conv1d/result.json`：`causal-conv1d` @ `cd81f04`。

镜像不会替你做脱敏：入库文件会原样出现在 GitLink。新增或更新结果时，先按
`examples/verification/pre-upload-check.sh` 复核主机名、IP、内网路径与凭据字段，再提交；
不要为通过检查而修改状态或提交号。
