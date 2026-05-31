---
title: L63 — 學習閉環需 aging alert 才能突破 owner 健忘
type: lesson
scope: universal
category: learning-loop
created: 2026-05-31
trigger_event: 5/31 self-retro RED — 學習閉環 flow=0% / crystals=0 / 5 proposal pending 40 天
related: [[L62_integration_continuous_validation_not_one_shot]], [[L53_facade_over_engineering_30day_pruning]]
tags: [learning-loop, proposal, crystallization, aging, owner-friction, anti-silent-dormant]
---

# L63 — 學習閉環需 aging alert 才能突破 owner 健忘

## 觸發事件

Owner 5/31 訴求「學習閉環 + 日誌 + 坤哥真活」反饋核心議題。

真實狀態揭發:
- 5 個 proposal pending（2 LOW intent + 3 MEDIUM soul）
- 最老的 pending 40 天
- crystals_applied = 0
- pipeline_red_consecutive_days = 11 主因之一

**自動化做到** trace → pattern → proposal ✅
**斷層真因** proposal → crystal **依賴 owner approve** (owner 健忘 / 決策成本高)

## Lesson 本體

### 學習閉環架構

```
auto: trace → pattern_extractor (cron 04:00)
auto: pattern → crystallizer (cron 04:30)
auto: proposal → wiki/memory/proposals/
🛑 manual: owner approve → crystal_applier (require_admin)
auto: crystal → wiki/SOUL.md / intent_rules.yaml 真實 apply
```

斷在 🛑 — 自動化能做到 proposal 寫好，但 apply 是 hard gate。

### 為何不能 auto-apply

- crystal-intent: 改 intent_rules.yaml routing rule (低風險但 affect 全 agent flow)
- crystal-soul: 改 SOUL.md 人格信念 (中風險 affect agent 自我認知)
- 都是不可逆 (需 git revert)
- 對齊 owner「備份安全為主要考量」訴求

### 為何 owner 會忘記

- proposal 寫在 wiki/memory/proposals/ (檔案系統)
- owner 平時看 LINE / web UI，不會主動 grep wiki
- self-retro 顯示「proposals_pending: 4」是數字，不含內容
- **靜態檔案 + 無主動推 = silent dormant (與 critique 同型)**

### 修法 — 主動 aging alert

#### 5 元素 owner-friendly LINE 推送

1. **風險分級**：LOW / MEDIUM / UNKNOWN（先列低風險，最易決策）
2. **age 天數**：直觀看「卡多久」
3. **target file**：知道會改哪
4. **完整 reason**：知道為什麼建議
5. **approve SOP**：1-click curl 指令 + web 路徑

#### Cron 排程

每週日 02:20（避用戶時段 + misfire_grace 7200）

#### 觸發條件

`age >= 7 days` 才推 (避新生 proposal noise)

### 突破性 vs 一次性對照

| 反模式 (一次性) | 正模式 (突破性) |
|---|---|
| 寫 self-retro 數字 proposals_pending: 4 | 主動列名 + age + reason 推 owner |
| 等 owner 主動查 | 每週推 + 1-click curl |
| 無 aging filter (新舊混雜) | aging > 7d 才推 (signal/noise) |
| 純檔案 silent | LINE + cron + jsonl 三層 |

## 衍生規範

### 「決策依賴 owner」場景三件套（強制）

任何「auto-process 終止於 owner approve」的閉環必走:

1. **產出時**: 寫檔案 / 入 DB（自動）
2. **aging 監督**: cron 每 N 日掃 pending，age > threshold 主動推
3. **完成度監控**: fitness step 統計 pending / approved 比率，趨勢異常 → RED

## ROI 評估

- **避免**: 「自動學會但 owner 忘記 approve」silent dormant（過去 40+ 天）
- **效益**: owner 決策成本降低 90%（風險分級 + 1-click + LINE 推送）
- **成本**: 每週 1 次 cron + ~1KB LINE 訊息

## 對齊 owner 哲學

### 真活大於規劃
- 不只規劃 crystallizer，建 aging alert 真活
- 不只 dashboard 數字，**列名主動推送**

### 整合連通 / 突破性 / 非一次性
- 從靜態檔案 → 動態週期推送
- 從 owner 主動查 → 主動推 owner

### 日誌+周報=靈魂
- 周報（autobiography）真實揭發學習量
- aging alert 真實揭發「學了沒結晶」斷層

### 備份安全
- 不繞 owner approve（純揭發）
- 對齊 crystal_applier 7 step SOP

## 跨 repo 適用

任何「owner approval 是 hard gate」的場景:
- CK_lvrland / CK_PileMgmt（業務審批）
- CK_AaaP（治理決策）
- 任何 ADR proposed → accepted 流程

## 歷史軌跡

| 版本 | 動作 | 學習閉環健康 |
|---|---|---|
| v6.6 (2026-05) | crystal_applier code 完成 | proposal accumulate but 0 apply |
| v6.7 (2026-05) | wiki/proposals/ 累積 | 仍 0 apply (silent) |
| v6.12 (2026-05-30) | crystal_review_overdue_alarm 每週日 09:30 | 簡單數字 alert |
| **v6.13 (2026-05-31)** | **proposal_aging_alert 完整推送（本批）** | **expected: crystals > 0 within 1 week** |

---

> **核心精神**：學習閉環不能依賴 owner 健忘。
> 主動推送 = 揭發即動作 = silent dormant 防範。
> 對齊 owner「真活大於規劃」+「整合連通真活」+「日誌+周報=靈魂」哲學。
