# 篩選機制模組化：盤點、評估與方案（owner 2026-09-09）

> `lifecycle: status=current reviewed=2026-09-09 owner=CK_Missive`
>
> owner：「請統整評估篩選機制模組化，與統計相同概念避免頁面重複建構，一則也可避免異質同工，
> 另減少 A 頁面有某查詢條件但 B 頁面卻無等操作不一致等問題，如專案財務三個分頁就有此問題。」
> 另：「目前關鍵字搜尋多以案號，但使用端常用案名，因此有需統整規劃。」

## 一、盤點：三個財務分頁的篩選條件（收斂前）

| 條件 | `/erp/quotations` | `/erp/client-accounts` | `/erp/vendor-accounts` |
|---|---|---|---|
| 年度 | 表頭漏斗 | 下拉 | 下拉 |
| 計畫類別 | 有 | **無** | **無** |
| 承辦同仁 | 有 | 有 | 有 |
| 委託單位 | 有 | （本頁以它分組） | **無** |
| 金流異常 | 有 | **無** | **無** |
| 關鍵字涵蓋 | 案號／案名／報價單號 | 單位名／統編（**沒有案名**） | 廠商名／統編（**沒有案名**） |

後端更直接：`VendorAccountListRequest` 與 `ClientAccountListRequest` 的
`year／keyword／staff_user_id／skip／limit` **逐字重複兩份，連註解都是複製的**。
那就是篩選層的異值同工——與統計層完全同一個形狀。

前端第三份：`PROJECT_CATEGORY_OPTIONS` 的 value 是 `'01委辦招標'`（建案表單存進 DB 的字串），
報價單頁把 `{value:'01'}` 寫在頁面裡，帳款頁沒有。**同一個概念三種寫法。**

## 二、與統計中心服務是同一件事

**篩選是「範圍」的 UI 面。** 統計已收斂成「範圍 × 指標」
（`services/stats/case_scope.CaseStatsScope` 是範圍的唯一定義：年度／身分／類別／狀態）。
列表能篩的維度，統計卡就必須能跟；反過來也一樣。兩者的維度集合若不一致，
就會出現「列表篩了、卡片沒篩」——09-09 上午修了兩次的那個缺陷。

⇒ 篩選條件的單一定義必須**與 `CaseStatsScope` 同維度**。

## 三、本輪已做（09-09 下午）

| 層 | 做了什麼 |
|---|---|
| 後端 schema | `schemas/erp/vendor_financial.CaseListFilters`：年度／類別／關鍵字／承辦／分頁的**單一定義**，帳款兩頁 Request 改為繼承 |
| 後端表達式 | `stats/finance.case_category_expr()`：類別碼 ORM 表達式進中心服務（財務摘要那份 text 版是存量） |
| 後端 repository | 帳款兩頁接 `category`；關鍵字**三頁一致涵蓋案名**（委託帳款兩條腿、協力帳款 join 報價單） |
| 前端 | `constants/projectOptions.CASE_CATEGORY_OPTIONS` 單一定義；帳款兩頁加「計畫類別」下拉；型別 `AccountListRequest.category`；搜尋提示改「…／案名」 |

驗證（容器內）：協力帳款用案名「桃園市興辦」4 家（此前 0）、類別 01→8 家；委託帳款同案名 1 家（此前 0）。

⚠️ 委託帳款第一版仍回 0：那條腿**已經有一個只搜單位名的關鍵字條件**，我把案名條件加在別處，
兩者被 AND 疊加 ⇒ 案名命中仍被單位名擋掉。**加條件之前先找有沒有既存的同名條件**——
那正是「第二份實作」在寫入當下的樣子。

## 四、方案：三層各一個家

```
後端  schemas/erp/vendor_financial.CaseListFilters   ← 條件的形狀（哪些維度、什麼型別）
      services/stats/case_scope.CaseStatsScope       ← 條件怎麼套進查詢（統計與列表共用）
前端  components/erp/CaseFilterBar（待建）            ← 條件怎麼畫（年度／類別／承辦／委託單位／異常／關鍵字）
```

`CaseFilterBar` 的設計原則：

1. **維度集合由後端 schema 決定，不由頁面自己挑。** 頁面只說「我這頁支援哪幾個」（傳 `CaseListFilters` 的鍵名陣列），
   元件負責畫；新增一個維度＝改 schema ＋ 元件各一處，所有頁面同時拿到。
2. **與表頭漏斗共用同一份狀態**（規範 §2.6 ④）：`buildServerFilters` 已讓漏斗與 params 綁定，
   `CaseFilterBar` 讀寫同一個 params 物件，不另持狀態。
3. **手機版**：元件自己處理折疊（現況「篩選 ▾」按鈕已是），各頁不再各自寫 RWD。
4. **關鍵字的涵蓋範圍寫在 placeholder 裡**，且由後端 schema 的 `description` 供給——
   placeholder 說「案名」而後端不搜案名，就是 09-09 之前帳款頁的狀態。

守門：weekly 132 已盯後端「第二份範圍判定」；前端 `CaseFilterBar` 建好後，
加一條「列表頁不得自行渲染年度／類別／承辦 Select」（weekly 108 家族）。

## 五、存量與下一步

| 項 | 何時 |
|---|---|
| `CaseFilterBar` 元件＋三個財務分頁遷移 | 下一輪（本輪先讓三頁條件一致，元件化是第二步） |
| 帳款兩頁加「金流異常」條件 | 需要帳款彙總端點回 anomaly 資訊，與異常機制對接後做 |
| 財務摘要 repository 的 text 版類別表達式改用 `case_category_expr` | 基線存量，隨 GROUP BY 版片段一起清 |
| `PROJECT_CATEGORY_OPTIONS`（建案表單用）與 `CASE_CATEGORY_OPTIONS`（篩選用）的關係寫進 `FIELD_SEMANTICS` | 本輪已在常數註解說明，文件下一輪 |

## 六、一句話

**A 頁有 B 頁沒有，不是漏了一個下拉，是條件沒有一個家。** 現在後端有了；前端的家是下一步。

---

## 七、擴大評估：全部列表頁（owner 追加「請擴大各頁面整合評估」）

### 7.1 盤點方法

不掃頁面上的下拉（那會把詳情頁分頁與表單頁抓進來，首版抓到 63 頁而其中一半不是列表），
改從三個權威來源交叉：**路由表的列表路由**、**後端列表類 schema 的維度**、**repository 關鍵字涵蓋的欄位**。

### 7.2 三類頁面，三種結論

| 類 | 頁面 | 後端篩選 schema | 結論 |
|---|---|---|---|
| **案件類** | `/contract-cases`、`/pm/cases`、`/erp/quotations`、`/erp/client-accounts`、`/erp/vendor-accounts` | **四份**各自定義（見 `schemas/erp/case_filters.py` 檔頭矩陣） | **要收成一份** —— 這是異值同工的主戰場 |
| **文件類** | `/documents`、`/document-numbers` | `DocumentListQuery`（列表）＋`DocumentSearchRequest`（進階搜尋，多值） | 兩份但語意不同（單值 vs 多值），**不合併**；列表那份與案件類共用「年度／類別／狀態／關鍵字」的形狀，可抽更上層基底 |
| **主檔類** | `/agencies`、`/vendors`、`/clients`、`/staff` | 各自 `關鍵字＋狀態` | 維度天然少，**不需要案件維度**；只要關鍵字欄名統一 |

### 7.3 案件類四份的差異（這才是要修的）

| 差異 | 實況 | 後果 |
|---|---|---|
| 關鍵字欄名 | 三份叫 `search`、一份叫 `keyword` | 前端呼叫端寫錯名字不報錯，靜靜變成不篩 |
| 維度集合 | 承攬案沒有委託單位／異常；帳款沒有狀態／委託單位／異常 | A 頁能篩的 B 頁不能 |
| 基底 | 兩份繼承 `BaseQueryParams`（有 page/limit/sort），兩份繼承 `BaseModel`（skip/limit） | 分頁參數也有兩種形狀 |
| 關鍵字涵蓋 | 6 個 repository 有案名（含本輪補的兩個）；主檔類不需要 | 案件類已一致 |

### 7.4 方案（分三步，每步可獨立驗證）

| 步 | 做什麼 | 風險 |
|---|---|---|
| **① 家先立起來**（本輪） | `schemas/erp/case_filters.CaseListFilters` 搬到中立模組，帳款兩頁繼承它（契約不變） | 零 |
| **② 三份遷移** | `ProjectListQuery`／`PMCaseListRequest`／`ERPQuotationListRequest` 改繼承 `CaseListFilters`；`search` 改名 `keyword` **並保留 `search` 別名一個版本**（Pydantic `alias`），前端逐頁改用 `keyword` 後再拿掉別名 | 中——三頁前端呼叫端要跟；別名讓舊呼叫不斷 |
| **③ 前端家** | 帳款兩頁改用既有 `FilterBar`（另三頁已在用），`CaseFilterBar` 在其上宣告式渲染維度 | 低——`FilterBar` 已存在，只是帳款兩頁沒用 |

⚠️ 步驟②的 `search`→`keyword` 改名是本方案唯一會動到契約的地方。**不做別名直接改，前端漏一頁就是靜默不篩**——那正是 weekly 130 抓的「猜欄位」形狀。

### 7.5 守門

- 後端：weekly 132 擴一條「案件類 `*ListRequest` 不得自行宣告 `year／category／staff_user_id`」（必須繼承 `CaseListFilters`）。
- 前端：weekly 108 家族加一條「案件類列表頁不得自行渲染年度／類別／承辦 Select」（必須經 `FilterBar`）。
- 兩條都是「新增即紅、存量走基線」。
