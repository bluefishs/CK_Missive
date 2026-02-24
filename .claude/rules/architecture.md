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

## 後端 Service 層結構

```
backend/app/services/
├── base/                       # 基礎服務 (ImportBaseService, ServiceResponse)
├── ai/                         # AI 服務
│   ├── embedding_manager.py    # Embedding 管理與覆蓋率統計
│   ├── entity_extraction_service.py  # NER 實體提取
│   ├── relation_graph_service.py     # 知識圖譜建構 (v1.0.0)
│   └── natural_search_service.py     # 自然語言搜尋
├── taoyuan/                    # 桃園派工服務
├── backup/                     # 備份服務套件 (v3.0.0)
│   ├── __init__.py             # BackupService (組合 4 個 Mixin)
│   ├── utils.py                # Docker 偵測、路徑、環境、日誌
│   ├── db_backup.py            # PostgreSQL pg_dump/restore
│   ├── attachment_backup.py    # 附件增量備份
│   └── scheduler.py            # 備份建立/列表/刪除、異地同步
├── backup_scheduler.py         # 備份排程器 + 異地自動同步 (v2.0.0)
├── system_health_service.py    # 系統健康檢查 (含備份狀態)
├── agency_service.py           # 機關服務
├── document_service.py         # 公文服務
├── project_service.py          # 專案服務
├── vendor_service.py           # 廠商服務
├── audit_service.py            # 審計服務 (獨立 session)
└── *_service.py                # 其他業務服務
```

## 後端 API 結構

```
backend/app/api/endpoints/
├── documents/              # 公文 API (模組化)
│   ├── list.py, crud.py, stats.py, export.py, import_.py, audit.py
├── document_calendar/      # 行事曆 API (模組化)
├── taoyuan_dispatch/       # 桃園派工 API (模組化)
├── ai/                     # AI API (薄端點層，邏輯在 services/ai/)
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

## 前端型別 SSOT (v1.60.0)

```
frontend/src/types/
├── api.ts              # 業務實體型別 (User, Agency, Document, Project 等)
├── ai.ts               # AI 功能型別 (GraphNode, IntentParsedResult 等)
├── document.ts         # 公文專用型別 (DocumentCreate, DocumentUpdate)
├── forms.ts            # 表單共用型別
└── admin-system.ts     # 系統管理型別
```

## 前端全域錯誤處理 (v1.60.0)

```
frontend/src/api/errors.ts          # ApiException + ApiErrorBus 事件匯流排
frontend/src/api/client.ts          # Axios 攔截器 → apiErrorBus.emit()
frontend/src/components/common/
├── GlobalApiErrorNotifier.tsx       # 訂閱 ApiErrorBus，自動顯示 403/5xx/網路錯誤
└── ...
```

錯誤分流規則：
- **業務錯誤** (400/409/422): 元件自行 catch 處理
- **全域錯誤** (403/5xx/網路): `GlobalApiErrorNotifier` 自動通知，3 秒去重
