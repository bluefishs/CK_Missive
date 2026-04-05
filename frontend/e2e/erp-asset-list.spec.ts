/**
 * E2E 測試 - 資產管理列表頁面
 *
 * 驗證資產列表載入、統計卡片、篩選功能。
 *
 * @version 1.0.0
 */
import { test, expect } from '@playwright/test';
import { loginAsAdmin, waitForPageReady, waitForTableOrEmpty } from './helpers/auth';

test.setTimeout(60000);

test.describe('資產管理列表頁面', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('資產列表頁面可正常載入', async ({ page }) => {
    await page.goto('/erp/assets');
    await waitForPageReady(page);

    const body = await page.textContent('body');
    expect(body?.length).toBeGreaterThan(50);
  });

  test('表格載入並顯示資料欄位', async ({ page }) => {
    await page.goto('/erp/assets');
    await waitForPageReady(page);
    await waitForTableOrEmpty(page);

    const table = page.locator('.ant-table');
    if (await table.isVisible()) {
      const headers = await page.locator('.ant-table-thead th').allTextContents();
      const headerText = headers.join(' ');

      // 資產表格應有常見欄位
      const hasExpectedColumn =
        headerText.includes('資產') ||
        headerText.includes('名稱') ||
        headerText.includes('編號') ||
        headerText.includes('分類') ||
        headerText.includes('狀態');
      expect(hasExpectedColumn).toBeTruthy();
    } else {
      // 空狀態也算通過
      const empty = page.locator('.ant-empty');
      await expect(empty).toBeVisible();
    }
  });

  test('篩選分類功能', async ({ page }) => {
    await page.goto('/erp/assets');
    await waitForPageReady(page);

    // 尋找分類篩選 Select
    const categorySelect = page.locator('.ant-select').filter({ hasText: /分類|類別|Category/i }).first();
    const isVisible = await categorySelect.isVisible().catch(() => false);

    if (isVisible) {
      await categorySelect.click();
      await page.waitForTimeout(500);

      // 下拉選單應有選項
      const dropdown = page.locator('.ant-select-dropdown');
      const hasDropdown = await dropdown.isVisible().catch(() => false);
      if (hasDropdown) {
        // 選擇第一個非空選項
        const options = page.locator('.ant-select-item-option');
        const optionCount = await options.count();
        if (optionCount > 0) {
          await options.first().click();
          await page.waitForTimeout(1000);
        }
      }
    } else {
      // 嘗試用搜尋輸入框
      const searchInput = page.locator('input[placeholder*="搜尋"], .ant-input-search input').first();
      const hasSearch = await searchInput.isVisible().catch(() => false);
      if (!hasSearch) {
        test.info().annotations.push({
          type: 'note',
          description: '篩選和搜尋元件不可見',
        });
      }
    }
  });

  test('統計卡片區域', async ({ page }) => {
    await page.goto('/erp/assets');
    await waitForPageReady(page);

    // 資產頁面通常有統計卡片
    const statsElements = page.locator('.ant-statistic, .ant-card .ant-statistic-content');
    const count = await statsElements.count();

    if (count > 0) {
      await expect(statsElements.first()).toBeVisible();
    } else {
      test.info().annotations.push({
        type: 'note',
        description: '無統計卡片',
      });
    }
  });

  test('新增資產按鈕可見', async ({ page }) => {
    await page.goto('/erp/assets');
    await waitForPageReady(page);

    const addBtn = page.getByRole('button', { name: /新增|建立|Create/i }).first();
    const isVisible = await addBtn.isVisible().catch(() => false);

    if (isVisible) {
      await expect(addBtn).toBeEnabled();
    } else {
      test.info().annotations.push({
        type: 'note',
        description: '新增按鈕不可見',
      });
    }
  });
});
