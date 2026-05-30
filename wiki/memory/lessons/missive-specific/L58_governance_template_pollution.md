---
title: L58 — 治理範本污染風險（meta-治理層 / L4x family 第十案 反向教訓）
type: lesson
date: 2026-05-30
fqid: CK_Missive#L58
family: meta-governance
related: [L31, L53, L54, L57]
---

# L58 — 治理範本污染風險

> **日期**：2026-05-30
> **觸發**：Owner 反思「CK_Missive 平台治理範本變成其他專案汙染源」
> **嚴重程度**：本日最深刻 lesson — 揭發治理本身的過度設計

---

## 真因

前批 install-template-to.sh 對 4 子專案套用 132 檔，認為「對外採用率 0% → 100%」是成功。

但 owner 反思：
- 132 檔中只有 **33% 真普適**（L1: paths/container/SSOT audit）
- 約 **57% 是 CK_Missive 特定**（L3: Facade B / Hermes baseline / daily_self_retrospective）
- 強推 L3 = 治理污染（語意污染 + 規範污染 + 觀測污染）

### 3 大污染徵兆

1. **語意污染**：子專案 lesson dir 出現「Facade B 方案 13→3」← 子專案不知 Facade 是啥
2. **規範污染**：子專案被迫遵守 v6.12 「修 PROJECT_ROOT 必同步 compose mount」（即使他們沒用 PROJECT_ROOT 抽象）
3. **觀測污染**：governance_lessons_l4x_family_count metric 對子專案無意義

---

## 我的盲點（meta 反思）

| 盲點 | 對齊 lesson | 修正 |
|---|---|---|
| 把採用率當成功 | L31 ROI = entities × usage_rate | 應加 `correctness_rate` |
| 未分級範本通用性 | L53 facade over-engineering | 範本也適用「30 天 trial 裁判」 |
| 強加 = 污染 | L54 套用 ≠ 落實 | L54 + L58 = 「套用 ≠ 落實 ≠ 適用」 |
| 治理過度 ≠ 治理良好 | （NEW）| 加 6 句立法 |

---

## L4x family 反向延伸（meta 層）

L41-L57 都是「跨檔 SSOT silent fail」事故教訓。
L58 是**反向**：「治理過度 = 治理污染」。

對應到：
- L31 ROI 公式延伸：`真實 ROI = entities × usage_rate × correctness_rate`
- L53 30 天裁判 SOP 適用範圍延伸：不只 ADR，也適用範本
- L54 雙層 audit 延伸：套用 + commit + **適用性**三層
- L57 sub-path SSOT 延伸：規範本身也有「適用性 SSOT」

---

## 新策略 — 範本 3 分級

| 層 | 性質 | 範例 | 對外推薦 |
|---|---|---|---|
| **L1 普適** | Docker/Python/Git 通用 | paths_compose_mount_audit | ✅ 全推 |
| **L2 推薦** | 中型 repo | run_fitness_daily.sh | 🟡 opt-in |
| **L3 特定** | CK_Missive 文化 | daily_self_retrospective | ❌ 不推 |

### install-template 升級

```bash
--tier=universal      # L1 only
--tier=recommended    # L1+L2
--tier=full           # L1+L2+L3 (僅 monorepo / opt-in)
```

### 子專案 opt-out

`.template-policy.yml` 機制：
```yaml
template_tier_accepted:
  - universal
template_excluded:
  - daily_self_retrospective.py
  - L53_facade_*.md
```

---

## 立法 — v6.12 第 6 句精神

> 1. 抽象不是錯，建後不 audit 才是
> 2. 觀測不是奢侈，自治理就是
> 3. 規範散落是必然，整合 SSOT 是責任
> 4. 修法不可逆，60 天 trial 是保險
> 5. 執行了不算落實，commit + push 才算
> 6. **範本是參考，不是強制，過度套用就是污染** ← L58 立法

---

## 元洞察 — owner 反思的真實價值

Owner 質疑「治理是否過度」遠比「執行治理」更深刻。

對齊 L53 + L54：
- L53：抽象不能建後不 audit
- L54：套用不算落實
- **L58：落實不算適用**

3 層遞進 = 治理進化的真實循環。

---

## 修法資產

| 檔案 | 行為 | commit |
|---|---|---|
| `docs/architecture/GOVERNANCE_TEMPLATE_POLLUTION_REASSESSMENT_20260530.md` | 評估報告 | （本批）|
| `wiki/memory/lessons/L58_*.md` | NEW lesson | （本批）|
| `scripts/install-template-to.sh` | 待升級 `--tier` flag | 下批 |
| `.template-policy.yml` | 待建機制 | 下批 |
| `cross_repo_template_drift_audit.py` | 待加 L1/L2/L3 維度 | 下批 |

---

## Owner 必要決策

- A. 立即回滾 4 子專案 L3 範本（~12 檔/repo PR）
- B. 分級升級保留現狀
- C. 維持現狀（風險可接受）
- D. 其他指示

---

> **核心精神**：治理範本是參考座標，不是強制中央。
> Owner 揭發「治理污染」= 治理進化最深刻的循環。
> 對應 L31 ROI 公式延伸 + L53/L54/L58 三層遞進。
