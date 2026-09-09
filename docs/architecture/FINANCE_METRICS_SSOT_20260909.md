# 統計的統一服務端：盤點、複查與整合（owner 2026-09-09）

> `lifecycle: status=current reviewed=2026-09-09 owner=CK_Missive`
>
> owner：「統計應建構統一服務端，不應依各別頁面各自建構。請盤點複查整合，
> 避免如此反覆查核每個頁面是否來源或統計基準等問題。」

## 一、盤點：同一個指標有幾份實作

| 指標 | 實作份數 | 散在幾個檔 |
|---|---|---|
| 承攬金額（議價→契約→報價） | **4** | 3 |
| 已請款合計 | **3** | 3 |
| 已收款合計 | **3** | 3 |
| 應付合計 | **3** | 3 |
| 年度＝案號年 | 3 | 2 |

前端另有 **64 頁**帶統計卡，其中 53 頁沒有專屬的後端統計來源
（多數是詳情頁的全量彙總，屬合理；業務列表與財務頁才是本次範圍）。

## 二、複查：已經分歧，只是還沒發作

「已收款」三份實作的狀態條件**三種都不同**：

```
financial_summary_repository   SUM(payment_amount) WHERE payment_status IN ('paid','partial')
quotation_repository           SUM(payment_amount) WHERE payment_status = 'paid'      ← 少了 partial
finance_anomaly                SUM(COALESCE(payment_amount, 0))                       ← 完全不看狀態
```

⚠️ **實測三者算出同一個數字**：23,072,409。
因為現有 59 筆有金額的請款，狀態剛好全是 `paid`。

**那是最危險的狀態。** 它看起來一致、沒有任何一方報錯，而只要出現第一筆 `partial`
或狀態為空而金額有值的請款，三個畫面就會給三個數字。
owner 說的「反覆查核每個頁面」——靠人比對是守不住這種東西的。

同一天另外兩個實例佐證這不是理論問題：

- 財務儀表板上方 KPI 用 `year` 欄算出 108,108,873，下方類別分解用**案號年**算出
  91,173,873，**同一個畫面兩個口徑**，差 16,935,000。
- `/contract-cases`、`/pm/cases` 的統計卡沒跟上列表的身分範圍（各自修過一次）。

## 三、整合：一份實作、一組判準鎖、一道守門

### 唯一實作

`backend/app/services/erp/finance_metrics.py`

```python
awarded_amount(c="c", q="q")        # 議價 → 契約 → 報價總價，取第一個非零
billed_amount(ref="q.id")           # 已請款
received_amount(ref="q.id")         # 已收款（只認 RECEIVED_STATUSES）
payable_amount(ref="q.id")          # 應付
paid_amount(ref="q.id")             # 已付
case_year_condition(year, ...)      # year 欄優先、案號年後備
```

**回 SQL 片段而不是數值**：消費端多半是「一個大查詢裡的一個欄位」，
回數值會逼每個消費端多打一次資料庫；回片段能直接嵌進既有查詢，遷移成本最低。
`ref` 讓它同時服務兩種形狀（join 了報價單用 `q.id`，只有參數時用 `:qid`）。

### 口徑由測試鎖住

`tests/unit/test_services/test_finance_metrics.py` —— 15 條，斷言寫得很死：
三層取值的先後順序、議價欄要用 `NULLIF`、已收款帶狀態條件而已請款不帶、
年度的後備必須綁在 `year IS NULL` 上、案號比對用 `CK2026_%` 前綴而不是 `%2026%`。

**改口徑時測試會紅，那正是它的目的** —— 改一個指標會同時改動每一支統計，
那必須是刻意的決定。

### 守門：weekly 132

`finance_metrics_ssot_audit.py` —— 掃 `finance_metrics` 以外的金額算式。
**存量走基線、新增即紅**。一天全部改完不可能，而「第一天 20 個紅點」的檢核
與沒有檢核是同一個下場（本 repo 在服務層規範上付過這個學費）。

⚠️ 判準首跑兩個誤報，都已修：
① 命中**這份文件同一份程式碼裡我自己寫的註解**（`case_code LIKE 'CK2026_%'`）
   —— 判準的掃描範圍不得包含描述它的文字，本 repo 今天第四次踩這個坑；
② 把 `case_profile.py` 正確的「year 欄優先、案號年後備」報成違規。

## 四、本輪已收斂的

| 檔 | 收斂了什麼 | 驗證 |
|---|---|---|
| `financial_summary_repository` | 承攬金額／已請款／已收款／年度 | 類別分解數字**完全不變**（01 86,519,210、02 21,589,663、all 108,108,873） |
| `quotation_repository` | 四個金額（原本是第三份，已收款還少了 `partial`） | 145 筆相關測試通過 |

統一到最嚴謹的那份**實測不改變任何現有數字**：
有金額的請款 59 筆與已付 36 筆，狀態全是 `paid`，三種口徑同值。

## 五、存量 7 處（基線內，逐一清）

| 位置 | 為什麼還沒清 |
|---|---|
| `financial_summary_repository` 應付／已付 | 是「依廠商分組」的 JOIN 聚合，不是單一報價單的子查詢；換片段會改變語意，需另設計分組版 |
| `finance_anomaly` 已請款／已收款 | 同上，GROUP BY 形式；且它目前不看狀態，收斂時要先確認會不會改變異常筆數 |
| `billing_service` 承攬金額 | 取單一案的議價當請款上限檢查，不是統計；要先確認它該不該退回契約額 |
| `quotation_service` 應付／承攬金額 ×2 | 在 Python 端組值不是 SQL 取值，形狀不同；要先確認優先序與 SQL 版一致 |

**下一步是設計「分組版片段」**（`GROUP BY` 場景），那會清掉其中 4 處。

## 六、一句話

**問題不是每頁的數字對不對，是「同一個名詞有幾份算法」。**
現在是一份，第二份會在下一次 weekly 被指名。
