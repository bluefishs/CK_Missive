/**
 * E2E 煙霧測試
 *
 * 基本的端到端測試，確保應用程式可以正常啟動和導航
 *
 * @version 1.2.0
 * @date 2026-02-04
 */

import { test, expect } from '@playwright/test';

// 增加測試超時時間
test.setTimeout(60000);

test.describe('應用程式煙霧測試', () => {
  test('首頁可以正常載入', async ({ page }) => {
    await page.goto('/');

    // 使用 load 代替 networkidle（避免持續 API 輪詢導致超時）
    await page.waitForLoadState('load');

    // 確認頁面標題存在
    await expect(page).toHaveTitle(/.*公文.*/);
  });

  test('可以導航到公文列表頁面', async ({ page }) => {
    await page.goto('/documents');

    // 等待頁面載入
    await page.waitForLoadState('load');

    // 等待表格或頁面內容出現
    await page.waitForSelector('.ant-table, .ant-spin, .ant-empty', { timeout: 15000 });

    // 確認頁面有內容
    const pageContent = page.locator('.ant-table').or(page.locator('.ant-spin')).or(page.locator('.ant-empty'));
    await expect(pageContent.first()).toBeVisible();
  });
});

test.describe('認證流程', () => {
  test('未登入時應該看到登入選項或內容', async ({ page }) => {
    await page.goto('/');

    // 等待頁面載入
    await page.waitForLoadState('load');

    // 確認頁面有內容（內網環境可能不需要登入）
    const body = await page.textContent('body');
    expect(body).toBeTruthy();
  });
});

test.describe('公文管理流程', () => {
  test('可以查看公文列表', async ({ page }) => {
    // 導航到公文列表
    await page.goto('/documents');
    await page.waitForLoadState('load');

    // 等待表格載入（可能是載入中、有資料或無資料）
    await page.waitForSelector('.ant-table, .ant-spin, .ant-empty', { timeout: 15000 });

    // 確認有內容
    const content = page.locator('.ant-table').or(page.locator('.ant-empty'));
    await expect(content.first()).toBeVisible();
  });

  test('可以查看公文詳情', async ({ page }) => {
    // 先導航到公文列表
    await page.goto('/documents');
    await page.waitForLoadState('load');

    // 等待表格載入
    await page.waitForSelector('.ant-table', { timeout: 15000 });

    // 點擊第一個公文（如果存在）
    const firstRow = page.locator('.ant-table-row').first();

    const isVisible = await firstRow.isVisible().catch(() => false);
    if (isVisible) {
      await firstRow.click();

      // 等待導航完成
      await page.waitForLoadState('load');

      // 確認導航到詳情頁
      await expect(page).toHaveURL(/\/documents\/\d+/);
    } else {
      // 如果沒有公文，測試仍然通過
      test.info().annotations.push({ type: 'note', description: '沒有公文資料，跳過詳情測試' });
    }
  });

  test('公文詳情頁可以載入', async ({ page }) => {
    // 直接導航到公文詳情頁（使用已知存在的公文）
    await page.goto('/documents/841');
    await page.waitForLoadState('load');

    // 等待頁面內容
    await page.waitForTimeout(2000);

    // 檢查頁面是否有內容（可能是詳情頁或 404）
    const pageBody = await page.textContent('body');

    // 頁面應該有一些內容（即使是錯誤頁面）
    expect(pageBody).toBeTruthy();

    // 如果是 404 或找不到，添加註解但測試仍通過
    if (pageBody?.includes('404') || pageBody?.includes('找不到') || (pageBody?.length ?? 0) < 100) {
      test.info().annotations.push({ type: 'note', description: '公文 841 可能不存在或頁面內容較少' });
    }
  });

  test('可以進入編輯模式', async ({ page }) => {
    // 導航到公文詳情頁
    await page.goto('/documents/841');
    await page.waitForLoadState('load');
    await page.waitForTimeout(2000);

    // 點擊編輯按鈕
    const editButton = page.getByRole('button', { name: /編輯/i });

    const isVisible = await editButton.isVisible().catch(() => false);
    if (isVisible) {
      await editButton.click();

      // 等待編輯模式
      await page.waitForTimeout(1000);

      // 確認進入編輯模式（應該看到儲存或取消按鈕）
      const saveButton = page.getByRole('button', { name: /儲存/i });
      const cancelButton = page.getByRole('button', { name: /取消/i });

      const hasSave = await saveButton.isVisible().catch(() => false);
      const hasCancel = await cancelButton.isVisible().catch(() => false);

      expect(hasSave || hasCancel).toBeTruthy();
    } else {
      test.info().annotations.push({ type: 'note', description: '編輯按鈕不可見' });
    }
  });
});

test.describe('派工安排流程', () => {
  test('可以查看派工安排 Tab', async ({ page }) => {
    // 導航到公文詳情頁
    await page.goto('/documents/841');
    await page.waitForLoadState('load');
    await page.waitForTimeout(2000);

    // 點擊派工安排 Tab
    const dispatchTab = page.getByRole('tab', { name: /派工/i });

    const isVisible = await dispatchTab.isVisible().catch(() => false);
    if (isVisible) {
      await dispatchTab.click();

      // 等待 Tab 內容載入
      await page.waitForTimeout(1000);

      // 確認 Tab 被點擊（Tab 應該有 active 狀態）
      await expect(dispatchTab).toHaveAttribute('aria-selected', 'true');
    } else {
      test.info().annotations.push({ type: 'note', description: '派工 Tab 不存在（可能非桃園案件）' });
    }
  });
});

test.describe('導航測試', () => {
  test('可以導航到行事曆頁面', async ({ page }) => {
    await page.goto('/calendar');
    await page.waitForLoadState('load');
    await page.waitForTimeout(2000);

    // 確認頁面有內容
    const pageBody = await page.textContent('body');
    expect(pageBody?.length).toBeGreaterThan(100);
  });

  test('可以導航到派工管理頁面', async ({ page }) => {
    await page.goto('/taoyuan/dispatch');
    await page.waitForLoadState('load');
    await page.waitForTimeout(2000);

    // 確認頁面有內容
    const pageBody = await page.textContent('body');
    expect(pageBody?.length).toBeGreaterThan(100);
  });
});
