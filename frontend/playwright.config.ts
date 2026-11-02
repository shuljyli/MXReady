import { defineConfig } from "@playwright/test";

const port = process.env.MXREADY_E2E_PORT ?? "8173";
const python = process.env.MXREADY_E2E_PYTHON ?? (process.platform === "win32" ? ".venv/Scripts/python.exe" : "python");
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: { baseURL: `http://127.0.0.1:${port}`, trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [
    { name: "desktop", use: { browserName: "chromium", viewport: { width: 1440, height: 960 } } },
    { name: "mobile", use: { browserName: "chromium", viewport: { width: 320, height: 720 } } },
  ],
  webServer: {
    command: `"${python}" tests/browser/serve.py --port ${port}`,
    cwd: "..", url: `http://127.0.0.1:${port}/api/health`, reuseExistingServer: false, timeout: 30_000,
  },
});
