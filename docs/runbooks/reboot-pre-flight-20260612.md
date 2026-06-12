# 重啟前 Pre-Flight Runbook — 2026-06-12（v6.18 治理體系成型後）

> 觸發：owner 準備重啟電腦。延續 06-09/06-02 runbook 格式。
> 本次重啟前完成 v6.18 圖譜治理擴大（8 audit 57b-57h）+ 真因根治連發（calendar/cron/security/坤哥）。

## A. Pre-Flight 4 步（重啟前確認，全通過）

| # | 項目 | 狀態（2026-06-12 07:5x） |
|---|---|---|
| A1 | **Git**：code commits 全 push origin（ahead 0）；唯餘 cron 副產物已歸檔 commit | ✅ working tree clean |
| A2 | **容器**：5 容器全 healthy；cloudflared pin `2026.5.0`、postgres `pgvector:0.8.0-pg15`、backend `ck-missive-backend:production`（含今日全部修法 baked） | ✅ |
| A3 | **DB volume（L43 防線）**：compose `name: ck_missive_postgres_dev_data` + `external: true`（非空殼 ck_missive_postgres_data） | ✅ |
| A4 | **公網**：`missive.cksurvey.tw/api/health` 200 | ✅ |

## B. 重啟驗收基準（業務量 — 重啟後須一致或自然成長）

| 指標 | 重啟前基準 |
|---|---|
| documents | **1846** |
| canonical_entities (KG) | **26837** |
| calendar synced (Google) | **1045**（推 6a3478 共享日曆） |
| 前端 dist | 06-12 07:46（57g 遷移已 build） |

## C. 重啟後驗收 5 步

1. `docker compose -f docker-compose.production.yml up -d` → 5 容器 healthy
2. 公網 `curl https://missive.cksurvey.tw/api/health` → 200
3. 業務量比對 B 基準（docs≥1846 / kg≥26837 / cal synced≥1045）— 低於即 L43 同型 volume drift，停！
4. **治理 audit smoke**（容器內）：
   - `python /app/scripts/checks/scheduler_liveness_audit.py` → 0 DORMANT/0 FAILED
   - `python /app/scripts/checks/dialogue_learning_coverage_audit.py` → 確認對話學習真活
   - `python /app/scripts/checks/calendar_sync_reconciliation_audit.py` → synced 對賬 GREEN
5. **cron 真活**：重啟後隔日 02:00 確認 cleanup_events/security_scan/fitness_daily 在 `/app/logs/cron_events.jsonl` 有 success（misfire 修法生效驗證）

## D. 本次治理交付索引（重啟後可參考）
- 8 audit：`scripts/checks/{config_settings_drift,calendar_title_standard,calendar_sync_reconciliation,code_duplication,scheduler_liveness,frontend_api_wiring,dialogue_learning_coverage}_audit.py`（fitness step 57b-57h）
- lessons：`LESSONS_REGISTRY.md#L70`（calendar drift）/`#L71`（圖譜≠治理）/`#L72`（排程註冊≠真活）
- SSOT 擴充：`redis_client.get_cached_redis` / `BaseRepository.{grouped_count,get_by_ids}` / `schemas/_text_utils` / `services/memory/_utils` / `services/common/roc_date`

## E. 唯一 owner 待辦（非 code）
- **57h 對話學習扎根真實**：用坤哥 chat（web `/kunge` ChatTab）問真實業務問題 → 餵真實 trace（近 7 日 204 synthetic/0 real）→ 57h RED→GREEN。
