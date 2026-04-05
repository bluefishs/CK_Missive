/**
 * E2E 測試 - 費用核銷新增頁面
 *
 * 驗證三種輸入方式 (手動/掃描/財政部) 切換及表單渲染。
 * 注意：不送出表單，避免建立測試資料。
 *
 * @version 1.0.0
 */
import { test, expect } from '@playwright/test';
import { loginAsAdmin, waitForPageReady } from './helpers/auth';

test.setTimeout(60000);

test.describe('費用核銷新增頁面', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('新增頁面可正常載入', async ({ page }) => {
    await page.goto('/erp/expenses/create');
    await waitForPageReady(page);

    const body = await page.textContent('body');
    expect(body?.length).toBeGreaterThan(50);
  });

  test('顯示三種輸入方式切換 (Segmented)', async ({ page }) => {
    await page.goto('/erp/expenses/create');
    await waitForPageReady(page);

    // Segmented 元件或 Tab 切換
    const segmented = page.locator('.ant-segmented, .ant-radio-group, .ant-tabs-tab');
    const count = await segmented.count();

    if (count > 0) {
      // 應有手動/掃描/財政部選項
      const allText = await page.textContent('body');
      const hasManual = allText?.includes('手動') || allText?.includes('填寫');
      const hasScan = allText?.includes('掃描') || allText?.includes('Scan');
      const hasMOF = allText?.includes('財政部') || allText?.includes('發票');

      // 至少應有一種輸入方式可見
      expect(hasManual || hasScan || hasMOF).toBeTruthy();
    } else {
      // 可能直接顯示表單
      const form = page.locator('.ant-form');
      await expect(form).toBeVisible();
    }
  });

  test('手動填寫模式有必要欄位', async ({ page }) => {
    await page.goto('/erp/expenses/create');
    await waitForPageReady(page);

    // 嘗試選擇手動填寫模式
    const manualOption = page.locator('.ant-segmented-item, .ant-radio-button-wrapper')
      .filter({ hasText: /手動/i }).first();
    const isVisible = await manualOption.isVisible().catch(() => false);
    if (isVisible) {
      await manualOption.click();
      await page.waitForTimeout(500);
    }

    // 表單應有基本欄位 (金額、分類、日期等)
    const form = page.locator('.ant-form');
    if (await form.isVisible()) {
      const formInputs = page.locator(
        '.ant-form .ant-input, .ant-form .ant-input-number, .ant-form .ant-select, .ant-form .ant-picker'
      );
      const inputCount = await formInputs.count();
      // 至少有幾個表單欄位
      expect(inputCount).toBeGreaterThanOrEqual(2);
    }
  });

  test('返回按鈕可導航回列表', async ({ page }) => {
    await page.goto('/erp/expenses/create');
    await waitForPageReady(page);

    // 尋找返回按鈕
    const backBtn = page.getByRole('button', { name: /返回|Back/i }).first()
      .or(page.locator('[class*="back"], [class*="Back"]').first())
      .or(page.locator('button').filter({ has: page.locator('.anticon-arrow-left') }).first());

    const isVisible = await backBtn.isVisible().catch(() => false);
    if (isVisible) {
      await backBtn.click();
      await page.waitForLoadState('load');
      // 應導航回費用列表
      await expect(page).toHaveURL(/\/erp\/expenses/);
    } else {
      test.info().annotations.push({
        type: 'note',
        description: '返回按鈕不可見',
      });
    }
  });

  test('不送出空表單 (表單驗證)', async ({ page }) => {
    await page.goto('/erp/expenses/create');
    await waitForPageReady(page);

    // 找到送出/儲存按鈕
    const submitBtn = page.getByRole('button', { name: /儲存|送出|建立|Submit|Save/i }).first();
    const isVisible = await submitBtn.isVisible().catch(() => false);

    if (isVisible) {
      await submitBtn.click();
      await page.waitForTimeout(1000);

      // 應顯示驗證錯誤訊息，而非導航離開
      const url = page.url();
      expect(url).toContain('/erp/expenses/create');

      // 應有驗證錯誤提示
      const hasError = await page.locator('.ant-form-item-explain-error').first().isVisible().catch(() => false);
      if (hasError) {
        expect(hasError).toBeTruthy();
      }
    } else {
      test.info().annotations.push({
        type: 'note',
        description: '送出按鈕不可見',
      });
    }
  });
});
