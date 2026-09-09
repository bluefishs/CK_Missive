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
