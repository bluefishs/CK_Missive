# Producer 自我檢核契約（Producer Self-Check Contract）

> **強制等級**：高 — 新增 producer cron job 必走
> **建立日期**：2026-07-18
> **觸發**：反覆低階問題共同根＝沉默成功（job 報 success 但產出 0）。結構圖譜抓不到行為產出。
> **對齊**：`AI_ROLE_REPOSITIONING.md`（運維自主＝AI 真強項）、`silent_success_self_check`

---

## 為何需要這份契約

反覆的「數據消失/機制沒動」問題（KG embedding embedded=0、tender records=0…）都是**沉默成功**：
job 報 success 但實際沒產出，失敗隱形直到人看到症狀。**根治＝每個 producer 的產出被獨立監控**。

但一次性清單會腐化——新增的 cron job 若沒納入監控，就是新的 blind spot，沉默失敗會繼續滋生。
**故需制度化：每個 producer 必須註冊產出信號，違反者被 audit 抓。**

---

## 定義：什麼是 Producer

**Producer** = 產出「業務資料 / 檔案 / 外部推送」的 cron job（scrape/ingest/generate/sync/report/backfill/compile/push）。

**非 Producer** = 稽核/檢查/watchdog/清理/暖機（fitness/security_scan/cron_self_health/cleanup/warmup…）——無業務產出需監控。

---

## 契約：新增 Producer cron job 必做

### 規則 1：註冊產出信號到 watchdog registry
在 `scripts/checks/producer_output_watchdog.py` 的 `PRODUCER_OUTCOME_REGISTRY` 加一筆，選一種信號：

| 信號型 | 用於 | 範例 |
|---|---|---|
| `db_table_today` | 寫 DB 表的 producer（**最 robust**，獨立驗證，不信任 job 自報） | tender_records 今日有新增？ |
| `cron_detail` | job 回傳 `{output_count, reason}` 者 | kg_embedding embedded>0 |
| `file_fresh` | 產出檔案的 producer | 晨報/覆盤/週報檔新鮮？ |
| `db_row_count` | 維護**持久資料集**的 producer（抓「非零但塌陷」——非零檢查會漏） | 程式圖譜關係 ≥5000（健康~9670/塌陷85）？ |

> `db_row_count` 立法背景（2026-07-20）：程式圖譜關係曾被每日 ingest job 靜默洗成僅 FK（9669→85），85 非零 → 前三種信號皆綠＝漏抓。當 producer 維護「應維持一定規模的資料集」（非每日增量）時用 `min` 閾值驗，抓塌陷/被洗類降級。spec：`{"signal":"db_row_count","table":"X","where":"...","min":N}`。

```python
# 範例：新 producer 寫 foo 表
{"name": "新機制", "signal": "db_table_today", "table": "foo", "date_col": "created_at",
 "weekend_legit": False},  # 若週末合理空則 True
```

### 規則 2（建議）：job 回傳 detail
若走 `cron_detail`，job 應 `return {"<output_key>": count, "reason": "<ok|問題原因>"}`——
`@tracked_job` 會記為 cron_events detail，沉默成功現形。**區分合理空 vs 失敗**（如 tender 的
`weekend_no_publish` vs `fetch_failed`），避免合理空誤報。

### 規則 3：非 Producer 明確 allowlist
若新 job 確定無業務產出（純檢查/清理），加入 audit 的 `NON_PRODUCER_JOBS` allowlist。
**不可兩者皆不做**——unclassified job 會被 `producer_output_watchdog --coverage` 抓為 blind spot。

### 規則 4（2026-07-30 新增）：**驗證型 job 也必須留下可驗產出；外部依賴缺失一律 raise**

原契約把「稽核/檢查/watchdog」歸為非 Producer、直接 allowlist 豁免。
**2026-07-30 證明這個豁免有洞**：`cf_tunnel_verify` 連續數月「記 success 但一項都沒驗」——

1. 容器內無 `pwsh`（5/27 廢 PM2 改純 Docker 後）→ `shutil.which` 找不到即 `logger.warning + return`；
2. `MISSIVE_PUBLIC_URL` **.env 與 compose 皆未定義** → 容器內恆為空 → job 第一行就 return。

兩層都讓 `@tracked_job` 記成功，而它在 allowlist 內、watchdog 也不看它 → **完全無人察覺**。

故驗證型 job 另立兩條硬性要求：

- **(4a) 產出可驗結果**：每次執行必須寫下「驗了什麼、結果為何」（檔案或 detail），
  並用 `file_fresh` / `cron_detail` 註冊進 registry。
  「cron 記 success」與「什麼都沒驗」在外部必須可區分。
  範例：`cf_tunnel_verify` 每次寫 `wiki/memory/integration-health/cf-tunnel-verify.json`（7 項結果）。
- **(4b) 外部依賴缺失一律 `raise`，不得 `return`**：缺 binary／缺必要 config（生產環境）
  都要讓 job 記 failure，watchdog 才抓得到。
  由 **fitness step 76 `cron_external_binary_guard.py`** 靜態強制（AST 掃 `@tracked_job`，
  「探測外部執行檔後 return 而不 raise」即 RED；負向測試已驗非永久綠）。

> ⚠️ allowlist 的正確語意是「**無本地可驗產出**」，不是「不重要」。
> 驗證型 job 有產出（驗證結果本身），不該再被豁免。

---

## 案例庫：一天之內四例同型（2026-07-30）

同一天 owner 回報的四個「功能壞掉」，根因形狀**完全相同——元件回報成功，實際沒做或做錯，
錯誤被上層吞掉或誤標**。四例都曾被誤判過，故列為契約教材：

| 案例 | 表象 | 真相 | 誤判過的版本 |
|---|---|---|---|
| 異地備份「沒在跑」 | UI 顯示「尚未同步」 | NAS 每日都有新檔；後端讀 config **UTF-8 BOM 解析失敗** silent 退預設值 | 曾判「UI 誤解」，只加說明 Alert（07-03） |
| 發票辨識全失敗 | 「未辨識出發票資訊」 | 容器缺 zbar/tesseract/libGL（5/27 Docker 化遺失）→ QR/OCR/視覺**三路全滅**，端點仍回 200 | 曾以為「一直都 OK」 |
| 核銷無法存檔 | create 回 409「憑證重複」 | **資料已寫入**；`items` lazy-load → MissingGreenlet → ValidationError（ValueError 子類）被 `except ValueError` 誤標 409 | 曾判「重複發票」 |
| CF Tunnel 監控 | cron 記 success | 三層空跑，一項都沒驗 | 從未被質疑（正因為記 success） |

**共通教訓**：**「成功訊號」本身不可信，必須看產出物。**
`LastTaskResult=0`／`HTTP 200`／`cron success` 都不等於做對事。

---

## 強制機制

- **`producer_output_watchdog.py --coverage`**（fitness step 69）：讀 scheduler.py 全 `@tracked_job`，
  交叉比對 registry（已監控）+ NON_PRODUCER allowlist（豁免）→ 剩下 = **未納管 producer（blind spot）**，
  列出驅動補註冊。
- **每月/每週 fitness**：新 producer 未註冊即現形。
- **cron 自動告警**：`cron_outcome_freshness` 每日檢已註冊 producer，沉默失敗即 LINE 推。

---

## 現況（2026-07-18 首次盤點）

- 52 個 `@tracked_job`；已監控 producer 10、非 producer allowlist ~21、**未納管 producer ~20（blind spot，待逐一補註冊或分類）**。
- 這是誠實的覆蓋缺口——`--coverage` 每次跑會顯示,隨補註冊而縮小(自我進化)。

---

> **核心精神**：**沉默失敗不是靠人盯,是靠制度自動抓。** 每個 producer 註冊產出信號,
> 新增即納管,反覆問題結構性終結。這是免費本地模型也能做好的「運維自主」——AI 的真強項。
