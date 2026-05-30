---
title: L59 — 治理架構倒置（CK_AaaP 缺 audit / CK_Missive 反向 audit 子專案）
type: lesson
date: 2026-05-30
fqid: CK_Missive#L59
family: meta-governance
related: [L58]
---

# L59 — 治理架構倒置

> **日期**：2026-05-30（與 L58 同一天揭發）
> **觸發**：Owner「CK_AaaP 名義是 meta-governance index 但實際治理機制成熟度落後於它索引的 source repo（CK_Missive）」

---

## 真因

| Repo | ADR | Registry | Audit | 角色 vs 實際 |
|---|---|---|---|---|
| CK_AaaP（meta 上游）| 37 | CONVENTIONS.md ✓ | **❌ 無 scripts/checks** | 應是裁判但只定 standard |
| CK_Missive（業務 source）| 23 | 無 | 88 audit | 應被治理但反而 audit 子專案 |
| 子專案 4 個 | 4-9 | 無 | 1-19 | 被 CK_Missive 治理但 CK_AaaP 缺席 |

「該是的方向」：CK_AaaP → 各 repo（含 CK_Missive）
「實際方向」：CK_Missive → 4 子專案（反向）

---

## 與 L58 互補

| Lesson | 視角 | 修法 |
|---|---|---|
| L58 | 下游：過度套用 | 範本分級 L1/L2/L3 |
| **L59** | **上游：缺 audit** | **CK_AaaP 加 audit + 自我被治理** |

合起來 = 治理架構正常化。

---

## v6.12 第 7 句立法

> 上游缺機制 = 治理倒置，下游反向 audit 是症狀

---

## 平衡策略（owner 追問）

對應「如何取得平衡」：

| 維度 | 不平衡（極端）| 平衡點 |
|---|---|---|
| 上游 vs 下游 | CK_Missive 變源頭 | CK_AaaP 補 audit 收回主導 |
| 範本通用性 | 132 檔強推 4 子專案 | 分級 L1 全推 / L3 僅參考 |
| 治理執行者 | 單方 audit 對外 | 自我也接受被 audit |
| 規範密度 | 過度規範限制演進 | universal/recommended/specific 三層 |

---

> **核心精神**：Meta-governance 必須先治自己，再治下游。
> Owner 兩日連續揭發 L58 + L59 = 治理進化真實循環。
