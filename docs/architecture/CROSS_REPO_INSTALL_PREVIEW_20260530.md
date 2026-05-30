# 跨 Repo Install-Template 預覽報告 — 2026-05-30

> **建立**：2026-05-30 接續完成前述規劃時的整合決策資料
> **目的**：4 RED-zero 子專案 install-template 套用前 dry-run 結果
> **owner 決策點**：approve 後直接套用或選擇性套用

---

## 揭發背景

`scripts/checks/cross_repo_template_drift_audit.py` 首跑揭發：
- 4 子專案 v6.12 治理範本採用度 **0/6** 全 RED-zero
- 對外範本實際採用率 = 0%

## Dry-run 結果摘要

| 目標 Repo | 待套用檔數 | 影響範圍 |
|---|---|---|
| CK_lvrland_Webmap | 33 檔 | scripts/checks + .claude/rules + wiki/lessons + docs/architecture |
| CK_PileMgmt | 33 檔 | 同上 |
| CK_Showcase | 33 檔 | 同上 |
| CK_KMapAdvisor | 33 檔 | 同上 |
| **合計** | **132 檔** | 4 repo × 5 個分類目錄 |

## 套用清單（4 個分類）

### 1. cross-file-ssot（5 檔）

- `.claude/rules/cross-file-ssot-governance.md` SOP
- `scripts/checks/paths_compose_mount_audit.py` (L52)
- `scripts/checks/container_env_alignment_audit.py` (L51)
- `scripts/checks/container_image_freshness_check.py` (L51.7.1)
- `scripts/checks/compose_dockerfile_healthcheck_ssot.py` (L45)

### 2. fitness-tier（5 檔 + Tier 1/2 runner）

- `scripts/checks/run_fitness_daily.sh` Tier 1 (8 step)
- `scripts/checks/run_fitness_weekly.sh` Tier 2 (15 step)
- `scripts/checks/cron_silent_dormant_check.py`
- `scripts/checks/daily_self_retrospective.py`
- `docs/architecture/FITNESS_LAYERED_EXECUTION_SOP_20260530.md`

### 3. governance-dashboard（3 檔）

- `scripts/checks/generate_governance_dashboard.py` generator
- `scripts/checks/dashboard_freshness_check.py` audit
- `scripts/checks/governance_alignment_audit.py` 規範對應

### 4. l4x-lessons（8 條 family lesson）

- L41 jwt_secret_drift
- L43 volume_mount_drift
- L44 sso_session_lock
- L45 compose_dockerfile_healthcheck_drift
- L49 container_host_dependency_family
- L50 multi_source_identifier_link
- L52 paths_compose_mount_drift
- L53 facade_over_engineering_30day_pruning

---

## 套用前 owner 決策點

### 必要決策

1. **是否一次全套用 4 子專案？**（推薦）
   - 推薦：是。對外範本一致性最重要
   - 反例：lvrland/PileMgmt 業務領域差異大可能不需 GitNexus

2. **是否需要對應 ADR 同步？**
   - 推薦：先套 fitness + lesson 不套 ADR
   - 理由：ADR 含 Missive 特定脈絡，可能誤導

3. **套用後子專案 owner 是否會反彈？**
   - 評估：可能。子專案 owner 需要時間消化
   - 建議：附 commit message 說明來源 + 文件指引

### 套用後子專案 expected state

- 6/6 範本資產 → 🟢 GREEN（從 0/6 RED-zero 起跳）
- fitness daily 可跑 8 step
- dashboard 可生成自家版 SSOT
- L4x family 8 lesson 可參考避免重複事故

---

## 推薦執行指令

```bash
# 一次性套用 4 子專案（推薦）
for r in CK_lvrland_Webmap CK_PileMgmt CK_Showcase CK_KMapAdvisor; do
  bash scripts/install-template-to.sh ../$r \
    --include=cross-file-ssot,fitness-tier,governance-dashboard,l4x-lessons
done

# 套用後到各子專案 commit
for r in ../CK_lvrland_Webmap ../CK_PileMgmt ../CK_Showcase ../CK_KMapAdvisor; do
  cd $r
  git add scripts/checks/ .claude/rules/ wiki/memory/lessons/ docs/architecture/
  git commit -m "chore: install v6.12 governance template from CK_Missive"
  git push
  cd -
done
```

### 套用後重跑 audit 驗證

```bash
cd D:/CKProject/CK_Missive
python scripts/checks/cross_repo_template_drift_audit.py
# 預期: 4/4 RED-zero → 4/4 GREEN
```

---

## 自我覆盤閉環真活驗證

本報告產生方式對齊「owner 訴求 → audit 揭發 → 整合決策 → 等 owner approve」流程：

1. ✅ owner trigger（「規範散落」訴求）
2. ✅ cross_repo_template_drift_audit 揭發 4 RED-zero
3. ✅ Dashboard §9 整合呈現
4. ✅ 本報告供 owner 決策
5. ⏳ 等 owner approve（不擅自跨 repo commit）

---

## 風險評估

| 風險 | 等級 | 緩解 |
|---|---|---|
| 子專案 owner 不知情就被改 | 高 | 預覽報告先看 + commit message 透明 |
| Fitness audit 在子專案 fail | 中 | 預設 warning mode 不 strict，先觀察 baseline |
| Lesson 引用 Missive 特定 commit | 低 | Lesson 內已標 family pattern 可通用 |
| install-template 漏檔 | 低 | dry-run 33 檔已對齊 |

---

> **執行門檻**：owner LINE 回覆 `approve install-template` 後執行
> **預估工時**：1 小時內全 4 repo 套用 + 驗證 + commit
> **後續 audit**：next cross_repo_drift_audit 跑時應 4/4 GREEN
