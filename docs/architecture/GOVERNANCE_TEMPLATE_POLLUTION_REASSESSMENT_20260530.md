# 平台治理範本「污染源」反思評估 — 2026-05-30

> **Owner 觸發**：「CK_Missive 平台治理範本....變成其他專案汙染源...請再評估建議策略」
> **嚴重程度**：高 — 前批 install-template 對 4 子專案套用 132 檔可能造成治理過度污染
> **設計失誤**：未分級範本通用性 / 未提供 opt-out / 未尊重子專案業務獨立性

---

## 1. 真實污染風險

### 1.1 範本「全套」缺乏分級

前批 `install-template-to.sh --include=cross-file-ssot,fitness-tier,governance-dashboard,l4x-lessons`：

| 套用內容 | 子專案真實需求 | 風險 |
|---|---|---|
| cross-file-ssot-governance.md SOP | ✅ Docker 多服務都需 | LOW |
| paths_compose_mount_audit | ✅ 任何 Docker repo 都需 | LOW |
| container_env_alignment | ✅ 普適 | LOW |
| container_image_freshness | ✅ 普適 | LOW |
| run_fitness_daily.sh 8 step | ⚠️ 含 step 60 (image freshness) 對齊 SOP，但其他 step 可能無關 | MID |
| daily_self_retrospective.py 7 aspects | ❌ **高度 CK_Missive 特定**（含 Facade B 方案 / governance_lessons_l4x） | HIGH |
| generate_governance_dashboard.py | ❌ **CK_Missive 特定**（10 章節含 v6.12 4 原則 / Facade trial） | HIGH |
| L41/L43/L44/L45/L49/L50/L52/L53 lessons | ❌ **CK_Missive 事故敘事**（VolumeMount / SSO / Facade ROI 全是 CK_Missive 案例） | HIGH |

**結論**：132 檔中只有約 **20-30 檔真普適**，其餘 100+ 是 CK_Missive 特定。

### 1.2 範本污染 3 大徵兆

1. **語意污染**：子專案 lesson dir 出現「Facade B 方案 13→3 收口」← 子專案不知道 Facade 是啥
2. **規範污染**：子專案被迫遵守 v6.12 「修 PROJECT_ROOT 必同步 compose mount」（即使他們沒用 PROJECT_ROOT 抽象）
3. **觀測污染**：daily_self_retrospective 顯示 `governance_lessons_l4x_family_count=5` ← 對子專案無意義

### 1.3 為何 owner 反應「污染」

- ✅ Owner 之前 approve 是「範本採用」概念
- ❌ 實際變成「強加 CK_Missive 文化」
- 各子專案有自己的業務領域 + 演進節奏
- 統一治理框架對 monorepo 適用，對獨立 repo 是過度

---

## 2. 範本分類重新評估

### 2.1 三層分級

| 層 | 性質 | 範例 | 對外推薦度 |
|---|---|---|---|
| **L1 — 普適 (Universal)** | Docker / Python / Git 任何 repo 都需 | paths_compose_mount_audit / container_image_freshness / cross-file-ssot-governance SOP | ✅ 全推薦 |
| **L2 — 推薦 (Recommended)** | 中型 repo 適用 | run_fitness_daily.sh / governance_alignment_audit | 🟡 opt-in |
| **L3 — 特定 (Opinionated)** | CK_Missive 文化 | daily_self_retrospective / generate_governance_dashboard / L4x lessons | ❌ 不推薦套用，僅參考 |

### 2.2 既有 132 檔重新分類

| 類別 | 檔數 | L1 普適 | L2 推薦 | L3 特定 |
|---|---|---|---|---|
| cross-file-ssot | 5 | 5 | 0 | 0 |
| fitness-tier | 5 | 2 | 2 | 1 |
| governance-dashboard | 3 | 0 | 0 | 3 |
| l4x-lessons | 8 | 0 | 0 | 8 (全 CK_Missive 敘事) |
| **合計** | **21/repo** | **7 (33%)** | **2 (10%)** | **12 (57%)** |

**真實普適率僅 33%** — 前批 100% 套用嚴重失衡。

---

## 3. 新策略 — 5 道防線

### 3.1 install-template 升級為分級模式

```bash
# L1 only (推薦給所有 CK 系列)
bash scripts/install-template-to.sh ../CK_lvrland_Webmap --tier=universal

# L1 + L2 (有 fitness 文化的 repo)
bash scripts/install-template-to.sh ../CK_PileMgmt --tier=recommended

# L1 + L2 + L3 (完全 CK_Missive 化，僅 monorepo)
bash scripts/install-template-to.sh ../CK_Missive_internal --tier=full
```

### 3.2 子專案 opt-out 機制

每個子專案根目錄加 `.template-policy.yml`：
```yaml
template_source: CK_Missive
template_tier_accepted:
  - universal     # L1 自動接受
  - recommended   # L2 手動 approve 後接受
# - full          # L3 拒絕 (default)

template_excluded:
  - daily_self_retrospective.py  # 子專案 owner 不想要
  - L53_facade_over_engineering*  # 業務無關
```

install-template 跑時讀 policy → 自動 skip excluded。

### 3.3 lesson 命名分流

- `wiki/memory/lessons/universal/L01-L99` — 純技術教訓 (Docker / Python / SSOT)
- `wiki/memory/lessons/missive-specific/M01-M99` — CK_Missive 業務脈絡教訓
- 跨 repo 只套用 universal/，missive-specific/ 留本 repo

### 3.4 對外文件分流

- `docs/architecture/REFERENCE_UNIVERSAL.md` — 對所有 CK 系列推薦
- `docs/architecture/REFERENCE_FOR_OTHER_SYSTEMS.md` — 本批已寫，需重新分級

### 3.5 套用後 audit 升級

`cross_repo_template_drift_audit` 加維度：
- L1 覆蓋率（應 100%）
- L2 覆蓋率（應 30-60%）
- L3 覆蓋率（應 < 10%，子專案應該很少採用）

> 反指標：若子專案 L3 覆蓋率高 → 表示治理污染，需檢討。

---

## 4. 對前批 132 檔回滾建議

### 4.1 給 4 子專案 owner 的訊息

```
親愛的子專案 owner，

5/30 我自動套用了 CK_Missive 的 v6.12 治理範本 (~21 檔/repo)。
經 owner 反思指出可能造成治理污染，建議：

1. ✅ 保留 (L1 普適, ~7 檔/repo)：
   - paths_compose_mount_audit.py
   - container_env_alignment_audit.py
   - container_image_freshness_check.py
   - compose_dockerfile_healthcheck_ssot.py
   - cross-file-ssot-governance.md SOP
   - cron_silent_dormant_check.py

2. 🟡 評估後保留 (L2 推薦, ~2 檔/repo)：
   - run_fitness_daily.sh (改 step 名單適合本 repo)
   - governance_alignment_audit.py (改 ADR 目錄路徑)

3. ❌ 建議刪除 (L3 CK_Missive 特定, ~12 檔/repo)：
   - daily_self_retrospective.py (7 aspects 含 v6.12 4 原則特定)
   - generate_governance_dashboard.py (10 章節含 Facade B trial)
   - L41/L43/L44/L45/L49/L50/L52/L53 lessons (CK_Missive 事故敘事)
   - FITNESS_LAYERED_EXECUTION_SOP_20260530.md (CK_Missive 工程文化)

請依各 repo 業務需求自行調整保留範圍。
```

### 4.2 寫 lesson L58: 治理範本污染風險

L4x family 第十案（**meta-治理層**）：
- 之前 L41-L57 都是「跨檔 SSOT silent fail」
- L58 是「**過度治理 = 治理污染**」反向教訓

---

## 5. 元洞察 — owner 的深刻洞察

### 5.1 我的盲點

- 把「對外採用率 0% → 100%」當成功
- 未區分「規範採用」vs 「規範強加」
- 未尊重子專案 owner 的演進自由度

### 5.2 對齊 owner 哲學

> 範本是參考，不是強制
> Owner 不希望「CK_Missive 治理文化」變成「CK 系列強推範本」
> 各子專案有自己的業務 + 節奏 + 文化

### 5.3 對應 5 句核心精神延伸

加第 6 句：

> 6. **範本是參考，不是強制，過度套用就是污染**

---

## 6. 立即行動計劃

### Phase 0（本批）

- ✅ 寫此評估報告
- ✅ 通知 owner 揭發污染風險
- 待 owner 決策回滾範圍

### Phase 1（owner approve 後）

- 升級 install-template 加 `--tier` flag (L1/L2/L3)
- 寫 lesson L58
- 修 REFERENCE_FOR_OTHER_SYSTEMS 加分級表
- 給 4 子專案發 PR 「建議移除 L3 範本」

### Phase 2

- 加 `.template-policy.yml` 機制
- 升級 cross_repo_drift_audit 加 L1/L2/L3 維度
- 反指標：L3 覆蓋率高 = 治理污染警示

---

## 7. 風險評估

| 風險 | 等級 | 緩解 |
|---|---|---|
| 已套用範本內容子專案 owner 已參考 | 中 | 提供分級指南 + 自由刪 |
| 反向衝擊：強制刪除被當「侵犯」 | 高 | 改為「建議刪除」+ 提供 PR |
| 治理金字塔反向坍塌（owner 失去信心）| 中 | 強調「分級而非廢棄」 |
| L1-L3 分類判定爭議 | 低 | 提供清楚規則 + 反指標 |

---

## 8. Owner 必要決策點

請 owner 回覆：

- **A. 立即回滾**：對 4 子專案發 PR 建議刪除 L3 範本（~12 檔/repo）
- **B. 分級升級**：保留現狀但升級 install-template + 寫指南供下次參考
- **C. 維持現狀**：認為過度套用風險可接受
- **D. 其他指示**

---

> **核心精神**：v6.12 立法 5 句精神 + 第 6 句：「**範本是參考，不是強制，過度套用就是污染**」
> Owner 的反思是治理進化的真實價值 — 揭發「治理本身的過度設計」遠比「執行治理」更深刻。
