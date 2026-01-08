# CK_Missive 公文管理系統 - Claude Code 配置

> **專案代碼**: CK_Missive
> **技術棧**: FastAPI + PostgreSQL + React + TypeScript + Ant Design
> **Claude Code 配置版本**: 1.0.0
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
| `/data-quality-check` | 資料品質檢查 | `.claude/commands/data-quality-check.md` |
| `/db-backup` | 資料庫備份管理 | `.claude/commands/db-backup.md` |
| `/csv-import-validate` | CSV 匯入驗證 | `.claude/commands/csv-import-validate.md` |
| `/api-check` | API 端點一致性檢查 | `.claude/commands/api-check.md` |
| `/type-sync` | 型別同步檢查 | `.claude/commands/type-sync.md` |
| `/dev-check` | 開發環境檢查 | `.claude/commands/dev-check.md` |

### 領域知識 Skills (自動載入)

以下 Skills 會根據關鍵字自動載入對應的領域知識：

| Skill 檔案 | 觸發關鍵字 | 說明 |
|------------|------------|------|
| `document-management.md` | 公文, document, 收文, 發文 | 公文管理領域知識 |
| `calendar-integration.md` | 行事曆, calendar, Google Calendar | 行事曆整合規範 |
| `api-development.md` | API, endpoint, 端點 | API 開發規範 |
| `database-schema.md` | schema, 資料庫, PostgreSQL | 資料庫結構說明 |
| `testing-guide.md` | test, 測試, pytest | 測試框架指南 |

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
│   ├── data-quality-check.md   # 資料品質檢查
│   ├── db-backup.md            # 資料庫備份管理
│   ├── csv-import-validate.md  # CSV 匯入驗證
│   ├── api-check.md            # API 端點一致性檢查
│   ├── type-sync.md            # 型別同步檢查
│   └── dev-check.md            # 開發環境檢查
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
└── settings.local.json         # 本地權限設定
```

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
*最後更新: 2026-01-09*
