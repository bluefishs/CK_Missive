# Google OAuth 設定說明

## 🔧 修復 Google OAuth 登入問題

### 問題識別
- ✅ Google Client ID 已正確配置
- ❌ Google Client Secret 設為佔位符值 `your_google_client_secret`
- ❌ Google OAuth 無法正常工作

### 解決步驟

1. **前往 Google Cloud Console**
   - 網址：https://console.cloud.google.com/
   - 選擇您的專案

2. **取得 OAuth 憑證**
   - 進入：API 和服務 → 憑證
   - 找到「OAuth 2.0 用戶端 ID」
   - 點擊您的用戶端 ID（以 .apps.googleusercontent.com 結尾）

3. **複製 Client Secret**
   - 在憑證詳情頁面找到「Client Secret」
   - 複製真實的 secret（不是佔位符）

4. **更新 .env 檔案**
   ```bash
   # 將這行：
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   
   # 改為（替換為真實的 secret）：
   GOOGLE_CLIENT_SECRET=your_actual_google_client_secret_here
   ```

5. **重新啟動後端服務**
   ```bash
   cd C:/GeminiCli/CK_Missive/backend
   python main.py
   ```

### 驗證
- Google OAuth 應該在 http://localhost:3000/login 正常工作
- 使用者可以透過 Google 帳號登入並自動建立系統帳號

### 注意事項
- Client Secret 是敏感資訊，不要提交到版本控制
- 確保 Google OAuth 的重導向 URI 包含：http://localhost:3000/auth/callback