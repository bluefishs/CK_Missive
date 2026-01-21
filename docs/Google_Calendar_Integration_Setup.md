# Google Calendar 整合設定指南

## 概述
本系統實現了公文截止日期自動推送至 Google Calendar 的功能，採用單向同步機制，將重要公文事件即時同步到指定的 Google Calendar。

## 前置準備

### 1. Google Cloud Console 設定

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立新專案或選擇現有專案
3. 啟用 Google Calendar API：
   - 在左側選單選擇「API 和服務」→「資料庫」
   - 搜尋「Calendar API」並啟用

### 2. 建立服務帳戶

1. 在 Google Cloud Console 中選擇「API 和服務」→「憑證」
2. 點選「建立憑證」→「服務帳戶」
3. 填寫服務帳戶詳細資料：
   - 名稱：`missive-calendar-sync`
   - 說明：`乾坤測繪公文管理系統 Calendar 同步服務`
4. 點選「建立並繼續」
5. 授予角色：選擇「編輯者」或建立自訂角色（僅需 Calendar 權限）
6. 完成建立

### 3. 下載服務帳戶金鑰

1. 在「憑證」頁面找到剛建立的服務帳戶
2. 點選編輯（鉛筆圖示）
3. 切換到「金鑰」標籤
4. 點選「新增金鑰」→「建立新金鑰」
5. 選擇「JSON」格式
6. 下載 JSON 檔案並重新命名為 `credentials.json`

### 4. Google Calendar 權限設定

1. 登入 Google Calendar (cksurvey0605@gmail.com)
2. 在左側「其他日曆」區域，點選「+」→「建立新日曆」
3. 或使用現有日曆，點選日曆設定
4. 在「與特定人員共用」區域新增服務帳戶：
   - 電子郵件：使用服務帳戶的 email（在 JSON 檔案中的 `client_email` 欄位）
   - 權限：選擇「變更活動」

## 系統配置

### 1. 環境變數設定

在後端 `.env` 檔案中新增以下配置：

```env
# Google Calendar 整合設定
GOOGLE_CALENDAR_ID=cksurvey0605@gmail.com
GOOGLE_CREDENTIALS_PATH=./credentials.json
GOOGLE_CLIENT_ID=your-service-account-client-id
GOOGLE_CLIENT_SECRET=your-service-account-private-key-id
```

### 2. 檔案放置

將下載的 `credentials.json` 檔案放置在後端專案根目錄：
```
backend/
├── credentials.json  # 服務帳戶金鑰檔案
├── main.py
├── .env
└── ...
```

### 3. 安裝相依套件

確保後端已安裝 Google API 相關套件：

```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

## 使用方式

### 1. API 端點

系統提供以下 API 端點進行公文行事曆整合：

#### 同步公文截止日期
```http
POST /api/document-calendar/sync-deadline
Content-Type: application/json

{
  "document_id": 123,
  "document_title": "重要公文標題",
  "deadline": "2024-01-15T14:00:00",
  "description": "公文處理截止提醒",
  "force_update": false
}
```

#### 移除公文截止日期
```http
DELETE /api/document-calendar/remove-deadline/{document_id}
```

#### 檢查服務狀態
```http
GET /api/document-calendar/calendar-status
```

#### 批量同步
```http
POST /api/document-calendar/bulk-sync
```

### 2. 程式整合

在公文建立或更新時，可以使用便利函數：

```python
from app.api.endpoints.document_calendar import auto_sync_document_deadline

# 在公文建立/更新時自動同步
success = auto_sync_document_deadline(
    db=db,
    document_id=document.id,
    document_title=document.subject,
    deadline=document.deadline,
    description=f"公文類型：{document.doc_type}"
)
```

### 3. 事件特徵

推送到 Google Calendar 的事件具有以下特徵：
- 📋 標題前綴，便於識別
- 紅色標記（colorId: 11）表示重要性
- 自動提醒：1天前（電子郵件）+ 1小時前（彈窗）
- 包含返回系統的連結
- 1小時事件時長

## 疑難排解

### 常見問題

1. **403 權限錯誤**
   - 檢查服務帳戶是否已新增到目標日曆的共用設定
   - 確認服務帳戶具有「變更活動」權限

2. **認證檔案錯誤**
   - 確認 `credentials.json` 路徑正確
   - 檢查檔案權限，確保應用程式可讀取

3. **Calendar API 未啟用**
   - 在 Google Cloud Console 確認 Calendar API 已啟用
   - 檢查 API 配額是否足夠

4. **日曆 ID 錯誤**
   - 確認 `.env` 中的 `GOOGLE_CALENDAR_ID` 設定正確
   - 可使用 `primary` 代表主要日曆

### 除錯模式

在開發環境中啟用詳細日誌：

```python
import logging
logging.getLogger('googleapiclient.discovery').setLevel(logging.DEBUG)
```

### 測試連線

使用以下端點測試 Google Calendar 連線：

```bash
curl -X GET "http://localhost:8001/api/document-calendar/calendar-status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

預期回應：
```json
{
  "google_calendar_available": true,
  "target_calendar": "cksurvey0605@gmail.com",
  "service_type": "單向推送（本地 → Google Calendar）",
  "features": [
    "公文截止日期自動推送",
    "事件更新同步",
    "事件刪除同步",
    "電子郵件和彈窗提醒"
  ]
}
```

## 安全注意事項

1. **保護服務帳戶金鑰**
   - 將 `credentials.json` 加入 `.gitignore`
   - 在生產環境使用環境變數或安全的金鑰管理服務

2. **權限最小化**
   - 服務帳戶僅授予必要的 Calendar 權限
   - 定期檢查和更新存取權限

3. **API 配額管理**
   - 監控 Google Calendar API 使用量
   - 實作適當的重試和錯誤處理機制

## 監控與維護

系統會自動記錄同步狀態和錯誤，可透過以下方式監控：

1. 檢查應用程式日誌中的 Google Calendar 相關訊息
2. 使用 `/api/document-calendar/calendar-status` 端點定期檢查服務狀態
3. 監控資料庫中的 `calendar_events` 表格，查看同步狀態

定期維護建議：
- 每月檢查服務帳戶權限
- 監控 API 配額使用情況
- 備份重要的行事曆事件資料