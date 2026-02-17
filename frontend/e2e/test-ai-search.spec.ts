import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';

test.describe('AI 助理搜尋功能', () => {
  test('開啟 AI 助理並執行搜尋', async ({ page }) => {
    // 1. 前往首頁
    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 15000 });

    // 截圖：首頁載入
    await page.screenshot({ path: 'screenshots/01-homepage.png', fullPage: false });
    console.log('✅ 首頁載入完成');

    // 2. 尋找 AI 助理按鈕（浮動按鈕）
    const aiButton = page.locator('#ai-assistant-portal').locator('..').locator('button').first()
      .or(page.locator('button').filter({ hasText: /AI|助理|搜尋/ }).first())
      .or(page.locator('[class*="float"]').first())
      .or(page.locator('button[style*="position"]').first());

    // 嘗試直接找到 AI 浮動按鈕
    const floatButtons = page.locator('.ant-float-btn, [class*="FloatButton"], [class*="float-btn"]');
    const floatCount = await floatButtons.count();
    console.log(`找到 ${floatCount} 個浮動按鈕`);

    if (floatCount > 0) {
      await floatButtons.first().click();
      console.log('✅ 點擊浮動按鈕');
    } else {
      // 備選：找所有 fixed/absolute 定位的按鈕
      const fixedBtns = page.locator('button');
      const btnCount = await fixedBtns.count();
      console.log(`頁面上共有 ${btnCount} 個按鈕`);

      // 截圖方便除錯
      await page.screenshot({ path: 'screenshots/02-looking-for-ai-btn.png', fullPage: true });

      // 嘗試找 portal 容器
      const portal = page.locator('#ai-assistant-portal');
      const portalExists = await portal.count();
      console.log(`AI Portal 存在: ${portalExists > 0}`);
    }

    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'screenshots/03-after-click-ai.png', fullPage: false });

    // 3. 尋找「公文搜尋」Tab
    const searchTab = page.locator('[role="tab"]').filter({ hasText: /搜尋|Search/ });
    const searchTabCount = await searchTab.count();
    console.log(`找到 ${searchTabCount} 個搜尋 Tab`);

    if (searchTabCount > 0) {
      await searchTab.first().click();
      console.log('✅ 點擊搜尋 Tab');
      await page.waitForTimeout(500);
    }

    await page.screenshot({ path: 'screenshots/04-search-tab.png', fullPage: false });

    // 4. 輸入搜尋文字
    const searchInput = page.locator('input[placeholder*="自然語言"], input[placeholder*="搜尋"]');
    const inputCount = await searchInput.count();
    console.log(`找到 ${inputCount} 個搜尋輸入框`);

    if (inputCount > 0) {
      await searchInput.first().fill('找桃園市政府的公文');
      console.log('✅ 輸入搜尋文字');

      // 5. 按搜尋按鈕
      const searchBtn = page.locator('button').filter({ hasText: /搜尋/ });
      if (await searchBtn.count() > 0) {
        await searchBtn.first().click();
        console.log('✅ 點擊搜尋按鈕');
      } else {
        // 按 Enter
        await searchInput.first().press('Enter');
        console.log('✅ 按 Enter 搜尋');
      }

      // 6. 等待搜尋結果
      await page.waitForTimeout(5000);
      await page.screenshot({ path: 'screenshots/05-search-results.png', fullPage: false });

      // 檢查結果
      const resultText = page.locator('text=/找到.*筆/');
      const hasResults = await resultText.count();
      console.log(`搜尋結果: ${hasResults > 0 ? '有結果' : '無結果或載入中'}`);

      if (hasResults > 0) {
        const text = await resultText.first().textContent();
        console.log(`結果文字: ${text}`);
      }

      // 檢查錯誤訊息
      const errorText = page.locator('text=/錯誤|失敗|無法/');
      const hasError = await errorText.count();
      if (hasError > 0) {
        const errMsg = await errorText.first().textContent();
        console.log(`⚠️ 錯誤訊息: ${errMsg}`);
      }
    }

    // 最終截圖
    await page.screenshot({ path: 'screenshots/06-final.png', fullPage: false });
    console.log('✅ 測試完成');
  });
});
