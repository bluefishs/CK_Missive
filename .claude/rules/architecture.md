# 專案結構與架構（總覽）

> 本檔為入口索引。詳細清單分拆於後端 / 前端專檔，依需要開啟，避免每次 session 載入全部。

## 根目錄結構

```
CK_Missive/
├── .claude/                    # Claude Code 配置
├── backend/                    # FastAPI 後端 → 詳 architecture-backend.md
├── frontend/                   # React 前端  → 詳 architecture-frontend.md
├── configs/                    # 外部配置 (PostgreSQL tuning, init.sql)
├── docs/                       # 文件目錄
├── scripts/                    # 腳本目錄（分類：dev/checks/health/deploy/init/backup/archive）
├── wiki/                       # LLM Wiki 產出 (Karpathy 4-Phase) → 詳 skills/wiki-authoring.md
├── .env                        # 環境設定（唯一來源）
├── docker-compose.infra.yml    # 基礎設施 Compose (PostgreSQL+Redis)
├── docker-compose.dev.yml      # 全 Docker 開發 Compose
├── backend/config/
│   ├── agent-policy.yaml       # Agent 路由/工具/回退策略
│   ├── inference-profiles.yaml # 推理 Profile (6 profiles)
│   └── remote_backup.json      # 異地備份配置
├── CLAUDE.md                   # 主配置
├── README.md                   # 專案說明
└── ecosystem.config.js         # PM2 配置
```

## 詳細結構檔索引

| 範圍 | 檔案 | 內容 |
|---|---|---|
| 後端 | [`architecture-backend.md`](./architecture-backend.md) | Models / Services / API endpoints / Repositories |
| 前端 | [`architecture-frontend.md`](./architecture-frontend.md) | Pages / Hooks / 型別 SSOT / 錯誤處理 |
| AI Wiki | [`../skills/wiki-authoring.md`](../skills/wiki-authoring.md) | LLM Wiki 4-Phase 規範 |

## 治理金字塔（v6.10 候選 - 2026-05-18）

> 從「該長什麼樣」到「上線前對齊」到「上線後監控」到「每日自動巡檢」四層。

```
docs/architecture/STANDARD_REFERENCE.md           ← 該長什麼樣（範本）
       ↓
docs/architecture/MODULARIZATION_STANDARDS_v1.md  ← 上線前對齊（落地門檻）
       ↓
.claude/rules/adr-anti-half-wired-sop.md          ← ADR 級半接通防範
       ↓
docs/architecture/CAPABILITY_GOVERNANCE.md        ← 上線後持續監控
       ↓
docs/architecture/OPTIMIZATION_PIPELINE.md        ← 每日自動巡檢
```

執行工具：
- `scripts/checks/capability_usage_audit.py`（fitness step 23）
- `backend/app/services/optimization_pipeline_orchestrator.py`（每日 cron）
- `scripts/install-template-to.sh` 擴 standards/pipeline/capability 跨 repo 部署

## 分層職責（摘要）

| 層級 | 位置 | 職責 |
|---|---|---|
| API | `backend/app/api/endpoints/` | HTTP 處理、參數驗證 |
| Service | `backend/app/services/` | 業務邏輯（11 AI 子包 + 領域服務） |
| Repository | `backend/app/repositories/` (34 類別) | 資料存取、ORM 查詢 |
| Model | `backend/app/extended/models/` | ORM 模型定義 |
| 前端資料 | `frontend/src/hooks/` | React Query + Zustand 雙層 |
| 前端型別 | `frontend/src/types/` | SSOT（barrel re-export）|

> 詳細清單請讀對應拆分檔。
