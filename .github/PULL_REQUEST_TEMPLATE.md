## 變更類型

- [ ] feat — 新功能
- [ ] fix — bug 修復
- [ ] refactor — 重構（行為不變）
- [ ] docs — 文件
- [ ] test — 測試
- [ ] chore — 雜務 / 依賴 / 配置
- [ ] **範本貢獻**（template contribution from consumer repo）

---

## 一般 PR

### 變更摘要

<!-- 1-3 句說明這個 PR 做了什麼、為什麼 -->

### Refs

<!-- 引用 LESSONS_REGISTRY 的 L## -->
- Refs: L##

<!-- 若涉及範本資產，加 FQID -->
- Asset FQID: `CK_Missive#XXX_vY.Z`

### 驗證

- [ ] `cd backend && pytest tests/ -q --tb=no` 0 regression
- [ ] `cd frontend && npx tsc --noEmit` 0 errors
- [ ] `bash scripts/checks/run_fitness.sh` 全綠
- [ ] 若改 service 結構：`python scripts/checks/service_dir_entropy.py` 通過
- [ ] 若改 yaml config：`python scripts/checks/config_dead_reader_scan.py` 通過

---

## 範本貢獻 PR（適用：consumer repo 改良範本）

> 此段僅當勾選「**範本貢獻**」時填寫。
> 詳見 `docs/architecture/CROSS_REPO_REFERENCE_GUIDE.md` §5 貢獻回流規範。

### Source Asset FQID

<!-- 範例：CK_Missive#dead_ui_detector_v1.0 -->
- **From**: `CK_Missive#XXX_vY.Z`
- **Proposed bump**: vY.Z → v?.?
  - [ ] Patch（bug fix，向後相容）
  - [ ] Minor（加新功能，向後相容）
  - [ ] **Major（Breaking change，引用方需 review）**

### Consumer Repo

<!-- 在哪個 repo 先發現/驗證這個改良 -->
- Repo: `CK_<RepoName>`
- 在該 repo 的 commit hash: `<sha>`

### 改良動機

<!-- 為什麼需要這個改良？解決什麼 anti-pattern / lesson？ -->

### 在 Consumer 端的驗證

<!-- 證據：跑了什麼測試 / fitness / 實際使用觀察 -->

### 適用範圍評估

<!-- 是否所有 consumer 都受惠？或只特定情境？ -->

- [ ] 全部 consumer 受惠（建議直接 merge）
- [ ] 部分 consumer 受惠（需考慮加 opt-in flag）
- [ ] 僅 consumer-specific（不該回流，請改在 consumer repo 客製）

### Breaking Change 影響

<!-- 若 Major bump，列出已知影響 + 升級 guide -->

- 影響的 consumer：
- 升級指南：

### Note for consumers

<!-- 此段會抄進 CHANGELOG，consumer 月度健檢時看得到 -->

---

## 跨 repo 引用紀律

- [ ] 引用 ADR 用 FQID（`CK_Missive#0028`）非裸編號
- [ ] 引用 lesson 用 `CK_Missive#L##`
- [ ] 引用範本用 `CK_Missive#NAME_vX.Y`
- [ ] commit message 末尾有 `Refs: L##`

---

> PR 模板自身 FQID: `CK_Missive#PULL_REQUEST_TEMPLATE_v1.0`
