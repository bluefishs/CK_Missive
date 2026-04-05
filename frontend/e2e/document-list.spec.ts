/**
 * E2E 測試 - 公文列表頁面
 *
 * 驗證公文列表載入、搜尋功能、篩選操作。
 * 注意：不修改任何資料 (唯讀測試)。
 *
 * @version 1.0.0
 */
import { test, expect } from '@playwright/test';
import { loginAsAdmin, waitForPageReady, waitForTableOrEmpty } from './helpers/auth';

test.setTimeout(60000);

test.describe('公文列表頁面', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('公文列表頁面可正常載入', async ({ page }) => {
    await page.goto('/documents');
    await waitForPageReady(page);
    await waitForTableOrEmpty(page);

    // 表格或空狀態應可見
    const table = page.locator('.ant-table');
    const empty = page.locator('.ant-empty');
    const hasContent = (await table.isVisible()) || (await empty.isVisible());
    expect(hasContent).toBeTruthy();
  });

  test('表格有正確的欄位標頭', async ({ page }) => {
    await page.goto('/documents');
    await waitForPageReady(page);
    await waitForTableOrEmpty(page);

    const table = page.locator('.ant-table');
    if (await table.isVisible()) {
      // 公文表格應有常見欄位
      const headers = await page.locator('.ant-table-thead th').allTextContents();
      const headerText = headers.join(' ');
      // 至少應有文號或主旨欄位
      const hasExpectedColumn =
        headerText.includes('文號') ||
        headerText.includes('主旨') ||
        headerText.includes('日期') ||
        headerText.includes('類別');
      expect(hasExpectedColumn).toBeTruthy();
    }
  });

  test('可以使用搜尋功能', async ({ page }) => {
    await page.goto('/documents');
    await waitForPageReady(page);
    await waitForTableOrEmpty(page);

    // 尋找搜尋輸入框
    const searchInput = page.locator('input[placeholder*="搜尋"], input[placeholder*="關鍵字"], .ant-input-search input').first();
    const isSearchVisible = await searchInput.isVisible().catch(() => false);

    if (isSearchVisible) {
      await searchInput.fill('測試');
      await searchInput.press('Enter');
      await page.waitForTimeout(2000);

      // 搜尋後應仍顯示表格或空狀態
      await waitForTableOrEmpty(page);
    } else {
      test.info().annotations.push({
        type: 'note',
        description: '搜尋輸入框不可見',
      });
    }
  });

  test('點擊列表項可導航到詳情頁', async ({ page }) => {
    await page.goto('/documents');
    await waitForPageReady(page);
    await waitForTableOrEmpty(page);

    const firstRow = page.locator('.ant-table-row').first();
    const isVisible = await firstRow.isVisible().catch(() => false);

    if (isVisible) {
      await firstRow.click();
      await page.waitForLoadState('load');

      // 應導航到詳情頁 (URL 含 /documents/ + ID)
      await expect(page).toHaveURL(/\/documents\/\d+/);
    } else {
      test.info().annotations.push({
        type: 'note',
        description: '沒有公文資料，跳過導航測試',
      });
    }
  });
});
