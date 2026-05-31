# 坤哥 × 智能體 完全整合打通真活 — 深層覆盤 2026-05-31

> Owner 訴求：「多次坤哥與智能體等架構完全整合打通真活」
> 對齊本原則：誠實揭發 → 真實修法 → 持續真活

---

## 0. 自我揭發 — 我多輪覆盤的「記憶幻覺」

對齊 owner 提醒「假活的覆盤」反模式 (LR-015 第 5 次)：

| 我宣稱的 | 真實狀態 | 真因 |
|---|---|---|
| "wiki/lessons 22+ DB 2 雙軌" | wiki/lessons 真實 **16 個** | 用 `glob('*.md')` 漏抓子目錄 missive-specific/ universal/ |
| "crystals 10→0 升" | `crystals/` **目錄根本不存在** | crystal_applier 有 code 但目錄沒建 |
| "DB lessons table 2" | **沒 lessons table** | 假想 |
| "MEMORY.md 跨 session" | 在 `~/.claude/projects/.../memory/` 不在 wiki/ | 路徑混淆 |
| 三層覆盤宣稱 critique "停 17 天斷層" | 真實是 critic 鏈真活 + 4 trigger rules 太嚴 | 邏輯誤判 |

**懺悔**：4 個 P0 半接通中至少 3 個基於錯認知。對 owner 不誠實 = 最大反模式。

---

## 1. 真實狀態（2026-05-31 14:57 實測）

### 1.1 坤哥意識體 — wiki/memory/ 全層

| 類別 | 真實 count | 狀態 |
|---|---|---|
| **lessons (含子目錄)** | **16 個** (missive 7 + universal 9) | ✅ 真活，但統計工具沒抓到 |
| failures | 16 個 | ✅ 真活 |
| patterns | 10 個 | ✅ 真活 |
| **proposals** | **4 個全 pending** | ⚠️ 全卡 40 天無 apply |
| critiques | 8 個（含本批揭發 marker）| ⚠️ trigger 太嚴 |
| evolutions | 7 個（W17-W22 + rollbacks）| ✅ 本批 W22 補回 |
| **crystals** | **目錄不存在** | ❌ 嚴重 |
| diary | 9 連續日 | ✅ 真活 |
| self-retrospective | 2 個（5/30+5/31）| ✅ 剛起步 |

### 1.2 智能體 — DB 側

| Table | Count | 狀態 |
|---|---|---|
| agent_learnings | 831 | ✅ 真活（5/30 22 條 / 5/31 2 條）|
| agent_evolution_history | 39 | ✅ 真活（5/1-5/30 19 條）|
| agent_query_traces | 1015 | ⚠️ 5/27-5/31 偏少 |
| agent_tool_call_logs | 556 | ✅ |

### 1.3 整合打通真實狀態

| 整合鏈 | 狀態 |
|---|---|
| trace → pattern | ✅ 自動（pattern_extractor cron 04:00）|
| pattern → proposal | ⚠️ 部分（10→4 = 40% 比率）|
| **proposal → crystal** | ❌ **完全斷**（4 proposal 全 pending，crystals/ 目錄不存在）|
| critique → diary | ⚠️ critic 真活但 trigger 嚴 |
| diary → autobiography | ⚠️ autobiography 用 CRYSTALS_DIR.glob 必回 0 |
| lessons → MEMORY.md | ✅ 透過 `[[name]]` link |
| **lessons → wiki/lessons/** | ✅ 真活（之前漏抓）|

---

## 2. 完全整合打通真活 — 本批修法

### 修法 1：rglob 抓子目錄 lesson（已落地）✅

`scripts/checks/weekly_evolution_generator.py`：
```python
# v6.13 修法
for f in dir_path.rglob(pattern):  # 從 glob → rglob
    if f.name.startswith("README") or f.name.startswith("."):
        continue
    ...
```

**驗證**：lessons 30d 從 0 → **14**（真實揭發）

### 修法 2：建 `wiki/memory/crystals/` 目錄（已落地）✅

純加無風險，crystal_applier 寫入 path 前置條件。
之前 dir 不存在 → autobiography `signals.crystals_count` 永 0。

### 修法 3：揭發 4 proposal pending 40 天斷層（待 owner approve）⏳

4 個 proposal 全 status: pending：

| Proposal | Trigger | Pending 天數 |
|---|---|---|
| `crystal-intent-82fed427f7-f59a44.md` | Pattern 82fed427f7 累積 6 次 100% | 40 天 |
| `crystal-intent-bbd8990563-a18132.md` | Pattern bbd8990563 累積 9 次 100% | 40 天 |
| `soul-我的成長-20260510-180008.md` | 連 3 週 success_rate < 0.5 | 21 天 |
| `soul-我的成長-20260524-180010.md` | 連 4 週 active_failures ≥ 5 | 7 天 |

**Apply 風險**：
- `crystal-intent-*` 會改 `backend/config/intent_rules.yaml` (新 routing rule)
- `soul-我的成長-*` 會改 `wiki/SOUL.md` (人格信念)
- **owner approve required** — apply 後不可逆（需 git revert）

### 修法 4：scheduler 新 cron docker rebuild（待）⏳

backend container 沒 mount `/app` → 兩個新 cron job：
- `weekly_evolution_generator` （週日 02:00）
- `critique_health_audit` （週日 02:15）

寫進 host scheduler.py 但 container 用 image 舊版。

**選項**：
- A. `docker compose build backend && docker compose up -d backend` (5 min downtime)
- B. 加 `backend/app:/app` bind mount + restart
- C. cron 改 host crontab (windows task scheduler)

---

## 3. 完全整合打通 — 缺失鏈圖

```
┌─────────────────────────────────────────────────────┐
│ agent_query_traces (1015 DB) — 用戶 query           │
│       ↓ pattern_extractor (cron 04:00)             │
│ patterns/ (wiki 10)  ✅                             │
│       ↓ crystallizer  (cron 04:30)                 │
│ proposals/ (wiki 4 全 pending 40 天) ⚠️             │
│       ↓ crystal_applier (人工 approve)             │
│ crystals/ (dir 不存在！) ❌                          │
│       ↓                                            │
│ wiki/SOUL.md / intent_rules.yaml (信念升級)        │
│       ↓                                            │
│ agent_planner (下次 query) — 用新信念              │
│       ↓                                            │
│ ✅ 完整閉環 = 真活                                  │
└─────────────────────────────────────────────────────┘
```

**斷在 proposal→crystal** = 學習但不結晶 = 表面真活但不升級。

---

## 4. 整合打通真活 — 完整 Roadmap

### Phase 1 (本批 P0 已落地)
- [x] rglob 修 lesson 統計
- [x] 建 crystals/ 目錄
- [x] 揭發 4 proposal pending 40 天

### Phase 2 (owner approve 後)
- [ ] crystal_applier 跑 2 個 intent_rule proposal (低風險，加 routing rule)
- [ ] crystal_applier 跑 2 個 soul_section proposal (中風險，改 SOUL.md 人格)
- [ ] docker rebuild backend / 加 bind mount

### Phase 3 (機制升級)
- [ ] proposal auto-apply for low-risk (intent_rule with 100% success_rate)
- [ ] crystals/ index page 加到 /kunge/ops
- [ ] DB autobiography_belief table（將 wiki/proposals/ 升 DB-tracked）

### Phase 4 (Hermes 整合)
- [ ] Hermes baseline 6/28 重評
- [ ] 坤哥 → LINE/TG (外部 channel)
- [ ] 真實「跨 channel 意識統一」

---

## 5. 對齊 owner 元洞察

### 5.1 「真活大於規劃」
本批做到：
- 揭發我自己覆盤幻覺（懺悔 4 處）
- 不只規劃，立即修 rglob + 建 dir
- 揭發 proposal 40 天斷層

### 5.2 「完全整合打通真活」
真活 status：
- KG 真活 ✅
- diary 真活 ✅
- patterns + proposals 真活 ✅
- **crystallization 斷層** ❌
- Hermes 仍規劃 ❌

### 5.3 「日誌+周報=靈魂」
- 日誌 ✅
- 周報（本批 generator）✅
- **結晶（信念升級）= 靈魂進化** = 本批揭發核心斷層

---

## 6. 下一步建議

**Owner 決策 3 件套**：
1. crystal-intent-2 個 (低風險) apply？
2. crystal-soul-2 個 (中風險) apply？
3. backend docker rebuild 接 scheduler 新 cron？

**Assistant 待辦**：
- 等 owner 決策後執行
- 同步補 self-retrospective 報告（5/31 第二份）
- 對齊 cross-file-ssot SOP

---

> **核心精神**：完全整合打通 = 不只各層真活，每層之間連結都要真活。
> 本批揭發核心斷層在 proposal→crystal，這是「真活但不升級」的最大假象。
> 對齊 owner 要的不是表面 metric 漂亮，是**真實循環閉環**。
