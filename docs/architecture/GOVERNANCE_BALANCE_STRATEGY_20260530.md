# 治理平衡策略 — Owner 追問「如何取得平衡與建議」

> **觸發**：Owner 連 2 天揭發 L58 範本污染 + L59 架構倒置 後追問
> **核心**：在「過度治理」（L58）vs「治理倒置」（L59）之間找平衡
> **答案**：4 軸 × 3 層 × 5 原則 = 治理平衡公式

---

## 1. 不平衡的兩個極端

| 極端 | 症狀 | Lesson |
|---|---|---|
| **過度治理** | CK_Missive 強推 132 檔到 4 子專案 | L58 |
| **治理倒置** | CK_AaaP 缺 audit / CK_Missive 反向 audit | L59 |

兩極都是失衡 — 平衡點不在中間，而在**結構正常化**。

---

## 2. 4 軸平衡公式

### 軸 1 — 上下游分離

| 角色 | 職責 | 不能做 |
|---|---|---|
| **CK_AaaP（上游）** | 定 standard + audit 下游 + 自我被檢 | 不寫業務 |
| **CK_Missive（業務）** | 遵守 standard + 業務迭代 + 接受被 audit | 不定 standard |
| **子專案** | 遵守 universal standard + 業務迭代 | 不寫 L3 specific |

平衡：CK_AaaP 主導 + CK_Missive 服從 + 子專案最小負擔。

### 軸 2 — 範本通用性分級

| 層 | 適用 | 強制度 | 範例 |
|---|---|---|---|
| L1 普適（33%）| 全 CK 系列 | ✅ 強制 | paths/container/SSOT |
| L2 推薦（10%）| 中型 repo | 🟡 opt-in | fitness daily |
| L3 特定（57%）| 僅 CK_Missive | ❌ 不外推 | Facade B / Hermes baseline |

平衡：L1 強推 + L2 自選 + L3 留本 repo（**對齊 L58**）。

### 軸 3 — Audit 流向

| 流向 | 對象 | 機制 |
|---|---|---|
| **上→下** | CK_AaaP audit 5 repo（含 CK_Missive）| `audit-cross-repo-triplet.sh` |
| **內部** | 每 repo 自己 audit 內部 | `run_fitness_daily.sh` |
| **下→上** | 子專案回報問題給上游 | GitHub issue + consumers.yml |

平衡：上下雙向 + 內部完整（**對齊 L59**）。

### 軸 4 — 規範密度

| 密度 | 適用 | 例 |
|---|---|---|
| 高（每事必規範）| 業務核心 / 安全 / 合規 | RLS / SSO |
| 中（治理層）| Docker / SSOT / 部署 | cross-file-ssot |
| 低（最小負擔）| 業務細節 / 風格 | （讓 owner 自決）|

平衡：高密度規範僅在 critical 層，業務層留自由（**對齊 L58 第 6 句**）。

---

## 3. 3 層治理金字塔（新架構）

```
┌──────────────────────────────────────────┐
│ Tier 1: CK_AaaP META-GOVERNANCE          │
│  - CONVENTIONS.md (跨 repo SOP)          │
│  - REGISTRY.md (跨 repo ADR index)       │
│  - audit-cross-repo-triplet.sh ★ NEW    │
│  - audit-doc-drift.sh (既有)             │
│  - 自我被 audit (CK_AaaP 也在對象內)     │
└──────────────────────────────────────────┘
              ↓ 統一 audit
┌──────────────────────────────────────────┐
│ Tier 2: SERVICE REPO LAYER               │
│  CK_Missive / lvrland / Pile / Show /    │
│  KMap (含 CK_Missive 平等被治理)         │
│  - 各自 ADR + audit + 業務               │
│  - 接 CK_AaaP universal standard         │
│  - 自由發展 L3 specific (不外推)         │
└──────────────────────────────────────────┘
              ↓ 業務反饋
┌──────────────────────────────────────────┐
│ Tier 3: BUSINESS EVOLUTION                │
│  - 業務迭代 (功能)                       │
│  - L3 specific lesson (本 repo 留存)     │
│  - 提案回 CK_AaaP (升 L1/L2)             │
└──────────────────────────────────────────┘
```

---

## 4. 5 原則 — 平衡守則

### 原則 1：上游必先自治

CK_AaaP 必須先有 audit 機制 + 接受自我被 audit，才有資格 audit 下游。

### 原則 2：範本分級不外推 L3

L3 specific（57%）留本 repo，不強推。即使其他 repo 想用也是 opt-in。

### 原則 3：audit 多源不互排

CK_AaaP 跨 repo audit + 各 repo 內部 audit 同時並行。互補而非取代。

### 原則 4：演進上送，不下推

新規範由 service repo 提案 → CK_AaaP 評估 → 升 L1 後下推。
**不是** CK_AaaP 單方產出全套 + 強推。

### 原則 5：30/60 天 trial 適用所有層

新規範上線後 30 天 audit 真實採用率，60 天決定保留/廢棄/升級。
對應 L31 ROI + L53 30 天裁判 SOP。

---

## 5. 具體實施建議（owner 必要決策）

### Phase 1（CK_Missive 內可立即做）

1. ✅ 寫 L58 + L59 + reassessment + balance strategy（本批）
2. 推 LINE 整理結論給 owner 決策
3. 待 owner approve 後執行 Phase 2

### Phase 2（CK_Missive 需 owner approve）

1. 升級 `install-template-to.sh` 加 `--tier` flag
2. 加 `.template-policy.yml` opt-out 機制
3. 移除 CK_Missive 的 `cross_repo_template_drift_audit`（職責回 CK_AaaP）
4. lesson 分流（universal/missive-specific 目錄）

### Phase 3（CK_AaaP 需 owner approve）

1. 加 `CK_AaaP/scripts/` 目錄
2. 寫 `audit-cross-repo-triplet.sh`（含 CK_Missive 在 audit 對象內）
3. CK_AaaP 自身加 `scripts/checks/` 接受被 audit
4. 升級 CONVENTIONS.md 加 L1/L2/L3 分級規範

### Phase 4（子專案 owner 知會）

1. 給 4 子專案 owner 發 PR「建議移除 L3 範本」
2. 加 universal standard 入各 repo 的 CLAUDE.md pointer

---

## 6. 風險控管

| 風險 | 緩解 |
|---|---|
| 短期：4 子專案 L3 內容已套用 | 提供分級指南讓子專案 owner 自由刪 |
| 中期：CK_AaaP 加 audit 增工作量 | 從 CK_Missive 已有 audit 移植即可 |
| 長期：CK_Missive 失去「source of truth」地位 | 改稱「reference implementation」（範例專案） |
| 哲學：治理永遠不會 100% 平衡 | 接受動態調整，每 30 天重評 |

---

## 7. 元洞察 — 平衡不是中間，是結構正常化

「中間值」式平衡 = 60% audit + 40% 自由 → 仍會傾斜
**結構正常化** = 每層各司其職 + 明確邊界 + 動態調整

對應：
- L58「範本是參考不是強制」+ L59「上游缺機制是倒置」
- = **v6.12 第 8 句立法（待加）**：「**平衡不在中間，在結構正常化**」

---

## 8. 立法擴展（v6.12 5+1+1+1 = 8 句）

> 1. 抽象不是錯，建後不 audit 才是
> 2. 觀測不是奢侈，自治理就是
> 3. 規範散落是必然，整合 SSOT 是責任
> 4. 修法不可逆，60 天 trial 是保險
> 5. 執行了不算落實，commit + push 才算
> 6. 範本是參考，不是強制，過度套用就是污染（L58）
> 7. 上游缺機制 = 治理倒置，下游反向 audit 是症狀（L59）
> 8. **平衡不在中間，在結構正常化**（L60 — 本批立法）

---

## 9. Owner 必要決策（請 LINE 回覆）

- **A. 全套執行**：Phase 1+2+3+4（推薦，~3 天）
- **B. 漸進執行**：先 Phase 1+3（CK_AaaP 加 audit）2 天
- **C. 僅 Phase 1**：保留本批 4 文件，下次再決策
- **D. 其他指示**

---

> **核心精神**：治理平衡 = 結構正常化 + 動態調整。
> Owner 連 2 反思 + 1 追問 = 治理進化的最深刻循環。
> 對應 v6.12 立法 8 句 + L31 ROI 延伸 + L4x family 反向 meta 層。
