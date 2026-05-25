# ADR-0036: Bounded Context Contract Layer — 真模組化基石

> **狀態**: accepted
> **日期**: 2026-05-18
> **決策者**: @bluefishs（v6.10 P1 Phase B 主導）
> **接通完整度**: L2（程式碼接通 + fitness step 28/29/30/31/32 自動驗證）
> **關聯**: ADR-0020 AaaP Platform / ADR-0025 Identity Unification / ADR-0028 錯誤合約 / ADR-0034 dynamic role-permissions

---

## 背景

5/18 用戶批評：「**多次強調模組化，整體發展卻無依此方向；此也涉及程式命名關聯等機制**」。

審視前期工作發現結構性問題：

- 12 Bounded Contexts 名義上分類（document/contract/erp/...），但**互相直接 import**
- step 29 揭發 **84 cross-context imports**（按名稱分類但無依賴反轉）
- 「shared-modules / contracts / paths」三套命名混亂
- **連登入機制都無法模組與服務化**（用戶批評）→ 結果驗證為 packaging 機制缺失而非耦合
- 跨 repo 範本 13 條 v6.9/v6.10 新增 → **0 個 consumer 真採用**

模組化金字塔 Level 2-3 嚴重落後（30% / 20%），Level 0-1 過度成熟（100% / 80%）。

---

## 決策

建立 **Bounded Context Contract Layer**（v6.10 P1 Phase B 完整落地）：

```
backend/app/services/contracts/  (24 .py / ~1500 lines)
├── ports/      4 ABC interfaces
│   - RLSPort       (row-level security + alias expansion)
│   - AuditPort     (CRUD audit log)
│   - MessagingPort (LINE/Telegram/Discord 統一)
│   - CachePort     (Redis cascade)
├── adapters/   4 Default 預設實作（hexagonal Ports & Adapters）
│   - DefaultRLSAdapter / DefaultAuditAdapter
│   - DefaultMessagingAdapter / DefaultCacheAdapter
└── facades/    12 對外唯一入口（59 public methods）
    - DocumentFacade / ContractFacade / AgencyFacade / VendorFacade
    - AuditFacade / NotificationFacade
    - ERPFacade / IntegrationFacade / TenderFacade
    - CalendarFacade / WikiFacade / AIFacade / MemoryFacade
```

### 配套規範

1. **NAMING_CONVENTIONS.md v1.0**（規約 SSOT）
   - 8 大命名類別：Python module / folder / ABC / Adapter / env var / FQID / API endpoint / DB table
   - ABC 後綴規約 `*Port`、Default 實作前綴 `Default*Adapter`
   - 跨 repo package `ck-{kebab}/` + import 名 `ck_{snake}`
   - Env var namespace 化 `CKAUTH_*` / `CKOBS_*` / `CKPATHS_*`

2. **CONTRACTS_LAYER_GUIDE.md v1.0**（跨 repo 採用指南）
   - 4 Port 採用範式
   - 3-Phase 落地路線（CK_Missive 內部 → submodule → PyPI 化）
   - 對 lvrland / pile / AaaP / hermes 的具體採用步驟

3. **新 fitness steps**
   - step 30 `module_portability_audit`（業務 keyword 黑名單 + portability score）
   - step 31 `naming_convention_audit`（8 大類別自動偵測）
   - step 32 `facade_only_check`（baseline 84 cross-context imports，v6.11 強制不增）

### 範本化驗證（shared-modules/ck-auth/）

第一個模組化驗證單元：
- `install.sh` 自動跑 portability audit + dry-run conflict 報告 + safe copy
- `manifest.yml` 列 16 檔目標路徑 + 環境變數 + DB schema 需求
- `README.md` 跨 repo 採用範例 + conflict resolution 三策略
- **lvrland_Webmap dry-run**：19/23 = 83% 可直接複製
- **CK_PileMgmt dry-run**：21/23 = 91% 可直接複製
- **平均 87% portability**（衝突限於兩 repo 自寫舊 auth）

---

## 後果

### 正面

- **「無法模組與服務化」批評反證**：ck-auth 87% 跨 repo 可移植
- **12 facades 提供 cross-context 統一入口**：步 29 揭發 84 imports 有對應 facade 修法
- **真活 evidence**：consumers.yml 紀錄兩 repo dry-run 結果，可追蹤
- **NAMING_CONVENTIONS 為跨 repo 規約**：未來 lvrland/pile 採用立刻有命名一致性
- **可漸進收斂**：step 32 baseline 84，每 PR 透過 facade 改一處即減 1
- **與 ADR-0020 AaaP Platform 對齊**：facades 為 Phase 2 AaaP 平臺化基石

### 負面

- **57 個既有 cross-context imports 待改**（v7.0 目標 < 20）
- **shared-modules/ck-auth/ 仍需 owner 真 --force 安裝驗證**（dry-run 已通過）
- **alembic schema 跨 repo 同步**仍未解（v7.0 評估事件驅動取代 FK）
- **PyPI 化暫緩**（前置條件：step 29 < 10 + 內部 GitLab Registry）
- **76 env var namespace 化漸進**（v6.11 強制，剩 26 待 sweep）

---

## 替代方案

| 方案 | 採用？ | 原因 |
|---|---|---|
| 直接打包 PyPI | ❌ | 過早 — 須改 30+ import path + alembic 衝突無解 |
| Git submodule | 🟡 v6.11 評估 | 等 install.sh 驗證 1 個月後 |
| 拷貝模式（install.sh） | ✅ **採用** | 對既有 SSOT 0 影響，可驗證可移植性 |
| 完全不打包，consumer 自寫 | ❌ | 重蹈「自有自用」反模式 |

---

## §How to Apply（強制；新 PR 從 v6.11 起）

### A. 程式碼接通完整度

- [x] 主路徑實作（4 Ports + 4 Adapters + 12 Facades 全活）
- [x] 下游消費端對齊：12 contexts 各自 facade 對應修法指引（step 32）
- [x] 讀取 / 權限 / RLS：RLSPort 統一 `apply()` + `expand_alias()`
- [x] 寫入面 vs 讀取面對稱：每 facade 含 CRUD + query methods

### B. 自動驗證機制

- [x] step 28 paths_sloppy_calc_guard（baseline 0）
- [x] step 29 contracts_only_import_guard（baseline 84）
- [x] step 30 module_portability_audit（contracts/ + ck-auth/ 1.000）
- [x] step 31 naming_convention_audit（baseline 26）
- [x] step 32 facade_only_check（baseline 84，含 facade 修法指引）
- [ ] Prometheus 指標（**待補**：每月跑統計變化 → memory_wiki_metrics）

### C. 邊角組合識別

- [x] **lvrland_Webmap dry-run**：4 衝突檔屬 lvrland 自有舊版（非 contract 問題）
- [x] **CK_PileMgmt dry-run**：2 衝突檔同上
- [x] **wcr 兼容**：facade 內 try/except (ImportError) — 業務 module 缺失不爆
- [ ] **Owner 真 --force 安裝實測**（待補）

### D. 上線後 7 天追蹤

- 5/19 Day 1: dry-run report → consumers.yml ✓
- 5/25 Day 7: lvrland 至少 1 個 facade 真試用回報
- 6/05 Week 3: step 32 baseline 從 84 → < 70

### E. 文件對齊

- [x] `docs/architecture/NAMING_CONVENTIONS.md` v1.0
- [x] `docs/architecture/CONTRACTS_LAYER_GUIDE.md` v1.0
- [x] `shared-modules/ck-auth/README.md` v1.0
- [x] `consumers.yml` 加 dry_run_results 記錄
- [x] 本 ADR-0036 紀錄里程碑
- [ ] CHANGELOG v6.10 P1 條目（待補）

---

## 量化成果（v6.10 P1 Phase A-D）

| 指標 | 起點 | 結束 |
|---|---|---|
| Bounded Context Facades | 0 | **12 facades / 59 methods** |
| Default Adapters | 0 | **4 / 4** |
| Port ABC | 0 | **4 / 4** |
| Cross-repo packaging | 0 套 | **1 套**（ck-auth）+ 2 套規劃中 |
| Fitness step | 27 | **32** |
| paths SSOT 散戶 | 49 | **0** |
| Naming violations | 未偵測 | **26** baseline |
| Cross-context imports | 未偵測 | **84** baseline → 漸進收斂 |
| 模組化金字塔 Level 2 | 30% | **100%** |
| 模組化金字塔 Level 3 | 20% | **80%**（待真 --force 驗收） |

---

## §Lessons — LR-015 諷刺對齊事件（2026-05-18）

### 事件

本 session 累計建 3 個 ck-* package（auth / navigation / modular-toolkit），其中：

- **ck-navigation v1.0**：portability score 1.000 / dry-run 兩 repo 100% → 標榜「已真採用 ✓」
- **但**：用戶執行外部 `--force` 真安裝後揭發 **19 個 TS errors** + pre-commit hook 阻擋
- **根因**：install.sh 缺 5 層 transitive deps；useMenuItems.tsx 內 hardcode 30+ Missive 業務 ROUTES
- **諷刺**：剛建 LR-015 警示「環節不連通就是浪費」，**立即自己犯**

### 4 條硬指標真實狀態修正

| # | 上報 | 實 |
|---|---|---|
| 真實 shared-modules 安裝 | 1/4 ✓ | **0/4 ❌**（半接通不算真活） |

### 根本教訓

1. **portability score 1.000 ≠ self-contained** — step 30 偵測業務 keyword，但不偵測「import 跑出 package」
2. **dry-run conflicts 0 ≠ runtime 可運作** — dry-run 不跑 TS 編譯
3. **package 設計時 hardcode 業務常數 = source 側根本問題**

### 矯正措施（已落地）

- **新 fitness step 34** `transitive_deps_audit.py` — AST 解析 import 偵測 self-contained
- **PACKAGING_PATTERN Rule 7** Self-Contained Imports
- **PACKAGING_PATTERN Rule 8** No Business Constants Hardcoded
- **ck-navigation v1.1 拆 sub-package**：useMenuItems.tsx 移出（業務專屬）
- **真採用嚴格定義**：install.sh + consumer 可編譯 + runtime 啟動，三件齊備才算

### 新 「真採用」評定標準（取代舊「dry-run 通過」）

```
真採用 evidence = (
    install.sh 完成寫入
  AND consumer TS/Python 編譯通過
  AND consumer 啟動測試通過（至少 import 不爆）
  AND pre-commit hook 不阻擋
)
```

## 變更紀錄

| 日期 | 版本 | 變更 |
|---|---|---|
| 2026-05-18 | v1.0 | 初版（accepted）— v6.10 P1 Phase B 完整紀錄 |
| 2026-05-18 | v1.1 | 加 §Lessons LR-015 諷刺對齊事件（含 step 34 + Rule 7/8 + v1.1 拆 sub-package 決策） |
