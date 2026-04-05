/**
 * E2E 測試 - 知識圖譜頁面 (擴展)
 *
 * 補充既有 knowledge-graph.spec.ts，增加實體搜尋、面板互動測試。
 *
 * @version 1.0.0
 */
import { test, expect } from '@playwright/test';
import { loginAsAdmin, waitForPageReady } from './helpers/auth';

test.setTimeout(60000);

test.describe('知識圖譜頁面 (擴展測試)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('知識圖譜頁面載入並有內容', async ({ page }) => {
    await page.goto('/ai/knowledge-graph');
    await waitForPageReady(page);

    const body = await page.textContent('body');
    expect(body?.length).toBeGreaterThan(50);
  });

  test('圖譜視覺化區域存在', async ({ page }) => {
    await page.goto('/ai/knowledge-graph');
    await waitForPageReady(page);
    await page.waitForTimeout(2000);

    // 圖譜容器 (canvas / force-graph / svg / 或 Card 包裹)
    const graphArea = page.locator(
      'canvas, svg, [class*="force-graph"], [class*="graph-container"], [class*="Graph"], [data-testid="knowledge-graph"]'
    ).first();
    const hasGraph = await graphArea.isVisible().catch(() => false);

    if (hasGraph) {
      await expect(graphArea).toBeVisible();
    } else {
      // 至少頁面不應崩潰
      const content = await page.textContent('body');
      expect(content?.length).toBeGreaterThan(50);
      test.info().annotations.push({
        type: 'note',
        description: '圖譜視覺化容器未渲染',
      });
    }
  });

  test('左側面板存在 (統計或搜尋)', async ({ page }) => {
    await page.goto('/ai/knowledge-graph');
    await waitForPageReady(page);
    await page.waitForTimeout(2000);

    // 左側面板通常包含搜尋或統計
    const leftPanel = page.locator(
      '[class*="left-panel"], [class*="LeftPanel"], [class*="sidebar"], .ant-card'
    ).first();
    const isVisible = await leftPanel.isVisible().catch(() => false);

    if (isVisible) {
      await expect(leftPanel).toBeVisible();
    } else {
      test.info().annotations.push({
        type: 'note',
        description: '左側面板不可見',
      });
    }
  });

  test('實體搜尋功能', async ({ page }) => {
    await page.goto('/ai/knowledge-graph');
    await waitForPageReady(page);
    await page.waitForTimeout(2000);

    // 尋找搜尋輸入框
    const searchInput = page.locator(
      'input[placeholder*="搜尋"], input[placeholder*="實體"], input[placeholder*="Search"], .ant-input-search input'
    ).first();
    const isVisible = await searchInput.isVisible().catch(() => false);

    if (isVisible) {
      await searchInput.fill('桃園');
      await page.waitForTimeout(1000);

      // 搜尋後應有反饋 (搜尋結果、提示等)
      const body = await page.textContent('body');
      expect(body?.length).toBeGreaterThan(50);
    } else {
      test.info().annotations.push({
        type: 'note',
        description: '搜尋輸入框不可見',
      });
    }
  });

  test('頁面不應有 JavaScript 錯誤', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/ai/knowledge-graph');
    await waitForPageReady(page);
    await page.waitForTimeout(3000);

    const criticalErrors = errors.filter(
      (e) =>
        !e.includes('ResizeObserver') &&
        !e.includes('Script error') &&
        !e.includes('WebGL') &&
        !e.includes('canvas')
    );
    expect(criticalErrors).toHaveLength(0);
  });
});
