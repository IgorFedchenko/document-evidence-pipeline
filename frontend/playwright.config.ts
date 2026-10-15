import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './e2e', timeout: 600_000, workers: 1, retries: 0,
  use: { baseURL: process.env.DEMO_URL || 'http://127.0.0.1:8016', viewport: { width: 1500, height: 1100 }, screenshot: 'only-on-failure', video: 'on', trace: 'retain-on-failure' },
  reporter: [['list'], ['html', { open: 'never' }]],
})
