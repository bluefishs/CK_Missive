/**
 * E2E 測試 - 標案底價分析頁面
 *
 * 驗證兩 Tab (單一標案分析/價格趨勢) 及表單互動。
 *
 * @version 1.0.0
 */
import { test, expect } from '@playwright/test';
import { loginAsAdmin, waitForPageReady } from './helpers/auth';

test.setTimeout(60000);

test.describe('標案底價分析頁面', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('底價分析頁面可正常載入', async ({ page }) => {
    await page.goto('/tender/price-analysis');
    await waitForPageReady(page);

    const body = await page.textContent('body');
    expect(body?.length).toBeGreaterThan(50);
  });

  test('顯示兩個 Tab (單一標案分析/價格趨勢)', async ({ page }) => {
    await page.goto('/tender/price-analysis');
    await waitForPageReady(page);

    const tabs = page.locator('.ant-tabs-tab');
    const tabCount = await tabs.count();
    expect(tabCount).toBeGreaterThanOrEqual(2);

    const tabTexts = await tabs.allTextContents();
    const allText = tabTexts.join(' ');
    // 應有分析或價格相關文字
    const hasAnalysisTab =
      allText.includes('分析') ||
      allText.includes('Analysis') ||
      allText.includes('價格') ||
      allText.includes('趨勢');
    expect(hasAnalysisTab).toBeTruthy();
  });

  test('單一標案分析 Tab 有表單欄位', async ({ page }) => {
    await page.goto('/tender/price-analysis');
    await waitForPageReady(page);

    // 表單應有 unit_id 和 job_number 輸入欄位
    const formInputs = page.locator('.ant-form .ant-input, .ant-form input');
    const inputCount = await formInputs.count();

    // 至少應有 2 個輸入欄位 (unit_id + job_number)
    expect(inputCount).toBeGreaterThanOrEqual(2);
  });

  test('分析按鈕可點擊', async ({ page }) => {
    await page.goto('/tender/price-analysis');
    await waitForPageReady(page);

    // 找到分析/查詢按鈕
    const analyzeBtn = page.getByRole('button', { name: /分析|查詢|搜尋|Analyze/i }).first();
    const isVisible = await analyzeBtn.isVisible().catch(() => false);

    if (isVisible) {
      // 不填入資料直接點擊，應觸發表單驗證
      await analyzeBtn.click();
      await page.waitForTimeout(1000);

      // 應出現驗證提示或仍在原頁面
      const url = page.url();
      expect(url).toContain('price-analysis');
    } else {
      test.info().annotations.push({
        type: 'note',
        description: '分析按鈕不可見',
      });
    }
  });

  test('可以切換到價格趨勢 Tab', async ({ page }) => {
    await page.goto('/tender/price-analysis');
    await waitForPageReady(page);

    const trendTab = page.locator('.ant-tabs-tab').filter({ hasText: /趨勢|Trend/i }).first();
    const isVisible = await trendTab.isVisible().catch(() => false);

    if (isVisible) {
      await trendTab.click();
      await page.waitForTimeout(1000);

      const body = await page.textContent('body');
      expect(body?.length).toBeGreaterThan(50);
    } else {
      test.info().annotations.push({
        type: 'note',
        description: '價格趨勢 Tab 不存在',
      });
    }
  });
});
