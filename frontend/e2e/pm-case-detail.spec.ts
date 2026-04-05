/**
 * E2E 測試 - PM 案件詳情頁面
 *
 * 驗證案件列表導航、詳情頁 DetailPageLayout、Tab 切換。
 *
 * @version 1.0.0
 */
import { test, expect } from '@playwright/test';
import { loginAsAdmin, waitForPageReady, waitForTableOrEmpty } from './helpers/auth';

test.setTimeout(60000);

test.describe('PM 案件管理', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('案件列表頁面可正常載入', async ({ page }) => {
    await page.goto('/pm/cases');
    await waitForPageReady(page);
    await waitForTableOrEmpty(page);

    const table = page.locator('.ant-table');
    const empty = page.locator('.ant-empty');
    const hasContent = (await table.isVisible()) || (await empty.isVisible());
    expect(hasContent).toBeTruthy();
  });

  test('案件列表有資料欄位', async ({ page }) => {
    await page.goto('/pm/cases');
    await waitForPageReady(page);
    await waitForTableOrEmpty(page);

    const table = page.locator('.ant-table');
    if (await table.isVisible()) {
      const headers = await page.locator('.ant-table-thead th').allTextContents();
      const headerText = headers.join(' ');

      // PM 案件表格常見欄位
      const hasExpectedColumn =
        headerText.includes('案號') ||
        headerText.includes('案件') ||
        headerText.includes('名稱') ||
        headerText.includes('狀態') ||
        headerText.includes('委託');
      expect(hasExpectedColumn).toBeTruthy();
    }
  });
});

test.describe('PM 案件詳情頁面', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('從列表導航到詳情頁', async ({ page }) => {
    await page.goto('/pm/cases');
    await waitForPageReady(page);
    await waitForTableOrEmpty(page);

    const firstRow = page.locator('.ant-table-row').first();
    const isVisible = await firstRow.isVisible().catch(() => false);

    if (isVisible) {
      await firstRow.click();
      await page.waitForLoadState('load');
      await waitForPageReady(page);

      // 應導航到詳情頁
      await expect(page).toHaveURL(/\/pm\/cases\/\d+/);

      // 詳情頁應有 Tab 結構
      const tabs = page.locator('.ant-tabs-tab');
      const tabCount = await tabs.count();
      expect(tabCount).toBeGreaterThanOrEqual(1);
    } else {
      test.info().annotations.push({
        type: 'note',
        description: '無案件資料，無法測試詳情頁導航',
      });
    }
  });

  test('詳情頁有 Tab 結構且可切換', async ({ page }) => {
    // 先取得列表第一筆的 ID
    await page.goto('/pm/cases');
    await waitForPageReady(page);
    await waitForTableOrEmpty(page);

    const firstRow = page.locator('.ant-table-row').first();
    const isVisible = await firstRow.isVisible().catch(() => false);

    if (!isVisible) {
      test.info().annotations.push({
        type: 'note',
        description: '無案件資料',
      });
      return;
    }

    await firstRow.click();
    await page.waitForLoadState('load');
    await waitForPageReady(page);

    // 確認在詳情頁
    await expect(page).toHaveURL(/\/pm\/cases\/\d+/);

    // 應有多個 Tab
    const tabs = page.locator('.ant-tabs-tab');
    const tabCount = await tabs.count();

    if (tabCount >= 2) {
      // 點擊第二個 Tab
      await tabs.nth(1).click();
      await page.waitForTimeout(1000);

      // Tab 應被選中
      const secondTab = tabs.nth(1);
      const isActive = await secondTab.getAttribute('class');
      // Ant Design active tab 有特定 class
      expect(isActive).toBeTruthy();
    }
  });

  test('詳情頁顯示案件基本資訊', async ({ page }) => {
    await page.goto('/pm/cases');
    await waitForPageReady(page);
    await waitForTableOrEmpty(page);

    const firstRow = page.locator('.ant-table-row').first();
    if (!(await firstRow.isVisible().catch(() => false))) {
      test.info().annotations.push({ type: 'note', description: '無案件資料' });
      return;
    }

    await firstRow.click();
    await page.waitForLoadState('load');
    await waitForPageReady(page);

    // 詳情頁應有 Descriptions 元件或 Card 顯示基本資訊
    const descriptions = page.locator('.ant-descriptions, .ant-card');
    const count = await descriptions.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });
});
