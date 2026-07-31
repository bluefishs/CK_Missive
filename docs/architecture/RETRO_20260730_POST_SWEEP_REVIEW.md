# 覆盤 — 2026-07-30「沉默成功」大掃除之後：實況複驗、watch item 診斷、待辦統整

> **性質**：v6.29 交付**之後**的獨立覆盤（不是 v6.29 的自述）。目的有三：
> ① 用 live 證據複驗當日宣稱；② 把三個掛在 pre-flight 的 watch item **診斷到可執行**；
> ③ 統整待辦並提出下一輪順序建議。
> **前置文件**：`docs/runbooks/reboot-pre-flight-20260730.md`（本輪交付與重啟 SOP）
> **本文遵循 L37**：附 §7 自我檢視、effort 估計含 2-3x 緩衝、不新增抽象層/守護腳本/標準文件。

---

## 1. 覆盤方法

只採**當下實跑的輸出**，不引用先前 session 的宣稱。所有數字為 2026-07-30 19:2x 實測。
凡「無法在 headless 驗證」者（瀏覽器體感）一律標記為 owner-only，不代行、不推測。

---

## 2. Live 實證（全綠，無新增缺陷）

| 面向 | 實測值 | 判定 |
|---|---|---|
| 容器 | 55 Up / **0 非健康** / 0 exited | ✅ |
| 五系統公網 | missive / lvrland / pilemgmt / digitaltwin / www **全 200**（0.32–0.46s） | ✅ |
| 後端 host `:8001/health` | healthy，DB 23ms，pool 15/1 checked_out | ✅ |
| 業務量 | documents **1968** / KG **49487** | ✅ 續增 |
| 前端 `tsc --noEmit` | EXIT=0 | ✅ |
| 後端 `py_compile app/**` | 845 檔 **0 fail** | ✅ |
| cron（近 500 事件） | **success 500 / fail 0** | ✅ |
| shared 套件 drift | `sync-vendored.sh --check` = **GREEN** | ✅ |
| 文件漂移 | 29 檔 **0 STALE**；跨 repo CLAUDE.md STALE 3（WARN，屬他 repo） | ✅ |
| producer watchdog | 15 監控 / 38 非producer / **未納管 0**；**RED 1**（見 §3.1） | 🟡 |
| fitness step 74 | 🟡 4 筆（187/188/190/191，門檻 10） | 🟡 預期 |
| ADR lifecycle | active 20（目標 ≤15）/ archived 14 | 🟡 治理債 |
| git | 工作樹 clean、ahead 0（全 push） | ✅ |

> 唯一「紅」是 producer watchdog 的 1 筆——**經查為誤報**，見下。

---

## 3. 三個 watch item：診斷結論

### 3.1 `標案業務推薦` producer RED ＝ **registry 訊號選錯，非缺陷**（結論已可執行）

**證據鏈**：

- `tender_recommendation_history` **總筆數 88**，`MAX(pushed_at) = 2026-06-23 09:00:02`。
- `scheduler.py:1706` — `TENDER_LINE_PUSH_ENABLED` 預設 `false` 時**直接 return**，
  這是 2026-06-23 owner 為節省 LINE 月配額所做的**政策決定**。
- 停止寫入的日期與 gate 生效日**完全吻合** → 今日 0 筆是 **100% 合理空**。

**故 RED 的真正性質**：registry 用 `db_table_today` 監控一張「依政策已停止寫入」的表，
而該 job **不回傳 detail**（`@tracked_job` 只在 job 回 dict 時記 detail），
watchdog 因此**無法區分「政策關閉」與「真失敗」**——這正是契約規則 2 未落實之例。

**另揭一層（本次新發現，比 pre-flight 記載更嚴重）**：
`tender_business_recommend_job` 的 `except Exception` **只 log 不 re-raise**（`scheduler.py:1722-1723`）
→ 真失敗時 `@tracked_job` 仍記 **success**。也就是說**即使 gate 打開後真的爆掉，也只會靜默**。
這與 07-30 四例是同一形狀（成功訊號不可信）。

**修法（3 處，皆小改）**：

```python
# backend/app/core/scheduler.py  tender_business_recommend_job
if os.getenv("TENDER_LINE_PUSH_ENABLED", "false").lower() != "true":
    logger.info("標案業務推薦 LINE 推送已暫緩（配額政策）")
    return {"pushed": 0, "reason": "line_push_disabled"}      # ← 規則 2：合理空要說得出原因
...
    return {"pushed": result["pushed"], "found": result["found"], "reason": "ok"}
except Exception as e:
    logger.error(f"標案業務推薦失敗: {e}", exc_info=True)
    raise                                                      # ← 規則 4b 精神：失敗要記 failure
```

```jsonc
// backend/config/producer_outcome_registry.json — 改訊號型
{"name": "標案業務推薦", "signal": "cron_detail", "job": "tender_business_recommend",
 "key": "pushed", "ok_zero_reasons": ["line_push_disabled", "no_match", "ok"]}
```

- 風險：低（job 目前不執行任何業務動作；registry 為 bind-mount 設定檔）。
- 影響：watchdog RED→GREEN 且**是真的綠**（能區分關閉 vs 失敗），不是把告警關掉。
- 需 backend rebuild（`scheduler.py` 已烤入 image）→ 適合與 §3.2 併為同一次 rebuild。

### 3.2 收據影像路徑前綴不一致 ＝ **真缺陷，1 行**（已定位）

- **SSOT 是相對路徑 `receipts/{filename}`**：`expenses_io.py:98`（upload-receipt）、
  `line_image_handler.py:98/148`（LINE 上傳）三個 writer 都用此形式；
  讀取端 `expenses_io.py:267-268` 對相對路徑補 `uploads/` 前綴。
- **唯一例外**：`expenses_io.py:208` smart-scan `auto_create` 寫 `uploads/receipts/{filename}`
  → 讀取時被補成 `uploads/uploads/...` → **檔案存在但一律 404**。
- **現況資料無污染**：DB 中唯一有影像的 `id=6` 值為 `receipts/scan_ab451e33.jpg`（正確），
  故**不需要資料修復**，只需修 writer。

**修法**：`expenses_io.py:208` → `receipt_image_path=f"receipts/{filename}"`。
（`:184` 的 `result_data["receipt_path"]` 是回給前端的顯示欄位、非入庫值，前端目前也不消費它，維持不動。）

- 風險：極低。建議同時補一條 regression 斷言「四個 writer 寫入值皆不以 `uploads/` 開頭」，
  避免第五個 writer 再犯（**不新增 fitness step**，就近放進既有 expense 測試檔即可——符合本文 §禁做）。

### 3.3 `ERPExpensePages.test.tsx` 27 測試全紅 ＝ **測試檔失去保護力**（本輪風險最高的一項）

- 已確認為 pre-existing（hooks mock 缺 `usePMCases` / `useCaseCodeMap` / `useAutoLinkEinvoice`），
  **非本輪修改造成**。
- 但今日**核銷模組改動最多**（QR 入口、返回導向、鑽取、審核 resync、序列化根治），
  卻正好是這個模組的測試在紅 → **今天所有核銷修法目前沒有自動化回歸保護**，
  完全依賴 owner 手動瀏覽器驗證。這是本次覆盤認定**優先級最高**的技術債。

### 3.4 【本次新增】owner 貼的兩則 LINE 告警 → 揭出**告警系統本身已成噪音迴圈**

覆盤進行中 owner 貼出兩則實收告警，逐一追查結果：

**(a) 07:00「⚠️ 排程產出異常：標案業務推薦 今日 0」** ＝ §3.1 的誤報，
**且它每天早上都推給 owner**。這把 §3.1 從「治理潔癖」升級為**每日騷擾**，優先級須上調。

**(b) 00:30「actionable 告警 66 筆」** ＝ 追查後是**真問題，但不是 66 件事要做**：

| 證據 | 數值 |
|---|---|
| 今日 `proactive_alert` 通知 | **66 筆** |
| 近 7 日每日產生量 | 66 / 66 / 68 / 67 / 67 / 67 / 65 ← **幾乎完全相同** |
| `proactive_alert` 歷史累積 | **4094 筆** |
| `system_notifications` 未讀 | **4708 筆** |
| 內容大宗 | 「事件已逾期 **568–574 天**」＋「請款/應付差異 x%」 |
| 樣本含 | `「[參考] Test Update」已逾期 574 天` ← **測試資料混在生產告警** |

再往下追資料面（`document_calendar_events`）：

| 狀態 | 筆數 |
|---|---|
| 過去日期仍 `pending` | **690**（最早 2025-01-02） |
| 逾期 > 180 天且未完成 | **668** |
| 逾期 > 365 天且未完成 | **396** |

**診斷（三層，與今日主題同型）**：

1. **資料面**：公文提醒事件建立後**沒有關閉路徑**——公文辦結了，事件永遠 `pending`。積壓 690 筆。
2. **告警面**：吹哨者每天把同一批陳年事件重新掃出、**重新建立通知（無去重、無抑制）**
   → 每天固定 ~66 筆，累積 4094，未讀 4708。
3. **價值面**：「逾期 574 天」對 owner **沒有任何今日可執行的動作**。
   於是告警被整批忽略 → **通知中心實質已死**（4708 未讀就是量化證據），
   真有事時也不會被看見。這是 L31（建表≠用表）在告警系統上的重演。

**建議修法（分三刀，不現在動；(3) 涉業務語意須 owner 決）**：

1. **抑制重複**（治本第一刀，效果最大）：同一 `source_table+source_id+title` 若已有**未讀**通知，
   則更新既有筆而非新建 → 每日 66 → 接近 0。
2. **逾期分級**：> 90 天無動作者不再列 `actionable`，改歸「陳年待清理」，
   月報一次，不進每日 digest。
3. **資料清理**（owner 決策）：690 筆舊 `pending` 事件依公文/派工實際狀態批次歸檔
   （可比照 v6.19 派工 closure 的推導法，非單看日期欄位）；順手清掉 `Test Update` 測試資料。

> ⚠️ 我**沒有**動任何通知或事件資料——批次改狀態屬破壞性且涉業務判斷，須 owner 先確認語意。

---

## 4. Facade B 方案 60 天 trial — **今日到期，判定與建議**

實測 caller（排除 `services/contracts/` 自身）：

| Facade | 目標 | 實際 caller | 位置 |
|---|---|---|---|
| IntegrationFacade | ≥5 | **4** | scheduler / scheduler_alert / agent_orchestrator / tender.business_recommendation |
| MemoryFacade | ≥5 | **3** | agent_orchestrator / agent_planner / agent_post_processing |
| WikiFacade | ≥3 | **3** ✅ | agent_orchestrator / agent_synthesis / agent_tools |

> 註：治理儀表板 §5 記 Integration=3，實測為 4（`tender/business_recommendation.py` 未被計入），
> 差異不影響結論。

**建議（owner 決）：結束 trial，三者全部保留，並停止再設成長目標。**

理由：
1. 三者**都不是 0-caller 空殼**（L53 當初要砍的是空殼），caller 且都在 agent 核心路徑上。
2. 未達標的是**目標值本身不切實際**——60 天內 caller 只增 0~1，說明「湊 caller 數」不是真需求；
   繼續掛著一個永遠不會達標的 KPI，只會每次覆盤重複佔用議題欄位（同 Tier 3 registry 的降噪邏輯）。
3. 移除 Memory/Integration facade 需改動 agent 核心 7 個檔 → **成本 > 收益**，屬 L53 反向過度工程。

**配套立法（一句，不新增文件）**：往後**不新增 facade**，除非提案時已能列出 **≥3 個既存 caller**。
落點：`docs/architecture/GOVERNANCE_INTEGRATED_DASHBOARD.md` §5 改為「已結案」一行。

---

## 5. 待辦統整（依優先序；effort 已含 2-3x 緩衝）

### P0 — owner-only，不可委任（阻斷後續工作）

| # | 項目 | 為何是 P0 | 阻斷了什麼 |
|---|---|---|---|
| O-1 | **Missive auth 閒置逾 1h 實測**（自 07-28 未驗） | headless 無法代行 | 通過才可 propagate lvrland/pile/DT + TTL 統一 60min |
| O-2 | **核銷全鏈路瀏覽器複驗**（先 `Ctrl+Shift+R`） | 今日改最多、且測試檔在紅 | 確認 6 項功能真活（見 pre-flight §A） |
| O-3 | 承攬案件 187/188/190/191 建立報價綁定 | 業務資料，需人決策 | fitness step 74 轉綠 |
| O-4 | **690 筆陳年 `pending` 行事曆事件如何歸檔**（§3.4-3） | 涉業務語意，不可代決 | 決定後才能寫批次歸檔；含清 `Test Update` 測試資料 |

### ✅ P1 — **已於同日執行完畢**（owner 指示「歷史案件註記忽略 + P1」，commit `34fd0b64`）

| # | 項目 | 結果（實測，非宣稱） |
|---|---|---|
| A-1 | 告警去重抑制 | 連續兩次掃描 **111 → 111（0 新增）**，原本每天 +66 |
| A-2 | 逾期分級 STALE_OVERDUE_DAYS=90 | 每日 actionable **66 → 45**（剩下為 ERP 請款逾期＝真實業務） |
| — | 歷史案件註記忽略（owner 決策，可逆 manifest） | 事件 **667 筆 → `ignored`**；過去仍 pending **690 → 15**；歷史通知 **4028 筆標已讀**；未讀 **4708 → 725** |
| A-3 | `ERPExpensePages.test.tsx` | **27 紅 → 24 綠**（含補 `useResponsive` 子路徑 mock、重寫改版後斷言） |
| A-4 | 標案 producer detail + raise + registry | cron_events 實錄 `{"pushed":0,"reason":"line_push_disabled"}`；watchdog **RED → 真 GREEN** |
| A-5 | 收據路徑 SSOT | 1 行修正；新增 regression 並負向測試證非永久綠 |
| — | 部署 | backend rebuild → **L76 host `:8001` 200 + 公網 200**；frontend build；backend 100 tests passed |

> **A-3 的 effort 遠超估計，印證 §7 第 4 點自我檢視**：預估 1.5–2.5h，實際失敗根因有三層
> （缺 hook mock → 缺子路徑 `useResponsive` mock → 頁面改版後斷言全部過時），
> 且清單頁已從「發票明細」改為「歸屬彙總」，等於重寫而非修補。

<details><summary>原始 P1 規劃（保留供對照）</summary>

### P1 — 可代行，建議下一 session 一次做完（**共用一次 backend rebuild**）

| # | 項目 | Effort（含緩衝） | 備註 |
|---|---|---|---|
| A-1 | **告警去重/抑制**：同 source+title 已有未讀則更新不新建（§3.4-1） | 1–2 h | **每日 66 筆噪音降到近 0**，owner 每天有感 |
| A-2 | **逾期分級**：> 90 天無動作者移出每日 `actionable`（§3.4-2） | 1–2 h | 與 A-1 同檔區域，建議併做 |
| A-3 | `ERPExpensePages.test.tsx` 27 紅修復（補 3 個 hooks mock） | 1.5–2.5 h | 今日核銷修法**目前零回歸保護**；不需部署 |
| A-4 | 標案推薦 producer：job 回 detail + `raise` + registry 改 `cron_detail`（§3.1） | 0.5–1 h | 消掉**每日 07:00 誤報**，且是真綠不是關告警 |
| A-5 | 收據路徑前綴 SSOT 修 1 行 + regression 斷言（§3.2） | 0.5–1 h | 現況無髒資料，純防未來 |
| — | rebuild + **L76 驗證**（host `:8001` + 公網 200） | 0.5 h | A-1/A-2/A-4/A-5 需要；A-3 不需要 |

> **排序理由**：A-1/A-2/A-4 都直接減少 owner 每日承受的噪音，**體感優先於潔癖**；
> A-3 風險零且補的是今天剛改的東西；A-5 順手。五項合併**一次 rebuild**，避免 churn（feedback_rigor）。
> **時機**：建議**在 owner 完成 O-2 之後**再 rebuild——否則 owner 驗的 bundle 與最終版本不同，
> 出問題時無法歸因。

</details>

> ⚠️ **上述「等 owner 驗完再 rebuild」的建議未被採用**（owner 直接指示執行 P1）。
> 影響：owner 進行 O-2 核銷複驗時，bundle 已含本輪變更（新增 `ignored` 狀態、
> 收據路徑修正、清單頁測試對齊）。核銷相關**行為**未改，但若複驗發現異常，
> 需同時考慮本輪變更為可能來源。

### P2 — 治理債（可排入月度，不急）

| # | 項目 | 現況 | 建議 |
|---|---|---|---|
| G-1 | ADR active 20 > 目標 15 | ADR-0020 仍 `PROPOSAL（待 5/20 會議）`，已逾期 2 個月 | 一次性 triage：決議或 archive，勿再掛著 |
| G-2 | 4 pending crystal 審批 | `wiki/memory/proposals/` 9 檔 | owner 批次處理（含一條 regex 太寬需收窄） |
| G-3 | Hermes baseline GO/NO-GO | p95 48.9s（本地 gemma），成功率 1.0 | 已知結構性限制，**維持「不列待辦」**，勿重複討論 |
| G-4 | 跨 repo CLAUDE.md STALE 3 | 含 CK_KMapAdvisor | 屬對應 repo session，此處只記不辦 |
| G-5 | Task Scheduler 重建 / `sync_enabled=true` | v6.10.1 遺留 | 低價值，建議直接標記「不辦」以除噪 |

### 明確「不辦」（除噪，避免每次覆盤重複出現）

- Facade caller 成長目標（§4 已結案）
- Hermes 對話智慧強化（模型強度牆，策略已定：AI = 運維自主 + 業務直呼）
- 標案 enrichment 爬蟲路徑重試（L77 死結）
- Tier 3 registry §1 所列 8 條刻意分歧

---

## 6. 下一輪建議順序

```
owner O-2 核銷瀏覽器複驗  ─┐
owner O-1 auth 閒置實測   ─┴─→  A-1 測試修復（無需部署，可並行先做）
                                  ↓
                          A-2 + A-3 合併 → 一次 rebuild → L76 驗證
                                  ↓
                          （O-1 通過才啟動）auth propagation 三 repo + TTL 統一
```

**單一原則**：owner 手動驗證未完成前，**不動主產品 runtime**。

---

## 7. 自我檢視（L37 要求，≥5 項）

1. **本文沒有驗證今日交付的功能真活**——只驗了「系統沒壞」。核銷 6 項功能是否真的可用，
   仍完全依賴 owner，本文無法替代（且測試檔在紅，連自動化替代品都沒有）。
2. **§3.1 的 `raise` 修法有副作用未量測**：gate 打開後若外部 LINE API 常態失敗，
   會從「靜默」變成「每日 failure + 告警」。這是設計意圖，但可能造成告警疲勞，未評估頻率。
3. **§4 的 Facade 判定偏保守**：我建議「全保留」，但沒有量測這三個 facade 實際省下多少重複碼；
   若真要嚴謹，應比較「移除後行數變化」，本次未做（成本考量）。
4. **effort 估計仍可能樂觀**：A-1 的 27 個測試若 mock 缺失只是表層、底下還有元件行為漂移，
   會遠超 2.5h。緩衝倍率是慣例值，非量測值。
5. **本文自身可能變 dead doc**：與過往多份 RETRO 同型風險。緩解＝所有結論都已落到
   §5 的具體待辦，而非只留在文件裡。
6. **§3.4 是 owner 主動貼告警才被發現的**——本次覆盤的既定流程（容器/公網/cron/fitness/drift）
   **全綠，完全沒有指向它**。原因是所有檢查都在問「機制有沒有跑」，沒有人問
   「跑出來的東西有沒有價值」。4708 未讀是躺在 DB 裡的公開事實，一句 SQL 就查得到，
   但**沒有任何一條巡檢在看它**——這是本次最該記的盲區，且不能靠再加一個守護腳本解決
   （那只會變成第 4709 筆沒人看的告警）。
7. **producer RED 的診斷依賴一條 SQL（MAX(pushed_at)）**；若歷史上曾有其他原因中斷寫入，
   我的「與 gate 生效日吻合」推論會被高估。已用總筆數 88 交叉佐證，但仍是單線證據。

---

## 8. 7 天 check-in（2026-08-06）

屆時檢查三件事，任一未達即視為本文失效：
1. §5 的 A-1/A-2/A-3 是否已執行或已明確放棄（而非默默留著）；
2. producer watchdog 是否仍有 1 RED（若有＝§3.1 沒落地）；
3. 本文是否被任何後續 session 引用（無引用＝dead doc，應刪除而非保留）。
