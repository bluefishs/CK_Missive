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
