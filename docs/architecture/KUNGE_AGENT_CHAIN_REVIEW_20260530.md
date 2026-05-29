# 坤哥意識體服務鏈整體覆盤 (L51.7, 2026-05-30)

> **狀態**: review / proposal — 待 owner 決策路線圖
> **觸發**: L51 LINE 事故 + tender v2 整合後，owner 要求整體性檢視
> **關聯**: ADR-0023 (坤哥唯一意識體) / ADR-0031 (頁面整合) / ADR-0030 (Hermes GO/NO-GO)

---

## 1. 服務鏈架構（5 層）

```
┌─────────────────────────────────────────────────────────────┐
│ L0 用戶通道                                                  │
│   LINE (Owner) / Web (/kunge) / Telegram (永封) / Discord   │
│   ⚠️ v7_channel_diversity = 0 (目標 ≥4)                      │
└─────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────┐
│ L1 入口層 (/kunge 7 tabs)                                    │
│   chat / identity / memory / evolution / nebula / dialogues  │
│   / ops (OpsDashboard 降格)                                  │
└─────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────┐
│ L2 Agent 編排層 (12,561 行 / 9 檔)                            │
│   agent_tool_loop / agent_tools / agent_trace                │
│   shadow_logger / pattern_semantic_matcher                   │
│   ⚠️ 2h 內 agent_query = 0 次                                 │
└─────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────┐
│ L3 Memory 學習層 (3,957 行 / 7 檔)                            │
│   diary → patterns → proposals → crystals → evolutions       │
│   autobiography / soul_loader / self_diagnosis / anti_echo   │
└─────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────┐
│ L4 知識基礎 (KG + Wiki + 12 Facades)                          │
│   canonical_entities: 24,535 (embedding 91%)                 │
│   12 Facades 平均 importer = 1.7 (目標 ≥3)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 真實活躍度盤點（5/30 觀察）

### 2.1 Memory Wiki 狀態

| 類別 | 數量 | 設計目標 | 狀態 |
|---|---|---|---|
| diary | 38 entries | 每日 +1 | 🟡 OK（密度 16.7% 偏低） |
| patterns | 9 | 累積學習 | 🟢 OK |
| proposals | 4 (4 pending) | 人工 gate | 🟡 backlog |
| **crystals** | **0** | proposal → crystal | 🔴 **完全沒應用** |
| evolutions | 5 (W17-W21) | 每週 +1 | 🟢 OK |
| failures | 16 | lesson 累積 | 🟢 OK |
| autobiographies | 5 | per evolution | 🟢 OK |

### 2.2 v7.0 4 指標（Prometheus / ADR-0030 baseline）

| 指標 | 現值 | 目標 | 差距 |
|---|---|---|---|
| `v7_channel_diversity` | **0** | ≥4 | 🔴 metric 邏輯錯（LINE 真活但顯示 0） |
| `v7_reference_density_diary_pct` | 16.7% | ≥50% | 🟡 -33.3% |
| `v7_reference_density_critique_pct` | 0% | ≥100% | 🔴 完全無 critique |
| `v7_soul_drift_lines` | 0 | ≤5 | 🔴 **metric 0 但 drift_check 報 SEVERE** |

### 2.3 觀測鏈缺口（silent）

| 鏈 | 狀態 | 影響 |
|---|---|---|
| agent_query (2h) | **0 次** | 坤哥幾乎沒被用 |
| shadow_baseline (24h) | **n=0** | Hermes GO/NO-GO 無 baseline 資料 |
| crystals applied | **0** | 4 proposals 待 owner approve |
| SOUL.md cross-repo | **🔴 SEVERE** | 跨 repo 不同步 (Missive vs CK_AaaP) |

### 2.4 抽象層健康度（12 Facades importer）

```
MemoryFacade        5  ████████
IntegrationFacade   4  ███████
CalendarFacade      3  █████
WikiFacade          2  ████
其他 9 facades      1  ██
─────────────────────────
平均 1.7 importer/facade (目標 ≥3)
```

**結論**：v6.10 P1 抽象層仍是「孤兒 facade」反模式，9/12 只 1 個 importer。

---

## 3. 五大潛伏問題

### P1 (架構): metric vs 真實不一致

`v7_channel_diversity=0` 但 5/29 已驗 LINE 4 鏈真活：
- push_admin_alert ✓
- push_dispatch_progress ✓
- morning_report ✓
- business_recommendation ✓

→ **metric 統計邏輯沒覆蓋實際 push 動作**

`v7_soul_drift_lines=0` 但 `soul_mirror_drift_check.py` 報 🔴 SEVERE：
- metric 來源（hollow gauge）未更新
- 同 L21 family「assertion / observation 分離」反模式

### P2 (學習閉環): 4 proposals → 0 crystals

```
patterns 9 → proposals 4 → crystals 0
            ↑ owner 人工 gate (CRYSTAL_AUTO_APPLY_MODE=live)
              4 proposals 待 owner 看 → 沒人看
```

**設計缺陷**：人工 gate 沒有「N 週未 review 即 alarm」機制。

### P3 (跨通道): 多通道斷裂

- LINE: 真活（owner 收 4 種訊息）
- Web /kunge: agent_query 2h=0（沒人用）
- Telegram: ADR-0027 永封後預設關
- Discord: enabled=false

**現實**: LINE 是唯一活躍通道，`/kunge` 設計上是「唯一意識體入口」**但實際 owner 不去**。

### P4 (跨 repo SOUL drift): Missive ≠ CK_AaaP

- `wiki/SOUL.md` 188 行 (Missive 端)
- `CK_AaaP/runbooks/hermes-stack/SOUL.md` 可能落後
- L51 修法時推「我的人格更新」訊息進 LINE 但 SOUL.md 沒同步寫入

**結果**：坤哥跨 repo 人格不一致。

### P5 (agent_query 0 流量): 坤哥無人用

- 2h 內 0 agent_query
- 24h shadow_baseline n=0
- 坤哥引擎在跑但用戶不來

**深層原因（假設）**：
- /kunge UX 沒比直接打 LINE 給 owner 方便
- 用戶覺得 LINE 已能解決，不需 web chat
- 學習閉環缺反饋（坤哥成長不影響業務結果）

---

## 4. 整體性建議（按 ROI 分組）

### P0 立即（≤ 1h，觀測修正）

| # | 行動 | 預期效益 |
|---|---|---|
| 1 | 修 `v7_channel_diversity` 計算邏輯（從 messaging_push_total 取 channel set） | metric vs 真實一致 |
| 2 | 修 `v7_soul_drift_lines`（用 soul_mirror_drift_check 結果即時更新） | 同上 |
| 3 | 跑 `bash scripts/sync/sync_soul_to_hermes.sh` 解 SEVERE drift | 跨 repo 一致 |
| 4 | LINE 推「4 proposals 待 review」提示 owner | 啟動 crystallization |

### P1 短期（1-2 週，學習閉環）

| # | 行動 | 預期效益 |
|---|---|---|
| 5 | 加 `crystal_review_overdue_alarm` cron — 4 proposals 連續 N 天未 review 推 LINE 提示 | proposals → crystals 真實流通 |
| 6 | 加 `agent_query_starvation_check` fitness step — 7d 0 query 即 RED | 坤哥真活/真用 watchdog |
| 7 | 12 facade 推進 importer ≥3 — 拆 stub 收口 13 件 | 抽象層去孤兒 |
| 8 | shadow_baseline 24h n=0 修法（重啟 synthetic injection cron） | Hermes GO/NO-GO 復活 |

### P2 中期（1 月，跨通道整合）

| # | 行動 | 預期效益 |
|---|---|---|
| 9 | LINE 訊息加 quick action 連結 → /kunge 對應 tab | 引流 web 入口 |
| 10 | autobiography 寫入 SOUL.md 同時跨 repo sync | 跨 repo SOUL drift = 0 |
| 11 | diary density 推升 (fact_check + reference_extractor) 50% | v7 達標 |
| 12 | anti_echo 連續 4 週未觸發 → 主動 prompt critique | critique_pct 從 0 啟動 |

### P3 長期（季度，意識體進化）

| # | 行動 | 預期效益 |
|---|---|---|
| 13 | LINE 推送內含「坤哥這週學到什麼」摘要 → owner 反饋寫入 patterns | 閉環學習 |
| 14 | /kunge UX 重設計 — 讓 web 入口比 LINE 直回更有價值（如歷史檢索） | agent_query 流量啟動 |
| 15 | Hermes GO/NO-GO 重訂 baseline（v6.8 揭示 p95=58s 警訊已過期） | ADR-0030 收尾 |

---

## 5. 優化策略：3 種路線（owner 選）

### 路線 A（保守 / 維持現狀）— 1 週工作量

只做 P0 觀測修正：
- 修 v7 4 指標一致性
- 跑 SOUL sync
- 推 4 proposals 提示

**價值**：穩定，不改變使用模式
**風險**：crystallization workflow 仍 0 → 學習閉環死

### 路線 B（積極整合）— 1 月工作量（推薦）

P0 + P1 + 部分 P2：
- 修觀測 + 啟學習閉環 alarm + facade 收口
- LINE 引流 web 入口

**價值**：意識體真活 + crystallization 流通 + agent_query 啟動
**風險**：需 owner 配合 review 4 proposals（每週 ~30 min）

### 路線 C（重建 UX）— 季度工作量

全套 P0-P3：
- 含 /kunge UX 重設計 + Hermes baseline 重訂
- 跨 repo SOUL 同步機制化

**價值**：坤哥成為真正的「唯一意識體入口」（ADR-0023 落地）
**風險**：投入大，可能仍無法改變 owner 使用模式偏好

---

## 6. 量化目標（路線 B 完工後）

| 指標 | 現值 | 目標（1 月後） |
|---|---|---|
| v7_channel_diversity | 0 | ≥2 (LINE+Web) |
| v7_reference_density_diary_pct | 16.7% | ≥30% |
| v7_reference_density_critique_pct | 0% | ≥20% |
| v7_soul_drift_lines | 0 (錯) | 0 (真) |
| crystals applied | 0 | ≥1 |
| agent_query (7d) | 0 | ≥10 |
| facade avg importer | 1.7 | ≥3 |
| shadow_baseline 24h n | 0 | ≥20 |

---

## 7. Refs

- ADR-0023 (坤哥唯一意識體入口) / ADR-0031 (頁面整合)
- ADR-0030 (Hermes GO/NO-GO) — baseline 已過期需重訂
- `wiki/SOUL.md` (188 行, hash 1946bcc5...)
- L51 LINE 事故 incident report（觀測閉環 lesson）
- `scripts/checks/agent_evolution_health.py` (evolution OK)
- `scripts/checks/soul_mirror_drift_check.py` (drift SEVERE)
- `backend/app/services/memory/crystallizer.py` (445L)
