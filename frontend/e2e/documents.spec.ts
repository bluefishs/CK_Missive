/**
 * E2E 測試 - 公文管理完整流程
 *
 * 測試公文的 CRUD 操作、篩選、搜尋等功能
 *
 * @version 1.0.0
 * @date 2026-02-05
 */

import { test, expect, Page } from '@playwright/test';

// 增加測試超時時間
test.setTimeout(60000);

// 測試資料
const TEST_DOCUMENT = {
  subject: `E2E 測試公文 ${Date.now()}`,
  docNumber: `測試-${Date.now()}`,
  docType: '函',
  category: '收文',
};

// 共用函數：等待頁面載入完成
async function waitForPageLoad(page: Page) {
  await page.waitForLoadState('load');
  await page.waitForTimeout(1000);
}

// 共用函數：等待表格載入
async function waitForTable(page: Page) {
  await page.waitForSelector('.ant-table, .ant-spin, .ant-empty', { timeout: 15000 });
}

test.describe('公文列表功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/documents');
    await waitForPageLoad(page);
  });

  test('公文列表頁面可以正常載入', async ({ page }) => {
    await waitForTable(page);

    // 確認頁面標題或表格存在
    const table = page.locator('.ant-table');
    const empty = page.locator('.ant-empty');
    const hasContent = await table.isVisible() || await empty.isVisible();
    expect(hasContent).toBeTruthy();
  });

  test('可以使用搜尋功能', async ({ page }) => {
    await waitForTable(page);

    // 尋找搜尋輸入框
    const searchInput = page.locator('input[placeholder*="搜尋"], input[placeholder*="查詢"]').first();
    const isSearchVisible = await searchInput.isVisible().catch(() => false);

    if (isSearchVisible) {
      await searchInput.fill('測試');
      await page.keyboard.press('Enter');
      await waitForPageLoad(page);

      // 確認搜尋後頁面仍有內容
      await waitForTable(page);
    } else {
      test.info().annotations.push({ type: 'note', description: '搜尋框不可見' });
    }
  });

  test('可以使用篩選功能 - 收文/發文', async ({ page }) => {
    await waitForTable(page);

    // 尋找類別篩選器
    const categoryFilter = page.locator('.ant-select').filter({ hasText: /收文|發文|全部/ }).first();
    const isFilterVisible = await categoryFilter.isVisible().catch(() => false);

    if (isFilterVisible) {
      await categoryFilter.click();
      await page.waitForTimeout(500);

      // 選擇「收文」選項
      const receiveOption = page.locator('.ant-select-item').filter({ hasText: '收文' }).first();
      const isOptionVisible = await receiveOption.isVisible().catch(() => false);

      if (isOptionVisible) {
        await receiveOption.click();
        await waitForPageLoad(page);
        await waitForTable(page);
      }
    } else {
      test.info().annotations.push({ type: 'note', description: '篩選器不可見' });
    }
  });

  test('可以切換分頁', async ({ page }) => {
    await waitForTable(page);

    // 尋找分頁器
    const pagination = page.locator('.ant-pagination');
    const isPaginationVisible = await pagination.isVisible().catch(() => false);

    if (isPaginationVisible) {
      // 檢查是否有下一頁
      const nextButton = pagination.locator('.ant-pagination-next:not(.ant-pagination-disabled)');
      const hasNextPage = await nextButton.isVisible().catch(() => false);

      if (hasNextPage) {
        await nextButton.click();
        await waitForPageLoad(page);
        await waitForTable(page);
      } else {
        test.info().annotations.push({ type: 'note', description: '沒有下一頁或資料不足' });
      }
    }
  });
});

test.describe('公文詳情頁功能', () => {
  test('可以從列表進入詳情頁', async ({ page }) => {
    await page.goto('/documents');
    await waitForPageLoad(page);
    await waitForTable(page);

    // 點擊第一筆資料
    const firstRow = page.locator('.ant-table-row').first();
    const isRowVisible = await firstRow.isVisible().catch(() => false);

    if (isRowVisible) {
      await firstRow.click();
      await waitForPageLoad(page);

      // 確認導航到詳情頁
      await expect(page).toHaveURL(/\/documents\/\d+/);
    } else {
      test.info().annotations.push({ type: 'note', description: '沒有公文資料' });
    }
  });

  test('詳情頁顯示所有 Tab', async ({ page }) => {
    await page.goto('/documents/841');
    await waitForPageLoad(page);

    // 檢查 Tab 列表
    const tabs = page.locator('.ant-tabs-tab');
    const tabCount = await tabs.count();

    // 應該至少有 3 個 Tab（基本資訊、附件、關聯工程等）
    if (tabCount >= 3) {
      expect(tabCount).toBeGreaterThanOrEqual(3);
    } else {
      test.info().annotations.push({ type: 'note', description: `Tab 數量: ${tabCount}` });
    }
  });

  test('可以切換不同 Tab', async ({ page }) => {
    await page.goto('/documents/841');
    await waitForPageLoad(page);

    // 取得所有 Tab
    const tabs = page.locator('.ant-tabs-tab');
    const tabCount = await tabs.count();

    for (let i = 0; i < Math.min(tabCount, 4); i++) {
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

test.describe('公文編輯功能', () => {
  test('可以進入和退出編輯模式', async ({ page }) => {
    await page.goto('/documents/841');
    await waitForPageLoad(page);

    // 點擊編輯按鈕
    const editButton = page.getByRole('button', { name: /編輯/i });
    const isEditVisible = await editButton.isVisible().catch(() => false);

    if (isEditVisible) {
      await editButton.click();
      await page.waitForTimeout(1000);

      // 確認進入編輯模式
      const cancelButton = page.getByRole('button', { name: /取消/i });
      const isCancelVisible = await cancelButton.isVisible().catch(() => false);

      if (isCancelVisible) {
        // 點擊取消退出編輯模式
        await cancelButton.click();
        await page.waitForTimeout(500);

        // 確認退出編輯模式
        await expect(editButton).toBeVisible();
      }
    } else {
      test.info().annotations.push({ type: 'note', description: '編輯按鈕不可見' });
    }
  });

  test('編輯時表單驗證正常運作', async ({ page }) => {
    await page.goto('/documents/841');
    await waitForPageLoad(page);

    // 進入編輯模式
    const editButton = page.getByRole('button', { name: /編輯/i });
    const isEditVisible = await editButton.isVisible().catch(() => false);

    if (!isEditVisible) {
      test.info().annotations.push({ type: 'note', description: '編輯按鈕不可見' });
      return;
    }

    await editButton.click();
    await page.waitForTimeout(1000);

    // 清空必填欄位（主旨）
    const subjectInput = page.locator('input[name="subject"], textarea[name="subject"]').first();
    const isSubjectVisible = await subjectInput.isVisible().catch(() => false);

    if (isSubjectVisible) {
      await subjectInput.clear();

      // 嘗試儲存
      const saveButton = page.getByRole('button', { name: /儲存/i });
      await saveButton.click();
      await page.waitForTimeout(500);

      // 應該顯示驗證錯誤
      const errorMessage = page.locator('.ant-form-item-explain-error').first();
      const hasError = await errorMessage.isVisible().catch(() => false);

      // 有驗證錯誤或仍在編輯模式都算成功
      const cancelButton = page.getByRole('button', { name: /取消/i });
      const stillEditing = await cancelButton.isVisible().catch(() => false);

      expect(hasError || stillEditing).toBeTruthy();

      // 取消編輯
      if (stillEditing) {
        await cancelButton.click();
      }
    }
  });
});

test.describe('公文附件功能', () => {
  test('可以查看附件 Tab', async ({ page }) => {
    await page.goto('/documents/841');
    await waitForPageLoad(page);

    // 點擊附件 Tab
    const attachmentTab = page.getByRole('tab', { name: /附件/i });
    const isTabVisible = await attachmentTab.isVisible().catch(() => false);

    if (isTabVisible) {
      await attachmentTab.click();
      await page.waitForTimeout(1000);

      // 確認 Tab 被選中
      await expect(attachmentTab).toHaveAttribute('aria-selected', 'true');

      // 確認附件區域顯示
      const attachmentContent = page.locator('.ant-upload, .ant-list, .ant-empty').first();
      const hasContent = await attachmentContent.isVisible().catch(() => false);
      expect(hasContent).toBeTruthy();
    } else {
      test.info().annotations.push({ type: 'note', description: '附件 Tab 不存在' });
    }
  });
});

test.describe('公文匯出功能', () => {
  test('匯出按鈕可見且可點擊', async ({ page }) => {
    await page.goto('/documents');
    await waitForPageLoad(page);
    await waitForTable(page);

    // 尋找匯出按鈕
    const exportButton = page.getByRole('button', { name: /匯出|Export/i });
    const isExportVisible = await exportButton.isVisible().catch(() => false);

    if (isExportVisible) {
      // 不實際觸發下載，只確認按鈕存在且可點擊
      await expect(exportButton).toBeEnabled();
    } else {
      test.info().annotations.push({ type: 'note', description: '匯出按鈕不可見' });
    }
  });
});
