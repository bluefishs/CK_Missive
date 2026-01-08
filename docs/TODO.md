# 待辦事項與系統優化規劃

> 更新日期: 2026-01-08 (v8)
> 此文件記錄系統待實作的功能、優化建議與改進項目

---

## 近期完成 (2026-01-08)

### 文件架構重構
**狀態**: ✅ 完成
**完成日期**: 2026-01-08

**已完成項目**:
- [x] 建立 `docs/specifications/` 規範目錄
- [x] 遷移 6 個 SKILL 規範文件至 `docs/specifications/`
- [x] 新增 `TYPE_MAPPING.md` 型別對照表
- [x] 新增 `API_RESPONSE_FORMAT.md` API 回應格式規範
- [x] 新增 `API_ENDPOINT_CONSISTENCY.md` API 端點一致性規範
- [x] 新增 `PORT_CONFIGURATION.md` 端口配置規範
- [x] 新增 `TESTING_FRAMEWORK.md` 測試框架規劃
- [x] 更新 `@AGENT.md` 引用新規範路徑
- [x] 更新 `docs/README.md` 文件索引 (v2.1.0)
- [x] 更新 `docs/DATABASE_SCHEMA.md` (v2.0.0)
- [x] 清理根目錄舊規範文件
- [x] 移動報告文件至 `docs/reports/`

### 測試框架建置
**狀態**: ✅ 完成
**完成日期**: 2026-01-08

**後端測試 (pytest)**:
- [x] 建立 `tests/conftest.py` 共用 fixtures
- [x] 建立 `tests/unit/` 單元測試目錄
- [x] 建立 `tests/integration/` 整合測試目錄
- [x] 建立 `test_validators.py` 驗證器測試
- [x] 建立 `test_documents_api.py` API 整合測試
- [x] 新增 pytest-cov 覆蓋率支援

**前端測試 (Vitest)**:
- [x] 設定 `vitest.config.ts`
- [x] 建立 `tests/setup.ts` 環境設定
- [x] 建立 `tests/mocks/handlers.ts` MSW mock handlers
- [x] 建立範例測試檔案
- [x] 新增測試腳本 (`npm run test`, `test:coverage`)

**測試指令**:
```bash
# 後端測試
cd backend && pytest --cov=app --cov-report=term-missing

# 前端測試
cd frontend && npm run test:run
cd frontend && npm run test:coverage
```

---

## 高優先級

### 1. 附件備份機制
**狀態**: ✅ 完成
**建立日期**: 2026-01-07
**完成日期**: 2026-01-08

**已實作方案** (方案 3 - `/db-backup` Skill):
- [x] 手動執行 `/db-backup` 進行即時備份
- [x] 支援指定目標路徑 (`-TargetPath` 參數)
- [x] 分離備份模式 (`-DatabaseOnly`, `-AttachmentsOnly`)
- [x] 保留策略 (`-RetentionDays` 預設 7 天)
- [x] 備份日誌記錄

**使用方式**:
```powershell
# 完整備份
/db-backup
# 備份到外接硬碟
powershell db_backup.ps1 -TargetPath "D:\Backup"
```

---

### 2. 匯入預覽功能
**狀態**: ✅ 完成
**建立日期**: 2026-01-07
**完成日期**: 2026-01-08

**已完成項目**:
- [x] 後端 API `/documents-enhanced/import/excel/preview`
- [x] 顯示前 N 筆預覽資料 (預設 10 筆，最多 50 筆)
- [x] 欄位驗證 (必填欄位、類別、公文類型)
- [x] 標示重複公文字號
- [x] 檢查資料庫已存在紀錄
- [x] 統計預計新增/更新筆數
- [x] 前端三步驟流程 (upload -> preview -> result)

---

### 3. 服務層重構
**狀態**: ✅ 完成
**建立日期**: 2026-01-08
**完成日期**: 2026-01-08

**已完成項目**:
- [x] 建立 `ImportBaseService` 基礎類別 (`base/import_base.py`)
- [x] 統一字串清理邏輯 (`StringCleaners.clean_string`)
- [x] 統一日期解析邏輯 (`DateParsers.parse_date`)
- [x] 統一 doc_type 驗證 (`DocumentValidators.validate_doc_type`)
- [x] 統一錯誤回應結構 (`ServiceResponse`, `ImportResult`)
- [x] ExcelImportService 繼承 ImportBaseService
- [x] DocumentImportService 繼承 ImportBaseService (2026-01-08 新增)
- [x] CSV 處理器整合共用驗證器
- [x] 建立統一開發規範總綱 (`docs/DEVELOPMENT_STANDARDS.md`)

---

### 4. 行事曆整合優化
**狀態**: ✅ 完成
**建立日期**: 2026-01-08
**完成日期**: 2026-01-08

**已完成項目**:
- [x] 建立 `CalendarEventAutoBuilder` 事件自動建立器 (`services/calendar/event_auto_builder.py`)
- [x] 批次建立現有公文行事曆事件 (616 筆)
- [x] 修改 `ExcelImportService` 匯入時自動建立事件
- [x] 修改 `DocumentService` 匯入時自動建立事件
- [x] 啟用 `ReminderScheduler` 提醒排程器
- [x] 事件覆蓋率從 0.32% 提升至 100%
- [x] **Phase 1 整合式 UI** (2026-01-08)
  - [x] 建立 `IntegratedEventModal` 整合式事件建立元件
  - [x] 整合提醒設定到事件建立流程 (無需分步操作)
  - [x] 後端 API `/events/create-with-reminders` 支援一站式建立
  - [x] 自動發送專案成員通知
  - [x] Google Calendar 同步選項
- [x] **Phase 2 通知機制強化** (2026-01-08)
  - [x] NotificationCenter 新增 calendar_event, project_update 類型
  - [x] ProjectNotificationService 完整實作 (團隊成員通知)
  - [x] 事件建立時自動通知專案相關成員
  - [x] 後端 NotificationType 常數同步更新

**事件類型分佈**:
| 類型 | 數量 |
|------|------|
| reminder | 272 |
| reference | 154 |
| meeting | 133 |
| review | 58 |
| deadline | 4 |

---

## 中優先級

### 4. 匯出功能增強
**狀態**: 規劃中

**建議功能**:
- [ ] 篩選條件匯出（僅匯出符合條件的資料）
- [ ] 自訂欄位選擇（使用者可選擇要匯出的欄位）
- [ ] 匯出格式選擇（Excel / CSV / PDF）
- [ ] 匯出歷史記錄

---

### 5. 機關資料管理優化
**狀態**: 部分完成

**已完成**:
- [x] AgencyMatcher 智慧匹配機制
- [x] ProjectMatcher 案件匹配機制
- [x] 匯入時自動關聯 agency_id

**待實作**:
- [ ] 機關代碼對照表管理介面
- [ ] 機關資料批次更新功能

---

### 6. 承辦人功能啟用
**狀態**: 規劃中

**現況**: `assignee` 欄位存在但無資料（0 筆）

**建議方案**:
- 連結 `users` 表（目前 11 筆使用者）
- 公文指派功能
- 承辦人篩選與統計

---

## 低優先級

### 7. 效能優化
**狀態**: 監控中

**觀察項目**:
- 大量匯出時的記憶體使用
- 分頁查詢效能
- 附件上傳/下載速度

---

### 8. 使用者體驗改進
**狀態**: 蒐集需求中

**可能項目**:
- 批次操作功能
- 快捷鍵支援
- 自訂檢視設定
- 匯出進度提示

---

### 9. 技術債務清理
**狀態**: 進行中
**建立日期**: 2026-01-08

| 項目 | 風險等級 | 說明 | 狀態 |
|------|----------|------|------|
| 文件架構 | 低 | 規範文件統一至 docs/specifications/ | ✅ 完成 |
| API 版本管理 | 低 | 建立 `/api/v1/` 前綴 | 待實作 |
| 錯誤處理統一 | 中 | 部分 API 錯誤格式不一致 | 規範已建立 |
| 測試覆蓋率 | 中 | 缺乏自動化測試 | 規劃完成 |
| 認證模式 | 低 | 開發模式下認證停用 | 待實作 |

---

## 已完成

### 匯入智慧關聯機制 (2026-01-08)
- [x] Excel 匯入整合 AgencyMatcher（發文/受文機關智慧匹配）
- [x] Excel 匯入整合 ProjectMatcher（承攬案件智慧匹配）
- [x] 重複公文字號檢查機制（doc_number 防呆）
- [x] 修復 "None" 字串問題（新增 `_clean_string` 方法）
- [x] 修復批次匯入流水號重複問題（記憶體計數器）
- [x] 批次更新歷史資料 agency_id（194 筆）
- [x] 清理 content/notes 欄位 "None" 字串（152 筆）

### 系統架構優化 (2026-01-08 下午)
- [x] 建立 API 回應輔助模組 (`api/response_helper.py`)
- [x] 更新服務層架構文件（新增 ImportBaseService 章節）
- [x] 執行系統整合測試（全部通過）
- [x] 驗證 ServiceResponse 與驗證器功能

### 前端表單優化 (2026-01-08)
- [x] 新增收發文紀錄頁面標題調整
- [x] 受文單位、收文日期預設值
- [x] 類別切換動態欄位連動
- [x] 修復 DOM 巢狀警告（DocumentImport.tsx）

### Excel 匯入功能 (2026-01-07)
- [x] 建立 Excel 匯入服務 (`excel_import_service.py`)
- [x] 新增 `/documents-enhanced/import/excel` 端點
- [x] 新增 `/documents-enhanced/import/excel/template` 範本下載
- [x] 前端統一匯入 UI (`DocumentImport.tsx`)
- [x] CSV 匯入更名為「電子公文檔匯入」
- [x] Excel 匯入命名為「手動公文匯入」
- [x] 支援公文ID判斷更新/新增

### Excel 匯出功能修復 (2026-01-07)
- [x] 新增 `/documents-enhanced/export/excel` 端點
- [x] 修正中文檔名編碼（RFC 5987 UTF-8）
- [x] CORS 暴露 Content-Disposition header
- [x] 前端支援 UTF-8 檔名解析
- [x] 移除 10 筆限制，支援全部匯出
- [x] 修正 CSV 匯入欄位對應（發文日期 → send_date）
- [x] 修正 CSV 匯入欄位對應（類別 → doc_type）
- [x] 修復現有 173 筆發文資料的 send_date
- [x] 修復現有 8 筆 doc_type 錯誤資料（收文/發文 → 函）
- [x] 新增 doc_type 白名單驗證
- [x] 調整匯出欄位順序（17 欄）
- [x] 新增公文ID欄位
- [x] 附件紀錄改為統計數量
- [x] 移除承辦人、雲端連結欄位
- [x] 機關名稱清理代碼

### 刪除公文同步刪除附件 (2026-01-07)
- [x] 刪除公文時同步刪除實體附件檔案
- [x] 自動清理空的公文資料夾 (`doc_{id}/`)
- [x] 資料庫 CASCADE 刪除附件記錄

---

## 系統現況統計 (2026-01-08 更新)

| 資料表 | 筆數 |
|--------|------|
| documents | 618 |
| document_attachments | 3 |
| government_agencies | 17 |
| contract_projects | 17 |
| users | 11 |

### 資料關聯完整性
| 欄位 | 有值筆數 | 完整率 |
|------|----------|--------|
| sender_agency_id | 585 | 94.7% |
| receiver_agency_id | 618 | 100% |
| contract_project_id | 497 | 80.4% |
| notes | 64 | 10.4% |

### 公文類型分佈
| 類別 | 公文類型 | 筆數 |
|------|----------|------|
| 收文 | 函 | 380+ |
| 收文 | 開會通知單 | 51 |
| 收文 | 會勘通知單 | 14 |
| 發文 | 函 | 167 |
| 發文 | 開會通知單 | 6 |

---

## 相關文件

- `docs/DEVELOPMENT_STANDARDS.md` - **統一開發規範總綱 (強制遵守)**
- `docs/reports/SYSTEM_REVIEW_20260108.md` - 系統全面檢視報告 (最新)
- `docs/reports/ARCHITECTURE_REVIEW_20260108.md` - 系統架構檢視報告
- `docs/reports/SYSTEM_SPECIFICATION_UPDATE_20260108.md` - 系統規範更新報告
- `docs/ERROR_HANDLING_GUIDE.md` - 錯誤處理指南
- `docs/reports/SYSTEM_OPTIMIZATION_REPORT_20260107.md` - 系統優化報告
- `docs/reports/EXCEL_EXPORT_FIX_REPORT_20260107.md` - Excel 匯出修正報告
- `docs/document_fields_mapping.csv` - 資料庫欄位對照表
- `docs/CSV_IMPORT_MAINTENANCE.md` - CSV 匯入維護指南
- `docs/DATABASE_SCHEMA.md` - 資料庫架構文件
- `docs/wiki/Service-Layer-Architecture.md` - 服務層架構說明
- `.claude/DEVELOPMENT_GUIDELINES.md` - 開發指引
