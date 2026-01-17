# CK_Missive Claude Code 配置變更日誌

> 本文件記錄 `.claude/` 目錄下所有配置文件的變更歷史

---

## [1.5.0] - 2026-01-15

### 新增
- `PUT /auth/profile` - 更新個人資料 API 端點
- `PUT /auth/password` - 修改密碼 API 端點
- `ProfileUpdate` schema 定義
- 共享 Skills 庫文檔化至 CLAUDE.md
- 本 CHANGELOG.md 變更日誌

### 改進
- `useAuthGuard.ts` v1.3.0 - superuser 角色現在擁有所有角色權限
- `auth.py` v2.2 - 新增個人資料與密碼管理端點
- `SiteManagementPage.tsx` - 修復 ValidPath 型別錯誤
- CLAUDE.md 升級至 v1.5.0

### 修復
- 修復 superuser 無法訪問管理員頁面的權限問題
- 修復 ProfilePage 的 404 錯誤 (缺失 API 端點)

---

## [1.4.0] - 2026-01-12 ~ 2026-01-14

### 新增
- `/security-audit` 資安審計檢查指令
- `/performance-check` 效能診斷檢查指令
- `navigation_validator.py` 路徑白名單驗證機制
- 導覽路徑下拉選單自動載入功能
- `route-sync-check.ps1` 路徑同步檢查 Hook
- API Rate Limiting (slowapi)
- Structured Logging (structlog)
- 擴展健康檢查端點 (CPU/Memory/Disk/Scheduler)

### 改進
- `route-sync-check.md` 升級至 v2.0.0 - 新增白名單驗證
- `api-check.md` 升級至 v2.1.0 - POST-only 安全模式檢查
- `MANDATORY_CHECKLIST.md` 升級至 v1.2.0 - 新增導覽系統架構說明
- `frontend-architecture.md` 新增至 Skills (v1.0.0)
- `EntryPage.tsx` 修復快速進入未設定 user_info 問題

### 修復
- bcrypt 版本降級至 4.0.1 (解決 Windows 相容性)
- 動態 CORS 支援多來源
- 統一日誌編碼 (UTF-8)
- 進程管理腳本優化

---

## [1.3.0] - 2026-01-10 ~ 2026-01-11

### 新增
- 環境智慧偵測登入機制 (localhost/internal/ngrok/public)
- 內網 IP 免認證快速進入功能
- Google OAuth 登入整合
- 新帳號審核機制
- 網域白名單檢查

### 改進
- `EntryPage.tsx` 升級至 v2.5.0 - 三種登入方式
- `useAuthGuard.ts` v1.2.0 - 支援內網繞過認證
- `config/env.ts` 集中式環境偵測

---

## [1.2.0] - 2026-01-08 ~ 2026-01-09

### 新增
- `/db-backup` 資料庫備份管理指令
- `/csv-import-validate` CSV 匯入驗證指令
- `/data-quality-check` 資料品質檢查指令
- 備份排程器 (每日凌晨 2:00)

### 改進
- 公文管理 CRUD 完善
- 行事曆 Google Calendar 雙向同步

---

## [1.1.0] - 2026-01-05 ~ 2026-01-07

### 新增
- `/pre-dev-check` 開發前強制檢查指令
- `/route-sync-check` 前後端路由檢查指令
- `/api-check` API 端點一致性檢查指令
- `/type-sync` 型別同步檢查指令
- `MANDATORY_CHECKLIST.md` 強制性開發檢查清單
- `DEVELOPMENT_GUIDELINES.md` 開發指引

### 改進
- Hooks 系統建立 (typescript-check, python-lint)
- Agents 建立 (code-review, api-design)

---

## [1.0.0] - 2026-01-01 ~ 2026-01-04

### 初始版本
- 專案架構建立
- FastAPI + PostgreSQL 後端
- React + TypeScript + Ant Design 前端
- 基本公文管理功能
- 基本認證系統

---

## 版本號說明

採用語義化版本 (SemVer):
- **Major (主版本)**: 重大架構變更或不相容更新
- **Minor (次版本)**: 新增功能，向後相容
- **Patch (修補版本)**: Bug 修復，向後相容

---

*維護者: Claude Code Assistant*
