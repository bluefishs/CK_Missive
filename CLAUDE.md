# CK_Missive 公文管理系統 - Claude Code 配置

> **專案代碼**: CK_Missive
> **技術棧**: FastAPI + PostgreSQL + React + TypeScript + Ant Design
> **Claude Code 配置版本**: 1.8.0
> **最後更新**: 2026-01-19
> **參考**: [claude-code-showcase](https://github.com/ChrisWiles/claude-code-showcase), [superpowers](https://github.com/obra/superpowers)

---

## 🎯 專案概述

CK_Missive 是一套企業級公文管理系統，具備以下核心功能：

1. **公文管理** - 收發文登錄、流水序號自動編排、附件管理
2. **行事曆整合** - 公文截止日追蹤、Google Calendar 雙向同步
3. **專案管理** - 承攬案件管理、專案人員配置
4. **機關/廠商管理** - 往來單位維護、智慧匹配

---

## 📚 Skills 技能清單

### Slash Commands (可用指令)

| 指令 | 說明 | 檔案 |
|------|------|------|
| `/pre-dev-check` | ⚠️ **開發前強制檢查** (必用) | `.claude/commands/pre-dev-check.md` |
| `/route-sync-check` | 前後端路由一致性檢查 | `.claude/commands/route-sync-check.md` |
| `/api-check` | API 端點一致性檢查 | `.claude/commands/api-check.md` |
| `/type-sync` | 型別同步檢查 | `.claude/commands/type-sync.md` |
| `/dev-check` | 開發環境檢查 | `.claude/commands/dev-check.md` |
| `/data-quality-check` | 資料品質檢查 | `.claude/commands/data-quality-check.md` |
| `/db-backup` | 資料庫備份管理 | `.claude/commands/db-backup.md` |
| `/csv-import-validate` | CSV 匯入驗證 | `.claude/commands/csv-import-validate.md` |
| `/security-audit` | 🔒 **資安審計檢查** (新增) | `.claude/commands/security-audit.md` |
| `/performance-check` | ⚡ **效能診斷檢查** (新增) | `.claude/commands/performance-check.md` |

### 🦸 Superpowers 指令 (v4.0.3)

整合自 [obra/superpowers](https://github.com/obra/superpowers) 的進階開發工作流：

| 指令 | 說明 | 檔案 |
|------|------|------|
| `/superpowers:brainstorm` | 互動式設計精煉 - 在編碼前釐清需求 | `.claude/commands/superpowers/brainstorm.md` |
| `/superpowers:write-plan` | 建立詳細實作計畫 | `.claude/commands/superpowers/write-plan.md` |
| `/superpowers:execute-plan` | 批次執行計畫並進行檢查點審核 | `.claude/commands/superpowers/execute-plan.md` |

### 領域知識 Skills (自動載入)

以下 Skills 會根據關鍵字自動載入對應的領域知識：

| Skill 檔案 | 觸發關鍵字 | 說明 |
|------------|------------|------|
| `document-management.md` | 公文, document, 收文, 發文 | 公文管理領域知識 |
| `calendar-integration.md` | 行事曆, calendar, Google Calendar | 行事曆整合規範 |
| `api-development.md` | API, endpoint, 端點 | API 開發規範 |
| `database-schema.md` | schema, 資料庫, PostgreSQL | 資料庫結構說明 |
| `testing-guide.md` | test, 測試, pytest | 測試框架指南 |
| `frontend-architecture.md` | 前端, React, 認證, auth, 架構 | **前端架構規範 (v1.0.0)** |
| `error-handling.md` | 錯誤處理, error, exception, 例外 | **錯誤處理指南 (v1.0.0)** |
| `security-hardening.md` | 安全, security, 漏洞, XSS | **安全加固指南 (v1.0.0)** |
| `type-management.md` | 型別, type, Pydantic, TypeScript, BaseModel | **型別管理規範 (v1.0.0) - SSOT 架構** |

### 🦸 Superpowers Skills (v4.0.3)

整合自 [obra/superpowers](https://github.com/obra/superpowers) 的開發工作流技能：

| Skill | 觸發關鍵字 | 說明 |
|-------|-----------|------|
| `brainstorming` | 設計, design, 規劃 | 蘇格拉底式設計精煉 |
| `test-driven-development` | TDD, 測試驅動 | RED-GREEN-REFACTOR 循環 |
| `systematic-debugging` | 除錯, debug, 根因分析 | 4 階段根因追蹤流程 |
| `writing-plans` | 計畫, plan, 實作 | 詳細實作計畫撰寫 |
| `executing-plans` | 執行計畫, execute | 批次執行與檢查點 |
| `subagent-driven-development` | subagent, 子代理 | 兩階段審查的子代理開發 |
| `requesting-code-review` | 程式碼審查, code review | 審查前檢查清單 |
| `using-git-worktrees` | worktree, 分支 | 平行開發分支管理 |
| `verification-before-completion` | 驗證, 完成 | 確保修復真正完成 |

> 📁 位置: `.claude/skills/superpowers/`

### 共享 Skills 庫 (_shared)

專案包含可重複使用的共享 Skills：

| 類別 | Skill | 觸發關鍵字 | 說明 |
|------|-------|-----------|------|
| **後端模式** | `postgres-patterns` | PostgreSQL, query, index | PostgreSQL 最佳實踐 |
| **後端模式** | `websocket-patterns` | WebSocket, 即時, real-time | WebSocket 整合指南 |
| **共享實踐** | `security-patterns` | 安全, security, 防護 | 安全性最佳實踐 |
| **共享實踐** | `testing-patterns` | 測試, test, coverage | 測試模式指南 |
| **共享實踐** | `systematic-debugging` | 除錯, debug, 調試 | 系統化除錯方法 |
| **共享實踐** | `dangerous-operations-policy` | 危險操作, 刪除, 重置 | 危險操作政策 |
| **共享實踐** | `code-standards` | 程式碼規範, coding style | 程式碼標準 |

> 📁 位置: `.claude/skills/_shared/`

---

## 🤖 Agents 代理

專案提供以下專業化代理：

| Agent | 用途 | 檔案 |
|-------|------|------|
| Code Review | 程式碼審查 | `.claude/agents/code-review.md` |
| API Design | API 設計 | `.claude/agents/api-design.md` |
| Bug Investigator | Bug 調查 | `.claude/agents/bug-investigator.md` |

---

## 🔧 Hooks 自動化

### PreToolUse Hooks

在工具執行前自動觸發的檢查：

| Hook | 觸發條件 | 說明 | 檔案 |
|------|---------|------|------|
| `validate-file-location` | Write/Edit | 確認檔案位置符合架構規範 | `.claude/hooks/validate-file-location.ps1` |

### PostToolUse Hooks

在工具執行後自動觸發的操作：

| Hook | 觸發條件 | 說明 | 檔案 |
|------|---------|------|------|
| `typescript-check` | 修改 .ts/.tsx | 自動執行 TypeScript 編譯檢查 | `.claude/hooks/typescript-check.ps1` |
| `python-lint` | 修改 .py | 自動執行 Python 語法檢查 | `.claude/hooks/python-lint.ps1` |

### 手動執行 Hooks

| Hook | 說明 | 檔案 |
|------|------|------|
| `route-sync-check` | 檢查前後端路徑一致性 | `.claude/hooks/route-sync-check.ps1` |

---

## 📁 配置目錄結構

```
.claude/
├── commands/                    # Slash Commands
│   ├── pre-dev-check.md        # ⚠️ 開發前強制檢查 (必用)
│   ├── route-sync-check.md     # 前後端路由一致性檢查
│   ├── api-check.md            # API 端點一致性檢查
│   ├── type-sync.md            # 型別同步檢查
│   ├── dev-check.md            # 開發環境檢查
│   ├── data-quality-check.md   # 資料品質檢查
│   ├── db-backup.md            # 資料庫備份管理
│   ├── csv-import-validate.md  # CSV 匯入驗證
│   └── superpowers/            # 🦸 Superpowers 指令
│       ├── brainstorm.md       # 互動式設計精煉
│       ├── write-plan.md       # 建立實作計畫
│       └── execute-plan.md     # 批次執行計畫
├── skills/                      # 領域知識 Skills
│   ├── document-management.md  # 公文管理
│   ├── calendar-integration.md # 行事曆整合
│   ├── api-development.md      # API 開發
│   ├── database-schema.md      # 資料庫結構
│   ├── testing-guide.md        # 測試指南
│   ├── frontend-architecture.md # 前端架構規範
│   ├── error-handling.md       # 錯誤處理指南
│   ├── security-hardening.md   # 安全加固指南
│   ├── type-management.md      # 型別管理規範 (SSOT)
│   ├── _shared/                # 共享 Skills 庫
│   └── superpowers/            # 🦸 Superpowers Skills (v4.0.3)
│       ├── brainstorming/      # 設計精煉
│       ├── test-driven-development/ # TDD 循環
│       ├── systematic-debugging/    # 系統化除錯
│       ├── writing-plans/      # 計畫撰寫
│       ├── executing-plans/    # 計畫執行
│       └── ...                 # 其他技能
├── agents/                      # 專業代理
│   ├── code-review.md          # 程式碼審查
│   ├── api-design.md           # API 設計
│   └── bug-investigator.md     # Bug 調查
├── hooks/                       # 自動化鉤子
│   ├── README.md               # Hooks 說明
│   ├── typescript-check.ps1    # TypeScript 檢查
│   ├── python-lint.ps1         # Python 檢查
│   ├── validate-file-location.ps1 # 檔案位置驗證
│   └── route-sync-check.ps1    # 路徑同步檢查 (2026-01-12)
├── DEVELOPMENT_GUIDELINES.md   # 開發指引
├── MANDATORY_CHECKLIST.md      # ⚠️ 強制性開發檢查清單 (必讀)
└── settings.local.json         # 本地權限設定
```

---

## 🔐 認證與環境檢測規範

### 環境類型定義

| 環境類型 | 判斷條件 | 認證要求 |
|----------|----------|----------|
| `localhost` | hostname = localhost / 127.0.0.1 | Google OAuth |
| `internal` | 內網 IP (10.x / 172.16-31.x / 192.168.x) | **免認證** |
| `ngrok` | *.ngrok.io / *.ngrok-free.app | Google OAuth |
| `public` | 其他 | Google OAuth |

### 集中式認證檢測 (必須遵守)

**所有認證相關判斷必須使用 `config/env.ts` 的共用函數：**

```typescript
// ✅ 正確 - 使用共用函數
import { isAuthDisabled, isInternalIP, detectEnvironment } from '../config/env';

const authDisabled = isAuthDisabled();  // 自動判斷是否停用認證
const envType = detectEnvironment();    // 取得環境類型

// ❌ 禁止 - 自行定義檢測邏輯
const isInternal = () => { /* 重複的 IP 檢測邏輯 */ };
const authDisabled = import.meta.env.VITE_AUTH_DISABLED === 'true';
```

### 內網 IP 規則

```typescript
// config/env.ts 中的標準定義
const internalIPPatterns = [
  /^10\./,                           // 10.0.0.0 - 10.255.255.255 (Class A)
  /^172\.(1[6-9]|2[0-9]|3[0-1])\./,  // 172.16.0.0 - 172.31.255.255 (Class B)
  /^192\.168\./                       // 192.168.0.0 - 192.168.255.255 (Class C)
];
```

---

## ⚠️ 開發前強制檢視 (MANDATORY)

> **重要**：任何開發任務開始前，必須先完成對應規範檢視。

### 強制檢查清單

**檔案位置**: `.claude/MANDATORY_CHECKLIST.md`

| 任務類型 | 必讀檢查清單 |
|---------|-------------|
| 新增前端路由/頁面 | 清單 A - 前端路由開發 |
| 新增後端 API | 清單 B - 後端 API 開發 |
| 新增/修改導覽項目 | 清單 C - 導覽項目變更 |
| 修改認證/權限 | 清單 D - 認證權限變更 |
| 資料匯入功能 | 清單 E - 資料匯入功能 |
| 資料庫變更 | 清單 F - 資料庫變更 |
| Bug 修復 | 清單 G - Bug 修復 |
| **新增/修改型別定義** | **清單 H - 型別管理 (SSOT)** |

### 必須同步的三處位置

新增導覽項目時，**必須同步更新**：

1. `frontend/src/router/types.ts` - ROUTES 常數
2. `frontend/src/router/AppRouter.tsx` - Route 元素
3. `backend/app/scripts/init_navigation_data.py` - DEFAULT_NAVIGATION_ITEMS

### 違規後果

- 程式碼審查不通過
- 前後端資料不同步
- 系統運行異常

---

## 🚨 強制規範

### 1. API 端點一致性

**前端必須使用集中式端點管理**：
```typescript
// ✅ 正確 - 使用 API_ENDPOINTS
import { API_ENDPOINTS } from './endpoints';
apiClient.post(API_ENDPOINTS.DOCUMENTS.LIST, params);

// ❌ 禁止 - 硬編碼路徑
apiClient.post('/documents-enhanced/list', params);
```

### 2. 環境設定管理 (Single Source of Truth)

**架構原則**：所有環境設定統一使用專案根目錄的 `.env` 檔案。

| 位置 | 用途 | 規範 |
|------|------|------|
| `/.env` | 環境設定 (唯一來源) | 所有環境變數設定 |
| `/backend/.env` | **禁止存在** | 會導致設定衝突 |
| `/backend/.env.example` | 範本 | 僅供參考，不應直接使用 |

```bash
# ✅ 正確 - 設定檔位置
CK_Missive/
├── .env                    # 唯一的環境設定檔
├── .env.example            # 範本檔案
└── backend/
    └── .env.example        # 後端範本（僅供參考）

# ❌ 禁止 - 重複的設定檔
CK_Missive/
├── .env
└── backend/
    └── .env                # 不應存在！
```

**驗證設定一致性**：
```powershell
# 執行設定檢查腳本
.\scripts\check-config.ps1
```

### 3. 型別定義同步 (Single Source of Truth)

**架構原則**：每個實體型別只能有一個「真實來源」定義。

#### 後端型別管理

| 位置 | 用途 | 規範 |
|------|------|------|
| `backend/app/schemas/` | Pydantic Schema (唯一來源) | 所有 Request/Response 型別 |
| `backend/app/api/endpoints/` | API 端點 | **禁止**本地 BaseModel，必須從 schemas 匯入 |

```python
# ✅ 正確 - 從 schemas 匯入
from app.schemas.document import DocumentCreateRequest, DocumentUpdateRequest

# ❌ 禁止 - 本地定義 BaseModel
class DocumentCreateRequest(BaseModel):  # 不允許！
    ...
```

#### 前端型別管理

| 位置 | 用途 | 規範 |
|------|------|------|
| `frontend/src/types/api.ts` | 業務實體型別 (唯一來源) | User, Document, Agency 等 |
| `frontend/src/api/*.ts` | API 呼叫 | **禁止**本地 interface，必須從 types/api.ts 匯入 |

```typescript
// ✅ 正確 - 從 types/api.ts 匯入
import { User, Agency, OfficialDocument } from '../types/api';
export type { User, Agency };  // 重新匯出供外部使用

// ❌ 禁止 - 在 api/*.ts 中定義
export interface User { ... }  // 不允許！
```

#### 新增欄位流程

新增一個欄位時，只需修改以下兩處：
1. **後端**: `backend/app/schemas/{entity}.py`
2. **前端**: `frontend/src/types/api.ts`

其他檔案透過匯入自動取得新欄位。

### 4. 程式碼修改後自檢

```bash
# 前端 TypeScript 檢查
cd frontend && npx tsc --noEmit

# 後端 Python 語法檢查
cd backend && python -m py_compile app/main.py
```

### 5. 服務層架構 (v1.8.0)

**後端服務層分層原則**：

| 層級 | 位置 | 職責 |
|------|------|------|
| API 層 | `backend/app/api/endpoints/` | HTTP 處理、參數驗證、回應格式化 |
| Service 層 | `backend/app/services/` | 業務邏輯、資料處理、跨實體操作 |
| Repository 層 | `backend/app/extended/` | 資料存取、ORM 模型 |

**BaseService 繼承原則**：

| 服務類型 | 繼承 BaseService | 說明 |
|----------|------------------|------|
| 簡單 CRUD | ✅ 推薦 | VendorService, AgencyService |
| 複雜業務邏輯 | ❌ 不建議 | DocumentService (有行事曆整合、匹配策略) |

```python
# ✅ 簡單實體 - 繼承 BaseService
class ProjectService(BaseService[ContractProject, ProjectCreate, ProjectUpdate]):
    def __init__(self):
        super().__init__(ContractProject, "承攬案件")

# ✅ 複雜實體 - 獨立實現
class DocumentService:
    def __init__(self, db: AsyncSession, auto_create_events: bool = True):
        self.db = db
        self._agency_matcher = AgencyMatcher(db)  # 策略類別
```

### 6. 前端狀態管理架構 (v1.8.0)

**雙層狀態管理**：React Query (Server State) + Zustand (UI State)

| 層級 | 位置 | 職責 |
|------|------|------|
| React Query | `frontend/src/hooks/use*.ts` | API 快取、伺服器同步 |
| Zustand Store | `frontend/src/store/*.ts` | UI 狀態、篩選條件、分頁 |
| 整合 Hook | `frontend/src/hooks/use*WithStore.ts` | 結合兩者的統一介面 |

```typescript
// ✅ 使用整合 Hook（推薦）
import { useProjectsWithStore } from '../hooks';
const { projects, filters, setFilters, createProject } = useProjectsWithStore();

// ✅ 只需要 Server State
import { useProjects } from '../hooks';
const { data, isLoading } = useProjects(params);
```

---

## 📖 重要規範文件

| 文件 | 說明 |
|------|------|
| `.claude/MANDATORY_CHECKLIST.md` | ⚠️ **強制性開發檢查清單** (開發前必讀) |
| `.claude/skills/type-management.md` | 🆕 **型別管理規範 (SSOT 架構)** |
| `.claude/commands/type-sync.md` | 🆕 **型別同步檢查 v2.0.0** |
| `docs/DEVELOPMENT_STANDARDS.md` | 統一開發規範總綱 |
| `docs/specifications/API_ENDPOINT_CONSISTENCY.md` | API 端點一致性 v2.0.0 |
| `docs/specifications/TYPE_CONSISTENCY.md` | 型別一致性規範 |
| `docs/specifications/TESTING_FRAMEWORK.md` | 測試框架規範 |
| `@AGENT.md` | 開發代理指引 |

---

## 🔗 快速連結

### 開發環境
- 後端 API: http://localhost:8001/docs
- 前端開發: http://localhost:3000
- 資料庫: PostgreSQL 16 (Docker)

### 常用命令
```bash
# 啟動後端
cd backend && uvicorn app.main:app --reload --port 8001

# 啟動前端
cd frontend && npm run dev

# 資料庫連線
docker exec -it ck_missive_postgres_dev psql -U ck_user -d ck_documents
```

---

## 🔄 整合來源

本配置整合以下最佳實踐：

### [claude-code-showcase](https://github.com/ChrisWiles/claude-code-showcase)
- **Skills**: 可重複使用的領域知識文檔
- **Hooks**: 自動化工具鉤子 (PreToolUse, PostToolUse)
- **Agents**: 專業化任務代理
- **Commands**: Slash 指令快捷操作

### [superpowers](https://github.com/obra/superpowers) (v4.0.3)
完整軟體開發工作流，強調紀律性開發：
- **brainstorming**: 在編碼前進行蘇格拉底式設計精煉
- **test-driven-development**: 強制 RED-GREEN-REFACTOR 循環
- **systematic-debugging**: 4 階段根因追蹤流程
- **subagent-driven-development**: 子代理驅動的並行開發
- **writing-plans/executing-plans**: 詳細計畫與批次執行

**核心理念**:
- 測試驅動開發 (TDD) - 先寫測試
- 系統化優於臨時性 - 流程優於猜測
- 複雜度簡化 - 簡潔為首要目標
- 證據優於聲稱 - 驗證後才宣告成功

---

*配置維護: Claude Code Assistant*
*最後更新: 2026-01-19*
