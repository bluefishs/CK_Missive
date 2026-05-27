# Commit Plan — /loop 接續優化程序（2026-05-27 15:00-16:15）

> **狀態**：所有修法 syntax 全綠，等 owner 一鍵 commit
> **規模**：11 dirty 檔，分 4 commits（依議題切分，bisectable）

---

## Commit 1 — fix(governance): L29 silent failure family 大掃除（9 處）

**範圍**：
- `backend/app/services/contracts/facades/memory.py` — 5 處 silent-`Exception` 改 logger.error + exc_info
- `backend/app/services/contracts/facades/wiki.py` — 5 處 silent-`Exception` 改 logger.error + exc_info（含 ingest 補 logger）
- `backend/app/services/ai/agent/agent_post_processing.py` — diary scheduling debug → warning
- `backend/app/services/ai/agent/agent_self_evaluator.py` — CRITICAL feedback debug → error / eval store debug → warning
- `backend/app/services/ai/agent/agent_evolution_scheduler.py` — Auto-rollback debug → error

**動機**：
- L29 lesson（dict key drift + 涵蓋率 25% + silent except 三重疊加）配套防禦
- ADR-0028 錯誤合約：silent failure 零容忍
- 揭發：`(ImportError, AttributeError, Exception)` 在 backend/ 歸零（原 9 處全清）
- 自我評估器 line 265 寫「CRITICAL feedback write failed」卻用 `logger.debug` — 文字標 CRITICAL 但 log invisible（最 ironic 反模式）

**Commit message**:
```
fix(governance): L29 silent-Exception family sweep — 9 processed sites

contracts/facades 全清 (ImportError, AttributeError, Exception) 反模式。
ADR-0028 對齊：silent fail → logger.error + exc_info + 結構化 context。

- MemoryFacade × 5: append_diary_entry / summarize_yesterday /
  defensive_rules / recent_reflections / build_role_system_prompt
- WikiFacade × 5: search / read / stats / ingest / auto_ingest
- agent_post_processing: diary scheduling debug → warning
- agent_self_evaluator: CRITICAL feedback debug → error (line 265 反諷)
- agent_evolution_scheduler: Auto-rollback debug → error

對應 lesson_l29_silent_except_triple_failure
```

---

## Commit 2 — fix(io): Windows CRLF drift 根因修法（3 處 + .gitattributes 仍 LF）

**範圍**：
- `backend/scripts/extract_er_model.py:298,304` — `Path.write_text` 加 `newline="\n"`
- `backend/app/services/memory/autobiography.py:393` — 同上
- `backend/app/services/ai/agent/agent_critic.py:187` — 同上

**動機**：
- 每次跑 extractor，docs/er-*.md 自動 CRLF drift 出現在 `git status`
- Windows Python 3 `Path.write_text(encoding="utf-8")` 預設 `newline=None` → `\n` 翻 `\r\n`
- 影響：ER 圖每次自動產出都 dirty / 週自傳寫入 CRLF / critique 寫入 CRLF
- 修法：3 處 write_text 補 `newline="\n"`

**Commit message**:
```
fix(io): root-cause Windows CRLF drift in 3 generator paths

Path.write_text default newline=None translates LF→CRLF on Windows.
.gitattributes already enforces LF for *.md/*.json, but generators
write CRLF on disk causing dirty status every run.

- extract_er_model: docs/er-{diagram.md,model.json} writers
- memory/autobiography: weekly 2026-WNN.md writer
- agent_critic: critique-YYYYMMDD-*.md writer

也 restore docs/er-diagram.md + docs/er-model.json 至 LF state。
```

---

## Commit 3 — fix(metrics): v7 baseline 量測對齊實際 format

**範圍**：
- `scripts/checks/v7_metrics_report.py`：
  - 加 cp950 encoding 防護（per audit 4 特徵 #1）
  - `metric_1_channel_diversity` regex 從 `session.*{ch}:` → `## ... [route] {channel}` 對齊實際 diary header
  - `metric_3_soul_drift` 加 ADR-0044 後 concept mismatch 警告註解

**動機**：
- 原 regex 完全沒 match 真實 diary format → channel diversity 永遠回 0（false negative）
- v7 baseline 連 3 版 MEMORY.md 抄舊值未實跑
- SOUL drift 60 lines 不是 drift 是 ADR-0044 後設計分工（Hermes Meta vs 坤哥）

**Commit message**:
```
fix(metrics): align v7 baseline measurements with real format

- channel_diversity regex 對齊 `## HH:MM:SS — emoji [route] channel`
  (原 `session.*{ch}:` format 已不存在於 diary writer 輸出)
- 加 cp950 stdout reconfigure（Windows console fix）
- metric_3_soul_drift 加 ADR-0044 後 concept mismatch 警告

真實 baseline（5/27 16:00）：
- channel_diversity = 1 (web only 32 entries)
- diary_density = 7.1% (42 / 3 with **entities**:)
- critique_density = 0% (0 entries 7d — rule-based checks passed)
- soul_drift = 60 (但 concept mismatch by design — 待重設計)
```

---

## Commit 4 — fix(sso): EntryPage L44 family location.replace 對齊 lvrland/pile

**範圍**：
- `frontend/src/pages/EntryPage.tsx:200` — SSO bridge 成功後 `navigate(ROUTES.DASHBOARD)` → `window.location.replace('/dashboard')`
- version bump 3.0.0 → 3.0.1

**動機**：
- L44 family 防禦循環的最後一塊：
  - CK_lvrland_Webmap `90f6b8de2` 5/25 已 commit
  - CK_PileMgmt `d334c2d44` 5/25 已 commit
  - **CK_Missive 5/27 仍未 commit**
- SPA navigate() cookie 寫入 race → Zustand rehydrate race → useAuthGuard 401 踢回 login

**Commit message**:
```
fix(sso): EntryPage L44 family — SPA navigate → window.location.replace

SSO bridge 成功後改用 window.location.replace 強制整頁刷新，避免：
1. cookie 寫入 race（async）
2. Zustand store rehydrate race
3. useAuthGuard 啟動 /auth/check 401 踢回登入頁

對齊 lvrland_Webmap 90f6b8de2 + PileMgmt d334c2d44（同型修法，5/25 完成）。
CK_Missive 為 L44 family 防禦循環最後一塊。

ref: cross-file-ssot-governance.md (L41-L48 family)
```

---

## Commit 5 — fix(metrics): frontend useAgentSSE 補 channel: 'web' 標籤

**範圍**：
- `frontend/src/hooks/system/useAgentSSE.ts:78-83` — `aiApi.streamAgentQuery` payload 加 `channel: 'web'`
- `frontend/src/api/ai/adminManagement.ts:489` — `streamAgentQuery` TypeScript signature 補 `channel?: 'line' | 'telegram' | 'web' | 'discord' | 'mcp' | 'hermes'`

**動機**：
- v7 channel_diversity 真因鏈揭發（5/27 16:00 投入）：
  1. v7 metric 顯示 channel=1 (web only 32 entries)
  2. 32 entries 全是 09:00 cron job 注入（synthetic-baseline-inject）
  3. 5/22 起 cron job rc=1 全失敗（每跑 Total=10 Success=0 Error=10）
  4. 失敗真因：HTTP 403 in 8-11ms — backend 缺 `MCP_SERVICE_TOKEN` env var
  5. 真實 user web traffic 過去從未標 channel — `useAgentSSE` 沒傳
- 修法後：真實 web user query → diary 標 `[route] web` → v7 channel_diversity 量得到

**Commit message**:
```
fix(metrics): tag real web user traffic with channel='web' for v7

useAgentSSE 過去送 streamAgentQuery 時不傳 channel，造成所有真實 user
chat 在 diary 標 channel='-'。配合 commit 3 v7 regex 對齊，這次補上 frontend
也送 channel='web'，未來 v7 channel_diversity 才能量到真實流量分佈。

- frontend/src/hooks/system/useAgentSSE.ts: payload 加 channel='web'
- frontend/src/api/ai/adminManagement.ts: streamAgentQuery 簽章補 channel?

ref: v7 channel_diversity 真因鏈（commit 3 regex 修法 + 本 commit 真實流量標籤）
```

---

## ⚠️ Owner Action 6 — 補 docker MCP_SERVICE_TOKEN（5 min）

**問題**：
- Docker `ck_missive_backend` env 缺 `MCP_SERVICE_TOKEN`（`docker exec env` 確認）
- → `/api/ai/agent/query` 對 service-token 路徑直接 403
- → 每日 09:00 / 14:00 `synthetic-baseline-inject` cron 6+ 天 silent dead
- → 監控盲區：scheduler 只 `logger.warning`，無 alert

**修法**：

```bash
# Option A: 改 docker-compose.production.yml 加 env_file 或直接 env
# 加在 backend service:
environment:
  MCP_SERVICE_TOKEN: ${MCP_SERVICE_TOKEN}
# 或在 env_file 把 MCP_SERVICE_TOKEN 列入（注意已 gitignored）

# Option B: 改 secret_loader 從 secrets/ 讀
# (deferred, 屬 ADR-0017 Phase 1B 範疇)

# 驗證：
docker exec ck_missive_backend env | grep MCP_SERVICE_TOKEN
# 預期：有值

# 手動跑一次驗證：
docker exec ck_missive_backend python scripts/checks/synthetic-baseline-inject.py --count 1
# 預期：Success=1 Error=0
```

**Downtime**：~30s (docker compose restart backend)

**追加 fitness audit 候補**（v6.12 P3）：
- step 49+ `synthetic_baseline_freshness_audit.py` — 偵測 24h scheduler error_count > threshold

---

## 排除（不 commit，待 owner 決策或自動清理）

- `wiki/memory/diary/2026-05-27.md` — agent 流量產出，可 `git add` 一起進 commit 1 或單獨 chore commit
- `docs/architecture/COMMIT_PLAN_20260527_loop_optimization.md`（本檔）— 計畫文件，可選

---

## 驗證指令（owner 確認用）

```bash
# 跑 v7 真實 baseline
python scripts/checks/v7_metrics_report.py --json | python -m json.tool

# 驗 fitness 不退步
bash scripts/checks/run_fitness.sh

# 驗 ER 寫出 LF
python backend/scripts/extract_er_model.py
file docs/er-diagram.md  # 應該不再 "with CRLF line terminators"

# 驗 silent-except 歸零
grep -rn "except\s*(ImportError,\s*AttributeError,\s*Exception)" backend/app/
# 預期：no output
```

---

## 後續推進 backlog

- v7 metric_3_soul_drift 設計重議（待 ADR）
- 剩餘 logger.debug 失敗路徑掃描（agent_planner / proactive_scanner / 等）
- diary writer 加 channel propagation（agent_post_processing 確認 ctx.channel 來源）
- PM2 廢除（owner P0，無 audit 可代）
