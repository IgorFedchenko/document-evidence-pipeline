import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  timeout: 600_000,
  workers: 1,
  retries: 0,
  outputDir: process.env.PLAYWRIGHT_OUTPUT_DIR || "test-results",
  use: {
    baseURL: process.env.DEMO_URL || "http://127.0.0.1:8017",
    viewport: { width: 1500, height: 1125 },
    screenshot: "only-on-failure",
    video: { mode: "on", size: { width: 1500, height: 1125 } },
    trace: "retain-on-failure",
  },
  reporter: [["list"], ["html", { open: "never" }]],
});
