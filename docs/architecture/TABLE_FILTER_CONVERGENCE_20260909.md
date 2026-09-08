# 調整欄位會不會讓表頭篩選失效：評估與通用方案（owner 2026-09-09 問題 2）

> `lifecycle: status=current reviewed=2026-09-09 owner=CK_Missive`
>
> owner 的問題：「若表格調整欄位呈現項目，那表標頭篩選排序機制是否又會失效或再次設定，
> 整體通用與優化方案請評估」。

**結論先講：會失效，有三種方式，而且三種都不會報錯。**
其中最容易踩的一種，`/erp/quotations` 現在就是那個形狀 —— 已於本輪收斂。

---

## 一、三種失效方式（都不報錯）

### ① 改欄位鍵 ⇒ onChange 讀不到（最常見）

後端分頁的表格，一條篩選鏈有**三處各自寫著它的名字**：

| 處 | 寫什麼 | 誰在維護 |
|---|---|---|
| ① 欄位的 `key` / `dataIndex` | 漏斗掛在哪一欄 | 欄位定義 |
| ② `filteredValue` 讀的參數名 | 勾選狀態從哪裡來 | 欄位定義 |
| ③ `onChange` 裡**手寫的字串** | 值怎麼被讀回查詢參數 | 表格宣告，**離欄位定義幾百行遠** |

`/erp/quotations`「年度」欄的實測（本輪收斂前）：

```
欄位：{ title: '年度', dataIndex: 'case_code', key: 'case_code', ... }
狀態：filteredValue: params.year ? [params.year] : null
讀值：const yr = first('case_code');  ⇒  year: yr
```

**同一件事三個名字。** 把年度獨立成 `dataIndex: 'year'` —— 一個再正常不過的欄位調整 ——
③ 立刻對不上，而 **tsc 全綠、主控台安靜、畫面上漏斗長得一模一樣，只是點了沒反應**。

同一頁還有一行死碼：`onChange` 讀 `filters.status`，而**表格裡沒有狀態欄**。
沒有造成問題只是因為沒有任何入口設過那個值。這說明 ③ 是可以與 ①② 完全脫節的。

### ② 欄位在手機被隱藏 ⇒ 篩選變隱形

`hideOnMobile: true` 的欄位在 <768px 整欄消失，**包含它的漏斗與勾選狀態**，
而查詢參數裡的值還在 ⇒ 資料被篩，畫面上沒有任何指示。

實查 5 欄同時具備「手機隱藏」與「有漏斗」：

| 位置 | 欄位 | 目前是否安全 |
|---|---|---|
| `ERPOperationalListPage` | 年度（預設當年度） | ✅ 工具列的年度下拉有綁 `value`，手機仍看得到「2026」 |
| `caseProfileColumns` ×3 | 計畫類別／承辦／文件狀態 | ✅ 全量在手（`clientFilter`），欄位消失時篩選也消失，兩者一致 |
| `CaseRolesTab` | 來源 | ✅ 同上 |

⇒ **目前 0 個隱形篩選**，但這是靠「工具列還留著」擋下來的。
`/contract-cases` 的四個篩選是**唯一入口**（工具列三個下拉已依 owner 要求撤掉），
那四欄現在都沒有 `hideOnMobile` —— **若日後給其中任一欄加上手機隱藏，當場就是隱形篩選**。

### ③ 表格從「全量在手」變成「後端分頁」（或反之）

`onFilter` 的有無在兩種表格上**要求相反**，而寫錯不會報錯：

| 表格 | 要怎麼寫 | 寫錯的下場 |
|---|---|---|
| 後端分頁 | `filters` + `filteredValue`，**不得帶 `onFilter`** | 帶了 ⇒ 剝除器把 `onFilter` **連同 `filters` 一起刪掉** ⇒ 原始碼看得到漏斗、線上看不到 |
| 全量在手 | `filters` + **必須帶 `onFilter`** | 沒帶 ⇒ 漏斗畫得出來但點了不篩 |

資料量長過分頁上限、或後端補了分頁，都會讓一張表從第二種變成第一種。
**那一天不會有人改前端**，而漏斗就在那天靜靜失效。

---

## 二、通用方案：一份宣告，兩邊必然同步

`frontend/src/utils/tableFilters.ts` 的 **`buildServerFilters`**：

```tsx
const F = buildServerFilters([
  { columnKey: 'case_code', param: 'year', options: YEAR_OPTIONS, numeric: true },
  { columnKey: 'project_code', param: 'category', options: CATEGORY_OPTIONS },
] as const, params);

// 欄位：{ title: '年度', dataIndex: 'case_code', key: 'case_code', ...F.bind('case_code') }
// 表格：onChange={(_p, filters, sorter) => setParams((p) => ({ ...p, ...F.read(filters, sorter), page: 1 }))}
```

它解掉三種失效的方式：

| 失效 | 怎麼被擋住 |
|---|---|
| ① 改欄位鍵 | 只改 `columnKey` 一個字，`bind` 與 `read` 同時跟上。**打錯字 tsc 直接報**（`bind` 的參數型別是從 defs 推導的字面聯集；`param` 的型別是查詢參數的鍵集合）——實測負向控制：`bind('case_cod')` 少一個字母即 `TS2345` |
| ② 隱形篩選 | `read` **必然涵蓋每一個宣告過的參數**，取消勾選是 `undefined` 而不是「這個 key 消失」。少一個 key 就會讓舊值留在 params 裡 —— 這正是隱形篩選的機制 |
| ③ onFilter 寫反 | `bind` 走 `serverFilter`，**刻意不回傳 `onFilter`**，不可能寫反 |

兩層防護都驗過（`serverTableFilters.test.ts` 9 筆）：型別層先擋，執行期再擋並拋出「未宣告」。

### 守門：weekly 128

`scripts/checks/table_filter_key_wiring_audit.py` —— 問「宣告了漏斗，那個勾選值有沒有人讀回去」。
用了 `buildServerFilters` 的欄位直接放行；其餘逐一比對 onChange。

三個控制都做過：

| 控制 | 結果 |
|---|---|
| 注入斷鏈（欄位鍵改一個字母） | rc=2 並指名該檔該鍵 ✅ |
| 現況 | rc=0，0 斷鏈 ✅ |
| 解析度不足 | rc=2（**不給綠燈**）✅ |

⚠️ 第三個控制是這支腳本最重要的部分。首版用大括號配對切欄位，
被 render 裡 JSX 模板字串的 `${...}` 打亂，三個檔案 2/3/5 個宣告**只認出 1/2/1 個**，
**而它報 0 違規** —— 解析度不足的症狀就是一片綠。
改用「兩個 `title:` 之間」當欄位範圍，並加認出率下限 80%，低於就判不可信。

---

## 三、現況與遷移

| 項目 | 數字 |
|---|---|
| 後端分頁樣式的篩選欄位 | 8 |
| 已收斂到 `buildServerFilters` | 3（`/erp/quotations`） |
| 仍為手寫三處、但目前接得上 | 4 |
| 斷鏈 | **0** |

**刻意不一次全改。** 剩下的四個分佈在 `/erp/assets`、`/erp/operational`、`/contract-cases`，
其中 `/contract-cases` 的篩選狀態是三個獨立 `useState`（不是單一 params 物件），
收斂它要動到那頁的排序與搜尋邏輯 —— **那是另一件事的風險，不該搭在這一件上**。
weekly 128 會持續盯著它們，斷了就報。

## 四、給 owner 的一句話

**問題不在「調整欄位會不會壞」，在於壞了不會有人告訴你。**
現在壞的當下 tsc 會報，沒被 tsc 涵蓋的每週會報。
