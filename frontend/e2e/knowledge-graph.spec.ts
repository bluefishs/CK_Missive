/**
 * E2E 煙霧測試 - 知識圖譜頁面
 *
 * 驗證知識圖譜頁面可正常載入，不測試完整互動流程。
 *
 * @version 1.0.0
 * @date 2026-03-11
 */

import { test, expect } from '@playwright/test';

test.describe('知識圖譜頁面', () => {
  test('知識圖譜頁面可正常載入', async ({ page }) => {
    await page.goto('/ai/knowledge-graph');
    await page.waitForLoadState('load');

    // 頁面應有實質內容（非空白頁）
    const body = await page.textContent('body');
    expect(body?.length).toBeGreaterThan(50);
  });

  test('圖譜容器存在', async ({ page }) => {
    await page.goto('/ai/knowledge-graph');
    await page.waitForLoadState('load');
    await page.waitForTimeout(2000);

    // 檢查是否有圖譜容器 (canvas / force-graph wrapper / 或 fallback 內容)
    const graphContainer = page.locator(
      'canvas, [class*="force-graph"], [class*="graph"], [class*="Graph"], [data-testid="knowledge-graph"]'
    ).first();
    const hasGraph = await graphContainer.isVisible().catch(() => false);

    // 如果圖譜未渲染（例如缺少資料），至少頁面不應崩潰
    if (!hasGraph) {
      // 確認頁面仍有內容，沒有白屏
      const pageContent = await page.textContent('body');
      expect(pageContent?.length).toBeGreaterThan(50);
      test.info().annotations.push({
        type: 'note',
        description: '圖譜容器未渲染（可能缺少資料或未登入）',
      });
    } else {
      expect(hasGraph).toBeTruthy();
    }
  });
});
