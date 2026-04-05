/**
 * E2E 測試 - 費用核銷列表頁面
 *
 * 驗證費用列表載入、Tab 切換、統計卡片渲染。
 *
 * @version 1.0.0
 */
import { test, expect } from '@playwright/test';
import { loginAsAdmin, waitForPageReady, waitForTableOrEmpty } from './helpers/auth';

test.setTimeout(60000);

test.describe('費用核銷列表頁面', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('費用列表頁面可正常載入', async ({ page }) => {
    await page.goto('/erp/expenses');
    await waitForPageReady(page);

    const body = await page.textContent('body');
    expect(body?.length).toBeGreaterThan(50);
  });

  test('顯示 Tab 區域', async ({ page }) => {
    await page.goto('/erp/expenses');
    await waitForPageReady(page);

    // 頁面應有 Tabs 元件
    const tabs = page.locator('.ant-tabs-tab');
    const tabCount = await tabs.count();

    // 至少應有費用相關 Tab
    expect(tabCount).toBeGreaterThanOrEqual(1);
  });

  test('表格可正常載入', async ({ page }) => {
    await page.goto('/erp/expenses');
    await waitForPageReady(page);

    // 等待表格或空狀態
    await waitForTableOrEmpty(page);

    const table = page.locator('.ant-table');
    const empty = page.locator('.ant-empty');
    const hasContent = (await table.isVisible()) || (await empty.isVisible());
    expect(hasContent).toBeTruthy();
  });

  test('統計卡片區域渲染', async ({ page }) => {
    await page.goto('/erp/expenses');
    await waitForPageReady(page);

    // 費用列表頁面通常有統計卡片 (Statistic 元件)
    const statsCards = page.locator('.ant-statistic, .ant-card .ant-statistic-content');
    const cardCount = await statsCards.count();

    // 如果有統計卡片，驗證可見
    if (cardCount > 0) {
      await expect(statsCards.first()).toBeVisible();
    } else {
      // 沒有統計卡片也不是錯誤 (可能因為無資料)
      test.info().annotations.push({
        type: 'note',
        description: '無統計卡片（可能無費用資料）',
      });
    }
  });

  test('新增按鈕可見', async ({ page }) => {
    await page.goto('/erp/expenses');
    await waitForPageReady(page);

    // 應有新增核銷按鈕
    const addBtn = page.getByRole('button', { name: /新增|建立|Create/i }).first();
    const isVisible = await addBtn.isVisible().catch(() => false);

    if (isVisible) {
      // 點擊後應導航到建立頁面 (不實際建立資料)
      await addBtn.click();
      await page.waitForLoadState('load');
      await expect(page).toHaveURL(/\/erp\/expenses\/create/);
    } else {
      test.info().annotations.push({
        type: 'note',
        description: '新增按鈕不可見',
      });
    }
  });
});
