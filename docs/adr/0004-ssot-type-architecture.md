# ADR-0004: 前後端型別 Single Source of Truth (SSOT) 架構

> **狀態**: accepted
> **日期**: 2026-01-17
> **決策者**: 開發團隊
> **關聯**: CHANGELOG v1.6.0, `.claude/rules/development-rules.md`

## 背景

在專案初期，型別定義分散在多個位置：

- 後端 API 端點檔案中直接定義 `BaseModel`
- 前端 API 呼叫檔案中定義 `interface`
- 元件檔案中定義本地型別
- Schema 檔案中定義 Pydantic 模型

這導致了嚴重的**型別漂移（Type Drift）**問題：

1. 後端新增欄位後，前端未同步更新，造成執行時期錯誤
2. 同一實體在不同檔案中有不同的型別定義，語意不一致
3. 修改一個欄位需要在多處搜尋並逐一更新，容易遺漏
4. TypeScript 編譯通過但執行時期資料結構不符預期

## 決策

建立**嚴格的型別唯一來源（SSOT）架構**，每個實體型別只能有一個權威定義：

### 後端（Pydantic Schema）

| 位置 | 角色 |
|------|------|
| `backend/app/schemas/*.py` | 唯一型別來源 |
| `backend/app/api/endpoints/` | **禁止**定義本地 `BaseModel` |

```python
# 正確 — 從 schemas 匯入
from app.schemas.document import DocumentCreateRequest, DocumentUpdateRequest

# 禁止 — 端點檔案中本地定義
class DocumentCreateRequest(BaseModel): ...  # 不允許
```

### 前端（TypeScript 型別檔案）

| 檔案 | 職責 |
|------|------|
| `frontend/src/types/api.ts` | 業務實體型別（User, Agency, Document, Project 等） |
| `frontend/src/types/ai.ts` | AI 功能型別（GraphNode, IntentParsedResult 等） |
| `frontend/src/types/document.ts` | 公文專用型別（DocumentCreate, DocumentUpdate） |
| `frontend/src/types/forms.ts` | 表單共用型別 |
| `frontend/src/types/admin-system.ts` | 系統管理型別 |

```typescript
// 正確 — 從 types/ 匯入
import { User, Agency, OfficialDocument } from '../types/api';

// 禁止 — 在 api/*.ts 或元件中定義
export interface User { ... }  // 不允許
```

### 新增欄位標準流程

新增一個欄位只需修改兩處：

1. **後端**：`backend/app/schemas/{entity}.py` — Pydantic Schema
2. **前端**：`frontend/src/types/api.ts`（或對應型別檔案） — TypeScript 型別

Schema 欄位必須是 ORM 模型（`backend/app/extended/models.py`）的子集。

## 後果

### 正面

- 修改一個欄位只需更動兩個檔案（後端 Schema + 前端 Type），大幅降低遺漏風險
- TypeScript 編譯器在編譯時期即可捕捉型別不一致，`npx tsc --noEmit` 作為品質關卡
- 型別定義的擁有權（Ownership）清晰明確，減少團隊溝通成本
- Mock 資料必須與 `types/api.ts` 完全一致，測試更可靠
- 搭配 `/type-sync` 指令可自動檢查前後端型別同步狀態

### 負面

- 型別檔案（如 `api.ts`）隨著實體增加會變得很大，瀏覽不便
- 新增一個簡單欄位也必須修改 Schema + Types 兩個檔案，有一定的儀式成本
- 嚴格的 SSOT 執行需要團隊紀律，新成員容易在元件中隨手定義本地型別
- 前端型別與後端 Schema 之間的對應仍需人工維護，尚未實現自動生成

## 替代方案

| 方案 | 評估結果 |
|------|----------|
| **OpenAPI Spec 自動生成 TypeScript** | 理論上最理想，但 FastAPI 自動生成的 Schema 對自訂型別支援不佳，容易產生不符預期的型別 |
| **型別與元件共置（Co-location）** | 開發時方便，但必然導致型別漂移，長期維護成本高 |
| **GraphQL Codegen** | 型別自動生成且嚴格同步，但本專案使用 REST API，技術棧不相容 |
| **共享型別套件（Monorepo）** | 前後端共用型別定義，但 Python 與 TypeScript 型別系統差異大，需要額外轉換層 |

最終選擇手動 SSOT 架構搭配工具輔助檢查，在嚴格性與實作可行性之間取得平衡。
