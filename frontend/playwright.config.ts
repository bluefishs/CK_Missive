/**
 * Playwright E2E 測試配置
 *
 * 用於關鍵用戶流程的端到端測試
 *
 * @version 1.0.0
 * @date 2026-02-04
 */

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  // 測試目錄
  testDir: './e2e',

  // 測試執行設定
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  // 報告配置
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
  ],

  // 全域設定
  use: {
    // 基礎 URL
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',

    // 追蹤設定（僅在失敗時記錄）
    trace: 'on-first-retry',

    // 螢幕截圖（僅在失敗時截圖）
    screenshot: 'only-on-failure',

    // 視頻錄製（僅在失敗時錄製）
    video: 'on-first-retry',
  },

  // 瀏覽器配置
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // 可選：Firefox 和 Safari
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  // 開發伺服器設定（可選）
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: !process.env.CI,
  // },
});
