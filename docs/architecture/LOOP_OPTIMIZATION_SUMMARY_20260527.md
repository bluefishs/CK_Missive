# /loop 接續優化程序 — Owner Executive Summary（2026-05-27）

> **時段**：2026-05-27 14:35 ~ 16:35（5 個 /loop iteration，自我配速 ~25 min/iter）
> **觸發**：owner /loop 連續推進 + 系統治理 sweep
> **規模**：17 dirty files / 0 commit（等 owner 一鍵）
> **狀態**：syntax 全綠 / fitness 48/48 PASS（baseline 不退）

---

## TL;DR — 一段話結論

過去 9 天的 v6.11 audit consolidation 已自動化 7/8 大根因，但 **fitness 全綠並非系統真綠** —— 公網仍命中 PM2 stale code、synthetic baseline cron 6+ 天 silent dead、Docker container 9 天零 agent 流量。本次 5 iteration sweep 揭發完整真因鏈、修法 16 處 silent failure 與 4 處 CRLF Windows bug、補 frontend channel 標籤、產出 5 bisectable commits + 1 owner action（補 docker MCP_SERVICE_TOKEN env）等 owner 一鍵收尾。

---

## 一、累計成果（按治理類別）

| 類別 | 處理數 | 詳情 |
|---|---|---|
| **L29 silent-Exception family（ADR-0028）** | **16 處** | contracts/facades × 10（memory ×5 / wiki ×5）+ agent layer × 6（post_processing / self_evaluator / evolution_scheduler / proactive_scanner / planner / token_tracker）|
| **CRLF Windows 根因** | **4 處** | extract_er_model / autobiography / agent_critic + restore docs/er-*.md 至 LF |
| **v7 baseline 量測對齊** | **3 處** | regex 對齊 diary header / cp950 防護 / SOUL drift ADR-0044 註解 |
| **真實流量 channel 標籤** | **1 處** | frontend useAgentSSE 補 `channel: 'web'` + TS signature 補型別 |
| **新發現 dormant 議題** | **5 件** | 見「二」|

---

## 二、新揭發 dormant 議題（按嚴重序）

### 🔴 P0 — synthetic_baseline_inject cron 6+ 天 silent dead

**因果鏈**：
```
v7 channel_diversity = 1 (web only 32 entries 7d)
  └── 32 entries 全是 5/20-5/21 09:00 cron job 產出
        └── 5/22 起 cron 每跑 Error=10/10 (rc=1)，但 scheduler 只 warning
              └── HTTP 403 in 8-11ms：「Service token not configured」
                    └── docker container 缺 `MCP_SERVICE_TOKEN` env var
                          └── docker-compose 沒 propagate .env 該變數
```

**修法**：補 `docker-compose.production.yml` backend service `environment: MCP_SERVICE_TOKEN: ${MCP_SERVICE_TOKEN}` + `docker compose restart backend`（5 min）。詳見 COMMIT_PLAN §Owner Action 6。

### 🔴 P0 — 公網仍命中 PM2 stale code（L43 路由迷宮 live）

```
local  /health → docker container（production / pool 完整 / docs=1799）
public /health → PM2 native uvicorn（development / 無 pool / 同 docs=1799）
```

- Docker container 47h+ healthy 但 **`memory_diary_appends_total = 0.0`**（9 天零流量）
- PM2 接收所有真實流量
- 所有 Prometheus / fitness metric 都是測 0 traffic 後的假象

**修法**：依 `docs/runbooks/pm2-deprecation-sop.md` 4 階段執行（3-4h，owner 親手，建議夜間離峰）。

### 🟡 P1 — v7 baseline MEMORY.md 連 3 版抄舊值

| 指標 | 抄舊值 | 實跑 5/27 16:00 |
|---|---|---|
| channel_diversity | 1 | 1 (web only)（但 cron 死，未來真實量測歸 0）|
| diary_density | 1.1% | **7.1%**（42 entries / 3 with `**entities**:`）|
| critique_density | 100% | **0%**（0 entries 7d — 規則式檢查皆通過，非寫入鏈死）|
| soul_drift | 57 | 60（但 ADR-0044 後 concept 分化，非真 drift）|
| provider_gap | 待跑 | 待跑（fidelity_log.jsonl 從未產出）|

**修法**：MEMORY.md 已校正（本次 loop 內），未來建議加 fitness audit 自動覆寫 baseline。

### 🟡 P1 — SOUL.md 跨 repo 治理 ambiguity

- Missive `wiki/SOUL.md` v2.0.0「坤哥 — Missive 意識體」frontmatter 宣告 `source_of_truth: true + sync_targets: CK_AaaP/...`
- AaaP `runbooks/hermes-stack/SOUL.md` v1.0.0「Hermes Meta — 共同大腦」（128 lines vs Missive 188 lines）
- ADR-0044 後 AaaP 升 meta-governance，兩檔本質為不同 entity，但 Missive frontmatter 未更新

**修法**：建議寫 ADR 重議 SOUL.md 跨 repo 角色（保留 source_of_truth 並做真 mirror / 或 deprecate sync_targets 改各自獨立人格）。

### 🟢 P2 — EntryPage L44 family 漏 commit

- CK_lvrland_Webmap `90f6b8de2` 5/25 已 commit
- CK_PileMgmt `d334c2d44` 5/25 已 commit
- **CK_Missive 5/27 仍 working tree 未 commit**（修法早已存在）

**修法**：見 COMMIT_PLAN commit 4（owner ack 即可）。

---

## 三、Commit Plan（5 bisectable + 1 owner action）

| # | Type | Scope | 檔數 |
|---|---|---|---|
| 1 | fix(governance) | L29 silent-Exception family sweep | 6 |
| 2 | fix(io) | Windows CRLF drift 根因 | 3 + 2 restore |
| 3 | fix(metrics) | v7 baseline 量測對齊 | 1 |
| 4 | fix(sso) | EntryPage L44 family location.replace | 1 |
| 5 | fix(metrics) | frontend channel='web' tag | 2 |
| **OA6** | **deploy** | **docker MCP_SERVICE_TOKEN env**（owner 5 min）| - |

詳細 commit messages：`docs/architecture/COMMIT_PLAN_20260527_loop_optimization.md`

---

## 四、Working Tree 17 dirty 一覽

```
M backend/app/services/ai/agent/agent_critic.py           # commit 2 (CRLF)
M backend/app/services/ai/agent/agent_evolution_scheduler # commit 1 (L29 × 4)
M backend/app/services/ai/agent/agent_planner.py          # commit 1 (L29)
M backend/app/services/ai/agent/agent_post_processing.py  # commit 1 (L29)
M backend/app/services/ai/agent/agent_proactive_scanner   # commit 1 (L29 × 2)
M backend/app/services/ai/agent/agent_self_evaluator.py   # commit 1 (L29 × 2)
M backend/app/services/ai/core/token_usage_tracker.py     # commit 1 (L29)
M backend/app/services/contracts/facades/memory.py        # commit 1 (L29 × 5)
M backend/app/services/contracts/facades/wiki.py          # commit 1 (L29 × 5)
M backend/app/services/memory/autobiography.py            # commit 2 (CRLF)
M backend/scripts/extract_er_model.py                     # commit 2 (CRLF 根因)
M frontend/src/api/ai/adminManagement.ts                  # commit 5 (TS signature)
M frontend/src/hooks/system/useAgentSSE.ts                # commit 5 (channel='web')
M frontend/src/pages/EntryPage.tsx                        # commit 4 (L44 family)
M scripts/checks/v7_metrics_report.py                     # commit 3 (regex/cp950/SOUL)
M wiki/memory/diary/2026-05-27.md                         # agent traffic 自動產出
? docs/architecture/COMMIT_PLAN_20260527_loop_optimization # commit 0 or 6 (此計畫文件)
```

---

## 五、驗證指令（owner 確認用）

```bash
# 1. Fitness baseline 不退步（應 48/48 PASS）
bash scripts/checks/run_fitness.sh

# 2. v7 真實 baseline（regex 修正後）
python scripts/checks/v7_metrics_report.py --json | python -m json.tool

# 3. 驗 L29 silent-Exception 在 contracts 歸零
grep -rn "except\s*(ImportError,\s*AttributeError,\s*Exception)" backend/app/services/contracts/
# 預期：no output

# 4. 驗 ER 寫出 LF（修法後不再 dirty）
python backend/scripts/extract_er_model.py
git status --short docs/er-*

# 5. （owner action 6 後）驗 synthetic baseline 恢復
docker exec ck_missive_backend env | grep MCP_SERVICE_TOKEN
docker exec ck_missive_backend python scripts/checks/synthetic-baseline-inject.py --count 1
# 預期：Success=1 Error=0
```

---

## 六、v6.12 backlog（推進方向）

### 立即可做（不需 owner）
- [ ] v7 metric_3_soul_drift 設計重議 ADR 草稿
- [ ] step 49 `synthetic_baseline_freshness_audit.py`（24h scheduler error_count alert）
- [ ] MEMORY.md v7 baseline 加 fitness 自動覆寫

### Owner action 排程
- [ ] **P0** owner action 6（補 docker MCP_SERVICE_TOKEN，5 min）
- [ ] **P0** PM2 廢除 4 階段（3-4h，依 SOP）
- [ ] **P0** Owner SSO E2E 3 subdomain（5 min，L41 收尾）

### v6.12 P3 audit 候補
- container startup race
- DB pool exhaustion silent
- cloudflared metric scraping 404
- frontend bundle size drift
- B-plan PowerShell hook 1 週觀察期

---

## 七、Session 結尾原則

- 不擅自 commit / push
- 不擅自改 docker-compose / .env
- 所有 silent failure 修法保留**降級行為**（避免引入新 raise 行為改變執行語意）
- 跨檔 SSOT family（L41-L48）規範持續引用

> **核心精神延續**：「Audit 自動化的價值不在 GREEN，在於把 dormant 從 days 縮到 seconds」（RETRO_20260527）。本次 loop 把 5 個新 dormant（含 6+ 天的 synthetic cron silent dead）攤在 owner 眼前，並把 16 處 L29 同型反模式根治。
