# CK_Missive 統一開發規範總綱

> 版本：1.0.0
> 建立日期：2026-01-06
> 狀態：**強制遵守 (MANDATORY)**

---

## ⚠️ 強制遵守聲明

**本文件所列規範為系統開發的強制性要求。**

任何代碼提交前必須通過本文件所列的檢查清單。
違反規範的代碼將導致系統不穩定、維護困難、或功能失效。

---

## 一、規範文件索引

### 核心規範 (CRITICAL)

| 文件 | 用途 | 強制等級 |
|------|------|----------|
| [`@TYPE_CONSISTENCY_SKILL_SPEC.md`](./\@TYPE_CONSISTENCY_SKILL_SPEC.md) | 型別一致性與 UI 風格 | 🔴 必須 |
| [`@SCHEMA_VALIDATION_SKILL_SPEC.md`](./\@SCHEMA_VALIDATION_SKILL_SPEC.md) | Model-Database 一致性 | 🔴 必須 |
| [`@CSV_IMPORT_SKILL_SPEC.md`](./\@CSV_IMPORT_SKILL_SPEC.md) | CSV 匯入模組規範 | 🟡 相關時必須 |
| [`@PROJECT_CODE_SPEC.md`](./\@PROJECT_CODE_SPEC.md) | 專案編號產生規則 | 🟡 相關時必須 |

### 參考文件

| 文件 | 用途 |
|------|------|
| [`@AGENT.md`](./\@AGENT.md) | Agent 建置指引與品質標準 |
| [`@system_status_report.md`](./\@system_status_report.md) | 系統狀態與架構文件 |
| [`@SYSTEM_ARCHITECTURE_REVIEW.md`](./\@SYSTEM_ARCHITECTURE_REVIEW.md) | 架構審查與優化規劃 |

---

## 二、開發原則 (Development Principles)

### 2.1 單一真實來源 (Single Source of Truth)

```
Database Schema → Backend Model → Backend Schema → Frontend Types → UI Components
      ↑
   權威來源
```

**規則**：
- ✅ 新增欄位時，從 Database 開始向下同步
- ❌ 禁止僅在前端新增欄位而不更新後端

### 2.2 型別安全優先 (Type Safety First)

**規則**：
- ✅ 所有 TypeScript 代碼必須通過 `npx tsc --noEmit`
- ✅ 使用泛型元件時明確指定型別參數
- ✅ API 回應使用防禦性預設值
- ❌ 禁止使用 `any` 除非有明確理由

### 2.3 POST-only API 設計

**規則**：
- ✅ 所有資料查詢使用 POST 方法
- ✅ GET 僅用於靜態資源或公開端點
- ❌ 禁止在 GET 參數中傳送敏感資訊

### 2.4 命名一致性

| 層級 | 風格 | 範例 |
|------|------|------|
| Database | snake_case | `delivery_method` |
| Backend (Python) | snake_case | `delivery_method` |
| Frontend (TypeScript) | snake_case (API 層) | `delivery_method` |
| UI Display | 中文標籤 | "發文形式" |

---

## 三、強制執行檢查清單

### 3.1 每次提交前 (Pre-commit Checklist)

```markdown
## TypeScript 檢查
- [ ] `cd frontend && npx tsc --noEmit` 無錯誤
- [ ] `npm run build` 成功

## 型別一致性
- [ ] 新增欄位已同步：Model → Schema → Types
- [ ] 介面擴展使用 `extends` 而非重複定義
- [ ] 泛型元件已指定型別參數

## API 一致性
- [ ] 使用 POST 方法（非 GET）查詢資料
- [ ] 使用 API_BASE_URL 而非相對路徑
- [ ] 回應格式符合 PaginatedResponse/SuccessResponse

## Schema 一致性
- [ ] `pytest tests/test_schema_consistency.py` 通過
- [ ] 新增欄位已建立 migration
- [ ] 後端啟動無 Schema 警告
```

### 3.2 新增欄位流程

```
1. Database Migration (alembic)
   └─ op.add_column('table', Column('field', Type))

2. Backend Model (models.py)
   └─ field = Column(Type, comment="說明")

3. Backend Schema (schemas/*.py)
   └─ field: Optional[Type] = Field(default, description="說明")

4. Frontend API Types (api/*Api.ts)
   └─ field?: Type;  // 說明

5. Frontend Business Types (types/index.ts)
   └─ readonly field?: Type;
```

### 3.3 TypeScript 嚴格模式必遵規則

| 情境 | 規則 | 範例 |
|------|------|------|
| 介面共用 | 使用 `extends` 繼承 | `interface X extends BaseX {}` |
| 泛型元件 | 明確指定型別 | `<InputNumber<number>>` |
| 日期範圍 | 檢查 null | `dates && dates[0] && dates[1]` |
| 陣列索引 | 使用 `??` 預設值 | `arr[0] ?? ''` |
| API 回應 | 型別斷言 | `as { items?: T[] }` |
| 可選屬性 | 提供預設值 | `prop ?? defaultValue` |

---

## 四、違規後果與修復

### 4.1 違規等級

| 等級 | 描述 | 後果 |
|------|------|------|
| 🔴 嚴重 | TypeScript 編譯失敗、Schema 不一致 | 必須立即修復，不可 merge |
| 🟡 中等 | 缺少型別定義、未使用 POST-only | 需在本次 PR 修復 |
| 🟢 輕微 | 未使用的 import、風格不一致 | 建議修復 |

### 4.2 快速修復指南

```typescript
// ❌ 問題：InputNumber formatter 型別錯誤
<InputNumber formatter={...} parser={(v) => parseFloat(v)} />

// ✅ 修復：使用泛型並返回 number
<InputNumber<number> formatter={...} parser={(v) => Number(v!.replace(...))} />
```

```typescript
// ❌ 問題：陣列索引可能為 undefined
const first = array[0];

// ✅ 修復：使用預設值或非空斷言
const first = array[0] ?? defaultValue;
// 或確認非空後
if (array.length > 0) { const first = array[0]!; }
```

```typescript
// ❌ 問題：RangePicker 日期可能為 null
onChange={(dates) => setDates(dates)}

// ✅ 修復：檢查 null
onChange={(dates) => setDates(
  dates && dates[0] && dates[1] ? [dates[0], dates[1]] : null
)}
```

---

## 五、自動化驗證

### 5.1 TypeScript 檢查

```bash
# 前端型別檢查（必須通過）
cd frontend && npx tsc --noEmit

# 前端建置（必須成功）
cd frontend && npm run build
```

### 5.2 後端 Schema 驗證

```bash
# Schema 一致性測試
cd backend && pytest tests/test_schema_consistency.py -v

# 啟動應用驗證（檢查啟動日誌無警告）
cd backend && uvicorn main:app --host 0.0.0.0 --port 8001
```

### 5.3 Git Hooks 建議

```bash
# .git/hooks/pre-commit (建議配置)
#!/bin/bash
cd frontend && npx tsc --noEmit
if [ $? -ne 0 ]; then
    echo "❌ TypeScript 檢查失敗，請修復後再提交"
    exit 1
fi
echo "✅ TypeScript 檢查通過"
```

---

## 六、規範更新流程

### 6.1 誰可以更新規範

- 系統架構師
- Claude Code Assistant (經授權)
- 經團隊審查的 PR

### 6.2 更新步驟

1. 修改對應的 SKILL 規範文件
2. 更新本文件的版本歷史
3. 更新 @AGENT.md 的相關章節
4. 提交 commit 註明規範變更

---

## 七、版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.0.0 | 2026-01-06 | 初版 - 整合所有開發規範，建立強制遵守機制 |

---

## 八、快速參考卡

```
┌─────────────────────────────────────────────────────────────────┐
│                    CK_Missive 開發規範速查                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📋 提交前必檢：                                                  │
│     npx tsc --noEmit    ← 必須 0 錯誤                            │
│     npm run build       ← 必須成功                               │
│                                                                  │
│  🔗 欄位同步順序：                                                │
│     DB → Model → Schema → API Types → UI                        │
│                                                                  │
│  📝 TypeScript 必遵：                                             │
│     • 介面用 extends 繼承                                         │
│     • 泛型明確指定 <T>                                            │
│     • 陣列索引用 ?? 預設值                                        │
│     • 日期檢查 null                                               │
│                                                                  │
│  🌐 API 規則：                                                    │
│     • 查詢用 POST（非 GET）                                       │
│     • 使用 API_BASE_URL                                          │
│     • 回應用 PaginatedResponse                                   │
│                                                                  │
│  📚 規範文件：                                                    │
│     @TYPE_CONSISTENCY_SKILL_SPEC.md    型別一致性                 │
│     @SCHEMA_VALIDATION_SKILL_SPEC.md   Schema 驗證               │
│     @CSV_IMPORT_SKILL_SPEC.md          CSV 匯入                  │
│     @PROJECT_CODE_SPEC.md              專案編號                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

*文件維護: Claude Code Assistant*
*強制遵守等級: MANDATORY*
