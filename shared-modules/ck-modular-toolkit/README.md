# ck-modular-toolkit v1.0 — Contributor Repo Guide

> **Source**: CK_Missive v6.10
> **FQID**: `CK_Missive#ck-modular-toolkit_v1.0`
> **目的**: 讓**任何 CK_ 系列 repo** 用統一規範自建 ck-* / ckgis-* / ckaap-* / ckhm-* 等 shared package
> **戰略意義**: 從「CK_Missive 程式碼工廠」轉為「多源 mesh + 規範提供者」

---

## 為何用 toolkit 而非從 Missive 拿成品

| 場景 | 舊模式 | 新模式 |
|---|---|---|
| lvrland 想分享 GIS 給 pile | Missive 重寫 GIS (NIH) | lvrland 用 toolkit 自建 `ckgis-platform` |
| CK_AaaP 想推 fitness 工具 | Missive 維護 | AaaP 用 toolkit 自建 `ckaap-fitness` |
| hermes 想分享 SOUL 機制 | 不行 | hermes 用 toolkit 自建 `ckhm-soul` |

**領域專家就在那裡** — 各 repo 用自己的專業建 package，CK_Missive 提供規範與工具。

---

## Toolkit 內容

```
ck-modular-toolkit/
├── README.md                              本文件
├── checks/                                跨 repo 共用 audit 工具
│   ├── module_portability_audit.py        portability score 計算
│   ├── naming_convention_audit.py         命名規約偵測
│   ├── business_keyword_blacklist.yml     業務 keyword 黑名單
│   │
│   │ # === L41-L48 跨檔 SSOT family 防禦循環 (2026-05-25~27 擴散) ===
│   ├── compose_dockerfile_healthcheck_ssot.py   L45: compose vs Dockerfile HEALTHCHECK
│   ├── cross_repo_secret_audit.py               L41: JWT secret 跨 repo drift
│   ├── cross_repo_auth_state_audit.py           L44: ck-sso-js drift + onSuccess anti-pattern
│   ├── subdomain_registry_audit.py              L47: subdomain typo (需 subdomain-registry.yaml)
│   ├── container_lifecycle_audit.py             L46: :latest tag + 跨 repo image 版本 drift
│   ├── db_schema_drift_audit.py                 #1: model vs alembic migration drift
│   ├── sso_autoload_completeness_audit.py       #7: consumer repo SSO 接通完整度
│   ├── docker_compose_volume_consistency.py     L43: 同邏輯 volume 跨 compose 檔 drift
│   │
│   │ # === v6.12 P3 forward-looking audits (2026-05-27) ===
│   ├── startup_dependency_race_audit.py         depends_on 缺 condition: service_healthy
│   ├── db_pool_exhaustion_audit.py              SQLAlchemy pool utilization / overflow
│   ├── synthetic_baseline_freshness_audit.py    L48: scheduler chronic silent dead 偵測
│   ├── frontend_bundle_size_drift_audit.py      CI 停用後 bundle 膨脹 silent 漂移
│   │
│   │ # === L49 container host dependency family (2026-05-27~28, v6.11) ===
│   ├── container_host_dependency_audit.py       L49: rglob / file_path / docker CLI 跨環境破口
│   ├── tender_subscription_watchdog_audit.py    L48 family: scheduler silent dormant 偵測
│   └── admin_backup_smoke_test.py               L49: in-container business endpoint smoke
├── lessons/                                跨 repo lessons learned
│   ├── L41_jwt_secret_drift_silent_fail.md      JWT secret 跨 repo drift
│   └── L49_container_host_dependency_family.md  PM2→docker 5 重 silent regression
├── standards/                             規範文件
│   ├── NAMING_CONVENTIONS.md              命名 SSOT
│   ├── CONTRACTS_LAYER_GUIDE.md           Bounded Context Layer
│   ├── CONTRACTS_MIGRATION_PATTERN.md     5 大 migration 模式
│   └── MODULAR_INVENTORY.md               盤點方法
└── templates/                             package skeleton
    ├── install.sh.template                一鍵安裝腳本
    ├── manifest.yml.template              package 元資料
    └── README.md.template                 採用指南
```

---

## 跨 repo 命名空間規約

| Source Repo | Namespace | 範例 |
|---|---|---|
| CK_Missive | `ck-{name}` | `ck-auth`, `ck-navigation`, `ck-contracts` |
| CK_lvrland_Webmap | `ckgis-{name}` | `ckgis-platform`, `ckgis-cadastral` |
| CK_AaaP | `ckaap-{name}` | `ckaap-fitness`, `ckaap-runbook` |
| hermes-agent | `ckhm-{name}` | `ckhm-bridge`, `ckhm-soul` |
| CK_PileMgmt | `ckpile-{name}` | （業務專屬，多半不模組化） |

**FQID 格式**：`{source_repo}#{namespace}-{name}_v{semver}`

範例：
- `CK_Missive#ck-auth_v1.0`
- `CK_lvrland_Webmap#ckgis-platform_v1.0`
- `CK_AaaP#ckaap-fitness_v1.0`

---

## 5 步驟建你的 ck-* package（PACKAGING_PATTERN）

### Step 1：識別候選

對你想抽出的 module / 子目錄跑 portability audit：

```bash
# 假設你在 lvrland_Webmap，想抽出 GisMap 模組
python /path/to/ck-modular-toolkit/checks/module_portability_audit.py \
    frontend/src/components/GisMap/
```

判定：
- **score 1.000 PORTABLE** → 直接建 package
- **score 0.7-0.99** → 清 docstring 提升到 1.000
- **score < 0.7** → 需重構（改業務 vocabulary）

### Step 2：建立 package 目錄

```bash
mkdir -p shared-modules/ckgis-platform/{backend,frontend,_meta}
```

### Step 3：套用三件套 template

```bash
TOOLKIT=/path/to/ck-modular-toolkit

# 複製 install.sh template
cp ${TOOLKIT}/templates/install.sh.template shared-modules/ckgis-platform/install.sh
# 改：VERSION / SCRIPT_DIR / 安裝路徑

# 複製 manifest.yml template
cp ${TOOLKIT}/templates/manifest.yml.template shared-modules/ckgis-platform/manifest.yml
# 改：package / source_repo / target_consumers / files

# 複製 README template
cp ${TOOLKIT}/templates/README.md.template shared-modules/ckgis-platform/README.md
# 改：採用指南 + dependencies
```

### Step 4：複製業務檔

```bash
cp -r frontend/src/components/GisMap/* shared-modules/ckgis-platform/frontend/components/GisMap/
cp -r frontend/src/components/LayerControl* shared-modules/ckgis-platform/frontend/components/
# ... 等
```

### Step 5：驗證 portability + dry-run

```bash
# 驗 portability
python ${TOOLKIT}/checks/module_portability_audit.py shared-modules/ckgis-platform/

# dry-run 試裝給某 consumer（如 CK_Missive）
bash shared-modules/ckgis-platform/install.sh /path/to/CK_Missive --dry-run

# 真安裝
bash shared-modules/ckgis-platform/install.sh /path/to/CK_Missive --force
```

---

## 採用 toolkit（在你的 repo 內）

### 方式 1：Git submodule（推薦）

```bash
cd /path/to/your-repo
git submodule add <ck-toolkit repo URL> shared-modules/ck-modular-toolkit
```

### 方式 2：複製（簡單）

```bash
cp -r /d/CKProject/CK_Missive/shared-modules/ck-modular-toolkit /path/to/your-repo/shared-modules/
```

---

## 規範強制檢查

每個你建的 package 上線前必須：

- [ ] portability score ≥ 1.000（或 0.7+ NEEDS_RENAME 但說明）
- [ ] 至少 1 個 consumer dry-run 通過
- [ ] install.sh 含 portability audit 強制 gate
- [ ] manifest.yml 列 env_vars / db_schema_requirements / dependencies
- [ ] README.md 含 Quick Start + Post-install checklist
- [ ] FQID 格式正確 `{source_repo}#{ns}-{name}_v{semver}`
- [ ] 寫入 `consumers.yml`（後改 `repo_registry.yml`）的 `provides` 欄位

---

## 跨 repo Mesh Registry

`docs/architecture/repo_registry.yml`（Phase 2 啟用）紀錄各 repo 雙向關係：

```yaml
repos:
  - id: CK_Missive
    role: source + consumer
    provides:
      - ck-auth v1.0
      - ck-navigation v1.0
      - ck-modular-toolkit v1.0
    consumes: []

  - id: CK_lvrland_Webmap
    role: source + consumer
    provides:
      - ckgis-platform v1.0  # 未來
    consumes:
      - CK_Missive#ck-navigation v1.0  # ✓ 真採用（5/18）
      - CK_Missive#ck-auth v1.0        # dry-run 87%
```

---

## 變更紀錄

| 日期 | 版本 | 變更 |
|---|---|---|
| 2026-05-18 | v1.0 | 初版：3 categories（checks / standards / templates）+ 5 步驟 SOP + 命名空間規約 |
