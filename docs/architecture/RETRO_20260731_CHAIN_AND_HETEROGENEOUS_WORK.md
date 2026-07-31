# 覆盤 — 2026-07-31：標案財務鏈路、掃描管線，與「異質同工」偵測的系統性盲區

> **範圍**：owner 當日回報的 8 項問題、對應修法、以及貫穿其中的架構議題。
> **方法**：所有結論附實跑證據；未完成者明確標示。
> **遵循 L37**：附 §7 自我檢視，不新增抽象層，effort 估計含緩衝。

---

## 1. 當日議題與處置

| # | owner 回報 | 真因 | 處置 | commit |
|---|---|---|---|---|
| 1 | `/erp/quotations/167` 核銷點不進去 | **改錯檔**：07-30 修的是 `pmCase/ExpensesTab`，實際頁面用 `erpQuotation/ExpensesTab`；且唯一入口受 `canEdit` 限制，`verified` 紀錄整列不可點 | 無條件「檢視」+ 點列導向 + 動態掃描式 regression | `3a3cdacb` |
| 2 | ezbid 頁「無法建案」 | 該分支**根本沒有此按鈕**；後端 `job_number` 必填擋掉全部 ezbid（37,980 筆） | L1 入口打通 | `01609b8c` |
| 3 | 建案會產生重複 | 查重只比對 `job_number` → ezbid 無此值 → **查重整段被跳過** | L2：候選偵測 + 關聯既有 + 三道查重 | `01609b8c` |
| 4 | `/contract-cases/187` 財務紀錄空 | 鏈路缺一段：直接建立的承攬案件無 `case_code`、無報價 | 先排除（創號 + 報價 168）；再治本（方案 B） | `01609b8c` / `1559b607` |
| 5 | PCC 與 ezbid 設計不一致 | 同一功能在兩個 render 分支各寫一套 | 收斂為 `TenderActionBar` 單一元件 | `874e144b` |
| 6 | `/erp/expenses/13` 看不到收據 | `service.create()` **沒有 `receipt_image_path` 參數**，端點卻以 kwarg 傳 → `TypeError` → auto_create 全數 500 | 路徑改放進 schema；兩處呼叫同步修 | `9b8948b2` |
| 7 | 金額 940 記成 957 | **QR 資料本身與紙本不符**（差額 17 為加油金折抵，商家 POS 於折抵前產生 QR） | 偵測 `total ≠ sales×1.05` 即警示（**不自動改**）；11 依紙本更正 | `9b8948b2` |
| 8 | 行動裝置批次掃描被中斷 | 建立成功一律 `navigate(清單)` | 「建立並繼續掃下一張」+ 行動版重點摘要卡 | `9b8948b2` |

### 三個我自己造成的問題（分開列，不混在上表裡）

1. **#6 是我 07-30 沒修對**：我改了那一行的字串值（`uploads/receipts/` → `receipts/`），
   卻沒有驗證這個呼叫**本身就會拋例外**。修了值、沒看產出物。
2. **#5 的不一致是我製造的**：補 ezbid 按鈕時只想「把缺的補上」，沒對照既有 PCC 頁設計。
3. **測試把真實 LINE 推播給 owner**：`test_scheduler_failure_alert` patch 的是
   `get_telegram_bot_service`，但實作 v6.12 已改走 `IntegrationFacade` → **過期的 mock 攔不到**
   → owner 17:06 實收兩則告警。已加 conftest autouse 安全網封鎖對外推播。

---

## 2. 貫穿的架構議題：「異質同工」偵測有系統性盲區

當日 8 項中，**#1 / #2 / #5 屬同一家族**：同一件事有兩份實作，改了一份、另一份沒動。
專案已有兩支審計在管這件事，但**它們都沒看見**：

### 2.1 `heterogeneous_work_audit`（fitness step 66）只管三個寫死維度

實跑結果：

```
[H1] 前端 axios.create 實例：2  [WATCH]
[H2] scripts 直呼 /api/embed：2（已登記）[GREEN]
[H3] 後端 services stub 轉發檔：3  [GREEN]
→ GREEN: 無異質同工增量
```

它監控的是**三個歷史個案**（SSO 的 axios 雙實例、embedding 繞道、DDD 遷移 stub），
不是「同一功能有兩份實作」這個**通則**。今天的三起完全在雷達之外，而它照樣報 GREEN。

### 2.2 `code_semantic_duplication_audit`（step 67）從不掃前端

圖譜其實有前端實體：

| entity_type | 數量 |
|---|---|
| ts_interface | 826 |
| ts_module | 748 |
| api_endpoint | 709 |
| **ts_hook** | **309** |
| **ts_component** | **274** |
| service | 101 |

但該審計預設 `--types api_endpoint,service` —— **274 個元件、309 個 hook 從來沒被檢查過**。

### 2.3 把它指向前端 → 719 個候選，且明顯是噪音

```
候選 719 (baseline<= 99)
  🔶 pages/ContractCaseDetailPage ⇄ pages/deployment/StatusTags   max_sim=0.905
  🔶 components/document/hooks/useAttachments ⇄ hooks/system/useAIPrompts   max_sim=0.905
```

`ContractCaseDetailPage` 與 `StatusTags` 相似度 0.905？`useAttachments` 與 `useAIPrompts` 0.905？
**這是同一天 pg_trgm 事故的同一種失敗**：工具回一個看似合理的數字，實則無鑑別力
—— 所有 React hook 的名稱嵌入本來就長得像，`use*` 前綴讓它們天然高相似。

> 結論：**不建議**把語意（嵌入）審計擴用到前端。它會製造 719 筆需要人工排除的噪音，
> 而真正的問題（同名不同檔、同檔兩分支）它一個都抓不到。

### 2.4 確定性偵測立刻抓到真候選

改用「**同一 basename 出現在不同目錄**」這個零成本、零誤判設計的檢查：

| 同名元件 | 位置 | 人工核實結果 |
|---|---|---|
| **ExpensesTab** | `erpQuotation/` vs `pmCase/` | ✅ **今天踩到的那組**（能力不一致，已修） |
| **DetailPageHeader** | `components/common/DetailPage/` vs `pages/contractCase/` | ⚠️ **後者生產程式碼無人使用，只有測試在 mock 它** —— 孤兒複本，且測試在保護一個幽靈 |
| StaffTab | `contractCase/tabs/` vs `pmCase/` | 🔍 223 行 vs 189 行、資料呼叫 0 vs 9 → 結構不同，需業務判斷 |
| MermaidBlock | `components/ai/` vs `components/common/` | 🔍 待核 |
| CategoryPieChart | `components/tender/` vs `pages/erpDashboard/` | 🔍 待核 |
| EvolutionTab | `digitalTwin/` vs `kunge/` | ✅ **合理**：CLAUDE.md 已載明語意不同（健康進化 vs 結晶進化） |
| ReportsPage / TaoyuanProjectDetailPage / UnifiedFormDemoPage | 頂層 vs 子目錄 | ✅ **合理**：頂層是 re-export shim（已逐一開檔確認，非重複） |

> 最後一列特別值得記：用「被引用數 = 0」判斷時它們看起來全是死檔，
> **開檔才發現是 re-export**。差一步就誤報三個模組化良好的檔案。

另一個確定性訊號是**複合型動作標籤重複**（同一領域動作被實作多次的指紋）：
「解除關聯」×5 檔、「建立關聯」×4 檔（document↔dispatch↔project 三方關聯各寫一套）。
通用動詞（新增/刪除/重新整理）重複屬正常，不列入。

---

## 3. 服務與功能完整性複查（實測）

| 面向 | 結果 |
|---|---|
| 容器 | 55 Up / **0 非健康** |
| 五系統公網 | missive・lvrland・pilemgmt・digitaltwin・www **全 200** |
| `/health` | healthy / documents 1970 / KG 49508 |
| **前端部署一致性** | dist `main-B52O5NlE.js` == 公網供應檔名 ✅ |
| **host↔容器程式碼對賬** | 9 個改動檔 **md5 全部一致**（無「改了沒進容器」）✅ |
| **功能逐條實跑** | **8/8 PASS**（L2 重複建案被擋 / L3 回指 / L4 預填 / 187 財務查得到 / QR 矛盾警示 / 一致發票不誤報 / 11 已更正） |
| 今日新增回歸 | 後端 **71 passed**、前端 **32 passed** |
| producer watchdog | **15 GREEN / 0 blind spot** |
| shared drift | GREEN |
| 告警噪音 | 未讀 **731**（清理前 4708）；過去仍 pending 事件 **0**（清理前 690） |
| fitness 74 / 75 / 76 | 🟡 3 筆待補 / ✅ GREEN / ✅ GREEN |

> 全測試套件對照（基準 53 個既有失敗）**尚在背景執行中**，本文完成時未回收。
> 中途一度看到「0 筆失敗」，經查是輸出檔 0 bytes、任務未完成 —— 不是結果。

---

## 4. 建議（依 CP 排序）

| # | 建議 | 成本 | 理由 |
|---|---|---|---|
| **R1** | 把「同名 basename 跨目錄」加入 `heterogeneous_work_audit` 的 H4 維度 | 小 | 零誤判設計、立刻抓到今天的案型；不需要嵌入、不需要圖譜 |
| **R2** | 清掉 `pages/contractCase/DetailPageHeader.tsx` 孤兒複本 + 其測試 mock | 小 | 生產無人使用；留著會讓下一個人改錯邊 |
| R3 | 核實 StaffTab / MermaidBlock / CategoryPieChart 三組 | 中 | **先核實再收斂**，勿直接合併 |
| R4 | 「解除關聯／建立關聯」四五處實作評估收斂 | 中 | 同一領域動作散落 |
| — | **不做**：把語意審計擴到前端 | — | 719 噪音、抓不到真問題（§2.3） |

---

## 5. 元教訓（今日第三次同型）

當日三個「工具回了數字但數字沒意義」：

1. **pg_trgm 對中文** → 量出假的 38% 重複率
2. **嵌入相似度對前端元件** → 719 個 0.905 的無意義配對
3. **背景測試的空輸出檔** → 差點報成「0 個失敗」

加上早上的「測試命中自己的註解」（兩次）與「過期的 mock」，
**同一天六次踩到「訊號存在 ≠ 訊號有效」**。

因此再補一條紀律，與 07-30 的「成功訊號本身不可信」互補：

> **任何比對／相似度／統計工具，在採信其輸出之前，必須先用「已知為真」與「已知為假」
> 各驗一次。** 驗不出鑑別力的工具，其輸出一律不得用於判斷 —— 它比沒有工具更危險，
> 因為它讓人以為量過了。

---

## 6. 待 owner

1. **瀏覽器複驗**（先 `Ctrl+Shift+R`）：ezbid 建案候選 Modal、報價核銷可點入、
   手機批次「建立並繼續掃下一張」、行動版金額摘要卡。
2. **`/erp/expenses/10~13` 的收據影像**：修法只對之後新掃的生效；
   那四筆當初路徑就沒寫入，要補需人工指認影像對應哪筆。
3. **方案 A**（補 188/190/191 的號與空白容器）——三案 `contract_amount` 皆 NULL，
   補出來是空容器，一句話即可執行。
4. **R1/R2 是否執行**。

---

## 7. 自我檢視

1. **#6 是我 07-30 的未完成修法**，而且我當時在 commit 訊息裡寫了「已修」。
   若不是 owner 再次回報，這個錯誤會一直躺著。
2. **我在同一天內兩次寫出比對到自己註解的測試**（一次假綠、一次假紅）。
   第二次發生時我已經知道這個陷阱 —— 知道不等於會避開，只有負向測試才擋得住。
3. §2.4 的同名偵測**我只做了分析、沒有做成 audit**（R1），因此本文的價值目前
   仍停留在「知道有這個盲區」。若 R1 不落地，下次還是靠人眼發現。
4. **719 個語意候選我只抽看了 5 筆**就判定為噪音。抽樣量偏少，
   若其中藏有真候選會被我一併否定；但由於前 5 筆的相似度與最大值同為 0.905，
   研判整批同質，風險可接受 —— 這是判斷，不是量測。
5. 全測試套件對照**未在本文完成前回收**，因此「無新增失敗」目前只有
   針對性測試（後端 71 / 前端 32）與 8 項功能實跑支撐，不是全量證據。
6. §4 的成本欄是我的估計值，**沒有依據**；R3/R4 標「中」純屬直覺。
