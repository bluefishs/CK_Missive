# CK_Missive 公文管理系統 - Claude Code 配置

> **專案代碼**: CK_Missive
> **技術棧**: FastAPI + PostgreSQL + React + TypeScript + Ant Design
> **Claude Code 配置版本**: 1.3.0
> **最後更新**: 2026-01-11
> **參考**: [claude-code-showcase](https://github.com/ChrisWiles/claude-code-showcase)

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
│   └── csv-import-validate.md  # CSV 匯入驗證
├── skills/                      # 領域知識 Skills
│   ├── document-management.md  # 公文管理
│   ├── calendar-integration.md # 行事曆整合
│   ├── api-development.md      # API 開發
│   ├── database-schema.md      # 資料庫結構
│   └── testing-guide.md        # 測試指南
├── agents/                      # 專業代理
│   ├── code-review.md          # 程式碼審查
│   ├── api-design.md           # API 設計
│   └── bug-investigator.md     # Bug 調查
├── hooks/                       # 自動化鉤子
│   ├── README.md               # Hooks 說明
│   ├── typescript-check.ps1    # TypeScript 檢查
│   ├── python-lint.ps1         # Python 檢查
│   └── validate-file-location.ps1 # 檔案位置驗證
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

### 2. 型別定義同步

- 後端 Schema: `backend/app/schemas/`
- 前端型別: `frontend/src/types/api.ts`
- 兩者必須保持同步

### 3. 程式碼修改後自檢

```bash
# 前端 TypeScript 檢查
cd frontend && npx tsc --noEmit

# 後端 Python 語法檢查
cd backend && python -m py_compile app/main.py
```

---

## 📖 重要規範文件

| 文件 | 說明 |
|------|------|
| `.claude/MANDATORY_CHECKLIST.md` | ⚠️ **強制性開發檢查清單** (開發前必讀) |
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

本配置參考 [claude-code-showcase](https://github.com/ChrisWiles/claude-code-showcase) 最佳實踐：

- **Skills**: 可重複使用的領域知識文檔
- **Hooks**: 自動化工具鉤子 (PreToolUse, PostToolUse)
- **Agents**: 專業化任務代理
- **Commands**: Slash 指令快捷操作

---

*配置維護: Claude Code Assistant*
*最後更新: 2026-01-11*
