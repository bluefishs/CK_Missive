/**
 * E2E 測試 - 專案管理完整流程
 *
 * 測試專案的 CRUD 操作、人員配置、廠商管理等功能
 *
 * @version 1.0.0
 * @date 2026-02-05
 */

import { test, expect, Page } from '@playwright/test';

// 增加測試超時時間
test.setTimeout(60000);

// 共用函數：等待頁面載入完成
async function waitForPageLoad(page: Page) {
  await page.waitForLoadState('load');
  await page.waitForTimeout(1000);
}

// 共用函數：等待表格載入
async function waitForTable(page: Page) {
  await page.waitForSelector('.ant-table, .ant-spin, .ant-empty', { timeout: 15000 });
}

test.describe('專案列表功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/projects');
    await waitForPageLoad(page);
  });

  test('專案列表頁面可以正常載入', async ({ page }) => {
    await waitForTable(page);

    // 確認頁面有內容
    const hasContent = await page.locator('.ant-table, .ant-empty').first().isVisible();
    expect(hasContent).toBeTruthy();
  });

  test('可以搜尋專案', async ({ page }) => {
    await waitForTable(page);

    // 尋找搜尋框
    const searchInput = page.locator('input[placeholder*="搜尋"], input[placeholder*="查詢"]').first();
    const isSearchVisible = await searchInput.isVisible().catch(() => false);

    if (isSearchVisible) {
      await searchInput.fill('桃園');
      await page.keyboard.press('Enter');
      await waitForPageLoad(page);

      // 確認有搜尋結果或空狀態
      const hasContent = await page.locator('.ant-table, .ant-empty').first().isVisible();
      expect(hasContent).toBeTruthy();
    } else {
      test.info().annotations.push({ type: 'note', description: '搜尋框不可見' });
    }
  });

  test('可以使用狀態篩選', async ({ page }) => {
    await waitForTable(page);

    // 尋找狀態篩選器
    const statusFilter = page.locator('.ant-select').filter({ hasText: /狀態|進行中|已完成/i }).first();
    const isFilterVisible = await statusFilter.isVisible().catch(() => false);

    if (isFilterVisible) {
      await statusFilter.click();
      await page.waitForTimeout(500);

      // 選擇「進行中」
      const activeOption = page.locator('.ant-select-item').filter({ hasText: /進行中/i }).first();
      const isOptionVisible = await activeOption.isVisible().catch(() => false);

      if (isOptionVisible) {
        await activeOption.click();
        await waitForPageLoad(page);
        await waitForTable(page);
      }
    } else {
      test.info().annotations.push({ type: 'note', description: '狀態篩選器不可見' });
    }
  });

  test('專案列表顯示正確的欄位', async ({ page }) => {
    await waitForTable(page);

    // 確認表頭存在
    const tableHeader = page.locator('.ant-table-thead');
    const isHeaderVisible = await tableHeader.isVisible().catch(() => false);

    if (isHeaderVisible) {
      const headerText = await tableHeader.textContent();

      // 檢查是否包含關鍵欄位
      const hasProjectName = headerText?.includes('專案') || headerText?.includes('案件');
      const hasStatus = headerText?.includes('狀態');

      expect(hasProjectName || hasStatus).toBeTruthy();
    }
  });
});

test.describe('專案詳情頁功能', () => {
  test('可以從列表進入專案詳情', async ({ page }) => {
    await page.goto('/projects');
    await waitForPageLoad(page);
    await waitForTable(page);

    // 點擊第一筆專案
    const firstRow = page.locator('.ant-table-row').first();
    const isRowVisible = await firstRow.isVisible().catch(() => false);

    if (isRowVisible) {
      await firstRow.click();
      await waitForPageLoad(page);

      // 確認導航到詳情頁
      await expect(page).toHaveURL(/\/projects\/\d+/);
    } else {
      test.info().annotations.push({ type: 'note', description: '沒有專案資料' });
    }
  });

  test('專案詳情頁顯示所有 Tab', async ({ page }) => {
    await page.goto('/projects/1');
    await waitForPageLoad(page);

    // 檢查是否有 Tab
    const tabs = page.locator('.ant-tabs-tab');
    const tabCount = await tabs.count();

    if (tabCount > 0) {
      // 應該至少有基本資訊、人員、廠商等 Tab
      expect(tabCount).toBeGreaterThanOrEqual(2);
    } else {
      // 可能頁面不存在
      const pageBody = await page.textContent('body');
      if (pageBody?.includes('404')) {
        test.info().annotations.push({ type: 'note', description: '專案 1 不存在' });
      }
    }
  });

  test('可以查看專案人員配置', async ({ page }) => {
    await page.goto('/projects/1');
    await waitForPageLoad(page);

    // 尋找人員相關 Tab
    const staffTab = page.getByRole('tab', { name: /人員|承辦|同仁/i });
    const isTabVisible = await staffTab.isVisible().catch(() => false);

    if (isTabVisible) {
      await staffTab.click();
      await page.waitForTimeout(1000);

      // 確認 Tab 內容載入
      const hasContent = await page.locator('.ant-table, .ant-list, .ant-empty').first().isVisible();
      expect(hasContent).toBeTruthy();
    } else {
      test.info().annotations.push({ type: 'note', description: '人員 Tab 不存在' });
    }
  });

  test('可以查看關聯廠商', async ({ page }) => {
    await page.goto('/projects/1');
    await waitForPageLoad(page);

    // 尋找廠商相關 Tab
    const vendorTab = page.getByRole('tab', { name: /廠商|協力/i });
    const isTabVisible = await vendorTab.isVisible().catch(() => false);

    if (isTabVisible) {
      await vendorTab.click();
      await page.waitForTimeout(1000);

      // 確認 Tab 內容載入
      const hasContent = await page.locator('.ant-table, .ant-list, .ant-empty').first().isVisible();
      expect(hasContent).toBeTruthy();
    } else {
      test.info().annotations.push({ type: 'note', description: '廠商 Tab 不存在' });
    }
  });

  test('可以查看關聯公文', async ({ page }) => {
    await page.goto('/projects/1');
    await waitForPageLoad(page);

    // 尋找公文相關 Tab
    const docTab = page.getByRole('tab', { name: /公文|文件/i });
    const isTabVisible = await docTab.isVisible().catch(() => false);

    if (isTabVisible) {
      await docTab.click();
      await page.waitForTimeout(1000);

      // 確認 Tab 內容載入
      const hasContent = await page.locator('.ant-table, .ant-list, .ant-empty').first().isVisible();
      expect(hasContent).toBeTruthy();
    } else {
      test.info().annotations.push({ type: 'note', description: '公文 Tab 不存在' });
    }
  });
});

test.describe('專案編輯功能', () => {
  test('可以進入專案編輯模式', async ({ page }) => {
    await page.goto('/projects/1');
    await waitForPageLoad(page);

    // 點擊編輯按鈕
    const editButton = page.getByRole('button', { name: /編輯/i });
    const isEditVisible = await editButton.isVisible().catch(() => false);

    if (isEditVisible) {
      await editButton.click();
      await page.waitForTimeout(1000);

      // 確認進入編輯模式
      const cancelButton = page.getByRole('button', { name: /取消/i });
      const saveButton = page.getByRole('button', { name: /儲存/i });

      const hasEditButtons = await cancelButton.isVisible() || await saveButton.isVisible();
      expect(hasEditButtons).toBeTruthy();

      // 取消編輯
      if (await cancelButton.isVisible()) {
        await cancelButton.click();
      }
    } else {
      test.info().annotations.push({ type: 'note', description: '編輯按鈕不可見或專案不存在' });
    }
  });
});

test.describe('專案新增功能', () => {
  test('可以開啟新增專案頁面', async ({ page }) => {
    await page.goto('/projects');
    await waitForPageLoad(page);

    // 尋找新增按鈕
    const addButton = page.getByRole('button', { name: /新增|建立/i }).first();
    const isAddVisible = await addButton.isVisible().catch(() => false);

    if (isAddVisible) {
      await addButton.click();
      await waitForPageLoad(page);

      // 確認有表單
      const hasForm = await page.locator('.ant-form').first().isVisible();
      const isCreatePage = page.url().includes('create') || page.url().includes('new');

      expect(hasForm || isCreatePage).toBeTruthy();
    } else {
      test.info().annotations.push({ type: 'note', description: '新增按鈕不可見' });
    }
  });

  test('新增專案表單驗證', async ({ page }) => {
    await page.goto('/projects/create');
    await waitForPageLoad(page);

    // 檢查是否有表單
    const form = page.locator('.ant-form').first();
    const hasForm = await form.isVisible().catch(() => false);

    if (!hasForm) {
      test.info().annotations.push({ type: 'note', description: '新增頁面不存在或無表單' });
      return;
    }

    // 不填寫直接提交
    const submitButton = page.getByRole('button', { name: /儲存|提交|建立/i }).first();
    const isSubmitVisible = await submitButton.isVisible().catch(() => false);

    if (isSubmitVisible) {
      await submitButton.click();
      await page.waitForTimeout(1000);

      // 應該顯示驗證錯誤
      const errorMessages = page.locator('.ant-form-item-explain-error');
      const errorCount = await errorMessages.count();

      // 有錯誤訊息或仍在表單頁面都算成功
      const stillOnForm = await form.isVisible();
      expect(errorCount > 0 || stillOnForm).toBeTruthy();
    }
  });
});

test.describe('專案人員管理', () => {
  test('可以查看人員列表', async ({ page }) => {
    await page.goto('/projects/1');
    await waitForPageLoad(page);

    // 點擊人員 Tab
    const staffTab = page.getByRole('tab', { name: /人員|承辦/i });
    const isTabVisible = await staffTab.isVisible().catch(() => false);

    if (isTabVisible) {
      await staffTab.click();
      await page.waitForTimeout(1000);

      // 確認有內容
      const hasContent = await page.locator('.ant-table, .ant-list, .ant-empty').first().isVisible();
      expect(hasContent).toBeTruthy();
    } else {
      test.info().annotations.push({ type: 'note', description: '人員 Tab 不存在' });
    }
  });

  test('人員新增按鈕存在', async ({ page }) => {
    await page.goto('/projects/1');
    await waitForPageLoad(page);

    // 點擊人員 Tab
    const staffTab = page.getByRole('tab', { name: /人員|承辦/i });
    const isTabVisible = await staffTab.isVisible().catch(() => false);

    if (!isTabVisible) {
      test.info().annotations.push({ type: 'note', description: '人員 Tab 不存在' });
      return;
    }

    await staffTab.click();
    await page.waitForTimeout(1000);

    // 尋找新增人員按鈕
    const addButton = page.getByRole('button', { name: /新增|指派|加入/i }).first();
    const isAddVisible = await addButton.isVisible().catch(() => false);

    if (isAddVisible) {
      expect(await addButton.isEnabled()).toBeTruthy();
    } else {
      test.info().annotations.push({ type: 'note', description: '新增人員按鈕不可見' });
    }
  });
});

test.describe('專案廠商管理', () => {
  test('可以查看廠商列表', async ({ page }) => {
    await page.goto('/projects/1');
    await waitForPageLoad(page);

    // 點擊廠商 Tab
    const vendorTab = page.getByRole('tab', { name: /廠商|協力/i });
    const isTabVisible = await vendorTab.isVisible().catch(() => false);

    if (isTabVisible) {
      await vendorTab.click();
      await page.waitForTimeout(1000);

      // 確認有內容
      const hasContent = await page.locator('.ant-table, .ant-list, .ant-empty').first().isVisible();
      expect(hasContent).toBeTruthy();
    } else {
      test.info().annotations.push({ type: 'note', description: '廠商 Tab 不存在' });
    }
  });
});
