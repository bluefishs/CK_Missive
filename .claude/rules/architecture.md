# 專案結構與架構

## 根目錄結構

```
CK_Missive/
├── .claude/                    # Claude Code 配置
├── backend/                    # FastAPI 後端
├── frontend/                   # React 前端
├── configs/                    # 外部配置 (PostgreSQL tuning, init.sql)
├── docs/                       # 文件目錄
├── scripts/                    # 腳本目錄 (啟動、維護、檢查)
├── .env                        # 環境設定 (唯一來源)
├── docker-compose.infra.yml    # 基礎設施 Compose (PostgreSQL+Redis)
├── docker-compose.dev.yml      # 全 Docker 開發 Compose
├── CLAUDE.md                   # 主配置
├── README.md                   # 專案說明
└── ecosystem.config.js         # PM2 配置
```

## 後端模型結構

ORM 模型統一位於 `backend/app/extended/models.py`，按 7 個模組分區：

| 模組 | 包含模型 |
|------|----------|
| 1. 關聯表 | project_vendor_association, project_user_assignment |
| 2. 基礎實體 | PartnerVendor, ContractProject, GovernmentAgency, User |
| 3. 公文模組 | OfficialDocument, DocumentAttachment |
| 4. 行事曆模組 | DocumentCalendarEvent, EventReminder |
| 5. 系統模組 | SystemNotification, UserSession, SiteNavigationItem, SiteConfiguration |
| 6. 專案人員模組 | ProjectAgencyContact, StaffCertification |
| 7. 桃園派工模組 | TaoyuanProject, TaoyuanDispatchOrder, TaoyuanDispatchProjectLink, etc. |

## 後端 API 結構

```
backend/app/api/endpoints/
├── documents/              # 公文 API (模組化)
│   ├── list.py, crud.py, stats.py, export.py, import_.py, audit.py
├── document_calendar/      # 行事曆 API (模組化)
├── taoyuan_dispatch/       # 桃園派工 API (模組化)
├── ai/                     # AI API
└── *.py                    # 其他 API 端點
```

## 前端元件結構

DocumentOperations 相關模組 (v1.13.0)：

```
frontend/src/components/document/operations/
├── types.ts                    # 型別定義
├── documentOperationsUtils.ts  # 工具函數
├── useDocumentOperations.ts    # 操作邏輯 Hook
├── useDocumentForm.ts          # 表單處理 Hook
├── CriticalChangeConfirmModal.tsx
├── DuplicateFileModal.tsx
├── ExistingAttachmentsList.tsx
├── FileUploadSection.tsx
└── index.ts                    # 統一匯出
```
