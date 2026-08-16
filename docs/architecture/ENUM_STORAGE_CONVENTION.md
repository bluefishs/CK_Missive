# 列舉值儲存慣例（分類／狀態）

> 建立：2026-08-16
> 觸發：owner「分類仍有中英紛雜 如統一帳本」「邀標與專案 承攬狀態混淆」

---

## 為什麼會有「中英紛雜」

盤點後發現系統裡**兩種儲存慣例並存**，而且沒有任何地方寫明該用哪一種：

| 慣例 | DB 存什麼 | 顯示怎麼來 | 現有例子 |
|---|---|---|---|
| **A 式** | 英文碼 | 前端 label 對照表 | `pm_cases.status`（`contracted`）／`finance_ledgers.entry_type`（`income`）／`operational_accounts.category`（`vehicle`）|
| **B 式** | 中文字面 | 直接顯示 | `expense_invoices.category`（`交通費`）／`finance_ledgers.category`（`收款`）／`contract_projects.status`（`執行中`）|

**兩式各自都合理，混用才是問題。** 實際造成的傷害有三種形態：

### 形態一：同一欄裝了兩種語言

`finance_ledgers.category` 同時存著

```
billing_payment   35 筆   ← 英文碼（2026-04-01 一次性匯入）
外包及勞務        33 筆
收款 / 設備採購 / 文具及印刷
```

按科目統計時 `billing_payment` 會**自成一類**，而它其實就是「收款」。
根因：`schemas/erp/expense.py` 的 `EXPENSE_CATEGORIES` 有 Literal 約束，
註解還寫著「新增分類請同步更新此處與 ledger.py」——
**但 `ledger.py` 的 category 是 `Optional[str]`，根本沒有可同步的東西**。
寫了等於沒寫。（已於 2026-08-16 修正並正規化那 35 筆。）

### 形態二：同一條業務鏈上前後兩段用不同慣例

```
PMCase（邀標）        status = 'contracted'   ← A 式
ContractProject（承攬） status = '執行中'      ← B 式
```

同一件工作走完流程，狀態欄一段是英文一段是中文。
報表要跨兩段統計時，就得在某處寫一份對照——而那份對照會是第三份事實。

### 形態三：定義了一份與現實對不上的詞彙

`types/api-project.ts` 的 `ContractCaseStatus`（`planned`/`in_progress`/`completed`）
與 DB 實際的 `執行中`/`已結案` **完全對不上**，
而它從來沒有任何消費者（只被 re-export）——**沒有人會發現它是錯的**。

---

## 慣例（往後一律照此）

### 規則 1：新欄位一律用 A 式（英文碼 ＋ 標籤對照）

理由不是「英文比較好」，而是：

- 中文字面值一旦要改顯示文字（「已結案」→「結案」），就得改資料
- 中文值在 URL query／檔名／log 裡會被編碼，難以肉眼比對
- 排序依中文筆劃，不是業務順序

**既有 B 式欄位不強制遷移** —— 遷移要動業務資料，風險大於收益。
但**不得再新增 B 式欄位**。

### 規則 2：每個列舉必須有唯一的定義處，而且前後端要指得到彼此

後端 `Literal`／前端 `Record<T, string>`，且註解互相指名：

```python
# backend/app/schemas/erp/ledger.py
LEDGER_CATEGORY_VALUES: tuple[str, ...] = (...)   # ← 前端 types/erp.ts LEDGER_CATEGORY_GROUPS
```

```ts
// frontend/src/types/erp.ts
/** 對應後端 `schemas/erp/ledger.py` 的 `LEDGER_CATEGORY_VALUES` */
export const LEDGER_CATEGORY_GROUPS = [...]
```

### 規則 3：寫入端必須約束，讀取端保持寬鬆

```python
class LedgerBase(BaseModel):
    category: Optional[str]              # 讀：寬鬆（相容歷史值）

class LedgerCreate(LedgerBase):
    category: Optional[LEDGER_CATEGORIES] # 寫：Literal 約束
```

**讀取端不可加 Literal** —— 庫裡的歷史值會讓整列讀取 400
（2026-07-20 的 `amount` `gt=0` 就是踩過這個坑）。

### 規則 4：表單不得用自由輸入的 Input 收列舉值

`ERPLedgerPage` 那個死掉的 Modal 就是反例：

```tsx
<Form.Item name="category" label="分類">
  <Input placeholder="例：交通費、材料費" />   {/* ← 這樣寫，庫裡就會長出任何東西 */}
</Form.Item>
```

一律用 `<Select options={...} />`，選項來自規則 2 的單一定義。

### 規則 5：詞彙變更必須確認消費端

移除或改名一個值之前，至少查三處：

1. 後端有沒有 `status == "舊值"` 之類的比對
2. 前端 label 對照表與篩選器選項
3. **統計面板**——最容易漏，因為它讀不到值時顯示 `0`，看起來像「還沒有」

2026-08-16 的實例：儀表板 PM 面板讀 `in_progress`（PM 沒這個狀態）與
`completed`（PM 的詞彙是 `closed`），**三個數字恆為 0**，
而系統裡有 74 筆案件。沒有人發現，因為 0 不像壞掉。

---

## 邀標 vs 承攬：狀態語意分界

owner 2026-08-16：「邀標不應有執行中選項」。

```
PMCase（邀標階段）        評估中 planning → 已承攬 contracted → 已結案 closed
                                              ↓ 成案
ContractProject（承攬階段）                    執行中 → 已結案
```

「執行中」**只屬於承攬案件**。邀標案件的終點是「承攬到了」，
之後的執行由承攬案件承接。

混淆的來源是 `promote_to_project` 成案時**同時**設了
`contract_projects.status='執行中'` 與 `pm_case.status='in_progress'`
——同一件工作在兩個模組各有一個「執行中」，無從分辨誰是誰。
（已修正為 `contracted`；實測 74 筆 PM 案件中 `in_progress` 本來就 0 筆，
那個值從來沒有意義過。）

---

## 現況清單（2026-08-16 盤點）

| 欄位 | 慣例 | 值 | 狀態 |
|---|---|---|---|
| `pm_cases.status` | A | planning／contracted／closed | ✅ 已移除 in_progress |
| `contract_projects.status` | B | 待執行／執行中／已結案／未得標 | 既有，不遷移 |
| `finance_ledgers.entry_type` | A | income／expense | ✅ |
| `finance_ledgers.category` | B | 18 項會計科目 | ✅ 已加寫入端約束 |
| `expense_invoices.category` | B | 15 項費用科目 | ✅ 既有 Literal |
| `operational_accounts.category` | A | office／vehicle／equipment… | ✅ |
| ~~`ContractCaseStatus`~~ | — | planned／in_progress／completed | ⚠️ **與 DB 不符且無消費者**，待移除 |
