# MXReady 前端设计图生成记录

日期：2026-10-25。

## 实施用插画

使用内置生图工具单独生成芯片插画，并将生成图编码为 WebP，未改变构图或视觉内容。最终项目资产：`frontend/src/assets/mx-chip.webp`，1086×1448，80,784 字节；由 Vite 打包，无外部图片请求。

最终提示词：

```text
Create a refined decorative illustration asset for the MXReady software developer workspace. Portrait composition approximately 3:4. A single abstract floating stack of three square microchip ceramic slabs in an isometric view, cream-white top face, frosted pale sage green edges, very dark forest green thin circuit traces elegantly extending toward the edges of the canvas. Top ceramic face bears just small letters 'MX' in dark green. Premium architectural product visualization, quiet technical sophistication, soft natural diffuse light, gentle shadows, warm off-white background #f3f5ef, extremely restrained green and cream palette. The chip occupies middle 65% with comfortable negative space above and below. Entirely decorative abstract conceptual chip, no representation of a real vendor hardware product. No UI, no panels, no borders, no buttons, no other text, no watermark, no blue or purple neon, no gradients or dark backdrop. High detail precise materials, clean lines, very low contrast background, similar to a luxury minimal engineering illustration.
```

使用内置 `image_gen` 工具生成，无 CLI/API 回退。图像是设计参考，不是实际运行截图。报告中的仓库、提交、代码与数量均为示例，不作为扫描证据。

## 首页提示词

```text
Use case: ui-mockup
Asset type: high fidelity frontend design concept for existing MXReady application, a Chinese developer tool for static assessment of PyTorch CUDA extensions migrating to MetaX MXMACA.
Primary request: Generate a polished, restrained desktop application screen design, landscape 1536x1024. Full bleed flat UI screenshot, no browser chrome, no perspective, no device frame. This is the NEW SCAN screen only. Focus on a functional form, beautiful spacious proportions, typography, precise aligned controls, minimal necessary text. No marketing paragraphs.
Style: quiet premium engineering workspace, warm off-white background #f7f8f5, white panels, very dark forest ink #182b27, muted grey-green labels, emerald #16745b primary action, hairline borders, soft subtle shadow, 16px corner radius. No neon, no purple gradients.
Composition: narrow 216px white left sidebar, remaining main area. Sidebar top compact geometric emerald M mark and MXReady wordmark. Under it one active nav item with outline scan icon and Chinese "源码体检". Bottom sidebar small "CUDA → MXMACA". Header across main: breadcrumb "工作台 / 源码体检", right small "规则集 v1". Main workspace generous margin 64px. Small eyebrow "MIGRATION WORKSPACE", prominent restrained heading "新建体检" and single small subtitle "PyTorch CUDA → MXMACA". Below, one broad white panel divided into left 60% form and right 40% quiet tinted technical illustration. Left panel: small step index 01, heading "输入公开仓库", label "公开仓库地址", large input with placeholder "https://github.com/owner/repository", short hint "支持 GitHub / Gitee", label "分支、标签或提交（可选）", input placeholder "默认分支", full width emerald button "开始体检" and small arrow. Bottom a shield icon and brief "仅静态分析，不执行仓库代码".
Right panel: sophisticated abstract isometric two-layer microchip geometry, cream and light sage slabs with precise dark green circuit trace lines, subtle warm shadows. The main chip has just text "MX". Not a colorful cartoon and not a photoreal photo. Small upper label "CUDA → MXMACA"; at bottom short "检查源码 · 定位风险".
Below form panel a simple horizontal 3-step strip with tiny outlined square icons: "01 源码扫描" then "02 迁移报告" then "03 真机验证", separated by fine lines. These are explanatory steps, not additional buttons.
Small note below "静态检查不等于硬件兼容认证".
Constraints: Chinese labels rendered accurately. All content contained inside screen with generous whitespace. No invented metrics, no compatibility percentages, no recent projects, no history, no account avatar, no pricing, no fake controls, no large promotional text. The form is the visual focal point. Design should feel ready to implement in React.
```

## 报告页提示词

参考图：`new-scan.png`，仅用于保持视觉风格。

```text
Use case: ui-mockup.
Create a second high-fidelity desktop page design for MXReady, the MIGRATION REPORT screen, using the attached NEW SCAN design solely as reference for the design system: sidebar, warm white background, white cards, forest ink, emerald buttons, precise borders and subtle shadows. Generate a flat full-page UI screenshot, landscape 1536x1024, no device frame. Chinese UI, minimal concise wording. This is a concept with illustrative data, not a real scan result.
Keep same left 216px sidebar: MXReady logo and single active navigation "源码体检", small bottom "CUDA → MXMACA". Main header breadcrumb "工作台 / 迁移报告", top right outline button "新建体检". No other nav, avatars or invented tools.
Main content top heading "迁移报告", small repository link "example/cuda-extension" and monospace commit "a1b2c3d4e5f6". Top right small "设计示例".
Below two clearly separate compact status cards: "静态检查" with amber badge "需要复核", and "真机验证" with neutral badge "未验证". NEVER show compatibility score or percentage. Then a compact metric strip showing "发现 3", "阻塞 0", "警告 2", "提示 1".
Main body two columns: wide left evidence section 66%, right tools 34%. Left card heading "源码发现", segmented real filter controls "全部 3", "阻塞 0", "警告 2", "提示 1". One expanded warning finding with badge "警告", rule ID "示例规则", title "CUDA 架构配置需复核", monospace location "CMakeLists.txt:18", small code block "set(CMAKE_CUDA_ARCHITECTURES 80)", then concise "建议动作" and "复核目标架构与构建参数。", small reference link "查看依据 ↗". Two compact rows below with labels "警告  设备选择需复核" and "提示  构建依赖需检查" with chevrons.
Below left card, compact "迁移清单" panel with numbered rows "01 复核构建配置" and "02 检查设备选择".
Right column top "导出报告" card with three equal outlined buttons "JSON", "Markdown", "Badge", one line "绑定当前提交". Right bottom "沐曦真机验证" card, neutral badge "未验证", concise important instruction "审阅命令后，在沐曦主机运行。", emerald button "下载验证包", native-style outlined file picker "选择 result.json", upload button "上传验证结果" visibly disabled because no file selected, small "JSON · 最大 1 MiB". Include compact expandable text "运行说明" with chevron. Do not imply cloud execution from webpage.
Footer small note "静态检查不等于硬件兼容认证".
Keep entire design aligned, professional, information dense but spacious, readable. No large illustration on report page. No fake charts, no made-up real-world projects, no percentages, no marketing paragraphs, no unnecessary text. No clipping or unreadable tiny labels. Color is used sparingly for statuses, primary actions, and selected filters.
```

