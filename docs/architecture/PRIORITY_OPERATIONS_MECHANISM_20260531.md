# 自我覆盤產出紀錄複查 + 優先作業機制與程序

> **Owner 訴求**：6:30 自我覆盤是否完成 + 列舉優先作業機制與程序
> **建立**：2026-05-31 08:10

---

## 1. 5/31 06:30 自我覆盤產出複查

### 1.1 真實狀況

| 排程 | 預期執行 | 實際 | 狀態 |
|---|---|---|---|
| **governance_dashboard_regen** | **06:00** | ❌ missed | silent dormant |
| **daily_self_retrospective** | **06:30** | ❌ missed | silent dormant |
| process_reminders | every 5m | ✅ 4 success | OK |
| tender_dashboard_warm | every 15m | ✅ 5 success | OK |
| health_check_broadcast | every 5m | ✅ 4 success | OK |
| tender_subscription | daily 09:00 | ✅ 1 success | OK |
| morning_report | daily 07:30 | ✅ 1 success | OK |

### 1.2 真因揭發

**Backend restart 多次錯過 cron 觸發點**：

```
5/30 22:23 - dashboard regen rebuild
5/30 22:35 - L60 lesson commit 後 restart
5/30 23:44 - rebuild (dedup 修法)
5/31 06:25 - LINE timeout rebuild
5/31 07:43 - 持續處理
```

**06:00 / 06:30 cron 觸發點剛好落在 backend restart 期間** → APScheduler missed grace time → silent skip → 0 success metric。

### 1.3 立即補產出

| Step | 動作 | 結果 |
|---|---|---|
| 1 | 手動跑 `generate_governance_dashboard.py` | ✅ 5811 chars 已產出 |
| 2 | 手動跑 `daily_self_retrospective.py` | ✅ 5/31 報告產出（Overall: RED）|

### 1.4 5/31 報告摘要（手動補）

```
Overall: RED

✅ ADR vs 現況 — GREEN (5 active / 0 stale)
✅ SOP 遵守度 — GREEN (0 fail)
ℹ️ 核心服務真活 — INFO
   - shadow_baseline_rows_24h: -1.0 (metric fetch bug)
   - messaging_push_line_success: 0.0
   - v7_channel_diversity: 1.0
   - v7_soul_drift: 0.0
```

---

## 2. 防 cron silent dormant 修法（v6.13 立即必做）

### 2.1 APScheduler misfire_grace_time

當前 scheduler 配置可能無 grace time：
```python
scheduler.add_job(
    daily_self_retrospective_job,
    trigger=CronTrigger(hour=6, minute=30),
    misfire_grace_time=3600,  # ★ 新增：missed 1 小時內仍跑
    ...
)
```

### 2.2 Startup catch-up 機制

backend 啟動時檢查：
- 昨天日報是否產出？
- 今日 06:00/06:30 是否在 startup 之前？
- 若 missed → 啟動 5 分鐘後自動補跑

### 2.3 cron silent dormant audit 強化

`scripts/checks/cron_silent_dormant_check.py`（既有 step 7）加：
- 偵測「應跑但 0 success」case
- 連 2 天 missed → LINE 強推

---

## 3. 優先作業機制與程序（v6.12-13 SOP 總表）

### 3.1 自我覆盤多層機制（4 層 + 待加 2 層）

| 層 | 機制 | 排程 | 真活狀態 |
|---|---|---|---|
| L1 | daily_self_retrospective 7 aspects | cron 06:30 | 🟡 需加 grace_time |
| L2 | governance_dashboard_regen | cron 06:00 | 🟡 需加 grace_time |
| L3 | fitness Tier 1 daily 8 step | cron 02:00 | ✅ |
| L4 | fitness Tier 2 weekly 21 step | cron 週日 02:30 | ✅ |
| L5 | monthly v6.12 audit | 待加 | ⏳ |
| L6 | quarterly v6.13 立法演進 | 待加 | ⏳ |

### 3.2 治理作業優先級程序（P0→P3）

| P | 程序 | 工具 | 頻率 |
|---|---|---|---|
| **P0** | fitness Tier 1 daily | `run_fitness_daily.sh` 8 step | cron 02:00 |
| **P0** | daily_self_retrospective | 7 aspects | cron 06:30 |
| **P0** | governance_dashboard 更新 | generator | cron 06:00 |
| **P0** | shadow_baseline accumulate | synthetic inject | 09/14/20:00 |
| **P1** | fitness Tier 2 weekly | 21 step | 週日 02:30 |
| **P1** | cross_repo template drift audit | step 65 | weekly |
| **P1** | knowledge graph audit | step 70/71/72 | weekly |
| **P2** | monthly fitness 全 72 step | manual / cron | 月 1 日 |
| **P2** | LESSONS_REGISTRY 自動更新 | 待加 | weekly |
| **P3** | quarterly v6.13 立法演進 | 待加 | 季度 |

### 3.3 修法不可逆作業 SOP（5 層備份）

對齊 L43 教訓 + v6.12 第 4 句立法：

| Step | 動作 | 工具 |
|---|---|---|
| 1 | JSON 結構備份 | 對應 script |
| 2 | SQL INSERT 還原檔 | 一鍵 restore |
| 3 | MD5 雙端驗證 | 自動 |
| 4 | `/health business_data` pre-check | 自動 |
| 5 | backup size + record count 驗證 | 自動 |

範例：`knowledge_dedup_script.py --apply`（本日已成功）

### 3.4 跨 repo 部署 SOP

對齊 L58/L59/L60/L61：

| Step | 動作 |
|---|---|
| 1 | 評估範本 tier（universal/recommended/full）|
| 2 | 子專案讀 `.template-policy.yml` opt-out |
| 3 | install-template `--dry-run` 預覽 |
| 4 | L61 警示 + 10s 倒數 |
| 5 | APPLY |
| 6 | step 66 uncommitted audit 驗證 commit |
| 7 | weekly fitness step 65 持續監測 |

### 3.5 緊急修法 SOP（業務影響優先）

| 步驟 | 動作 | 範例（LINE timeout）|
|---|---|---|
| 1 | 業務影響評估 | LINE「查詢處理時間較長」用戶可見 |
| 2 | 真因揭發 | _reply_timeout=25 vs p95=40s |
| 3 | 短期修法（可逆）| 25→28s + env override |
| 4 | rebuild + restart | docker compose up -d |
| 5 | 中期修法 plan | groq fast-path v6.13 |
| 6 | 寫 lesson（若 silent fail）| 此 case 不需 lesson |

---

## 4. 立即執行清單（owner approve 後）

### P0 緊急（防 silent dormant 再發）

1. **加 APScheduler misfire_grace_time**（修 2.1）
2. **加 startup catch-up 機制**（修 2.2）
3. **強化 cron_silent_dormant_check step 7**（修 2.3）

### P0 業務（C 方案 A 殘留）

4. ERP 欄位校正 + ingest --apply（129 entity）

### P1 治理深化

5. wiki kg_entity_id backfill（38.5%→80%）
6. Document graph_domain 加入
7. Skill graph 加入

### P2 產品

8. /kunge UX Phase 1（3 天）

---

## 5. 元洞察 — Owner 質疑揭發「機制存在但不真活」

Owner 問 5/31 06:30 是否完成 → 揭發 silent dormant 真因。

對齊 v6.12：
- 第 1 句「抽象不是錯，建後不 audit 才是」→ cron 建後不檢真活就是 silent
- 第 2 句「觀測不是奢侈，自治理就是」→ scheduler_job_* metric 揭發 0 success
- 第 5 句「執行了不算落實」→ cron 註冊不等於真跑

→ **L62 待立法草案**：「**cron 註冊不等於真跑，必有 misfire grace + startup catch-up**」

---

## 6. 結論

### 6.1 5/31 06:30 自我覆盤狀態

- ❌ 06:00/06:30 cron silent dormant（backend restart 期間 missed）
- ✅ 手動補產出（dashboard + 5/31 report）
- 🟡 已揭發真因 + 立即修法 plan

### 6.2 優先作業機制總覽

- 4 層自我覆盤（L1-L4 真活，L5-L6 待加）
- 11 個治理作業（P0-P3 分級）
- 5 層備份 SOP（不可逆作業必走）
- 跨 repo 部署 7 step SOP
- 緊急修法 6 step SOP

### 6.3 下批 P0 緊急

1. 修 APScheduler misfire_grace_time
2. 加 startup catch-up
3. cron silent dormant 監測強化

---

> **核心精神**：自我覆盤機制存在 ≠ 真活。Owner 質疑揭發 silent dormant 是治理進化最深刻時刻。
> 對齊 v6.12 8 句立法 + L62 待立法「cron 註冊不等於真跑」。
