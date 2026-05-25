# 後端 API 總覽

## API 端點列表

CK_Missive 後端提供 29 個 API 模組，按功能分類如下：

### 📄 核心業務模組

| 端點 | 路徑 | 說明 | 檔案位置 |
|------|------|------|----------|
| 公文管理 (增強版) | `/api/documents-enhanced` | 公文 CRUD、整合查詢 | `documents_enhanced.py` |
| 承攬案件 | `/api/projects` | 專案管理 | `projects.py` |
| 廠商管理 | `/api/vendors` | 協力廠商 CRUD | `vendors.py` |
| 機關單位 | `/api/agencies` | 政府機關管理 | `agencies.py` |
| 案件廠商關聯 | `/api/project-vendors` | 專案與廠商關係 | `project_vendors.py` |
| 案件人員 | `/api/project-staff` | 專案承辦同仁 | `project_staff.py` |

### 📅 行事曆與提醒

| 端點 | 路徑 | 說明 | 檔案位置 |
|------|------|------|----------|
| 行事曆 | `/api/calendar` | 統一行事曆模組 | `document_calendar.py` |
| 純行事曆 | `/api/pure-calendar` | 相容性行事曆 | `pure_calendar.py` |
| 提醒管理 | `/api/reminder-management` | 提醒排程 | `reminder_management.py` |

### 🔐 認證與使用者

| 端點 | 路徑 | 說明 | 檔案位置 |
|------|------|------|----------|
| 認證 | `/api/auth` | 登入、登出、Token | `auth.py` |
| 使用者 | `/api/users` | 使用者資料 | `users.py` |
| 使用者管理 | `/api/admin/user-management` | 權限管理 | `user_management.py` |

### 🛠️ 系統管理

| 端點 | 路徑 | 說明 | 檔案位置 |
|------|------|------|----------|
| 管理後台 | `/api/admin` | 管理功能 | `admin.py` |
| 網站管理 | `/api/site-management` | 導航設定 | `site_management.py` |
| 安全網站管理 | `/api/secure-site-management` | 安全設定 | `secure_site_management.py` |
| 系統監控 | `/api/system` | 系統狀態 | `system_monitoring.py` |
| 儀表板 | `/api/dashboard` | 統計數據 | `dashboard.py` |

### 📊 輔助功能

| 端點 | 路徑 | 說明 | 檔案位置 |
|------|------|------|----------|
| 發文字號 | `/api/document-numbers` | 文號管理 | `document_numbers.py` |
| 檔案管理 | `/api/files` | 附件上傳下載 | `files.py` |
| CSV 匯入 | `/api/csv-import` | 批次匯入 | `csv_import.py` |
| 公開 API | `/api/public` | 無需認證的端點 | `public.py` |
| 調試工具 | `/api/debug` | 開發調試 | `debug.py` |

---

## 常用 API 範例

### 取得公文列表
```bash
GET /api/documents-enhanced/integrated-search?page=1&limit=10&category=收文
```

**回應欄位 (✅ 2026-01-05 新增)**:
- `auto_serial`: 流水序號 (R0001/S0001 格式)
- `contract_project_name`: 關聯承攬案件名稱
- `assigned_staff`: 負責業務同仁列表 `[{user_id, name, role}]`

### 取得專案列表
```bash
GET /api/projects/?skip=0&limit=20
```

### 取得廠商列表
```bash
GET /api/vendors/?skip=0&limit=100
```

### 取得機關列表
```bash
GET /api/agencies/?skip=0&limit=50
```

---

## 回應格式

### 列表回應
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "limit": 10,
  "total_pages": 10
}
```

### 錯誤回應
```json
{
  "detail": "錯誤訊息"
}
```

---
*檔案位置: `backend/app/api/endpoints/`*
