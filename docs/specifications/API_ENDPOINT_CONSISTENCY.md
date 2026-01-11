# API 端點一致性規範 (API Endpoint Consistency)

> 版本：2.1.0
> 建立日期：2026-01-08
> 最後更新：2026-01-10
> 用途：確保前後端 API 端點路徑、HTTP 方法、參數格式一致

---

## 重要更新 (v2.1.0)

### ✅ POST-only API 設計 (資安規範)

從 2026-01-10 起，所有 API 端點**強制使用 POST 方法**，不再使用 GET/PUT/DELETE：

```
# 端點命名規範
POST /xxx/list          # 取得列表 (原 GET /xxx)
POST /xxx/{id}/detail   # 取得詳情 (原 GET /xxx/{id})
POST /xxx/{id}/update   # 更新資料 (原 PUT /xxx/{id})
POST /xxx/{id}/delete   # 刪除資料 (原 DELETE /xxx/{id})
```

**安全優勢**：
- 避免 URL 參數洩漏敏感資訊
- 統一 CSRF 防護機制
- 簡化前端 API 客戶端實作

### ✅ 集中式端點管理已實施

從 2026-01-08 起，所有前端 API 端點路徑統一由 `frontend/src/api/endpoints.ts` 管理。

```typescript
// 使用方式
import { API_ENDPOINTS } from './endpoints';

// 靜態端點
apiClient.post(API_ENDPOINTS.DOCUMENTS.LIST, params);

// 動態端點
apiClient.post(API_ENDPOINTS.DOCUMENTS.DETAIL(123));
```

---

## 一、問題背景

### 1.1 常見錯誤案例

**案例 1：路由前綴不一致 (2026-01-08)**

```
❌ 錯誤狀況：
前端呼叫: POST /api/document-calendar/events
後端註冊: POST /api/calendar/events

原因: 後端 routes.py 註冊時使用 prefix="/calendar"
      但前端開發時誤用 "/document-calendar"

結果: 404 Not Found
```

**案例 2：HTTP Method 不一致**

```
❌ 錯誤狀況：
前端呼叫: GET /api/agencies
後端定義: POST /api/agencies/list

原因: 後端實施 POST-only 安全機制，但前端未同步更新

結果: 405 Method Not Allowed
```

---

## 二、強制規範

### 2.1 API 路由註冊規則

後端 `app/api/routes.py` 是 **唯一的路由定義來源**：

```python
# backend/app/api/routes.py
api_router.include_router(documents.router, prefix="/documents-enhanced", tags=["公文管理"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["行事曆"])
api_router.include_router(agencies.router, prefix="/agencies", tags=["機關管理"])
```

### 2.2 前端 API 路徑定義規則

前端必須使用 **集中式 API 配置** (`frontend/src/api/endpoints.ts`)：

```typescript
// frontend/src/api/endpoints.ts (已實施)
import { API_ENDPOINTS } from './endpoints';

// 完整模組結構
API_ENDPOINTS.DOCUMENTS.LIST        // → '/documents-enhanced/list'
API_ENDPOINTS.DOCUMENTS.CREATE      // → '/documents-enhanced'
API_ENDPOINTS.DOCUMENTS.DETAIL(id)  // → '/documents-enhanced/{id}/detail'
API_ENDPOINTS.DOCUMENTS.UPDATE(id)  // → '/documents-enhanced/{id}/update'
API_ENDPOINTS.DOCUMENTS.DELETE(id)  // → '/documents-enhanced/{id}/delete'

API_ENDPOINTS.CALENDAR.USER_EVENTS       // → '/calendar/users/calendar-events'
API_ENDPOINTS.CALENDAR.EVENTS_UPDATE     // → '/calendar/events/update'
API_ENDPOINTS.CALENDAR.EVENTS_DELETE     // → '/calendar/events/delete'
API_ENDPOINTS.CALENDAR.EVENTS_SYNC       // → '/calendar/events/sync'

API_ENDPOINTS.AGENCIES.LIST              // → '/agencies/list'
API_ENDPOINTS.AGENCIES.DETAIL(id)        // → '/agencies/{id}/detail'
API_ENDPOINTS.AGENCIES.STATISTICS        // → '/agencies/statistics'

// 其他模組: PROJECTS, VENDORS, USERS, FILES, SYSTEM_NOTIFICATIONS 等
```

**已更新的 API 客戶端檔案**：
- `documentsApi.ts` - 公文管理
- `calendarApi.ts` - 行事曆
- `agenciesApi.ts` - 機關管理
- `projectsApi.ts` - 專案管理
- `vendorsApi.ts` - 廠商管理
- `usersApi.ts` - 使用者管理
- `filesApi.ts` - 檔案管理
- `dashboardApi.ts` - 儀表板
- `NotificationCenter.tsx` - 系統通知元件

### 2.3 禁止行為

| 禁止事項 | 說明 |
|----------|------|
| ❌ 硬編碼路徑 | 禁止在 service 中直接寫字串路徑 |
| ❌ 猜測前綴 | 禁止根據檔案名猜測路由前綴 |
| ❌ 複製貼上 | 禁止從其他專案複製 API 路徑 |

---

## 三、開發流程

### 3.1 新增 API 端點流程

```
步驟 1: 後端定義路由
────────────────────────────────────────────────────
# backend/app/api/endpoints/xxx.py
@router.post("/action", summary="操作說明")
async def some_action(...):
    ...

步驟 2: 確認路由前綴
────────────────────────────────────────────────────
# backend/app/api/routes.py
api_router.include_router(xxx.router, prefix="/xxx", tags=["模組名"])

步驟 3: 前端新增端點常數
────────────────────────────────────────────────────
# frontend/src/api/endpoints.ts
XXX: {
    ACTION: '/xxx/action',  // 前綴 + 路由
}

步驟 4: Service 使用端點常數
────────────────────────────────────────────────────
# frontend/src/services/xxxService.ts
import { API_ENDPOINTS } from '../api/endpoints';

const response = await fetch(
    `${API_BASE_URL}${API_ENDPOINTS.XXX.ACTION}`,
    { method: 'POST', ... }
);
```

### 3.2 檢查現有端點流程

```bash
# 1. 查看後端所有路由註冊
grep -n "include_router" backend/app/api/routes.py

# 2. 查看特定模組的路由定義
grep -n "@router" backend/app/api/endpoints/calendar.py

# 3. 確認完整 API 路徑
# 前綴 (routes.py) + 路由 (endpoint.py) = 完整路徑
# /calendar + /events = /api/calendar/events
```

---

## 四、路由對應表

### 4.1 核心模組路由

| 模組 | 後端前綴 | 常見端點 | 完整路徑 |
|------|----------|----------|----------|
| 公文管理 | `/documents-enhanced` | `/list` | `/api/documents-enhanced/list` |
| 行事曆 | `/calendar` | `/events` | `/api/calendar/events` |
| 機關管理 | `/agencies` | `/list` | `/api/agencies/list` |
| 廠商管理 | `/vendors` | `/list` | `/api/vendors/list` |
| 專案管理 | `/projects` | `/list` | `/api/projects/list` |
| 使用者 | `/users` | `/me` | `/api/users/me` |
| 認證 | `/auth` | `/login` | `/api/auth/login` |
| 文件號碼 | `/document-numbers` | `/next` | `/api/document-numbers/next` |

### 4.2 易混淆路由對照

| 易混淆名稱 | 正確前綴 | 錯誤前綴 |
|------------|----------|----------|
| 行事曆事件 | `/calendar` | ~~/document-calendar~~ |
| 公文列表 | `/documents-enhanced` | ~~/documents~~ |
| 機關下拉 | `/agencies` | ~~/government-agencies~~ |

---

## 五、驗證檢查清單

### 5.1 開發時檢查

- [ ] 確認後端 `routes.py` 中的 prefix 設定
- [ ] 確認端點路徑使用常數而非硬編碼字串
- [ ] 確認 HTTP Method 與後端一致 (優先使用 POST)

### 5.2 測試時檢查

```bash
# 測試 API 端點是否存在
curl -s -X POST http://localhost:8001/api/calendar/events \
  -H "Content-Type: application/json" \
  -d '{"title": "test"}' | head -1

# 預期回應: {"success":true,...} 或 {"detail":"..."}
# 錯誤回應: {"detail":"Not Found"} → 路徑錯誤
```

---

## 六、常見錯誤與解決

### 6.1 404 Not Found

**原因**：路由前綴或路徑錯誤

```typescript
// ❌ 錯誤
fetch(`${API_BASE_URL}/document-calendar/events`)

// ✅ 正確 (確認 routes.py 中的 prefix)
fetch(`${API_BASE_URL}/calendar/events`)
```

### 6.2 405 Method Not Allowed

**原因**：HTTP Method 不一致

```typescript
// ❌ 錯誤 (後端使用 POST)
fetch(`${API_BASE_URL}/agencies`, { method: 'GET' })

// ✅ 正確
fetch(`${API_BASE_URL}/agencies/list`, { method: 'POST', body: JSON.stringify({}) })
```

### 6.3 422 Unprocessable Entity

**原因**：請求參數格式不符 Schema

```typescript
// ❌ 錯誤 (缺少必要參數)
fetch(`${API_BASE_URL}/calendar/events`, {
  method: 'POST',
  body: JSON.stringify({})
})

// ✅ 正確 (符合 DocumentCalendarEventCreate schema)
fetch(`${API_BASE_URL}/calendar/events`, {
  method: 'POST',
  body: JSON.stringify({
    title: '事件標題',
    start_date: '2026-01-08T10:00:00'
  })
})
```

### 6.4 500 Internal Server Error - 時區問題

**症狀**：日曆事件建立失敗，錯誤訊息含 `offset-naive and offset-aware datetimes`

**原因**：
- 前端傳送 ISO 格式日期含時區：`2026-01-08T00:00:00.000Z`
- 資料庫欄位為 `TIMESTAMP WITHOUT TIME ZONE`
- SQLAlchemy 無法混用 timezone-aware 和 naive datetime

**解決方案**：後端在儲存前移除時區資訊

```python
# backend/app/api/endpoints/document_calendar.py
start_date = event_create.start_date
if start_date.tzinfo is not None:
    start_date = start_date.replace(tzinfo=None)
```

---

## 七、相關文件

| 文件 | 說明 |
|------|------|
| `docs/DEVELOPMENT_STANDARDS.md` | 統一開發規範總綱 |
| `docs/specifications/TYPE_CONSISTENCY.md` | 型別一致性規範 |
| `docs/FRONTEND_API_MAPPING.md` | 前後端 API 對應表 |
| `backend/app/api/routes.py` | 後端路由定義 |
| `frontend/src/api/client.ts` | 前端 API 客戶端 |

---

## 八、版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 2.1.0 | 2026-01-10 | 強制 POST-only API 設計，更新 user_management.py 端點，新增資安規範章節 |
| 2.0.0 | 2026-01-08 | 實施集中式端點管理，建立 endpoints.ts，更新所有 API 客戶端 |
| 1.1.0 | 2026-01-08 | 遷移至 docs/specifications/，更新相關文件路徑 |
| 1.0.0 | 2026-01-08 | 初版 - 基於 404 錯誤案例建立規範 |

---

*文件維護: Claude Code Assistant*
