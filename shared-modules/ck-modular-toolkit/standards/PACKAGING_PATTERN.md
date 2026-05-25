# PACKAGING_PATTERN — 建 ck-* package 5 步驟 SOP

> **版本**: v1.0 (2026-05-18)
> **配套**: ck-modular-toolkit README / NAMING_CONVENTIONS / CONTRACTS_LAYER_GUIDE
> **取代**: 散落於 ADR-0036 / shared-modules/ck-auth 內的 ad-hoc 步驟

---

## 為何需要 SOP

CK_Missive v6.10 經驗證 packaging pattern：

| Package | 結果 |
|---|---|
| ck-auth v1.0 | 16 檔 / 87% portability / 4 衝突 |
| ck-navigation v1.0 | 14 檔 / **100% portability / 0 衝突** ✓ |

**第二個 package 比第一個更乾淨且快得多** — 證明 pattern 已成熟可 SOP 化。

---

## 5 步驟（含 Quality Gate）

### Step 1 — 識別候選並評分

```bash
# 對候選 module 跑 portability audit
python ck-modular-toolkit/checks/module_portability_audit.py path/to/module/
```

| Score | Verdict | 下一步 |
|---|---|---|
| 1.000 | PORTABLE | Go to Step 2 |
| 0.7-0.99 | PORTABLE_WITH_NOTES | 修 docstring 提升再 audit |
| 0.4-0.7 | NEEDS_RENAME | 重新評估邊界（可能該抽 facade）|
| < 0.4 | NOT_PORTABLE | 不適合 packaging — 走 facade |

**Quality Gate 1**：score ≥ 0.7 才能進入 Step 2。

### Step 2 — 建目錄結構

依命名空間規約決定 package name 與位置：

```bash
mkdir -p shared-modules/{ns}-{name}/{backend,frontend,_meta}
# 範例：
mkdir -p shared-modules/ckgis-platform/{backend,frontend,_meta}
mkdir -p shared-modules/ckhm-bridge/{backend,frontend,_meta}
```

**Quality Gate 2**：目錄名符合 `{ns}-{name}` 規約（ns=ck/ckgis/ckaap/ckhm/ckpile）。

### Step 3 — 套用三件套 template

```bash
TOOLKIT=/path/to/ck-modular-toolkit
PKG=shared-modules/ckgis-platform

# 三件套
cp ${TOOLKIT}/templates/install.sh.template ${PKG}/install.sh
cp ${TOOLKIT}/templates/manifest.yml.template ${PKG}/manifest.yml
cp ${TOOLKIT}/templates/README.md.template ${PKG}/README.md

# install.sh 改 3 處：
# 1. VERSION="1.0.0"
# 2. backend 安裝目標路徑
# 3. frontend 安裝目標路徑

# manifest.yml 改 5 處：
# 1. package / version / source_repo / fqid
# 2. target_consumers
# 3. files (source → target mapping)
# 4. env_vars / db_schema_requirements
# 5. dependencies (python / npm)

# README.md 改 3 處：
# 1. Quick Start 範例
# 2. What's Included 結構
# 3. Post-install 步驟
```

**Quality Gate 3**：三件套都含「version / source_repo / target_consumers / 安裝路徑」必填。

### Step 4 — 複製業務檔

```bash
# Backend
cp -r source/path/* shared-modules/{pkg}/backend/

# Frontend
cp -r source/path/* shared-modules/{pkg}/frontend/
```

**注意**：
- 避免複製 `__pycache__` / `__init__.py`（除非必要）
- 確保檔在 source repo 真存在（hardware path verify）
- 保留原 docstring **但**對含業務 keyword 的範例**改通用**（如「公文」→「document」）

### Step 5 — 驗證 + dry-run + 真安裝

```bash
# 5a. 重 audit package（含修後）
python ck-modular-toolkit/checks/module_portability_audit.py shared-modules/{pkg}/

# 5b. dry-run 試裝給至少 1 個 consumer
bash shared-modules/{pkg}/install.sh /path/to/consumer-repo --dry-run

# 5c. 真安裝（--force 覆蓋既有衝突或 0 conflicts 直裝）
bash shared-modules/{pkg}/install.sh /path/to/consumer-repo --force

# 5d. consumer 端驗證
cd /path/to/consumer-repo
python -c "from app.api.endpoints.{pkg_path} import {module}"  # backend
# 或 frontend：npm run build 看是否成功 compile
```

**Quality Gate 4**：
- portability score = 1.000
- dry-run 至少 1 個 consumer ≥ 80% installable
- 真安裝後 consumer 能 import / build / 啟動

---

## 6 條 SOP 規約

### Rule 1：FQID 格式強制

```
{source_repo}#{ns}-{name}_v{semver}
```

範例：
- ✅ `CK_lvrland_Webmap#ckgis-platform_v1.0`
- ❌ `lvrland/gis-platform` (缺前綴 + 缺 ns + 缺版本)

### Rule 2：consumers.yml 雙向登記

任何 package 發布前必須在 `consumers.yml`（或 `repo_registry.yml`）登記：

```yaml
- id: CK_lvrland_Webmap
  provides:
    - ckgis-platform v1.0  # ← 新增此行
```

且 target_consumers 也須登記到 consumer 那 row 的 `consumes`。

### Rule 3：portability score 不容後退

每個 package 升版（v1.0 → v1.1）後跑 audit，**score 不可下降**。違反 → CI fail。

### Rule 4：dry-run 不等於真採用

`dry-run results` 不算「真採用」evidence。consumers.yml 必須區分：
- `dry_run_results: [...]`
- `real_installations: [...]`（含 method: install.sh --force + 日期）

### Rule 5：跨 repo source 不重複

同一個 module 不能在兩個 repo 都當 source（會分歧）。每個 ck-* package 唯一 source repo。

### Rule 6：toolkit version 對齊

所有 consumer 使用同版 ck-modular-toolkit 才能相容。toolkit major 升版 → 所有 ck-* 需同步驗證。

### Rule 7：Self-Contained Imports（LR-015 新加 / 2026-05-18）

> **起因**：ck-navigation v1.0 半接通事件 — install.sh 拷 14 檔但 frontend Sidebar 依賴 5 層 transitive deps（env.ts / navigationService / secureApiService / usePermissions / NotificationCenter / logger / router/types），導致 Webmap TS 編譯失敗 19 errors。

Package 內 import 不出 package（除以下例外）：

✅ **允許**：
- 相對 import 同 package 內（`./foo` / `../bar`）
- 框架白名單（fastapi / sqlalchemy / react / antd / ...）
- 標準函式庫（typing / datetime / pathlib / ...）
- 同源 repo 的 ck-* sibling packages（需 manifest 列依賴）

❌ **禁止**：
- 跨 package import 業務 module（`from app.services.X import Y`）
- 相對 import 跑出 package 邊界（`../../services/logger`）
- 寫死 repo-specific 路徑（`from ../../../router/types import ROUTES`）

**檢查**：`python scripts/checks/transitive_deps_audit.py shared-modules/{pkg}/`

**目標**：v6.11 後新 package 強制 violations = 0。

### Rule 8：No Business Constants Hardcoded（LR-015 配套）

> **起因**：ck-navigation v1.0 useMenuItems.tsx 內 hardcode 30+ 個 ROUTES.DOCUMENTS / DOCUMENT_NUMBERS / CONTRACT_CASES / AGENCIES 等 Missive 業務路由常數，Webmap 完全無對應，**source 側就不 portable**。

Package 內**禁止 import 業務常數**：

❌ **禁止 import**：
- `ROUTES.*` 業務路由常數
- `API_ENDPOINTS.*` 業務 API 路徑
- 業務 enum（如 DocumentType / DispatchStatus）
- 業務 magic number（TAOYUAN_PROJECT_ID = 1）

✅ **應改 props-driven**：
```typescript
// ❌ Bad
import { ROUTES } from '../../../router/types';
const menuItems = [{ key: ROUTES.DOCUMENTS, path: ROUTES.DOCUMENTS }];

// ✅ Good - 由 consumer 注入
interface MenuConfig { documents?: string; dashboard?: string; }
function useMenuItems(config: MenuConfig) {
  return [{ key: 'documents', path: config.documents }];
}
```

**檢查**：step 30 (business_keyword) + step 34 (transitive deps) 雙重門檻。

**v1.0 案例失敗 → v1.1 修法**：useMenuItems.tsx 完全移出 ck-navigation（業務專屬，consumer 自寫）。

### Rule 9：Frontend UI Component 慎重模組化（LR-015 終局教訓 / 2026-05-18 v2.0 收尾後立）

> **起因**：ck-navigation v1.0 試圖把 frontend layout components（Header/Sidebar/SidebarContent）一起 ship，揭發 frontend UI 強耦合 design system / route / permission schema → v2.0 改 backend-only 才達真採用嚴格定義（lvrland npx tsc exit 0）。

**Frontend UI components 通常不適合 packaging**：

❌ **不適合**：
- Layout shell（Sidebar / Header / 業務 menu）
- Page component（業務 view）
- Data view widget（含業務 schema 渲染）

理由：
- 各 repo 的 design system（Antd theme / icon set / color）不同
- 各 repo 的 route（ROUTES.X）不同
- 各 repo 的 permission schema 不同
- 各 repo 的 authService.UserInfo schema 不同

✅ **適合 packaging**：
- Backend API + service（**ck-navigation v2.0 保留**）
- TS type definitions / interface（給 consumer 自寫 hook / component 用）
- Utility hooks（pure logic, no UI）
- pure 純元件（如 ErrorBoundary、Loading spinner 簡單 wrapper）

**v2.0 收尾證實**：保留 backend 6 檔 + 1 TS type → lvrland 真採用 7 檔 TS exit 0 ✓

**新 audit 預警**：步 30 高 portability **+ 含 .tsx component** → 提示「考慮 backend-only 或 純 utility hook」

---

## 變更紀錄

| 日期 | 版本 | 變更 |
|---|---|---|
| 2026-05-18 | v1.0 | 初版（5 步驟 + 4 Quality Gates + 6 規約） |
