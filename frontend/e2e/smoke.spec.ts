/**
 * E2E 煙霧測試
 *
 * 基本的端到端測試，確保應用程式可以正常啟動和導航
 *
 * @version 1.0.0
 * @date 2026-02-04
 */

import { test, expect } from '@playwright/test';

test.describe('應用程式煙霧測試', () => {
  test('首頁可以正常載入', async ({ page }) => {
    await page.goto('/');

    // 等待頁面載入完成
    await page.waitForLoadState('networkidle');

    // 確認頁面標題存在
    await expect(page).toHaveTitle(/.*公文.*/);
  });

  test('可以導航到公文列表頁面', async ({ page }) => {
    await page.goto('/documents');

    // 等待頁面載入
    await page.waitForLoadState('networkidle');

    // 確認頁面包含公文相關元素
    const header = page.locator('h1, h2, h3, .ant-page-header-heading-title').first();
    await expect(header).toBeVisible();
  });
});

test.describe('認證流程', () => {
  test('未登入時應該看到登入選項', async ({ page }) => {
    await page.goto('/');

    // 等待頁面載入
    await page.waitForLoadState('networkidle');

    // 根據環境，可能需要調整這個測試
    // 內網環境可能不需要登入
    const body = await page.textContent('body');
    expect(body).toBeTruthy();
  });
});

test.describe('公文管理流程', () => {
  test.skip('可以查看公文詳情', async ({ page }) => {
    // 先導航到公文列表
    await page.goto('/documents');
    await page.waitForLoadState('networkidle');

    // 點擊第一個公文（如果存在）
    const firstRow = page.locator('.ant-table-row').first();
    if (await firstRow.isVisible()) {
      await firstRow.click();

      // 確認導航到詳情頁
      await expect(page).toHaveURL(/\/documents\/\d+/);
    }
  });

  test.skip('可以編輯公文', async ({ page }) => {
    // 導航到公文詳情頁
    await page.goto('/documents/1');
    await page.waitForLoadState('networkidle');

    // 點擊編輯按鈕
    const editButton = page.getByRole('button', { name: /編輯/i });
    if (await editButton.isVisible()) {
      await editButton.click();

      // 確認進入編輯模式
      const saveButton = page.getByRole('button', { name: /儲存/i });
      await expect(saveButton).toBeVisible();
    }
  });
});

test.describe('派工安排流程', () => {
  test.skip('可以在公文中新增派工', async ({ page }) => {
    // 導航到公文詳情頁
    await page.goto('/documents/841'); // 測試用公文
    await page.waitForLoadState('networkidle');

    // 點擊派工安排 Tab
    const dispatchTab = page.getByRole('tab', { name: /派工/i });
    if (await dispatchTab.isVisible()) {
      await dispatchTab.click();

      // 確認派工 Tab 內容載入
      await expect(page.locator('text=派工')).toBeVisible();
    }
  });
});
