# Google Calendar 整合設定指南

## 🎯 目前狀態
✅ Google Calendar API 連接成功  
✅ 服務帳號憑證配置完成  
✅ Python API 套件已安裝  
❌ 需要設定行事曆權限  

## 📋 完成設定的步驟

### 1. 分享行事曆給服務帳號
您需要將目標行事曆 `cksurvey0605@gmail.com` 分享給服務帳號：

**服務帳號郵箱地址：**
```
ck-missive-calendar@ck-missive-calendar.iam.gserviceaccount.com
```

**設定步驟：**
1. 前往 [Google Calendar](https://calendar.google.com/)
2. 使用 `cksurvey0605@gmail.com` 帳號登入
3. 在左側找到您要分享的行事曆
4. 點選行事曆名稱旁的三個點 → "設定和共用"
5. 在"與特定人員共用"區域中：
   - 點選"新增使用者"
   - 輸入服務帳號郵箱：`ck-missive-calendar@ck-missive-calendar.iam.gserviceaccount.com`
   - 權限選擇："進行變更和管理共用設定"
   - 點選"傳送"

### 2. 或者使用主要行事曆
如果您想使用主要行事曆，可以將目標行事曆 ID 改為：
```
primary
```

### 3. 測試連接
設定完成後，可以執行以下測試：

```bash
cd backend
python -c "
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

with open('GoogleCalendarAPIKEY.json', 'r') as f:
    creds_info = json.load(f)

credentials = service_account.Credentials.from_service_account_info(
    creds_info, 
    scopes=['https://www.googleapis.com/auth/calendar']
)

service = build('calendar', 'v3', credentials=credentials)

# 測試事件
event = {
    'summary': '測試公文截止提醒',
    'start': {'dateTime': '2024-09-12T10:00:00+08:00'},
    'end': {'dateTime': '2024-09-12T11:00:00+08:00'},
}

try:
    result = service.events().insert(
        calendarId='cksurvey0605@gmail.com',
        body=event
    ).execute()
    print(f'成功建立事件: {result.get(\"htmlLink\")}')
except Exception as e:
    print(f'失敗: {e}')
"
```

## 🚀 系統功能

設定完成後，您的系統將支援：

### 自動同步功能
- 公文建立時自動推送截止日期到 Google Calendar
- 公文更新時同步更新行事曆事件
- 公文刪除時自動移除相關事件

### API 端點
1. **檢查狀態**: `GET /api/document-calendar/calendar-status`
2. **同步截止日期**: `POST /api/document-calendar/sync-deadline`
3. **批量同步**: `POST /api/document-calendar/bulk-sync`
4. **移除事件**: `DELETE /api/document-calendar/remove-deadline/{document_id}`

### 前端整合
- 行事曆頁面顯示 Google Calendar 整合狀態
- 同步狀態指示器
- 一鍵批量同步功能

## 🔧 故障排除

### 常見問題
1. **404 Not Found**: 行事曆權限未正確設定
2. **403 Forbidden**: API 權限不足
3. **401 Unauthorized**: 憑證檔案有問題

### 檢查清單
- [ ] 服務帳號已分享目標行事曆
- [ ] 憑證檔案路徑正確
- [ ] API 範圍包含 calendar 權限
- [ ] 網路連接正常

## 📝 配置檔案

當前配置 (`.env`):
```
GOOGLE_CALENDAR_ID=cksurvey0605@gmail.com
GOOGLE_CREDENTIALS_PATH=./GoogleCalendarAPIKEY.json
GOOGLE_SERVICE_ACCOUNT_EMAIL=ck-missive-calendar@ck-missive-calendar.iam.gserviceaccount.com
GOOGLE_PROJECT_ID=ck-missive-calendar
```

## 🎉 完成！

完成權限設定後，您的公文管理系統就能自動將重要截止日期推送到 Google Calendar，幫助您更好地管理時間和提醒！