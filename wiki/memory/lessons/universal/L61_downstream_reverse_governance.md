---
title: L61 — 下游反治理 (PileMgmt R18 案例研究 / L60 真活驗證範本)
type: lesson
date: 2026-05-31
fqid: CK_Missive#L61
family: meta-governance
related: [L58, L59, L60]
---

# L61 — 下游反治理（PileMgmt R18 案例研究）

> **日期**：2026-05-31
> **觸發**：L60 立法後 PileMgmt 真活反治理 commit `2a51d57b5` 案例研究
> **family**：meta-governance（與 L58/L59/L60 同層）
> **目的**：給其他 CK 系列「下游反治理」決策框架 + 範本

---

## PileMgmt R18 commit 完整內容

```
commit 2a51d57b556ddc2d2282b946a50492cb03793254
test(governance): R18 CK_Missive 跨 repo 污染守門 + fork-contract 邊界文件化

S2 防複發：新增 test_no_missive_contamination.py 兩層守門 (4 test)
- 檔名/目錄禁帶 (soul_loader/wiki_compiler/run_fitness/wiki/)
- 污染易落地目錄內容指紋掃描
  (canonical_entities/ck_missive/坤哥 等高特異性 token)

避誤報設計：不掃裸字 missive (CLAUDE.md 合法跨 repo 引用)
泛名 fitness 範本不列檔名黑名單改靠內容指紋
PileMgmt 合法用 canonical_user_id (非 canonical_entities)
與 vector(1536) (非 768D)

fork-contract.md 新增「CK_Missive sibling 污染邊界」段:
既有合約涵蓋 lvrland fork 上游
補上 sibling repo 污染邊界 (含指紋表)

經 ci-local.sh → .githooks/pre-push 自動 enforce

背景: 2026-05-30 覆盤清除 26 個誤入 PileMgmt 的 Missive 資產
(hidden-risks R18)
```

---

## 5 大設計亮點

### 亮點 1 — 兩層守門

| 層 | 目標 | 機制 |
|---|---|---|
| 第一層 | 檔名/目錄禁帶 | 黑名單 (soul_loader/wiki_compiler/run_fitness/wiki/) |
| 第二層 | 內容指紋掃描 | 高特異性 token (canonical_entities/ck_missive/坤哥) |

→ 雙層比單層 audit 涵蓋面廣。

### 亮點 2 — 避誤報設計

- 不掃裸字 `missive`（合法跨 repo 引用）
- 泛名 `fitness` 範本不列黑名單，改靠內容指紋
- 保留「合法自建同名範本」空間

→ Audit 不擾民 + 保留自由演進。

### 亮點 3 — fork-contract 邊界文件化

新增「CK_Missive sibling 污染邊界」段：
- 既有合約涵蓋 lvrland fork 上游
- 補 sibling repo 污染邊界（含指紋表）
- 指向具體守門機制

→ 文件 + 程式碼雙重定義邊界。

### 亮點 4 — CI 自動 enforce

`ci-local.sh → .githooks/pre-push` 自動跑：
- 不靠人記
- 不靠 review
- pre-push 攔截污染

→ 對齊 v6.12 第 2 句「觀測不是奢侈，自治理就是」。

### 亮點 5 — 覆盤式起點

> 「2026-05-30 覆盤清除 26 個誤入 PileMgmt 的 Missive 資產」

R18 不是憑空建立，是覆盤已發生污染後的防線。

→ 對齊 L58 「治理範本污染風險」即時驗證。

---

## 5 原則 — 下游反治理決策框架

各 CK 系列子專案可參考此框架決定是否建反治理機制：

### 原則 1 — 評估污染風險

```
✅ 該建反治理：
- 上游強推範本但業務脈絡不同
- 已發生範本誤入 (覆盤揭發)
- 上游缺 audit 機制 (L59 倒置)

❌ 不需建反治理：
- 上游範本確實適用 (L1 universal)
- 子專案無業務獨立性需求
- 上游已自治 (有 audit + 被檢查)
```

### 原則 2 — 雙層守門

```
第一層：檔名/目錄禁帶 (黑名單)
第二層：內容指紋掃描 (token 比對)

避免單層 audit 涵蓋不足
```

### 原則 3 — 避誤報設計

```
✅ 列入：高特異性 token (canonical_entities/坤哥)
❌ 不列：泛名 (fitness/missive)

子專案保留自由演進空間
```

### 原則 4 — 文件化邊界

```
fork-contract.md / TEMPLATE-POLICY.md
明確定義:
- 接受的範本 tier (universal/recommended/full)
- 拒絕的範本指紋
- 升級提案管道
```

### 原則 5 — CI enforce

```
.githooks/pre-push
+ ci-local.sh
自動 audit pre-push 攔截

不靠 owner 主動覆盤
不靠人記
```

---

## 對 CK 系列子專案的啟示

| 子專案 | 建議行動 |
|---|---|
| **CK_lvrland_Webmap** | 評估建類似 R18 反治理（若有污染風險） |
| **CK_PileMgmt** | 已建 ✅（R18 範本）|
| **CK_Showcase** | 評估，但業務脈絡不同（治理 API 屬性）|
| **CK_KMapAdvisor** | 評估，業務領域 (KG 顧問) 獨立性高 |

---

## 對 CK_Missive 自身的啟示

PileMgmt R18 揭發 CK_Missive 的責任：
1. **不再強推 L3 範本**（對齊 L58）
2. **加 install-template 警示**（套用前 dry-run 必要）
3. **接受被反治理**（不視為「子專案不合作」）
4. **學習 R18 設計**（CK_Missive 自身可加類似內容指紋 audit）

---

## v6.12 立法第 8 句真活驗證升級

> 第 8 句：「平衡不在中間，在結構正常化」（L60）

PileMgmt R18 是 L60 的 **真活案例**：
- 不是中間值（不刪除全部範本）
- 不是極端（保留 universal 範本）
- 是**結構正常化**：建立明確邊界 + 自動 enforce

對應 L60 5 原則：
- ✅ 原則 1：PileMgmt 自治
- ✅ 原則 2：拒絕 L3 specific
- ✅ 原則 3：建反治理（多源 audit）
- ✅ 原則 4：fork-contract 文件化（演進上送）
- ✅ 原則 5：CI enforce（動態調整）

5/5 原則對齊。

---

## 修法資產

| 檔案 | 行為 |
|---|---|
| `wiki/memory/lessons/universal/L61_*.md` | NEW lesson (本批，universal 因適用所有 CK 系列) |
| `docs/architecture/REFERENCE_FOR_OTHER_SYSTEMS.md` | 待補 R18 案例引用 |
| `scripts/install-template-to.sh` | 待加 dry-run 警示推薦 |

---

## 元洞察

**下游反治理 ≠ 反抗治理，而是治理進化的一環。**

對齊 v6.12 8 句立法：
- 第 1-5 句：上游視角（CK_Missive 自治）
- 第 6 句：下游視角（範本是參考）
- 第 7 句：上游缺機制（CK_AaaP 倒置）
- 第 8 句：平衡視角（L60）
- **L61 補強：下游反治理是平衡的實踐**

ROI 公式延伸：
```
真實 ROI = entities × usage_rate × commit_rate
           × correctness_rate × balance_rate
           × reverse_governance_rate ★ NEW
```

下游反治理率 = audit 覆蓋下游主動拒絕的範本比例。

---

> **核心精神**：下游反治理不是失敗，是治理進化的最高表現。
> PileMgmt R18 = L60 真活案例，給其他 CK 系列「如何反治理」的具體範本。
> 對應 v6.12 第 8 句立法 + L31 ROI 公式 6 維度延伸。
