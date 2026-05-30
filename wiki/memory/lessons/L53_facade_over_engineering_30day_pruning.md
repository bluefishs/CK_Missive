---
title: L53 — Facade over-engineering 30 天實證裁判 (ADR-0036 ROI 失敗 → B 方案收口)
type: lesson
date: 2026-05-30
fqid: CK_Missive#L53
family: over-engineering
related: [L31, feedback_stop_overengineering]
---

# L53 — Facade over-engineering 30 天實證裁判

> **日期**：2026-05-30
> **觸發**：v6.12 fitness step 61 facade_adoption_audit 揭發 10/13 zero caller
> **規模**：-1509 lines / -10 facade / -2 port / -2 adapter / -1 test
> **owner 圈選**：B 方案（補強 active + 廢 zero）

---

## ADR-0036 設想 vs 30 天實測

| 項目 | v6.10 P1 設想 | 30 天實測 |
|---|---|---|
| facade 數 | 13 個 bounded context | 13 建成 |
| caller 數 | 平均 ≥ 3/facade | 平均 0.46 (zero 主導) |
| ROI | entities × usage_rate | 13 × 0.46 = 6 |
| 維護成本 | 13 facade 邊際成本 | 高（每個都要同步 port/adapter）|

收口後：
| 項目 | 數據 |
|---|---|
| facade 數 | 3 active |
| caller 數 | 平均 2.00 |
| ROI | 3 × 2.00 = 6 (相同) |
| 維護成本 | 大降 (-77% entities) |

**核心洞察**：同 ROI 但 entities 減 77% → 維護負擔大降，dormant 風險也大降。

---

## L31 原則驗證

L31 原則：**ROI = entities × usage_rate**

L53 = L31 第一個正面執行案例：
- 建 N 個但只有 M (M<<N) 個被用 → 廢 N-M 個保留 M 個
- 留下的 entity 補強到 usage_rate↑ → ROI 不變但成本大降

---

## 為何 30 天才能裁判？

v6.10 P1 上線時無法判斷哪個 facade 會被用 — owner 質疑無法回答前置條件。
30 天 audit metric 化才能客觀裁判（fitness step 61 facade_adoption_audit）。

對應「治理本身 metric 化」原則 (v6.12 進化 #3)：
- 連 ADR 設計失誤也能 metric 出來
- audit 自身就是 self-correcting 機制
- 不需 owner 主動覆盤 — 自動暴露

---

## 60 天 trial 設計（escape hatch）

留 3 個 active facade trial 2026-07-30 重評：
- IntegrationFacade 目標 ≥5 caller (現 3)
- MemoryFacade     目標 ≥5 caller (現 3)
- WikiFacade       目標 ≥3 caller (現 1)

任一未達 → 升 C 全廢，回 service 直 import。

**設計理由**：
- B 方案 reversible — 60 天可撤回
- 不過早 commit 「facade 是對的」
- 給 entity 自證 usage rate 的機會

---

## 修法資產

| 檔案 | 行為 | commit |
|---|---|---|
| 10 facade .py | DELETE | `d0d24639` |
| 2 port .py (audit/cache) | DELETE | 同上 |
| 2 default adapter .py | DELETE | 同上 |
| 1 test_tender_facade.py | DELETE | 同上 |
| facades/__init__.py | export 3 active | 同上 |
| contracts/__init__.py | export 2 active port | 同上 |
| facade_adoption_audit.py | FACADES list 縮 3 | 同上 |
| ADR-0036 | status superseded by L53 | （本批配套）|
| FACADE_ABC_DECISION_20260530.md | 評估文件 | `0851bf64` |

---

## 元洞察

**Owner 質疑為何 ADR 反覆但仍重複錯誤** — 答案：

ADR 預測 + audit 30 天實證 = 治理自我進化閉環。

ADR-0036 不算「錯誤」— 算「假設待驗證」。30 天 audit + 60 天 trial 給足空間裁判。
L31 + L53 = 第一個 entity 設計 + audit 裁判 + 廢棄收斂的完整循環範例。

未來新 facade / 抽象層應該：
1. 上線前估 entities × usage_rate ROI
2. 30 天後 audit 真實 usage_rate
3. 60 天後執行裁判（保留 / 升級 / 廢棄）
4. 寫 lesson 入 LESSONS_REGISTRY

---

> **核心精神**：建抽象不是錯，建後不 audit 才是。
> ADR 是假設，audit 是裁判，lesson 是傳承。
