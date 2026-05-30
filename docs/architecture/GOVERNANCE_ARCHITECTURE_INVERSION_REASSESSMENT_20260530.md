# 治理架構倒置 — Owner 揭發 meta-governance index 機制缺口

> **Owner 觸發**：CK_AaaP 名義是 meta-governance index（治理標準上游），但實際治理機制成熟度落後於它索引的 source repo（CK_Missive）
> **嚴重程度**：架構級反思 — 治理上下游倒置 9 天 dormant 揭發
> **L58 + L59 連動**：L58 揭發「過度套用是污染」/ L59 揭發「上游缺機制 = 倒置」

---

## 1. 真實揭發 — 6 repo 三件套盤點

| Repo | ADR | Registry | Audit script | 角色 |
|---|---|---|---|---|
| **CK_AaaP**（meta 上游）| **37** | **CONVENTIONS.md ✓** | **❌ 無 scripts/checks/** | 缺裁判 |
| CK_Missive（業務 source）| 23 | ❌ 無 | 88 py | 過度 audit |
| CK_lvrland_Webmap | 4 | ❌ | 19 (install-template 來) | 被治理 |
| CK_PileMgmt | 9 | ❌ | 1 | 部分 |
| CK_Showcase | 無目錄 | ❌ | 19 (install-template) | 被動 |
| CK_KMapAdvisor | 無目錄 | ❌ | 19 (install-template) | 被動 |

### 倒置真實

- **CK_AaaP**：定 standard（ADR + Registry ✓）但**不檢查**（無 audit）
- **CK_Missive**：寫業務（ADR + Audit）但**沒索引** Registry
- **子專案**：被 CK_Missive audit（step 65/66）但 CK_AaaP 不在其中

**該是的方向**：
```
CK_AaaP (定 standard + audit) → CK_Missive + lvrland + ...
```

**實際方向**：
```
CK_AaaP (定 standard 不 audit) ← CK_Missive (反向 audit 4 子專案)
```

---

## 2. 為何 dormant 9+ 天

CK_AaaP 是 meta-governance index 但：
1. **無 scripts/checks/ 目錄** → 沒寫 audit 機制
2. **不在 cross_repo_template_drift_audit 對象** → 沒被檢查
3. **CK_Missive 反向 audit 子專案** → 倒置變慣性

**Silent 鏈**：
- CK_AaaP 寫 ADR 但無 audit 自驗
- CK_Missive 寫 audit 但沒被 CK_AaaP 反向驗
- 子專案被 CK_Missive 抓但 CK_AaaP 沒參與

---

## 3. ADR + Registry + Audit「三件套」正確架構

### 3.1 應該的上下游

```
┌────────────────────────────────────────────┐
│ CK_AaaP — Meta-Governance Source of Truth │
│  ✓ ADR registry (37 cross-repo ADR)       │
│  ✓ CONVENTIONS.md SOP                      │
│  ❌ scripts/checks/ ← 本批揭發缺口          │
│       → 應有 audit-cross-repo-triplet.sh   │
│       → 應有 audit-doc-drift.sh (已有)     │
└────────────────────────────────────────────┘
              ↓ 統一治理
┌────────────────────────────────────────────┐
│ CK_Missive / lvrland / Pile / Showcase /  │
│ KMap (含 CK_Missive 在內)                  │
│  - 各自 ADR + audit + 業務                │
│  - 接受 CK_AaaP audit (反向被檢查)        │
└────────────────────────────────────────────┘
```

### 3.2 CK_AaaP 應有的 audit 機制

| Audit | 用途 | 對象 |
|---|---|---|
| `audit-cross-repo-triplet.sh` | 各 repo ADR + Registry + Audit 三件套狀態 | **6 repo 含 CK_Missive** |
| `audit-cross-repo-adr-alignment.sh` | 各 repo ADR 編號 vs Registry 對齊 | 同上 |
| `audit-cross-repo-fitness-coverage.sh` | 各 repo audit script 覆蓋 universal/recommended/specific 比例 | 同上 |

---

## 4. 兩重反思（L58 + L59）

### L58 已立法（範本污染）

> 範本是參考，不是強制，過度套用就是污染

CK_Missive 強推 132 檔到 4 子專案 = **下游污染**。

### L59 立法（架構倒置）

> 上游缺 audit = 治理倒置，下游反向 audit 是症狀

CK_AaaP 缺 audit → CK_Missive 反向變 audit source → 子專案被反向治理。

**兩條一起看**：

| Lesson | 視角 | 修法 |
|---|---|---|
| L58 | 下游：過度套用 | 範本分級 (L1/L2/L3) |
| L59 | 上游：缺 audit | CK_AaaP 加 audit + 自我被治理 |

合起來 = **治理架構正常化**。

---

## 5. 修法策略 — 3 階段

### Phase 1（本批，CK_Missive 內可做）

- ✅ 寫此 reassessment
- ✅ 寫 L59 lesson
- ✅ 寫 audit script design (給 owner 看)
  - 推薦放 `CK_AaaP/scripts/audit-cross-repo-triplet.sh` (待 owner approve commit 到 CK_AaaP)

### Phase 2（owner approve 後，CK_AaaP 內動工）

- 在 `CK_AaaP/scripts/` 加 audit-cross-repo-triplet.sh
- 把 CK_Missive 加進 audit 對象 (與 4 子專案同等)
- CK_AaaP 自己也加 `scripts/checks/` 目錄收口

### Phase 3（架構長期）

- CK_Missive 移除 `cross_repo_template_drift_audit` （職責回 CK_AaaP）
- CK_Missive 改為被 audit 的對象
- CK_AaaP 成為真實 meta-governance index

---

## 6. 待寫的 audit script (草稿)

```bash
#!/bin/bash
# CK_AaaP/scripts/audit-cross-repo-triplet.sh
# v1.0 — 2026-05-30 (待 owner approve 移至 CK_AaaP)
#
# 反向 audit：CK_AaaP 檢視所有 6 個 source repo 是否有三件套

set -uo pipefail

REPOS=("CK_Missive" "CK_lvrland_Webmap" "CK_PileMgmt" "CK_Showcase" "CK_KMapAdvisor")
PROJ_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

for repo in "${REPOS[@]}"; do
  echo "── $repo ──"
  R="$PROJ_ROOT/$repo"
  if [ ! -d "$R" ]; then
    echo "  ⚪ repo 不存在"
    continue
  fi

  # ADR
  adr_count=$(ls "$R"/docs/adr/*.md 2>/dev/null | wc -l)
  if [ "$adr_count" -lt 5 ]; then
    echo "  ❌ ADR=$adr_count (< 5, 應 ≥10)"
  else
    echo "  ✓ ADR=$adr_count"
  fi

  # Registry pointer
  if grep -qE "(CK_AaaP|CONVENTIONS.md|ADR Registry)" "$R/CLAUDE.md" 2>/dev/null; then
    echo "  ✓ Registry pointer 在 CLAUDE.md"
  else
    echo "  ❌ Registry pointer 缺 (應引用 CK_AaaP/CONVENTIONS.md)"
  fi

  # Audit fitness
  fitness_count=$(ls "$R"/scripts/checks/*.py 2>/dev/null | wc -l)
  if [ "$fitness_count" -lt 3 ]; then
    echo "  ❌ Fitness audit=$fitness_count (< 3, 應 ≥3)"
  else
    echo "  ✓ Fitness audit=$fitness_count"
  fi
done
```

---

## 7. Owner 必要決策

- A. **執行**：在 CK_AaaP 加 audit script + 把 CK_Missive 移除 cross_repo_drift_audit
- B. **保留**：CK_Missive 仍 audit 子專案 + CK_AaaP 補 audit （並行雙路）
- C. **延後**：本批僅 reassessment 等下批決策
- D. **其他指示**

推薦 **A** — 真正治理上下游正常化。

---

## 8. 元洞察 — 連 2 天 2 個深刻反思

| 日期 | 反思 | 教訓 |
|---|---|---|
| 5/30 13:00 | 為何規範散落 5 處 | L58 整合 SSOT 是責任 |
| 5/30 22:00 | 治理範本是污染源 | L58 範本是參考不是強制 |
| 5/30 22:30 | 治理架構倒置 | **L59 上游缺機制 = 倒置** |

3 個反思**同一天**，深度遞增。
對應 v6.12 治理進化從「執行」→「整合」→「分級」→「**上下游正常化**」4 層遞進。

---

## 9. 對齊 5+1 句立法 + L59

> 1. 抽象不是錯，建後不 audit 才是
> 2. 觀測不是奢侈，自治理就是
> 3. 規範散落是必然，整合 SSOT 是責任
> 4. 修法不可逆，60 天 trial 是保險
> 5. 執行了不算落實，commit + push 才算
> 6. 範本是參考，不是強制，過度套用就是污染（L58）
> 7. **上游缺機制 = 治理倒置，下游反向 audit 是症狀**（L59 新立法）

---

> **核心精神**：Meta-governance 上游必須有 audit 機制。沒有的話下游反向治理就是症狀。
> Owner 連 2 天連續揭發 2 個深刻反思 — 治理進化真實循環的最高表現。
