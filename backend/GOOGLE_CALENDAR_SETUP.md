# Google Calendar API 設置指南

## 概述
此文件說明如何為 CK_Missive 系統完成 Google Calendar API 整合，包括服務帳戶設置和權限配置。

## 已完成設置

### 1. 服務帳戶憑證
- **Project ID**: `ck-missive-calendar`
- **Service Account Email**: `ck-missive-calendar@ck-missive-calendar.iam.gserviceaccount.com`
- **憑證文件**: `GoogleCalendarAPIKEY.json` (已配置)

### 2. API 權限
服務帳戶已啟用以下 API：
- Google Calendar API
- Google Sheets API (備用)

## 🚨 待完成設置

### 步驟 1: Calendar 共享設置

由於使用服務帳戶，需要將 Google Calendar 共享給服務帳戶才能進行讀寫操作：

1. **打開 Google Calendar** (https://calendar.google.com)
2. **選擇要整合的日曆**
3. **點擊日曆設定**
4. **新增使用者**：
   ```
   ck-missive-calendar@ck-missive-calendar.iam.gserviceaccount.com
   ```
5. **設定權限為**：`建立及管理活動`

### 步驟 2: 環境變數設置

在後端 `.env` 文件中確認以下設置：

```bash
# Google Calendar 設置
GOOGLE_CALENDAR_ENABLED=true
GOOGLE_CALENDAR_CREDENTIALS_PATH=./GoogleCalendarAPIKEY.json
GOOGLE_CALENDAR_ID=primary  # 或指定的日曆 ID
```

### 步驟 3: 測試連接

執行以下測試以驗證設置：

```bash
# 在後端目錄執行
cd backend
python -c "
from google.oauth2 import service_account
from googleapiclient.discovery import build

credentials = service_account.Credentials.from_service_account_file('GoogleCalendarAPIKEY.json')
service = build('calendar', 'v3', credentials=credentials)

# 測試列出日曆
calendars = service.calendarList().list().execute()
print('可用日曆：')
for calendar in calendars.get('items', []):
    print(f'  {calendar[\"summary\"]} - {calendar[\"id\"]}')
"
```

## API 端點狀態

### ✅ 已實作端點
- `GET /api/calendar/events` - 查詢行事曆事件
- `POST /api/calendar/events` - 建立行事曆事件
- `GET /api/calendar/google/connect` - Google OAuth 連結
- `GET /api/calendar/google/callback` - OAuth 回調處理
- `POST /api/calendar/google/sync` - 手動同步
- `GET /api/calendar/sync/status` - 同步狀態
- `GET /api/calendar/stats` - 統計資訊

### 🔄 需要完成的功能
1. **Calendar 選擇機制** - 讓用戶選擇要同步的日曆
2. **雙向同步** - 本地事件同步到 Google，Google 事件同步到本地
3. **衝突解決** - 處理同步衝突的邏輯
4. **權限檢查** - 驗證服務帳戶是否有日曆存取權限

## 前端整合

### 已完成
- Calendar 路由已啟用 (`/calendar`)
- 導航菜單已包含行事曆選項

### 待實作
1. 建立 Calendar 頁面組件
2. 實作事件建立/編輯界面
3. 新增 Google Calendar 同步設定界面

## 故障排除

### 常見錯誤
1. **404 錯誤**: 檢查服務帳戶是否有日曆存取權限
2. **403 錯誤**: 確認 API 已啟用且配額足夠
3. **憑證錯誤**: 檢查 `GoogleCalendarAPIKEY.json` 路徑和格式

### 檢查清單
- [ ] 服務帳戶有日曆存取權限
- [ ] Google Calendar API 已啟用
- [ ] 憑證文件路徑正確
- [ ] 環境變數設置正確
- [ ] 網路連接正常

## 安全注意事項

1. **憑證保護**: `GoogleCalendarAPIKEY.json` 包含私鑰，不得提交到版本控制
2. **權限最小化**: 僅授予必要的日曆權限
3. **監控使用**: 定期檢查 API 使用量和存取日誌

## 下一步

1. 完成日曆共享設置
2. 實作前端 Calendar 頁面
3. 測試完整的 CRUD 操作
4. 實作同步機制
5. 新增錯誤處理和重試邏輯