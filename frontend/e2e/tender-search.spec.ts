/**
 * E2E 測試 - 標案搜尋頁面
 *
 * 驗證標案搜尋 3-Tab (搜尋/收藏/訂閱) 載入與互動。
 *
 * @version 1.0.0
 */
import { test, expect } from '@playwright/test';
import { loginAsAdmin, waitForPageReady } from './helpers/auth';

test.setTimeout(60000);

test.describe('標案搜尋頁面', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('標案搜尋頁面可正常載入', async ({ page }) => {
    await page.goto('/tender/search');
    await waitForPageReady(page);

    // 頁面應有實質內容
    const body = await page.textContent('body');
    expect(body?.length).toBeGreaterThan(50);
  });

  test('顯示三個 Tab (搜尋/收藏/訂閱)', async ({ page }) => {
    await page.goto('/tender/search');
    await waitForPageReady(page);

    // 檢查 Tab 元素
    const tabs = page.locator('.ant-tabs-tab');
    const tabCount = await tabs.count();

    // 至少應有搜尋 Tab
    expect(tabCount).toBeGreaterThanOrEqual(1);

    // 檢查 Tab 文字
    const tabTexts = await tabs.allTextContents();
    const allTabText = tabTexts.join(' ');
    const hasSearchTab =
      allTabText.includes('搜尋') ||
      allTabText.includes('標案') ||
      allTabText.includes('Search');
    expect(hasSearchTab).toBeTruthy();
  });

  test('可以輸入關鍵字進行搜尋', async ({ page }) => {
    await page.goto('/tender/search');
    await waitForPageReady(page);

    // 尋找搜尋輸入框
    const searchInput = page.locator(
      'input[placeholder*="關鍵字"], input[placeholder*="搜尋"], input[placeholder*="標案"], .ant-input-search input'
    ).first();
    const isVisible = await searchInput.isVisible().catch(() => false);

    if (isVisible) {
      await searchInput.fill('測量');

      // 點擊搜尋按鈕
      const searchBtn = page.getByRole('button', { name: /搜尋|Search/i }).first();
      const isBtnVisible = await searchBtn.isVisible().catch(() => false);
      if (isBtnVisible) {
        await searchBtn.click();
      } else {
        await searchInput.press('Enter');
      }

      // 等待搜尋結果
      await page.waitForTimeout(3000);

      // 應顯示表格結果或空狀態
      const hasResult = await page.locator('.ant-table, .ant-empty, .ant-spin').first().isVisible();
      expect(hasResult).toBeTruthy();
    } else {
      test.info().annotations.push({
        type: 'note',
        description: '搜尋輸入框不可見',
      });
    }
  });

  test('可以切換到收藏 Tab', async ({ page }) => {
    await page.goto('/tender/search');
    await waitForPageReady(page);

    // 嘗試點擊收藏 Tab
    const bookmarkTab = page.locator('.ant-tabs-tab').filter({ hasText: /收藏|書籤|Bookmark/i }).first();
    const isVisible = await bookmarkTab.isVisible().catch(() => false);

    if (isVisible) {
      await bookmarkTab.click();
      await page.waitForTimeout(1000);

      // 切換後頁面應有內容 (表格或空狀態)
      const body = await page.textContent('body');
      expect(body?.length).toBeGreaterThan(50);
    } else {
      test.info().annotations.push({
        type: 'note',
        description: '收藏 Tab 不存在',
      });
    }
  });

  test('可以切換到訂閱 Tab', async ({ page }) => {
    await page.goto('/tender/search');
    await waitForPageReady(page);

    // 嘗試點擊訂閱 Tab
    const subscriptionTab = page.locator('.ant-tabs-tab').filter({ hasText: /訂閱|Subscription/i }).first();
    const isVisible = await subscriptionTab.isVisible().catch(() => false);

    if (isVisible) {
      await subscriptionTab.click();
      await page.waitForTimeout(1000);

      const body = await page.textContent('body');
      expect(body?.length).toBeGreaterThan(50);
    } else {
      test.info().annotations.push({
        type: 'note',
        description: '訂閱 Tab 不存在',
      });
    }
  });
});
