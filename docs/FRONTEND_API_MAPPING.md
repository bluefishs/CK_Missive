# 前端功能與後端 API 對應關係

本文件旨在明確前端應用程式的各項功能與後端 FastAPI API 端點之間的對應關係，以促進開發團隊的協作，減少重複開發，並作為功能實現的參考依據。

**重要提示：**
*   **API 詳細資訊請參考自動生成的 Swagger UI (`/api/docs`) 或 ReDoc (`/api/redoc`)。**
*   本文件將持續更新，以反映最新的功能與 API 變動。

---

## 1. 公文管理 (Documents) - 文管中心核心

| 前端功能描述       | 前端頁面 | API 端點 (Method & Path) | 相關後端檔案 (Endpoint, Service, Schema, Model) | 說明                                     |
| :----------------- | :------- | :----------------------- | :---------------------------------------------- | :--------------------------------------- |
| **公文列表顯示**   | `DocumentList.tsx`, `DocumentPage.tsx` | `GET /api/documents`     | `documents.py`, `document_service.py`, `document.py`, `OfficialDocument` | 獲取所有公文列表，支援更複雜的篩選、排序、分頁。 |
| **公文 CSV 匯入**  | `POST /api/documents/import` | `documents.py`, `document_import_service.py`, `csv_processor.py`, `document_service.py`, `document.py`, `OfficialDocument` | 上傳 CSV 檔案，自動處理、去重並匯入公文數據。 |
| **獲取公文年度列表** | `GET /api/documents/documents-years` | `documents.py`, `document_service.py`           | 獲取資料庫中所有公文的年度列表。         |
| **公文總覽統計**   | `GET /api/documents/stats` | `documents.py`, `document_service.py`           | 獲取公文總數、收發文統計、年度分佈等儀表板數據。 |
| **公文數據匯出**   | `GET /api/documents/export` | `documents.py`, `document_service.py`           | 匯出公文數據至指定格式（例如 Excel），支援篩選。 |
| **公文批量更新**   | `POST /api/documents/batch-update` | `documents.py`, `document_service.py`           | 根據 ID 列表批量更新公文狀態、承辦人等資訊。 |
| **公文批量刪除**   | `POST /api/documents/batch-delete` | `documents.py`, `document_service.py`           | 根據 ID 列表批量軟刪除公文。             |
| **公文詳情顯示**   | `DocumentDetailPage.tsx` | `GET /api/documents/{id}` | `documents.py`, `document_service.py` | 獲取單一公文的詳細資訊。                 |
| **公文新增**       | `DocumentCreatePage.tsx` | `POST /api/documents/` | `documents.py`, `document_service.py` | 創建新的公文記錄。                       |
| **公文編輯**       | `DocumentEditPage.tsx` | `PUT /api/documents/{id}` | `documents.py`, `document_service.py` | 更新現有公文的資訊。                     |
| **公文刪除**       | `DocumentPage.tsx` | `DELETE /api/documents/{id}` | `documents.py`, `document_service.py` | 刪除單一公文記錄。                       |
| **公文匯入**       | `DocumentImportPage.tsx` | `POST /api/documents/import` | `documents.py`, `document_import_service.py` | CSV 檔案匯入公文數據。                   |
| **公文匯出**       | `DocumentExportPage.tsx` | `GET /api/documents/export` | `documents.py`, `document_service.py` | 匯出公文數據至 Excel 等格式。            |
| **公文工作流**     | `DocumentWorkflowPage.tsx` | 相關端點 | `documents.py`, `document_service.py` | 公文處理工作流程。                       |
| **公文複雜搜尋**   | `DocumentPage.tsx` | `POST /api/documents/search` | `documents.py`, `document_service.py` | 支援多條件的複雜公文查詢。               |
| **公文快取統計**   | 開發用途 | `GET /api/documents/cache/stats` | `documents.py`, `document_service.py` | 獲取公文快取統計信息。                   |

---

## 2. 儀表板與總覽 (Dashboard & Overview)

| 前端功能描述       | 前端頁面 | API 端點 (Method & Path) | 相關後端檔案 (Endpoint) | 說明                                     |
| :----------------- | :------- | :----------------------- | :---------------------- | :--------------------------------------- |
| **主儀表板**       | `DashboardPage.tsx` | `GET /api/documents/statistics` | `documents.py`          | 顯示公文統計、最近處理公文等總覽資訊。   |
| **個人設定**       | `SettingsPage.tsx` | `GET/PUT /api/auth/me` | `auth.py`               | 使用者個人設定和偏好配置。               |
| **個人資料**       | `ProfilePage.tsx` | `GET/PUT /api/auth/me` | `auth.py`               | 使用者個人資料管理和密碼變更。           |

---

## 3. 承攬案件管理 (Contract Cases & Projects)

| 前端功能描述       | 前端頁面 | API 端點 (Method & Path) | 相關後端檔案 (Endpoint, Service, Schema, Model) | 說明                                     |
| :----------------- | :------- | :----------------------- | :---------------------------------------------- | :--------------------------------------- |
| **承攬案件管理頁面** | `ProjectPage.tsx` | `GET /api/projects`      | `projects.py`, `project.py`, `ContractProject`  | 獲取所有承攬案件列表，支援篩選、搜尋、分頁。 |
| **案件管理主頁**   | `ContractCasePage.tsx` | `GET /api/cases/`        | `cases.py`                                       | 承攬案件綜合管理介面。                   |
| **案件詳情頁面**   | `ContractCaseDetailPage.tsx` | `GET /api/cases/{id}`    | `cases.py`                                       | 查看單一承攬案件的詳細資訊。             |
| **案件表單頁面**   | `ContractCaseFormPage.tsx` | `POST/PUT /api/cases/`   | `cases.py`                                       | 新增或編輯承攬案件的表單介面。           |
| **新增承攬案件**   | `ProjectPage.tsx` | `POST /api/projects`     | `projects.py`, `project.py`, `ContractProject`  | 建立新的承攬案件記錄。                   |
| **承攬案件詳情**   | `ProjectPage.tsx` | `GET /api/projects/{id}` | `projects.py`, `project.py`, `ContractProject`  | 獲取單一承攬案件的詳細資訊。             |
| **更新承攬案件**   | `ProjectPage.tsx` | `PUT /api/projects/{id}` | `projects.py`, `project.py`, `ContractProject`  | 更新現有承攬案件的資訊。                 |
| **刪除承攬案件**   | `ProjectPage.tsx` | `DELETE /api/projects/{id}` | `projects.py`, `ContractProject`                | 刪除承攬案件及其相關聯的廠商關係。       |

---

## 4. 廠商管理 (Vendors)

| 前端功能描述       | 前端頁面 | API 端點 (Method & Path) | 相關後端檔案 (Endpoint, Service, Schema, Model) | 說明                                     |
| :----------------- | :------- | :----------------------- | :---------------------------------------------- | :--------------------------------------- |
| **廠商管理頁面**   | `VendorPage.tsx` | `GET /api/vendors`       | `vendors.py`, `vendor.py`, `PartnerVendor`      | 獲取所有廠商列表，支援篩選、搜尋、分頁。 |
| **新增廠商**       | `VendorPage.tsx` | `POST /api/vendors`      | `vendors.py`, `vendor.py`, `PartnerVendor`      | 建立新的廠商記錄。                       |
| **廠商詳情**       | `VendorPage.tsx` | `GET /api/vendors/{id}`  | `vendors.py`, `vendor.py`, `PartnerVendor`      | 獲取單一廠商的詳細資訊。                 |
| **更新廠商**       | `VendorPage.tsx` | `PUT /api/vendors/{id}`  | `vendors.py`, `vendor.py`, `PartnerVendor`      | 更新現有廠商的資訊。                     |
| **刪除廠商**       | `VendorPage.tsx` | `DELETE /api/vendors/{id}` | `vendors.py`, `PartnerVendor`                   | 刪除廠商（需無關聯專案）。               |

---

## 4. 案件與廠商關聯 (Project-Vendors)

| 前端功能描述       | API 端點 (Method & Path) | 相關後端檔案 (Endpoint, Service, Schema, Model) | 說明                                     |
| :----------------- | :----------------------- | :---------------------------------------------- | :--------------------------------------- |
| **建立關聯**       | `POST /api/project-vendors` | `project_vendors.py`, `project_vendor.py`, `project_vendor_association` | 建立案件與廠商之間的合作關聯。           |
| **獲取案件關聯廠商** | `GET /api/project-vendors/project/{project_id}` | `project_vendors.py`, `project_vendor.py`, `project_vendor_association` | 獲取特定承攬案件所有關聯的廠商列表。     |
| **獲取廠商關聯案件** | `GET /api/project-vendors/vendor/{vendor_id}` | `project_vendors.py`, `project_vendor.py`, `project_vendor_association` | 獲取特定廠商所有關聯的承攬案件列表。     |
| **更新關聯**       | `PUT /api/project-vendors/project/{project_id}/vendor/{vendor_id}` | `project_vendors.py`, `project_vendor.py`, `project_vendor_association` | 更新案件與廠商關聯的詳細資訊。           |
| **刪除關聯**       | `DELETE /api/project-vendors/project/{project_id}/vendor/{vendor_id}` | `project_vendors.py`, `project_vendor_association` | 刪除案件與廠商之間的關聯。               |
| **所有關聯列表**   | `GET /api/project-vendors` | `project_vendors.py`, `project_vendor.py`, `project_vendor_association` | 獲取所有案件與廠商關聯的列表。           |

---

## 5. 管理後台 (Admin)

| 前端功能描述       | API 端點 (Method & Path) | 相關後端檔案 (Endpoint, Service) | 說明                                     |
| :----------------- | :----------------------- | :------------------------------- | :--------------------------------------- |
| **資料庫資訊**     | `GET /api/admin/database/info` | `admin.py`, `admin_service.py`   | 獲取資料庫基本信息（大小、表格、記錄數）。 |
| **表格數據查詢**   | `GET /api/admin/database/table/{table_name}` | `admin.py`, `admin_service.py`   | 分頁獲取指定資料庫表格的數據。           |
| **SQL 唯讀查詢**   | `POST /api/admin/database/query` | `admin.py`, `admin_service.py`   | 執行安全的唯讀 SQL SELECT 查詢。         |
| **資料庫健康檢查** | `GET /api/admin/database/health` | `admin.py`, `admin_service.py`   | 檢查資料庫連線健康狀況。                 |

---

## 6. 認證與使用者管理 (Auth & User Management)

| 前端功能描述       | 前端頁面 | API 端點 (Method & Path) | 相關後端檔案 (Endpoint) | 說明                                     |
| :----------------- | :------- | :----------------------- | :---------------------- | :--------------------------------------- |
| **使用者登入**     | `LoginPage.tsx` | `POST /api/auth/login`   | `auth.py`               | 傳統帳密登入和 Google OAuth 登入。       |
| **使用者註冊**     | `RegisterPage.tsx` | `POST /api/auth/register` | `auth.py`               | 新使用者註冊功能。                       |
| **忘記密碼**       | `ForgotPasswordPage.tsx` | `POST /api/auth/forgot-password` | `auth.py` | 密碼重設功能。                           |
| **獲取當前使用者** | 所有頁面 | `GET /api/auth/me`       | `auth.py`               | 獲取當前登入使用者資訊。                 |
| **使用者登出**     | 所有頁面 | `POST /api/auth/logout`  | `auth.py`               | 使用者登出並撤銷會話。                   |
| **刷新令牌**       | 所有頁面 | `POST /api/auth/refresh` | `auth.py`               | 刷新存取令牌。                           |
| **Google OAuth**   | `GoogleAuthDiagnosticPage.tsx` | `POST /api/auth/google` | `auth.py` | Google OAuth 第三方登入診斷。            |

---

## 7. 使用者管理 (User Management) - **管理員功能**

| 前端功能描述       | 前端頁面 | API 端點 (Method & Path) | 相關後端檔案 (Endpoint) | 說明                                     |
| :----------------- | :------- | :----------------------- | :---------------------- | :--------------------------------------- |
| **使用者管理頁面** | `UserManagementPage.tsx` | `GET /api/admin/user-management/users` | `user_management.py` | 管理員查看所有使用者列表。               |
| **新增使用者**     | `UserManagementPage.tsx` | `POST /api/admin/user-management/users` | `user_management.py` | 管理員新增使用者。                       |
| **取得使用者詳情** | `UserManagementPage.tsx` | `GET /api/admin/user-management/users/{id}` | `user_management.py` | 獲取指定使用者詳細資訊。                 |
| **更新使用者資訊** | `UserManagementPage.tsx` | `PUT /api/admin/user-management/users/{id}` | `user_management.py` | 更新使用者資訊。                         |
| **刪除使用者**     | `UserManagementPage.tsx` | `DELETE /api/admin/user-management/users/{id}` | `user_management.py` | 軟刪除使用者。                           |
| **管理使用者權限** | `PermissionManagementPage.tsx` | `GET/PUT /api/admin/user-management/users/{id}/permissions` | `user_management.py` | 管理使用者詳細權限設定。                 |
| **檢查權限**       | 所有頁面 | `POST /api/admin/user-management/permissions/check` | `user_management.py` | 檢查使用者是否具有指定權限。             |

---

## 8. 網站管理 (Site Management)

| 前端功能描述       | 前端頁面 | API 端點 (Method & Path) | 相關後端檔案 (Endpoint) | 說明                                     |
| :----------------- | :------- | :----------------------- | :---------------------- | :--------------------------------------- |
| **網站管理頁面**   | `SiteManagementPage.tsx` | `GET /api/site-management/navigation` | `site_management.py` | 管理網站導覽列結構和配置。               |
| **更新導覽列**     | `SiteManagementPage.tsx` | `PUT /api/site-management/navigation` | `site_management.py` | 更新導覽列配置。                         |
| **安全網站管理**   | `SiteManagementPage.tsx` | 相關端點 | `secure_site_management.py` | 安全級別的網站管理功能。                 |

---

## 9. 行事曆功能 (Calendar)

| 前端功能描述       | 前端頁面 | API 端點 (Method & Path) | 相關後端檔案 (Endpoint) | 說明                                     |
| :----------------- | :------- | :----------------------- | :---------------------- | :--------------------------------------- |
| **行事曆頁面**     | `CalendarPage.tsx` | `GET /api/calendar/events` | `calendar.py`           | 獲取使用者行事曆事件。                   |
| **新增行事曆事件** | `CalendarPage.tsx` | `POST /api/calendar/events` | `calendar.py`           | 創建新的行事曆事件。                     |
| **行事曆狀態**     | `CalendarPage.tsx` | `GET /api/calendar/status` | `calendar.py`           | 取得行事曆服務狀態。                     |
| **行事曆統計**     | `CalendarPage.tsx` | `GET /api/calendar/stats` | `calendar.py`           | 取得行事曆統計資訊。                     |
| **純粹行事曆**     | `PureCalendarPage.tsx` | `GET /api/pure-calendar/events` | `pure_calendar.py`      | 純粹行事曆功能（無需認證）。             |
| **公文行事曆整合** | `DocumentPage.tsx` | `POST /api/document-calendar/sync-event` | `document_calendar.py` | 同步公文事件到 Google Calendar。        |

---

## 10. 發文字號管理 (Document Numbers)

| 前端功能描述       | 前端頁面 | API 端點 (Method & Path) | 相關後端檔案 (Endpoint) | 說明                                     |
| :----------------- | :------- | :----------------------- | :---------------------- | :--------------------------------------- |
| **發文字號頁面**   | `DocumentNumbersPage.tsx` | `GET /api/document-numbers/` | `document_numbers.py`   | 取得發文字號列表。                       |
| **發文字號統計**   | `DocumentNumbersPage.tsx` | `GET /api/document-numbers/stats` | `document_numbers.py`   | 取得發文字號統計資料。                   |
| **下一個字號**     | `DocumentCreatePage.tsx` | `GET /api/document-numbers/next-number` | `document_numbers.py`   | 取得下一個可用的發文字號。               |

---

## 11. 系統管理與監控 (System Management)

| 前端功能描述       | 前端頁面 | API 端點 (Method & Path) | 相關後端檔案 (Endpoint) | 說明                                     |
| :----------------- | :------- | :----------------------- | :---------------------- | :--------------------------------------- |
| **404 錯誤頁面**   | `NotFoundPage.tsx` | 無直接 API | 無後端檔案              | 處理路由錯誤和 404 狀態的頁面。          |
| **管理員儀表板**   | `AdminDashboardPage.tsx` | 相關端點 | `admin.py`              | 管理員專用儀表板。                       |
| **資料庫管理**     | `DatabaseManagementPage.tsx` | `GET /api/admin/database/info` | `admin.py`              | 獲取資料庫基本信息。                     |
| **系統監控**       | `SystemPage.tsx` | 相關端點 | `system_monitoring.py`  | 系統健康狀況監控。                       |
| **調試功能**       | 開發用途 | `GET /api/debug/*` | `debug.py`              | 各種調試和系統狀態查詢功能。             |

---

## 12. 報表與統計 (Reports & Analytics)

| 前端功能描述       | 前端頁面 | API 端點 (Method & Path) | 相關後端檔案 (Endpoint) | 說明                                     |
| :----------------- | :------- | :----------------------- | :---------------------- | :--------------------------------------- |
| **報表頁面**       | `ReportsPage.tsx` | `GET /api/documents/statistics` | `documents.py`          | 公文統計報表。                           |
| **機關統計**       | `AgenciesPage.tsx` | `GET /api/agencies/statistics` | `agencies.py`           | 機關單位分類統計資訊。                   |

---

## 13. 檔案管理 (File Management)

| 前端功能描述       | 前端頁面 | API 端點 (Method & Path) | 相關後端檔案 (Endpoint) | 說明                                     |
| :----------------- | :------- | :----------------------- | :---------------------- | :--------------------------------------- |
| **檔案上傳**       | 多個頁面 | `POST /api/files/upload` | `files.py`              | 檔案上傳功能。                           |
| **檔案下載**       | 多個頁面 | `GET /api/files/{id}/download` | `files.py`              | 檔案下載功能。                           |
| **檔案刪除**       | 多個頁面 | `DELETE /api/files/{id}` | `files.py`              | 檔案刪除功能。                           |

---

## 14. API 文件與開發工具 (API Documentation & Development Tools)

| 前端功能描述       | 前端頁面 | API 端點 (Method & Path) | 相關後端檔案 (Endpoint) | 說明                                     |
| :----------------- | :------- | :----------------------- | :---------------------- | :--------------------------------------- |
| **API 文件**       | `ApiDocumentationPage.tsx` | `GET /openapi.json` | FastAPI 自動生成        | 完整的 OpenAPI 3.1.0 規範文件。         |
| **API 映射顯示**   | `ApiMappingDisplayPage.tsx` | 無直接 API | 靜態顯示                | 顯示前端與後端 API 對應關係。            |
| **統一表單示例**   | `UnifiedFormDemoPage.tsx` | 無直接 API | 示例頁面                | 統一表單組件示例。                       |

---

## 15. 公共端點 (Public Endpoints)

| 前端功能描述       | 前端頁面 | API 端點 (Method & Path) | 相關後端檔案 (Endpoint) | 說明                                     |
| :----------------- | :------- | :----------------------- | :---------------------- | :--------------------------------------- |
| **公共狀態檢查**   | 各頁面   | `GET /api/public/*` | `public.py`             | 無需認證的公共狀態端點。                 |

---

## 摘要統計

### 前端頁面統計
- **總計頁面數**: 35 個
- **主要功能模組**: 15 個
- **管理功能頁面**: 8 個
- **業務功能頁面**: 27 個

### 後端 API 統計
- **總計 API 檔案**: 21 個
- **主要端點類別**: 15 個
- **認證端點**: 7 個
- **管理端點**: 多個
- **業務邏輯端點**: 多個

### 完整覆蓋的功能模組
1. ✅ **公文管理** - 完整 CRUD + 匯入匯出 + 搜尋統計
2. ✅ **承攬案件管理** - 完整 CRUD 操作
3. ✅ **廠商管理** - 完整 CRUD 操作
4. ✅ **案件廠商關聯** - 完整關聯管理
5. ✅ **認證系統** - 登入/註冊/OAuth/權限管理
6. ✅ **使用者管理** - 管理員功能完整
7. ✅ **網站管理** - 導覽列和配置管理
8. ✅ **行事曆功能** - 事件管理和 Google 整合
9. ✅ **發文字號管理** - 字號生成和統計
10. ✅ **系統監控** - 資料庫和系統狀態
11. ✅ **報表統計** - 各類數據分析
12. ✅ **檔案管理** - 上傳下載刪除
13. ✅ **API 文件** - 完整的開發工具
14. ✅ **管理後台** - 完整的管理功能
15. ✅ **公共服務** - 無需認證的端點

---

**文件版本**: v2.1.0
**最後更新**: 2026-01-08
**更新內容**:
- 2026-01-08: 更新日期格式為 ISO 8601
- 2025-09-15: 新增 9 個功能模組的完整映射
- 補充所有缺漏的前端頁面對應關係
- 新增前端頁面欄位以便開發參考
- 完善 API 端點與後端檔案的對應
- 新增統計摘要信息

**建議**:
- 定期檢查此文件與實際實現的一致性
- 新增功能時請同步更新此映射表
- 開發團隊應以 `/api/docs` 的 Swagger UI 為 API 規範參考
- 前端路由與此文件保持同步
