# 自我檢核與進化標準（Self-Audit & Evolution Standard）v1.0

> **強制等級**：高 — 新增任何功能、模組、cron、頁面時適用
> **建立**：2026-08-01（owner：「將自我檢核與進化標準化」）
> **上位文件**：`PRODUCER_SELF_CHECK_CONTRACT.md`（行為層產出契約，本標準的第 3 階）
> **本標準回答一個問題**：一個東西壞了，系統要**在誰之前**知道？

---

## 0. 立法背景

2026-07-30 ～ 08-01 兩日內，owner 連續回報 11 項缺陷。逐一追根後發現，
**沒有一項是「程式碼寫錯」被靜態檢查漏掉**，而是分佈在五種不同的失效型態上：

| 型態 | 實例 | 當時哪一層該抓到 |
|---|---|---|
| 報成功但沒做 | cf_tunnel_verify 空跑數月 | 行為層（產出） |
| 功能根本不存在 | ezbid 頁沒有建案鈕 | 頁面層 |
| 同一功能兩份實作 | 兩個 ExpensesTab 能力不一致 | 結構層 |
| 前後端契約不一致 | erp-graph 送 query:'' 必 422，被 catch 吞成 0 筆 | 頁面層 + 契約層 |
| 有產出但沒價值 | 每日 66 筆重複告警、未讀 4708 | **無人負責** |

當時的治理有 76 個 fitness step、15 個 producer 監控、五系統公網探針，
**全部是綠的**。因為它們只問「機制有沒有跑」，沒問「跑出來的東西對不對、有沒有用」。

---

## 1. 六階檢核階梯（Detection Ladder）

任何新東西上線前，先問：**它壞掉的時候，是哪一階會發現？**
若答案是「使用者」，就代表少了一階。

| 階 | 名稱 | 問的問題 | 現有機制 | 抓不到什麼 |
|---|---|---|---|---|
| 1 | **靜態層** | 程式碼結構對嗎 | fitness 1–78 步 | 跑起來是壞的 |
| 2 | **契約層** | 前後端說的是同一件事嗎 | response_model / 型別 SSOT / regression | 沒綁 model 的裸 dict |
| 3 | **行為層** | job 真的產出東西了嗎 | producer watchdog（18 producer） | 產出有沒有價值 |
| 4 | **服務層** | 服務活著嗎 | `/health` + 五系統探針 + L76 | 單一頁面壞掉 |
| 5 | **頁面層** | 這一頁打開來是對的嗎 | `ui_flow_smoke`（深度 7）+ `ui_page_sweep`（廣度 87） | 寫入型流程 |
| 6 | **價值層** | 產出有人用嗎、有意義嗎 | ⚠️ **仍是最弱的一階** | 見 §5 |

### 分工原則

- **深度 vs 廣度**：flow smoke 驗「這個功能還在嗎」（對應曾回報過的具體問題）；
  page sweep 驗「有沒有整頁壞掉」（大面積崩壞、契約不一致）。兩者不可互相取代。
- **靜態 vs live**：`route-sync-check` 是原始碼對原始碼；
  `navigation_live_integrity_audit` 才看 live DB。**導覽是使用者唯一入口，必須驗 live**。

---

## 2. 新增功能時的強制要求

### 2.1 新增 cron / 排程 job

依 `PRODUCER_SELF_CHECK_CONTRACT.md` 規則 1–4，**擇一必做**：

- 有業務產出 → 註冊 producer registry（`db_table_today` / `cron_detail` / `file_fresh` / `db_row_count`）
- 純檢查/清理 → 加入 `NON_PRODUCER_JOBS` allowlist
- **驗證型 job**（稽核/watchdog）→ 仍須留下可驗產出（規則 4），
  且外部依賴缺失一律 `raise` 不得 `return`

> ⚠️ registry 是 **SSOT**。2026-08-01 發現 watchdog 自己維護了第二份 `MONITORED_JOBS`
> 寫死清單，導致新註冊的 job 仍被報為 blind spot ——
> **抓異質同工的審計自己就是異質同工**。已改為從 registry 衍生。

### 2.2 新增 API 端點

- 回應**必須綁 `response_model`**。回裸 dict = 前後端各自定義型別，
  後端改欄位不會有人發現（實例：`case-finance` 端點，兩個 ExpensesTab 各宣告一份）
- 前端型別放 `types/`，由頁面 import；**不得在 `pages/` 內本地宣告**

### 2.3 新增頁面 / 重要互動

- 靜態路由自動被 `ui_page_sweep` 涵蓋（讀 `router/types.ts`，無需登記）
- 若是**曾被回報過的問題**或**關鍵業務動作**，加一條 `ui_flow_smoke` 檢查
- **同一功能不得在兩個分支各寫一套** —— 抽共用元件
  （H4 審計會抓同名檔跨目錄，但同檔內的兩個分支它抓不到，靠 review）

### 2.4 新增檢核機制本身

**檢核器也要被檢核**：
- 寫結果檔 → 註冊 producer registry（`file_fresh`）→ 停跑時由既有告警抓到
- **不得新建第二套通知管道**（那是下一個異質同工）
- fitness 加一步驗其新鮮度與上次結果

---

## 3. 檢核結果的可信度規則（今日最貴的教訓）

> **任何比對／相似度／統計工具，採信其輸出之前，必須先用「已知為真」與「已知為假」
> 各驗一次。驗不出鑑別力的工具，其輸出一律不得用於判斷。**

兩日內踩到 **7 次**「訊號存在 ≠ 訊號有效」：

| # | 工具 | 假訊號 | 怎麼發現的 |
|---|---|---|---|
| 1 | pg_trgm 對中文 | 「38% 案件重複」全假 | 抽樣核對 |
| 2 | 嵌入相似度對前端元件 | 719 個 0.905 無意義配對 | 看前 5 筆就知道 |
| 3 | 背景測試空輸出檔 | 差點報成「0 個失敗」 | 檢查檔案大小 |
| 4 | 測試比對命中自己註解 | 假綠 1 次、假紅 2 次 | 負向測試 |
| 5 | 過期的 mock | 測試真的推播到 owner 手機 | owner 收到訊息 |
| 6 | 我寫的 UI 檢核器 | 5 項 SKIP 仍印「GREEN」 | 看輸出時發現 |
| 7 | producer 覆蓋檢查 | 已註冊仍報 blind spot | 複查時發現 |

### 強制作法

1. **負向測試**：任何新 regression／audit，必須實際變異程式碼並確認它會紅，
   且要**驗證變異真的落地**（md5 對照）—— `str.replace` 不匹配是靜默失敗
2. **比對原始碼前先剝註解**：說明文字裡就寫著要抓的關鍵字（今日踩 3 次）
3. **SKIP ≠ PASS**：未驗完必須與通過區分（退出碼 0/1/2）
4. **先懷疑檢查、再懷疑系統**：UI 檢核首跑 3 個 FAIL，全是檢查寫錯

---

## 4. 自我修復（Evolution）

檢核只會標黃等人來看；**修復是自己動手**。

### 何時可以自動修

同時滿足才可以：

1. **修法唯一且確定**（不需業務判斷）
2. **冪等**（重跑無害）
3. **逐項獨立**（單項失敗不影響其他）
4. **fail-soft**（修不動不得阻斷主流程）
5. **回報 detail** 供 watchdog 區分「沒東西要修」與「真失敗」

### 現有實例

| 機制 | 修什麼 | 效果 |
|---|---|---|
| `case_finance_bridge_selfheal`（每日 02:50） | 承攬案件缺 `case_code` → 自動產號 + 建財務容器 | 覆蓋率 86.2% → **100%** |
| `code_graph_reconcile`（每週） | 程式圖譜 orphan | 1970 → 0 |
| `crystal_applier`（confidence ≥ 0.9） | intent_rules 自動套用 | SOUL/synonyms 仍人審 |

### 何時**不可以**自動修

- 涉及金額、狀態、業務語意（例：QR 金額與紙本不符 → **只警示不自動改**，
  因為混含免稅品項的發票本來就會偏離 5%）
- 刪除型操作
- 需要跨系統協調者

---

## 5. 誠實列出：最弱的一階

**第 6 階「價值層」目前沒有任何自動機制。**

告警噪音那次（每日 66 筆、累積 4094、未讀 4708）之所以拖了那麼久，
是因為所有機制都在問「有沒有產出」，而它**確實有產出**——只是沒有價值。
最後是 owner 貼了一則 LINE 訊息才被發現。

已知可觀測的價值訊號（尚未自動化）：
- 通知未讀率（4708 未讀 = 通知中心已死）
- 功能使用率（`capability_usage_audit` 存在但輸出為空，需修）
- 重複產出率（同一批告警每日重生 = 無效循環）

> 這一階**不能靠再加一個守護腳本解決**——那只會變成第 4709 筆沒人看的告警。
> 正確方向是把「產出被使用的程度」變成 metric，而不是把「產出存在」變成告警。

---

## 5.5 跨專案移植：pilot 實測結果（2026-08-01，CK_lvrland_Webmap）

**結論：引擎可攜成立，但「照抄設定」必失敗。** lvrland 移植共踩 10 個坑，
全數已回饋 canonical。分兩類——

### A. 引擎缺陷（已修，未來 repo 不會再遇到）

| # | 症狀 | 根因 |
|---|---|---|
| 1 | 找不到 config | ROOT 由 `__dirname` 上推——vendored 安裝比原生多一層目錄 → 改以 **config 檔位置**為基準 |
| 2 | 結果檔寫到 `scripts/docs/health/` | 同上，`writeFileSync` 也在上推 |
| 3 | `--check` 永遠 DRIFT | 截圖寫進 vendored 目錄內 → 改寫進該 repo `docs/health/` |
| 4 | 掃到 0 條路由卻印 PASS | **假綠**：設定錯 = 全部健康 → 改 exit 2 |
| 5 | 路由擷取失敗 | 各 repo pattern 群組數不同（`ROUTES` 常數 2 群組 vs `<Route path>` 1 群組）→ 取第一個以 `/` 開頭者 |
| 6 | 登入態注入無效 | 前端 session 儲存慣例不同（`user_info` raw vs zustand persist `auth-storage`）→ config 化 |

### B. per-repo 必須自己解（移植時預期會遇到）

| # | 事項 | 說明 |
|---|---|---|
| 7 | 容器內結構 | Missive `/app`＝backend；lvrland `/app/backend` → adapter 多候選路徑探測 |
| 8 | adapter 以 stdin 執行 | `__file__ == "<stdin>"`（**不是 NameError**）→ `parents[2]` 拋 IndexError |
| 9 | Windows 編碼／路徑 | config 含中文 → 明確 `encoding="utf-8"`（L49.8）；Git Bash `/d/...` → `cygpath` |
| 10 | **認證細節** | 見下 |

### 最貴的一個：認證不可從「機制刻意分歧」推論

lvrland 花三次 401 才通。每一次都是「以為懂了」：

1. 以為無狀態 → 實際 `sub` 要真實 `users.id`
2. 補了真實 id → 實際 `jti` 必填
3. 以為 jti 只是黑名單 → 實際還要 **`user_sessions` 有對應 active 列**

**規則：adapter 必須逐層以真實呼叫驗證（打一個需認證端點看 200），
不得從任何文件或印象推論具體機制。** 我們自己維護的跨 repo 分歧
registry 只記「哪裡刻意不同」，不保證細節——它不是實作規格書。

### Pilot 的實際收益（證明這不是自嗨）

lvrland 首次執行就抓到：
- `/admin/security-center` → `POST /admin/security/**security**/owasp-summary` 404
  （路徑重複段，靜態檢查全綠、只有瀏覽器抓得到）
- `/admin/code-architecture` 整頁空白
- 另 6 頁 422／空白待確認
- **附帶發現**：該 repo 6 支檢核腳本從來沒有任何東西會去跑
  → 建 `run_checks.sh`，首跑即發現 `templates_ssot_check` 早就是 RED

---

## 5.6 成熟度覆盤：對照 SSO／前端共享套件的四條反面守則（2026-08-01）

移植機制是否夠成熟，不該用「跑得動」判斷，而該用**既有的跨專案標準化教訓**
（`MODULARIZATION_CROSS_PROJECT_STRATEGY.md` §7）逐條檢驗。實際檢驗結果——
**四條中有兩條，selfaudit 一開始就違反了**，靠這次覆盤才抓到：

| 守則 | selfaudit 初版 | 結果 |
|---|---|---|
| 禁 over-standardize（L58） | ❌ **把 CK_Missive 專屬的入口腳本當 canonical 同步出去**——lvrland 因此拿到寫死 `ck_missive_backend` 的檔案，而且它躺在「禁手改」的 `.shared-selfaudit/` 裡 | 已改為 `templates/run_selfaudit.sh.template`（複製一次、自行改，不同步） |
| 禁 advisory-only | ❌ **canonical 的原生 repo 自己不在 drift gate 內**——CK_Missive 以手動 `cp` 消費，忘了 copy 就 silent 分歧、下游永遠拿不到修正 | CK_Missive 也改為 vendored 消費並納入 `sync-vendored.sh --check` |
| 禁複製實作當共享 | ✅ 引擎是薄庫，per-repo 的認證與檢查清單全在 config／adapter | — |
| 禁單向強推 | ✅ 先在 lvrland 證值（抓到 8 個未知缺陷）才談推廣 | — |

### 這一輪覆盤額外抓到的 6 個缺陷（全部是「移植才會爆」）

1. **漏寫 `flows` → 印「GREEN 全部 0 項通過」**（假綠）。廣度引擎修過同型問題，
   深度引擎沒修——因為兩支各有一份開頭邏輯。**同一件事兩份來源＝異質同工**，
   已抽 `_bootstrap.cjs` 單一源。
2. 設定漏欄位／regex 非法／`routes_source` 指向不存在的檔案 → 原本只在執行中途
   拋 node 堆疊。改為**上線前結構驗證**，一律 exit 2「未驗完」。
3. **playwright 路徑寫死 `C:/Users/User1/...`** → 換機器／換使用者／CI 上
   `MODULE_NOT_FOUND` 崩在 require 行。改為 env → repo node_modules → 全域 →
   快取掃描，找不到時印**可操作的三種解法**。**崩潰不等於清楚**。
4. 廣度引擎寫死 `localStorage['user_info']`，深度引擎讀 config → 同型不一致，已合流。
5. config 位置以固定層數上推 → CK_Missive 改 vendored 消費（多一層）立刻指錯。
   改為**往上尋找**（最多 6 層）。
6. **輸出路徑 config 化時，我改了 Missive 的落點，卻沒同步新鮮度檢核與
   producer registry** → 檢核器對著舊路徑喊「從未執行」。修法有二：輸出復原到
   該 repo 既有慣例（保住已接好的告警），且**新鮮度檢核改讀同一份 config**。

> **教訓**：把東西抽成共享的當下，最容易斷的不是功能，是**它與既有治理的接線**。
> 抽取後必須回頭確認「誰在監看它的產出」還指得對。

### 結論（誠實版）

**引擎本身已可移植**（lvrland 實證 62 條路由、8 個真缺陷）。
**但「成熟」的門檻不是能跑，是設定寫錯時不會給你綠燈**——這點在本次覆盤前
**不成立**（漏 `flows` 就是綠的）。現已補上結構驗證 + 7 項負向測試各自以正確
原因失敗。第三個 repo 導入前建議先跑一次負向測試，確認 gate 真的擋得住。

---

## 6. 檢查清單（新功能上線前）

- [ ] 它壞掉時，第幾階會發現？若答案是「使用者」，補上該階
- [ ] 新 cron → registry 或 allowlist 二擇一（不得兩者皆無）
- [ ] 新端點 → 綁 `response_model`；型別放 `types/`
- [ ] 新頁面 → 靜態路由自動涵蓋；關鍵互動加 flow 檢查
- [ ] 新檢核器 → 自己也要被監控，且不新建通知管道
- [ ] 任何 audit/regression → **負向測試通過**（變異會紅、變異確實落地）
- [ ] 可自動修的（§4 五條件全滿足）→ 寫成 self-heal，不要只標黃
