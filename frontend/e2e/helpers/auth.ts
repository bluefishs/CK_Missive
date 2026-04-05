/**
 * E2E 共用認證工具
 *
 * 在 localhost 環境使用快速進入 (dev bypass) 登入，
 * 並注入 localStorage token 以通過 ProtectedRoute。
 *
 * @version 1.0.0
 */
import { Page } from '@playwright/test';

/** 模擬管理員使用者 */
const MOCK_ADMIN_USER = {
  id: 2,
  username: 'admin',
  email: 'admin@example.com',
  full_name: '系統管理員',
  is_active: true,
  is_admin: true,
  role: 'admin',
  auth_provider: 'local',
  login_count: 100,
  email_verified: true,
  permissions: [],
};

/** 模擬 token (JWT 格式, exp=9999999999) */
const MOCK_TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  'eyJzdWIiOiJhZG1pbiIsImVtYWlsIjoiYWRtaW5AZXhhbXBsZS5jb20iLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTcwMDAwMDAwMCwianRpIjoiZTJlLXRlc3QifQ.' +
  'fake_e2e_signature';

/**
 * 注入認證狀態到 localStorage + mock /auth/me API
 *
 * 用於需要認證的頁面測試，避免依賴真實登入流程。
 */
export async function loginAsAdmin(page: Page) {
  // Mock /auth/me to return admin user
  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_ADMIN_USER),
    });
  });

  // Mock /auth/check to return authenticated
  await page.route('**/api/auth/check', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ authenticated: true, user: MOCK_ADMIN_USER }),
    });
  });

  // Inject token into localStorage before navigating
  await page.addInitScript((token: string) => {
    localStorage.setItem('access_token', token);
    localStorage.setItem('auth_user', JSON.stringify({
      id: 2,
      username: 'admin',
      email: 'admin@example.com',
      full_name: '系統管理員',
      is_active: true,
      is_admin: true,
      role: 'admin',
    }));
  }, MOCK_TOKEN);
}

/**
 * 等待頁面載入完成 (load state + 短暫穩定期)
 */
export async function waitForPageReady(page: Page) {
  await page.waitForLoadState('load');
  // Give React time to hydrate
  await page.waitForTimeout(1000);
}

/**
 * 等待 Ant Design 表格或空狀態出現
 */
export async function waitForTableOrEmpty(page: Page, timeout = 15000) {
  await page.waitForSelector('.ant-table, .ant-empty, .ant-spin', { timeout });
}
