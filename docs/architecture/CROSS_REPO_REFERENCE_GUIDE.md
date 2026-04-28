# 跨 Repo 範本引用治理規範

> **建立**：2026-04-28（v5.10.1+）
> **狀態**：accepted（CK_Missive 範本資產提供方規範）
> **適用對象**：
>   - **Source**：CK_Missive（範本資產來源）
>   - **Consumer**：CK_lvrland_Webmap / CK_lvrland_dataform / CK_PileMgmt / CK_KMapAdvisor / CK_Showcase / CK_AaaP / hermes-agent
> **與 CK_AaaP/CONVENTIONS.md 關係**：本文補完 ADR FQID 之外的「範本資產」引用規範
> **跨 repo 引用 FQID**：`CK_Missive#CROSS_REPO_REFERENCE_GUIDE_v1.0`

---

## 0. 為什麼需要這份規範

CK_Missive v5.9.9~v5.10.1 累積大量範本資產（7 SOP / 21 lessons / 3 detector / 11 fitness checks
/ 3 retrospective / TEMPLATE_EXTRACTION 等），但缺：

| 缺口 | 後果 |
|---|---|
| FQID 不統一（ADR 有 `Repo#0014` 但 lessons / playbook 各寫各的）| 跨 repo 引用易斷 |
| 沒約定「該全 copy 還是 symlink」 | 升級時不知影響面 |
| 範本升級無自動通知 | 引用方版本永遠落後 |
| 引用方改良無回流路徑 | 改良孤兒，浪費 |
| 無版本相容性聲明 | 引用方不知該升 v1.0 → v2.0 嗎 |

本規範建立**最小可運作的引用治理體系**，支援上述 7 個 consumer repo 長期使用。

---

## 1. FQID 統一規範（補 CK_AaaP/CONVENTIONS §1.3）

### 1.1 範本資產 FQID 語法

```
<Repo>#<AssetID>[_<Version>]

範例：
  CK_Missive#0014                           ← ADR（同 CONVENTIONS §1.3）
  CK_Missive#WAVE_1_PLAYBOOK_v2.2          ← 範本文件
  CK_Missive#L21                            ← Lesson
  CK_Missive#AliasIntegrationDrawer_v1.0   ← 元件範本
  CK_Missive#install-template-to_v1.0      ← 工具腳本
  CK_Missive#fitness_step_7                 ← Fitness check
```

### 1.2 五大類別範本資產 FQID

| 類別 | FQID 格式 | 範例 | 版本必填 |
|---|---|---|---|
| **ADR** | `Repo#NNNN`（4-digit） | `CK_Missive#0028` | 否（同 CONVENTIONS）|
| **Lesson** | `Repo#L##` | `CK_Missive#L21` | 否（lesson 不版本化）|
| **Playbook / Doc** | `Repo#DOC_NAME_vX.Y` | `CK_Missive#WAVE_1_PLAYBOOK_v2.2` | **是** |
| **Component** | `Repo#ComponentName_vX.Y` | `CK_Missive#AliasIntegrationDrawer_v1.0` | **是** |
| **Tool / Script** | `Repo#tool_name_vX.Y` | `CK_Missive#install-template-to_v1.0` | **是** |

### 1.3 FQID 必出現位置

- ✅ 文件最後一行：`> 跨 repo 引用 FQID：\`CK_Missive#XXX_vY.Z\``
- ✅ 元件 docstring header
- ✅ 腳本 docstring `Refs:` 段
- ✅ Lesson registry 條目
- ✅ ADR `關聯` 欄位

### 1.4 引用方寫法

```markdown
本案 KG fitness step 7 借鏡 CK_Missive#fitness_step_7（agent_evolution_health.py）。
詳見 CK_Missive#L21 排查 SOP。
若採 v2 升級，注意 breaking change（見 CK_Missive#WAVE_1_PLAYBOOK_v2.2 §4.x）。
```

---

## 2. 引用模式三選一

### 2.1 模式對比

| 模式 | 適用 | 升級成本 | 客製空間 | 例 |
|---|---|---|---|---|
| **A. Copy（snapshot）** | 大改範本 / 試 v2.0 | 高（手動 sync） | 高 | install-template-to.sh 預設 |
| **B. Symlink** | 共用 monorepo / dev 環境 | 自動 | 0（無法改） | 開發機快速試 |
| **C. Git submodule** | 跨組織共用 / 嚴格版本 | 中 | 0（同 source）| 多 repo 共用 fitness 套件 |

**強烈建議 v1：採 A. Copy + install-template-to.sh**：
- 工具自動 dry-run 預覽 → apply copy → 印安裝後人工步驟
- 引用方有完整客製空間（修變數、加 EXCLUDE）
- 升級時用 `--diff` 模式（v2 規劃）看有什麼變

### 2.2 install-template-to.sh 標準用法

```bash
# Source repo (CK_Missive)
cd /path/to/target_repo

# Dry-run 預覽（不改檔）
bash /path/to/CK_Missive/scripts/install-template-to.sh . --dry-run

# 全量 apply
bash /path/to/CK_Missive/scripts/install-template-to.sh .

# 選擇性 apply（推薦：先小範圍）
bash /path/to/CK_Missive/scripts/install-template-to.sh . --include=fitness,guards

# 安裝後人工步驟（工具會印）：
#   1. 改 scripts/checks/run_fitness.sh 內 WIKI_DIR / SERVICES_ROOT 等變數
#   2. 改 ADR header 的 repo 名稱
#   3. 跑 bash scripts/checks/run_fitness.sh 取得 baseline
```

---

## 3. 版本治理

### 3.1 SemVer 應用

範本資產採 SemVer：

| 升級類型 | 範例 | 引用方影響 |
|---|---|---|
| **Major (vX.0 → v(X+1).0)** | playbook v2.2 → v3.0 | **Breaking** — 必須 review 升級計畫 |
| **Minor (vX.Y → vX.(Y+1))** | playbook v2.0 → v2.1 | 加新 SOP / detector，向後相容 |
| **Patch（vX.Y.Z）** | scanner v3.0 → v3.0.1 | bug fix，自動 apply 安全 |

### 3.2 Breaking Change 觸發條件

任一即為 Major bump：
- detector 改 exit code 語義（如原 0=pass → 改 0=fail）
- playbook SOP step 順序大改（影響操作習慣）
- FQID 重新命名
- 引用方 import path 需改

### 3.3 Changelog 必填項

每個範本資產 update 需有：
```markdown
## [vX.Y.Z] - YYYY-MM-DD

### Breaking
- （列改動 + 升級指南）

### Added
- （新增功能）

### Fixed
- （bug 修復）

### Note for consumers
- （引用方須知）
```

範例：`scripts/checks/README.md` 內各 detector 段落。

---

## 4. 範本升級通知機制

### 4.1 Source 端（CK_Missive）責任

每次範本 commit 必：
1. **commit message** 含 `Refs: <FQID>` 段
2. **CHANGELOG.md** 加條目（含 Breaking / Note for consumers）
3. **Major bump** 額外發 GitHub Release（手動 trigger，避免 GitHub Actions 費用）

### 4.2 Consumer 端拉取機制（v1：手動 + reminder）

**月度範本健檢**（推薦每月覆盤排程）：

```bash
# 在 consumer repo
cd /path/to/lvrland_Webmap

# 1. fetch source repo 最新 changelog
git -C /path/to/CK_Missive log --oneline --grep="範本\|playbook\|detector" --since="1 month ago"

# 2. diff 自己的範本資產 vs source
diff -r /path/to/CK_Missive/scripts/checks/ scripts/checks/ | head -30

# 3. 若有重大更新，跑 install 工具升級
bash /path/to/CK_Missive/scripts/install-template-to.sh . --include=fitness --dry-run
```

### 4.3 v2 規劃（pull-based detector）

未來在 source repo 提供 `scripts/notify-consumers.py`：
- 讀 `consumers.yml` 註冊清單
- diff 各 consumer 的範本版本
- 發 issue / Telegram 通知該升級

---

## 5. 引用方貢獻回流規範

### 5.1 流程

```
Consumer 改良範本（如 lvrland 加 dead_ui_detector v1.1 baseline file）
  ↓
1. 在 consumer repo 先驗證 + commit
  ↓
2. 開 PR 到 CK_Missive（或 issue 提案）
  ↓
3. CK_Missive owner review + accept
  ↓
4. 升 source 版本 v1.0 → v1.1
  ↓
5. CHANGELOG + 通知其他 consumers
  ↓
6. 其他 consumers 月度健檢時拉新版
```

### 5.2 PR 模板（待加 .github/PULL_REQUEST_TEMPLATE.md）

```markdown
## 範本貢獻

**Source asset FQID**: <e.g., CK_Missive#dead_ui_detector_v1.0>
**Consumer repo**: <e.g., CK_PileMgmt>
**改良內容**: <一句話說明>
**Breaking?**: <yes/no>

## 改良動機

## 在 consumer 端的驗證

## 適用範圍評估
```

---

## 6. 跨 repo 範本目錄（CK_Missive 提供方）

當前可被引用的範本資產（v5.10.1+ 完整清單）：

### 6.1 L4 Plug-and-Play（改 1~2 變數即可用）

| FQID | 用途 |
|---|---|
| `CK_Missive#run_fitness_v3.0` | 7-step fitness runner |
| `CK_Missive#service_dir_entropy_v1.0` | services/ 散戶比例 |
| `CK_Missive#config_dead_reader_scan_v3.0` | dead config + deferred marker |
| `CK_Missive#async_session_race_guard_v1.0` | asyncpg session 守護 |
| `CK_Missive#sse_headers_guard_v1.0` | SSE Content-Encoding 守護 |
| `CK_Missive#schema_lazy_load_guard_v1.0` | Pydantic schema 守護 |
| `CK_Missive#agent_evolution_health_v1.0` | Agent evolution 診斷 |
| `CK_Missive#lessons_drift_check_v1.0` | Lessons registry 自我保護 |
| `CK_Missive#dead_ui_detector_v1.0` | Dead UI 候選偵測 |
| `CK_Missive#install-template-to_v1.0` | 跨 repo 一鍵部署 |

### 6.2 L3 Configurable（改 config 後可用）

| FQID | 用途 |
|---|---|
| `CK_Missive#timeouts_v1.0` | TimeoutContract + SLOContract SSOT |
| `CK_Missive#prometheus_middleware_v1.0` | /metrics endpoint |
| `CK_Missive#grafana_dashboards_v1.0` | 3 dashboards |
| `CK_Missive#alerts_v1.0` | 12 alert rules |

### 6.3 L2 Reference（需重寫但結構可借）

| FQID | 用途 |
|---|---|
| `CK_Missive#STANDARD_REFERENCE_v1.0` | 12 章架構標準 |
| `CK_Missive#TEMPLATE_EXTRACTION_v1.0` | 30-min quick-start |
| `CK_Missive#WAVE_1_PLAYBOOK_v2.2` | 7 SOP + 1 anti-pattern |
| `CK_Missive#WAVE_1_RETROSPECTIVE_v1.0` | Wave 1 反思 |
| `CK_Missive#WAVE_2_TO_7_RETROSPECTIVE_v1.0` | Wave 2-7 反思 |
| `CK_Missive#WAVE_2_PLAN_v1.0` | 規劃模板 |
| `CK_Missive#SERVICE_CONTEXT_MAP_v1.0` | 散戶分類 |
| `CK_Missive#LESSONS_REGISTRY_v1.0` | 21 條 lessons |
| `CK_Missive#AliasIntegrationDrawer_v1.0` | Drawer 元件範本 |
| `CK_Missive#CROSS_REPO_REFERENCE_GUIDE_v1.0` | 本檔 |

### 6.4 ADR 範本（拷貝後改 repo 名）

| FQID | 用途 |
|---|---|
| `CK_Missive#0028` | Error contract policy |
| `CK_Missive#0029` | ADR Lifecycle policy |
| `CK_Missive#0030` | Hermes GO/NO-GO（含 SLO 拍板模板）|

---

## 7. Consumer 端使用流程（lvrland/PileMgmt 視角）

### 7.1 首次採用（Day 0）

```bash
cd /path/to/CK_lvrland_Webmap

# Step 1: dry-run 看會 copy 什麼
bash /path/to/CK_Missive/scripts/install-template-to.sh . --dry-run

# Step 2: 選擇性 apply（建議先 fitness + guards）
bash /path/to/CK_Missive/scripts/install-template-to.sh . --include=fitness,guards

# Step 3: 改變數
vim scripts/checks/run_fitness.sh   # 改 WIKI_DIR / SERVICES_ROOT
vim scripts/checks/agent_evolution_health.py   # 改 DSN / REDIS_URL（若不用 evolution 可刪）

# Step 4: 跑 baseline
bash scripts/checks/run_fitness.sh

# Step 5: commit baseline（accept current state as ground truth）
git add scripts/checks/ && git commit -m "feat: 採 CK_Missive 範本資產 v5.10.1+ baseline"
```

### 7.2 月度健檢

```bash
# Step 1: fetch CK_Missive 最新 changelog
git -C /path/to/CK_Missive log --oneline --since="1 month ago" -- scripts/checks/ docs/architecture/

# Step 2: 檢查我引用的版本是否需升
# 查 CK_Missive 各範本 README / docstring 看當前版本

# Step 3: 若需升，dry-run 預覽
bash /path/to/CK_Missive/scripts/install-template-to.sh . --include=fitness --dry-run

# Step 4: 套用
bash /path/to/CK_Missive/scripts/install-template-to.sh . --include=fitness

# Step 5: review diff
git diff scripts/checks/

# Step 6: 跑 fitness 確認沒新 regression
bash scripts/checks/run_fitness.sh
```

### 7.3 引用方該避免的事

- ❌ 直接修改範本檔再 commit（無法回流，修法後無法升級）→ 改去 source repo 提 PR
- ❌ 跳過 install 工具手動 cp（容易漏檔，以及錯失 README 警語）
- ❌ 引用「裸 ADR-0028」而非 FQID（語意歧義）
- ❌ 自己 copy 一份 LESSONS_REGISTRY 並修改（lessons SSOT 應只一份在 source）

---

## 8. 治理檢核（給 source repo 月度跑）

CK_Missive owner 月度應跑：

```bash
# 1. 確認 lessons drift health
python scripts/checks/lessons_drift_check.py

# 2. 確認 dead config / dead UI 在閾值內
python scripts/checks/config_dead_reader_scan.py
python scripts/checks/dead_ui_detector.py

# 3. fitness 全綠
bash scripts/checks/run_fitness.sh

# 4. 確認本檔 FQID 清單與實際範本同步（手動 review §6）
ls scripts/checks/ docs/architecture/ docs/adr/

# 5. 若有 consumer 回饋，accept 並升 minor/patch
```

---

## 9. v6.0 規劃（待實作）

- `scripts/notify-consumers.py` — pull-based 通知 detector
- `consumers.yml` — 註冊使用範本的 repo 清單
- GitHub Release（每 major bump 手動發）
- PR template (`.github/PULL_REQUEST_TEMPLATE.md`)

---

## 10. 變更紀錄

- 2026-04-28 v1.0：首次發布
  - 5 大類別 FQID 規範
  - 3 引用模式 + install-template-to.sh 為 default
  - SemVer 治理 + Breaking Change 觸發條件
  - Consumer 月度健檢 SOP
  - 27 個現存範本資產完整目錄

---

> **此檔自身 FQID**: `CK_Missive#CROSS_REPO_REFERENCE_GUIDE_v1.0`
> **引用範例**: `本 fitness step 7 採 CK_Missive#agent_evolution_health_v1.0，引用治理見 CK_Missive#CROSS_REPO_REFERENCE_GUIDE_v1.0`
> **回饋**: 開 PR 到 CK_Missive 或 issue 提案
