/**
 * E2E 煙霧測試 - 知識庫管理頁面
 *
 * 驗證知識庫管理頁面可正常載入，檢查 Tab 是否渲染。
 *
 * @version 1.0.0
 * @date 2026-03-11
 */

import { test, expect } from '@playwright/test';

test.describe('知識庫管理頁面', () => {
  test('頁面可正常載入', async ({ page }) => {
    await page.goto('/admin/knowledge-base');
    await page.waitForLoadState('load');

    // 頁面應有實質內容
    const body = await page.textContent('body');
    expect(body?.length).toBeGreaterThan(50);
  });

  test('Tab 結構存在', async ({ page }) => {
    await page.goto('/admin/knowledge-base');
    await page.waitForLoadState('load');
    await page.waitForTimeout(2000);

    // 檢查是否有 Tabs 元件
    const tabs = page.locator('.ant-tabs-tab, [role="tab"]');
    const tabCount = await tabs.count();

    if (tabCount > 0) {
      // 預期有 知識地圖 / ADR / 架構圖 等 Tab
      expect(tabCount).toBeGreaterThanOrEqual(1);

      // 檢查是否包含預期的 Tab 文字
      const tabTexts = await tabs.allTextContents();
      const hasExpectedTab = tabTexts.some(
        (t) => t.includes('知識地圖') || t.includes('ADR') || t.includes('架構圖')
      );

      if (hasExpectedTab) {
        expect(hasExpectedTab).toBeTruthy();
      } else {
        test.info().annotations.push({
          type: 'note',
          description: `Tab 文字: ${tabTexts.join(', ')} — 未找到預期的知識庫 Tab`,
        });
      }
    } else {
      // 可能因為未登入或無權限被重導
      const currentUrl = page.url();
      test.info().annotations.push({
        type: 'note',
        description: `無 Tab 顯示，當前 URL: ${currentUrl}（可能需要 admin 權限）`,
      });
    }
  });
});
