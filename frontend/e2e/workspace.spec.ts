import { expect, test } from "@playwright/test";

test("scan, history, checklist, navigation and verification history", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await page.getByLabel("公开仓库地址").fill("https://github.com/example/browser-fixture");
  await page.getByRole("button", { name: "开始体检" }).click();
  await expect(page.getByRole("heading", { name: "迁移报告" })).toBeVisible();
  const scanId = new URL(page.url()).searchParams.get("scan")!;
  const checkbox = page.getByRole("checkbox").first();
  await checkbox.check();
  await expect(checkbox).toBeEnabled();
  await page.reload();
  await expect(page.getByRole("checkbox").first()).toBeChecked();
  await page.getByRole("link", { name: "MCP 接入", exact: true }).click();
  await expect(page.getByRole("heading", { name: "MCP 接入", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "get_scan", exact: true })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("heading", { name: "迁移报告" })).toBeVisible();
  await page.getByRole("link", { name: "扫描历史", exact: true }).click();
  await page.getByRole("button", { name: "打开扫描 " + scanId }).click();
  await page.getByText("验证详情与历史", { exact: true }).click();
  await expect(page.getByText("还没有上传验证结果。", { exact: true })).toBeVisible();
  const now = new Date().toISOString();
  const payload = {
    schema_version: "1.0", scan_id: scanId, repository_commit: "a".repeat(40), runner_version: "0.3.1",
    environment_fingerprint: "sha256:" + "a".repeat(64), started_at: now, finished_at: now,
    overall_status: "passed", commands: [],
    checks: ["uname", "python-version", "mx-smi-version", "mx-smi", "pytorch-device"].map((id) => ({
      id, command: ["fixture"], status: "passed", return_code: 0, duration_ms: 1, stdout: "TOKEN=browser-secret", stderr: "",
    })),
  };
  const result = await page.request.get(`/api/scans/${scanId}/verification-bundle`);
  expect(result.ok()).toBeTruthy();
  await page.getByLabel("选择验证结果 JSON").setInputFiles({ name: "result.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(payload)) });
  await page.getByRole("button", { name: "上传验证结果", exact: true }).click();
  await expect(page.getByText("沐曦 GPU 环境验证已通过", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /当前采用/ })).toBeVisible();
  await page.getByRole("button", { name: /当前采用/ }).click();
  await expect(page.getByRole("region", { name: "验证记录详情" })).toBeVisible();
  await page.getByText("mx-smi · passed · 1ms", { exact: true }).click();
  await expect(page.locator("details[open] > pre").filter({ hasText: "TOKEN=[REDACTED]" }).first()).toBeVisible();
  expect(await page.locator("body").innerText()).not.toContain("browser-secret");
  const width = await page.evaluate(() => ({ content: document.documentElement.scrollWidth, screen: innerWidth }));
  expect(width.content).toBeLessThanOrEqual(width.screen);
  expect(errors).toEqual([]);
});

test("large reports paginate, retain filters, and fit the viewport", async ({ page }) => {
  await page.goto("/?scan=00000000-0000-0000-0000-000000000099");
  await expect(page.getByRole("article")).toHaveCount(50);
  await page.getByRole("button", { name: "发现下一页", exact: true }).click();
  await expect(page.getByRole("article")).toHaveCount(50);
  await page.getByRole("searchbox", { name: "搜索发现" }).fill("fixture-999");
  await expect(page.getByRole("article")).toHaveCount(1);
  await page.reload();
  await expect(page.getByRole("searchbox", { name: "搜索发现" })).toHaveValue("fixture-999");
  await expect(page.getByRole("article")).toHaveCount(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
});

test("report exposes scope, occurrence source links and SARIF export", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("公开仓库地址").fill("https://github.com/example/browser-fixture");
  await page.getByRole("button", { name: "开始体检" }).click();
  await expect(page.getByRole("heading", { name: "扫描范围", exact: true })).toBeVisible();
  const card = page.getByRole("article").first();
  const details = card.locator("details").first();
  if ((await details.getAttribute("open")) === null) await details.locator("summary").click();
  const source = card.getByRole("link", { name: /查看固定提交源码/ }).first();
  await expect(source).toHaveAttribute("href", /\/blob\/a{40}\/.+#L\d+/);
  const sarif = await page.request.get(await page.getByRole("link", { name: "SARIF", exact: true }).getAttribute("href") as string);
  expect(sarif.ok()).toBeTruthy();
  expect((await sarif.json()).version).toBe("2.1.0");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
});

test("batch scans, persisted reviews and remediation guide", async ({ page }) => {
  await page.goto("/?page=batch");
  await page.getByLabel("批量仓库列表").fill("https://github.com/example/batch-one\nhttps://github.com/example/batch-two");
  await page.getByRole("button", { name: "提交批量扫描", exact: true }).click();
  await expect(page.getByText("完成 2 / 2。", { exact: false })).toBeVisible({ timeout: 20000 });
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "下载批量汇总 JSON" }).click();
  expect((await download).suggestedFilename()).toBe("mxready-batch-summary.json");
  await page.reload();
  await expect(page.getByText("完成 2 / 2。", { exact: false })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.getByRole("button", { name: /^打开任务 / }).first().click();
  await page.getByText("人工复核与误报反馈", { exact: true }).click();
  await page.getByLabel("复核结论").selectOption("false-positive");
  await page.getByLabel("判断依据").fill("已检查，属于测试夹具；保留静态发现。");
  await page.getByRole("button", { name: "保存复核记录" }).click();
  await expect(page.getByText("记录共 1 条，最新记录在前。", { exact: false })).toBeVisible();
  await page.reload();
  await page.getByText("人工复核与误报反馈", { exact: true }).click();
  await expect(page.getByText("已检查，属于测试夹具；保留静态发现。", { exact: true })).toBeVisible();
  await page.getByText("整改示例与验证步骤", { exact: true }).first().click();
  await expect(page.getByText(/以下是同类问题示例/).first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
});
