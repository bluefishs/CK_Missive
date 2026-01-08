# CK Missive 文件中心

> 版本: 2.0.0
> 最後更新: 2026-01-08
> 乾坤測繪公文管理系統 (CK_Missive) 技術文件索引

---

## 快速導覽

| 我要... | 請參閱 |
|---------|--------|
| 了解開發規範 | [DEVELOPMENT_STANDARDS.md](./DEVELOPMENT_STANDARDS.md) |
| 查看資料庫結構 | [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) |
| 了解 API 對應 | [FRONTEND_API_MAPPING.md](./FRONTEND_API_MAPPING.md) |
| 查看待辦事項 | [TODO.md](./TODO.md) |
| 處理 CSV 匯入 | [CSV_IMPORT_MAINTENANCE.md](./CSV_IMPORT_MAINTENANCE.md) |

---

## 文件結構

```
docs/
├── README.md                      ← 你在這裡
├── DEVELOPMENT_STANDARDS.md       # 🔴 統一開發規範總綱 (必讀)
├── TODO.md                        # 待辦事項與規劃
├── DATABASE_SCHEMA.md             # 資料庫結構
├── FRONTEND_API_MAPPING.md        # 前後端 API 對應
├── CSV_IMPORT_MAINTENANCE.md      # CSV 匯入維護指南
├── ERROR_HANDLING_GUIDE.md        # 錯誤處理指南
├── CONTRIBUTING.md                # 貢獻指南
├── DEVELOPMENT_GUIDE.md           # 開發指南
├── DOCUMENT_CENTER_DESIGN.md      # 文管中心設計
├── SYSTEM_MAINTENANCE.md          # 系統維護指南
├── FILTER_OPTIMIZATION.md         # 篩選器優化
│
├── specifications/                # 🔴 規範文件 (強制遵守)
│   ├── TYPE_CONSISTENCY.md        # 型別一致性規範
│   ├── SCHEMA_VALIDATION.md       # Schema 驗證規範
│   ├── TYPE_MAPPING.md            # 前後端型別對照表
│   ├── API_RESPONSE_FORMAT.md     # API 回應格式規範
│   ├── API_ENDPOINT_CONSISTENCY.md # API 端點一致性規範
│   ├── PORT_CONFIGURATION.md      # 端口配置規範
│   ├── CSV_IMPORT.md              # CSV 匯入規範
│   ├── PROJECT_CODE.md            # 專案編號規範
│   └── TESTING_FRAMEWORK.md       # 測試框架規劃
│
├── architecture/                  # 架構設計文件
│   ├── PROJECT_OPTIMIZATION_INTEGRATION_PLAN.md
│   └── VERSION_MANAGEMENT_STRATEGY.md
│
├── wiki/                          # 技術 Wiki
│   ├── Home.md
│   ├── Backend-API-Overview.md
│   ├── Frontend-Architecture.md
│   ├── Frontend-Components.md
│   ├── Database-Models.md
│   ├── Service-Layer-Architecture.md
│   └── CODEWIKI.md
│
└── reports/                       # 系統報告
    ├── SYSTEM_REVIEW_20260108.md
    ├── ARCHITECTURE_REVIEW_20260108.md
    ├── SYSTEM_SPECIFICATION_UPDATE_20260108.md
    ├── CALENDAR_OPTIMIZATION_20260108.md
    └── ...
```

---

## 核心規範文件

### 🔴 必讀文件 (MANDATORY)

| 文件 | 說明 | 強制等級 |
|------|------|----------|
| [DEVELOPMENT_STANDARDS.md](./DEVELOPMENT_STANDARDS.md) | **統一開發規範總綱** | 🔴 必讀 |
| [specifications/TYPE_CONSISTENCY.md](./specifications/TYPE_CONSISTENCY.md) | 型別一致性規範 | 🔴 必須 |
| [specifications/SCHEMA_VALIDATION.md](./specifications/SCHEMA_VALIDATION.md) | Schema 驗證規範 | 🔴 必須 |
| [specifications/API_ENDPOINT_CONSISTENCY.md](./specifications/API_ENDPOINT_CONSISTENCY.md) | API 端點一致性 | 🔴 必須 |
| [specifications/PORT_CONFIGURATION.md](./specifications/PORT_CONFIGURATION.md) | 端口配置規範 | 🔴 必須 |
| [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) | 資料庫架構 | 🔴 必須 |

### 🟡 相關時參閱

| 文件 | 說明 | 適用情境 |
|------|------|----------|
| [specifications/TYPE_MAPPING.md](./specifications/TYPE_MAPPING.md) | 型別對照表 | 前後端整合時 |
| [specifications/API_RESPONSE_FORMAT.md](./specifications/API_RESPONSE_FORMAT.md) | API 回應格式 | 開發 API 時 |
| [specifications/CSV_IMPORT.md](./specifications/CSV_IMPORT.md) | CSV 匯入規範 | 開發匯入功能時 |
| [specifications/PROJECT_CODE.md](./specifications/PROJECT_CODE.md) | 專案編號規範 | 開發案件功能時 |
| [specifications/TESTING_FRAMEWORK.md](./specifications/TESTING_FRAMEWORK.md) | 測試框架規劃 | 開發測試時 |
| [FRONTEND_API_MAPPING.md](./FRONTEND_API_MAPPING.md) | API 對應表 | 開發 API 時 |

### 🟢 參考文件

| 文件 | 說明 |
|------|------|
| [wiki/Service-Layer-Architecture.md](./wiki/Service-Layer-Architecture.md) | 服務層架構說明 |
| [wiki/Frontend-Architecture.md](./wiki/Frontend-Architecture.md) | 前端架構說明 |
| [wiki/Backend-API-Overview.md](./wiki/Backend-API-Overview.md) | 後端 API 總覽 |

---

## 開發檢查清單

### 每次提交前

```bash
# 1. TypeScript 型別檢查 (必須 0 錯誤)
cd frontend && npx tsc --noEmit

# 2. 建置檢查 (必須成功)
cd frontend && npm run build
```

### 新增欄位時

1. [ ] 更新 `backend/app/extended/models.py`
2. [ ] 建立 Alembic migration
3. [ ] 更新 `backend/app/schemas/*.py`
4. [ ] 更新 `frontend/src/api/*Api.ts`
5. [ ] 更新 `docs/DATABASE_SCHEMA.md`
6. [ ] 更新 `docs/specifications/TYPE_MAPPING.md`

### 新增 API 時

1. [ ] 建立後端端點
2. [ ] 更新 Swagger 文件
3. [ ] 建立前端 API 方法
4. [ ] 更新 `docs/FRONTEND_API_MAPPING.md`

---

## 系統概況

### 技術棧

| 層級 | 技術 |
|------|------|
| 前端 | React 18 + TypeScript + Ant Design + React Query |
| 後端 | FastAPI + SQLAlchemy + Pydantic |
| 資料庫 | PostgreSQL 15 (Docker) |
| 快取 | Redis (可選) |
| 部署 | Docker Compose |

### 主要功能模組

| 模組 | 說明 |
|------|------|
| 公文管理 | 收發文登錄、匯入、匯出、查詢 |
| 承攬案件 | 案件建立、追蹤、廠商關聯 |
| 行事曆 | 事件管理、Google Calendar 同步 |
| 使用者 | 帳號管理、權限控制 |
| 系統管理 | 資料庫管理、網站配置 |

---

## 聯絡資訊

- **專案維護**: 乾坤測繪開發團隊
- **技術支援**: 系統管理員
- **文件更新**: Claude Code Assistant

---

## 變更記錄

| 日期 | 版本 | 變更內容 |
|------|------|----------|
| 2026-01-08 | v2.1.0 | 新增 API 端點、端口配置、回應格式規範 |
| 2026-01-08 | v2.0.0 | 重建文件索引，新增規範目錄結構 |
| 2025-09-10 | v1.0.0 | 初始建立 |
