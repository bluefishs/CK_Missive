# CK_Missive 對外參考指南 — 服務層 / 架構設計 / 管理機制

> **定位**：本專案為其他 CK 系列系統（lvrland / PileMgmt / Showcase / KMapAdvisor）參考範本
> **適用對象**：架構設計 / 治理機制 / 持續進化 SOP 想借鑑的 repo
> **更新日**：2026-05-30（v6.12 收尾後）
> **跨 repo 部署**：`bash scripts/install-template-to.sh ../<target_repo>`

---

## 為何 CK_Missive 是好範本

從 v6.8 (5/04) 到 v6.12 (5/30) 累積經驗：
- **53 個 lesson**（L01~L53，含 8 個 L4x family 跨檔 SSOT 治理失效案例）
- **64 個 fitness check**（涵蓋 daily 8 / weekly 14 / monthly 64）
- **39 個 ADR**（含 ADR-0036 30 天 trial 失敗 → B 方案收口的完整裁判流程範例）
- **3 道 governance 防線**（generator + 入口 + freshness audit）
- **真實事故修法軌跡**：5/21 L43 volume drift 10h dormant、5/22 L45 healthcheck drift 18min FailingStreak、5/29 L51 LINE 40h silent fail

不是教科書，是**血淚教訓蒸餾**。

---

## 8 大可借鑑模組（按重要性）

### 1. 服務層 — Bounded Context + DDD 漸進遷移

**核心資產**：
- `backend/app/services/` 12 contexts × 73 檔（Wave 1-8 遷移完成，0 regression）
- Repository pattern 34 類（含 `BaseRepository[T]` 泛型 + 業務專用方法）
- Query Builder 3 類（Fluent API）

**借鑑要點**：
- 不要一次重構 — 走 Wave 漸進，每 wave 留 stub 維持向後相容
- `docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md` 完整 SOP
- `docs/architecture/SERVICE_CONTEXT_MAP.md` 散戶映射表

**禁忌（L31 ROI）**：
- 建抽象前先 audit 30 天 usage_rate，不要先建供給
- ADR-0036 B 方案範例：13 facade → 3 收口 -1509L
- 留下的 entity 補強 caller，廢 zero entity

### 2. 架構設計 — paths.py + cross-file SSOT

**核心資產**：
- `backend/app/core/paths.py` — PROJECT_ROOT 集中 SSOT
- `.claude/rules/cross-file-ssot-governance.md` — 6 規則 + 9 audit 配套表格
- `scripts/checks/paths_compose_mount_audit.py` — fitness step 62

**借鑑要點 — L4x family 8 案教訓**：

| Family | 事故 | 防禦 |
|---|---|---|
| L41 | JWT secret 跨 repo drift | cross_repo_secret_audit |
| L43 | docker volume name 雙軌 | docker_compose_volume_consistency |
| L44 | SSO session lock 雙軌 | cross_repo_auth_state_audit |
| L45 | compose vs Dockerfile healthcheck | compose_dockerfile_healthcheck_ssot |
| L51 | docker-compose env 注入缺漏 | container_env_alignment |
| L51.7.1 | container image 過舊 | container_image_freshness |
| L52 | paths.py 改 + compose mount 沒跟上 | paths_compose_mount_audit |
| L53 | 廢 module 沒清父 __init__ | （手動 grep 規範） |

**規則 1**：每個跨檔資源指定 SSOT 位置（9 類分類表）
**規則 2**：每類 SSOT 必有 audit script + fitness step
**規則 3**：runtime healthcheck 必須驗業務量（不只 process up）
**規則 4**：dual-write 必 atomic 或 dual-validation
**規則 5**：跨 repo standard 走 ADR + Registry + Audit 三件套

### 3. 管理機制 — Fitness 3 層分層 forcing

**核心資產**：
- `scripts/checks/run_fitness_daily.sh` — Tier 1 8 step (~1min, cron 02:00)
- `scripts/checks/run_fitness_weekly.sh` — Tier 2 14 step (~3min, cron 週日 02:30)
- `scripts/checks/run_fitness.sh` — Tier 3 64+ step (~10min, manual / monthly)
- `docs/architecture/FITNESS_LAYERED_EXECUTION_SOP_20260530.md`

**借鑑要點**：
- 不要一個檔塞 64 step — owner 不會跑
- 分層讓 daily 跑 critical / weekly 跑 trend / monthly 跑全範圍
- 連 2 週 RED → 推 LINE 強制 owner 排 sprint
- 每個 step 必有 `--strict` mode 給 cron 用

**Daily 8 step 範例**（最 critical）：
1. container env alignment（L51 防禦）
2. container image freshness（L51.7.1 防禦）
3. docker volume consistency（L43 防禦）
4. compose/dockerfile healthcheck（L45 防禦）
5. startup race condition
6. agent_query starvation
7. cron silent dormant
8. dashboard freshness（整合 SSOT 防禦）

### 4. 管理機制 — 整合 SSOT Dashboard 三道防線

**核心資產**：
- `scripts/checks/generate_governance_dashboard.py` — generator
- `docs/architecture/GOVERNANCE_INTEGRATED_DASHBOARD.md` — 10 章節 SSOT 輸出
- `.claude/hooks/session-start.ps1` — session 啟動入口提示
- `scripts/checks/dashboard_freshness_check.py` — fitness step 64
- scheduler `governance_dashboard_regen` job — cron 06:00 自動 regenerate

**借鑑要點 — 治理本身 metric 化**：

三道防線確保 dashboard 永遠真活：

1. **Generator 真活** — cron 06:00 自動 regenerate
2. **入口提示** — session-start hook 自動顯示 dashboard 位置 + freshness
3. **Freshness audit** — fitness daily 偵測 > 48h 未更新 silent dormant

對應「audit 自己的觀測閉環」終極形式：連治理工具自身都被治理。

**dashboard 10 章節**：
1. 規範清單（ADR/lesson/SOP/fitness/architecture）
2. 真活 metric（從 /metrics 即時抓）
3. 進化軌跡（git log -8）
4. session 覆盤（memory/）
5. B 方案 60 天 trial 進度
6. Lesson 索引
7. v6.12 4 原則狀態
8. 漂移看板
9. Owner action 待辦
10. 整合視角結論

### 5. 管理機制 — ADR 30 天 trial 裁判流程

**核心資產**：
- `docs/architecture/FACADE_ABC_DECISION_20260530.md` — A/B/C 決策矩陣
- `wiki/memory/lessons/L53_facade_over_engineering_30day_pruning.md` — 完整案例
- ADR-0036 superseded 標記 SOP

**借鑑要點 — ADR 治理 SOP**（L53 立法）：

```
1. 上線前 估 entities × usage_rate ROI
2. 30 天 audit 真實 usage_rate
3. 60 天 執行裁判（保留 / 升級 / 廢棄）
4. 寫 lesson 入 LESSONS_REGISTRY
```

**ROI 公式**（L31）：
```
ROI = entities × usage_rate
```

ADR-0036 範例：
- 設想 13 facade × ≥3 caller = 39 importer 預期
- 30 天實測：13 × 0.46 = 6（10/13 zero caller）
- B 方案：3 × 2.00 = 6（同 ROI）
- 但 entities -77% → 維護成本大降

「ADR=假設 / audit=裁判 / lesson=傳承」

### 6. 觀測棧 — Prometheus + 治理 metric 化

**核心資產**：
- 7 個 `governance_*` gauge（治理自身真活度）
- `scheduler_job_*` prometheus expose（cron silent dormant 偵測）
- `v7_*` 4 gauge（產品成熟度）
- 17 alert rules / 5 Grafana dashboards / Promtail v2

**借鑑要點 — 治理本身 metric 化**：
- `governance_pipeline_red_consecutive_days` — pipeline 連 RED 天數
- `governance_fitness_report_freshness_hours` — fitness report 新鮮度
- `governance_lessons_total` — lesson 累積數
- `governance_lessons_l4x_family_count` — L4x family 反覆案
- `governance_wiki_pages_total` / `_freshness_hours` — wiki 規模 + 新鮮度

→ 連設計失誤、治理債、知識積累都能 metric 出來。

### 7. 元覆盤 — Daily Self-Retrospective 7 aspects

**核心資產**：
- `scripts/checks/daily_self_retrospective.py` — 7 面向自我覆盤
- scheduler `daily_self_retrospective` job — 每日 06:30 跑 + LINE 推

**7 面向**：
1. ADR vs 現況落差
2. SOP 遵守度
3. 核心服務真活
4. L4x family 反覆模式
5. 學習閉環健康
6. 觀測閉環健康
7. 已建構資產真活

**借鑑要點**：
- 不依賴 owner 主動覆盤
- 每日 cron 自動跑 + 推 LINE
- 失敗即推 owner（forcing function）

### 8. 跨 repo 部署 — install-template-to.sh

**核心資產**：
- `scripts/install-template-to.sh` — 一鍵部署 9 類資產到目標 repo
- `docs/architecture/CROSS_REPO_REFERENCE_GUIDE.md` — FQID 5 類別 + consumer registry
- `consumers.yml` — pull-based 升級通知

**借鑑要點**：
- 不要 git submodule（綁太死）
- 不要 npm/pip package（過度工程）
- 直接 copy + audit drift（最簡單）

**v6.12 新增類別**（本批補完）：
- governance-dashboard（generator + audit + entry）
- cross-file-ssot（SOP + 9 audit script）
- new-lessons-l4x（L41-L53 family 8 條）
- container-defense（L49 family + step 57/58/60）

---

## 對應其他 CK 系列驗收清單

把這份指南當「自查表」：

| 模組 | lvrland | PileMgmt | Showcase | KMapAdvisor |
|---|---|---|---|---|
| 1. 服務層 DDD | ? | ? | ? | ? |
| 2. paths.py + cross-file SSOT | ? | ? | ? | ? |
| 3. Fitness 3 層 | ? | ? | ? | ? |
| 4. 整合 SSOT Dashboard | ? | ? | ? | ? |
| 5. ADR 30 天 trial 流程 | ? | ? | ? | ? |
| 6. 治理 metric 化 | ? | ? | ? | ? |
| 7. 元覆盤 cron | ? | ? | ? | ? |
| 8. install-template 接受方 | ? | ? | ? | ? |

→ 子專案 owner 自填，CK_Missive 提供範本 + audit 工具

---

## 跨 repo drift 偵測（待做）

下批新增 `scripts/checks/cross_repo_template_drift_audit.py`：
- 掃 ../CK_lvrland_Webmap / ../CK_PileMgmt / ... 目標 repo
- 對比 CK_Missive 範本資產（fitness / lesson / SOP / dashboard）
- 漂移 > 30 天 → RED + LINE 提示

→ 讓「對外參考」也走 audit 而非靠人記。

---

## 用法

### 立即部署（給其他 CK 系列）

```bash
# 全部 9 類資產
bash scripts/install-template-to.sh ../CK_lvrland_Webmap

# 只裝 fitness + cross-file-ssot
bash scripts/install-template-to.sh ../CK_PileMgmt --include=fitness,cross-file-ssot

# 預覽不執行
bash scripts/install-template-to.sh ../CK_Showcase --dry-run
```

### 持續更新

範本資產更新時，目標 repo 走 pull-based notify：
- `notify_consumers.py` 自動發 GitHub issue 給 listed consumer
- `consumers.yml` 註冊感興趣的 repo

---

## 核心精神

> **抽象不是錯，建後不 audit 才是。**
> **觀測不是奢侈，自治理就是。**
> **規範散落是必然，整合 SSOT 是責任。**
> **修法不可逆，60 天 trial 是保險。**

ADR=假設 / audit=裁判 / lesson=傳承 — 三位一體治理迴圈。

---

> **下批延伸**：cross_repo_template_drift_audit 落地後，本指南本身也被 audit。
> 對應 owner 訴求：「規範與現況真活 + 自我檢核進化 + 整合效應」。
