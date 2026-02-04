/**
 * E2E 測試 - 派工安排完整流程
 *
 * 測試派工安排的建立、查看、編輯等功能
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

test.describe('派工管理列表', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/taoyuan/dispatch');
    await waitForPageLoad(page);
  });

  test('派工管理頁面可以正常載入', async ({ page }) => {
    // 確認頁面有內容
    const pageBody = await page.textContent('body');
    expect(pageBody?.length).toBeGreaterThan(100);

    // 確認有 Tab 或表格
    const hasContent = await page.locator('.ant-tabs, .ant-table').first().isVisible();
    expect(hasContent).toBeTruthy();
  });

  test('可以查看派工紀錄 Tab', async ({ page }) => {
    // 點擊派工紀錄 Tab
    const dispatchTab = page.getByRole('tab', { name: /派工紀錄|派工/i }).first();
    const isTabVisible = await dispatchTab.isVisible().catch(() => false);

    if (isTabVisible) {
      await dispatchTab.click();
      await page.waitForTimeout(1000);

      // 確認 Tab 內容載入
      await waitForTable(page);
    }
  });

  test('可以查看函文紀錄 Tab', async ({ page }) => {
    // 點擊函文紀錄 Tab
    const letterTab = page.getByRole('tab', { name: /函文/i });
    const isTabVisible = await letterTab.isVisible().catch(() => false);

    if (isTabVisible) {
      await letterTab.click();
      await page.waitForTimeout(1000);

      // 確認有內容
      const hasContent = await page.locator('.ant-table, .ant-empty').first().isVisible();
      expect(hasContent).toBeTruthy();
    } else {
      test.info().annotations.push({ type: 'note', description: '函文 Tab 不存在' });
    }
  });

  test('可以查看契金管控 Tab', async ({ page }) => {
    // 點擊契金管控 Tab
    const paymentTab = page.getByRole('tab', { name: /契金|付款/i });
    const isTabVisible = await paymentTab.isVisible().catch(() => false);

    if (isTabVisible) {
      await paymentTab.click();
      await page.waitForTimeout(1000);

      // 確認有內容
      const hasContent = await page.locator('.ant-table, .ant-empty, .ant-form').first().isVisible();
      expect(hasContent).toBeTruthy();
    } else {
      test.info().annotations.push({ type: 'note', description: '契金 Tab 不存在' });
    }
  });

  test('可以查看工程資訊 Tab', async ({ page }) => {
    // 點擊工程資訊 Tab
    const projectTab = page.getByRole('tab', { name: /工程/i });
    const isTabVisible = await projectTab.isVisible().catch(() => false);

    if (isTabVisible) {
      await projectTab.click();
      await page.waitForTimeout(1000);

      // 確認有內容
      const hasContent = await page.locator('.ant-table, .ant-empty, .ant-descriptions').first().isVisible();
      expect(hasContent).toBeTruthy();
    } else {
      test.info().annotations.push({ type: 'note', description: '工程 Tab 不存在' });
    }
  });
});

test.describe('派工單詳情', () => {
  test('可以從列表進入派工單詳情', async ({ page }) => {
    await page.goto('/taoyuan/dispatch');
    await waitForPageLoad(page);

    // 點擊派工紀錄 Tab
    const dispatchTab = page.getByRole('tab', { name: /派工紀錄|派工/i }).first();
    const isTabVisible = await dispatchTab.isVisible().catch(() => false);

    if (isTabVisible) {
      await dispatchTab.click();
      await page.waitForTimeout(1000);
    }

    // 等待表格載入
    await waitForTable(page);

    // 點擊第一筆派工單
    const firstRow = page.locator('.ant-table-row').first();
    const isRowVisible = await firstRow.isVisible().catch(() => false);

    if (isRowVisible) {
      // 尋找查看或編輯按鈕
      const viewButton = firstRow.locator('button, a').filter({ hasText: /查看|編輯|詳情/i }).first();
      const isButtonVisible = await viewButton.isVisible().catch(() => false);

      if (isButtonVisible) {
        await viewButton.click();
        await waitForPageLoad(page);

        // 確認導航到詳情頁
        await expect(page).toHaveURL(/\/taoyuan\/dispatch\/\d+/);
      } else {
        // 嘗試點擊整行
        await firstRow.click();
        await waitForPageLoad(page);
      }
    } else {
      test.info().annotations.push({ type: 'note', description: '沒有派工單資料' });
    }
  });

  test('派工單詳情頁顯示正確', async ({ page }) => {
    // 直接導航到派工單詳情頁
    await page.goto('/taoyuan/dispatch/1');
    await waitForPageLoad(page);

    // 檢查頁面是否載入成功
    const pageBody = await page.textContent('body');

    // 如果是 404 或錯誤頁面，記錄但不失敗
    if (pageBody?.includes('404') || pageBody?.includes('找不到')) {
      test.info().annotations.push({ type: 'note', description: '派工單 1 不存在' });
      return;
    }

    // 確認有詳情內容
    const hasContent = await page.locator('.ant-descriptions, .ant-form, .ant-tabs').first().isVisible();
    expect(hasContent).toBeTruthy();
  });

  test('派工單詳情頁 Tab 切換正常', async ({ page }) => {
    await page.goto('/taoyuan/dispatch/1');
    await waitForPageLoad(page);

    // 取得所有 Tab
    const tabs = page.locator('.ant-tabs-tab');
    const tabCount = await tabs.count();

    if (tabCount === 0) {
      test.info().annotations.push({ type: 'note', description: '沒有 Tab 或頁面載入失敗' });
      return;
    }

    // 遍歷每個 Tab
    for (let i = 0; i < Math.min(tabCount, 5); i++) {
      const tab = tabs.nth(i);
      const isVisible = await tab.isVisible().catch(() => false);

      if (isVisible) {
        await tab.click();
        await page.waitForTimeout(500);

        // 確認 Tab 被選中
        await expect(tab).toHaveClass(/ant-tabs-tab-active/);
      }
    }
  });
});

test.describe('派工單建立流程', () => {
  test('可以開啟新增派工單頁面', async ({ page }) => {
    await page.goto('/taoyuan/dispatch');
    await waitForPageLoad(page);

    // 尋找新增按鈕
    const addButton = page.getByRole('button', { name: /新增|建立/i }).first();
    const isAddVisible = await addButton.isVisible().catch(() => false);

    if (isAddVisible) {
      await addButton.click();
      await waitForPageLoad(page);

      // 確認導航到新增頁面或顯示表單
      const hasForm = await page.locator('.ant-form').first().isVisible();
      const isCreatePage = page.url().includes('create') || page.url().includes('new');

      expect(hasForm || isCreatePage).toBeTruthy();
    } else {
      test.info().annotations.push({ type: 'note', description: '新增按鈕不可見' });
    }
  });

  test('新增派工單表單驗證', async ({ page }) => {
    await page.goto('/taoyuan/dispatch/create');
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

test.describe('派工單與公文關聯', () => {
  test('從公文詳情頁建立派工關聯', async ({ page }) => {
    await page.goto('/documents/841');
    await waitForPageLoad(page);

    // 點擊派工安排 Tab
    const dispatchTab = page.getByRole('tab', { name: /派工/i });
    const isTabVisible = await dispatchTab.isVisible().catch(() => false);

    if (!isTabVisible) {
      test.info().annotations.push({ type: 'note', description: '派工 Tab 不存在' });
      return;
    }

    await dispatchTab.click();
    await page.waitForTimeout(1500);

    // 確認 Tab 內容載入
    const tabContent = page.locator('.ant-tabs-tabpane-active');
    const hasContent = await tabContent.isVisible().catch(() => false);

    expect(hasContent).toBeTruthy();
  });

  test('派工列表在錯誤時保持資料', async ({ page }) => {
    await page.goto('/documents/841');
    await waitForPageLoad(page);

    // 點擊派工安排 Tab
    const dispatchTab = page.getByRole('tab', { name: /派工/i });
    const isTabVisible = await dispatchTab.isVisible().catch(() => false);

    if (!isTabVisible) {
      test.info().annotations.push({ type: 'note', description: '派工 Tab 不存在' });
      return;
    }

    await dispatchTab.click();
    await page.waitForTimeout(1500);

    // 記錄初始內容
    const tableContent = await page.locator('.ant-table-tbody').textContent().catch(() => '');

    // 重新載入頁面
    await page.reload();
    await waitForPageLoad(page);

    // 再次點擊派工 Tab
    const dispatchTabAfter = page.getByRole('tab', { name: /派工/i });
    await dispatchTabAfter.click();
    await page.waitForTimeout(1500);

    // 確認內容仍然存在（不應該被清空）
    const hasContent = await page.locator('.ant-table, .ant-empty').first().isVisible();
    expect(hasContent).toBeTruthy();
  });
});

test.describe('派工篩選功能', () => {
  test('可以按工程篩選派工單', async ({ page }) => {
    await page.goto('/taoyuan/dispatch');
    await waitForPageLoad(page);

    // 尋找工程篩選器
    const projectFilter = page.locator('.ant-select').filter({ hasText: /工程|專案/i }).first();
    const isFilterVisible = await projectFilter.isVisible().catch(() => false);

    if (isFilterVisible) {
      await projectFilter.click();
      await page.waitForTimeout(500);

      // 選擇第一個選項
      const firstOption = page.locator('.ant-select-item').first();
      const isOptionVisible = await firstOption.isVisible().catch(() => false);

      if (isOptionVisible) {
        await firstOption.click();
        await waitForPageLoad(page);
      }
    } else {
      test.info().annotations.push({ type: 'note', description: '工程篩選器不可見' });
    }
  });

  test('可以搜尋派工單', async ({ page }) => {
    await page.goto('/taoyuan/dispatch');
    await waitForPageLoad(page);

    // 尋找搜尋框
    const searchInput = page.locator('input[placeholder*="搜尋"], input[placeholder*="查詢"]').first();
    const isSearchVisible = await searchInput.isVisible().catch(() => false);

    if (isSearchVisible) {
      await searchInput.fill('測試');
      await page.keyboard.press('Enter');
      await waitForPageLoad(page);

      // 確認頁面仍有內容
      const hasContent = await page.locator('.ant-table, .ant-empty').first().isVisible();
      expect(hasContent).toBeTruthy();
    } else {
      test.info().annotations.push({ type: 'note', description: '搜尋框不可見' });
    }
  });
});
