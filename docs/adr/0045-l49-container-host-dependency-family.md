# ADR-0045: L49 Container Host Dependency Family — 環境切換 SSOT 治理

> **狀態**: accepted
> **日期**: 2026-05-28
> **決策者**: @bluefishs（OA-3 PM2 廢除 5/27 → 5/28 連環事故修法）
> **接通完整度**: L2（程式碼接通 + fitness step 52/53 自動驗證 + admin smoke test）
> **關聯**: ADR-0028 錯誤合約 / ADR-0036 Bounded Context Contract Layer / ADR-0043 跨 repo network standard / ADR-0044 single SSOT volumes

---

## 背景

2026-05-27 19:04 OA-3 PM2 廢除階段 2-3 完成（commit `ed81bf87`），業務 backend / frontend 從 PM2 native 改 docker container。**3 小時內 owner 連環報 4 個業務頁面故障**：

1. `admin/backup` 顯示「Docker 環境不可用」
2. `files/storage-info` HTTP 500
3. `files/1263/download` HTTP 404
4. `admin/backup` 顯示 0 紀錄 + 「資料載入失敗」

每個看似獨立 bug，深入分析揭發 **L49 family — 5 個獨立但同根反模式**：

| 案 | 表面症狀 | 根因 |
|---|---|---|
| L49.1 | "Docker 環境不可用" | container 無 docker CLI（PM2 native 時 host 內建）|
| L49.2 | storage-info 500 | `rglob('*')` 遇 Windows mount 長中文檔名 OSError 中斷 |
| L49.3 | files download 404 | DB 內 `file_path = '2026\05\xxx'` Windows backslash 進 Linux container `os.path.exists` 必 false |
| L49.4 | backup 0 紀錄 | compose mount target（`./backend/backups:/backups`）與 service 內部 `self.project_root` Path() 計算不對齊 |
| L49.5 | backup/list 31.5s ReadTimeout | 8 個 attachment dir × ~4s rglob 全掃，frontend timeout 顯示「載入失敗」|

**核心問題**：L41-L48 family 立法（cross-file-ssot-governance.md）已覆蓋跨檔/跨 repo 資源 SSOT，但**沒覆蓋「環境切換」這條垂直破口** —— 隱式依賴在原環境（PM2 native Windows）可用、新環境（docker Linux container）失效。

owner 質疑：「為何那麼多覆盤經驗與優化程序還搞錯」。答覆即此 ADR 立法的本質 — meta-pattern 升級必須跟上實際遷移情境。

---

## 決策

確立**環境切換 SSOT 治理三件套**，補足 L41-L48 family 未覆蓋的垂直破口：

### 一、立法（rule）

任何「環境切換」類部署（PM2 → docker / Windows → Linux / 主機 → cloud）**強制走以下 SOP**：

1. **隱式依賴 audit** — 預先 scan host-bound deps（docker CLI / 特定 OS 路徑分隔符 / host-installed binaries）
2. **In-container business endpoint smoke** — 不能只驗 process up / 4 層自動重啟，必須跑業務 endpoint 自動化驗收
3. **Mount target ↔ service Path() 對齊** — compose mount 目標路徑與 service 內部計算的 `Path()` 必須對齊（SSOT）
4. **Cross-platform path normalization** — DB 內任何路徑字串都假設可能是 Windows backslash，讀取前過 SSOT helper

### 二、Audit（enforce）

**Fitness step 52** `container_host_dependency_audit.py`：
- **RED**: `subprocess.run(['docker', ...])` / `shutil.which('docker')` / `/var/run/docker.sock`
- **YELLOW**: `rglob('*')` 無 OSError 容錯 / `attachment.file_path` 未過 normalize helper

**Fitness step 53** `tender_subscription_watchdog_audit.py`（L48 family 同型擴展）：
- 偵測 Prometheus counter 24h 無 increment → silent dormant 警訊

**In-container smoke test 範本** `scripts/checks/admin_backup_smoke_test.py`：
- 從 DB 撈 admin user → user_sessions 找/插 active jti → settings.SECRET_KEY 簽合法 JWT → 帶 1.2s 間隔避 rate limit → 逐打 10 個關鍵 endpoint → 對照 expected status + 業務 validator

### 三、SSOT helper（implementation）

**`files/common.py:resolve_attachment_path(stored_path)`**：
- 自動 `\\` → `os.sep`
- 自動 join `UPLOAD_BASE_DIR`
- 所有 download/management/pm/taoyuan/documents/indexer 散戶就地收口

**`backup/attachment_backup.py:_safe_rglob(root)`**：
- OSError-tolerant generator
- 跳過個別壞 entry 不中斷主流程
- 共用於 attachment_backup + remote_syncer

---

## 後果

### 正面

- ✅ **5 個 silent regression 全部修復** + L49 family meta-pattern 立法
- ✅ **跨 repo 範本擴散**：3 個 audit + 2 個 lesson 同步進 ck-modular-toolkit
- ✅ **自動化驗收取代人工 F5**：admin_backup_smoke_test 10 endpoint 10/10 PASS
- ✅ **性能改善**：backup/list 31.5s → 0.06s（提升 525x）
- ✅ **OA-3 SOP 補丁**：Test 4 業務 endpoint smoke 強制（避免下次同型）
- ✅ **fitness 51 → 53 step**（+ step 52 container_host_dep + step 53 subscription_watchdog）

### 負面 / Trade-off

- backend image size 增加 ~30 MB（postgresql-client）— 可接受
- 既有 backup attachment listing size 從精確改顯示「—」（前端 UX 微降，性能淨提升大）
- audit regex 升級需 maintain whitelist（5/28 已加 docstring + resolve_attachment_path 識別）

### 跨 repo 影響

- **CK_lvrland_Webmap**：仿照 docker 化遷移時可 install toolkit 範本即得防禦
- **CK_PileMgmt**：PM2 → docker 遷移時同上
- **CK_Showcase**：ADR-0020 Phase 2 遷 AaaP 時必走此 SOP

---

## Refs

- **Commits**（v6.11 / 2026-05-27 → 28）：
  - `28df958d` fix(backup): l49 docker CLI → pg_dump 直連
  - `27efffc7` fix(files): l49 cross-platform file_path + osferror
  - `2ef95477` fix(frontend): l49 csrf single-flight + header self-heal
  - `8cdc03d2` feat(checks): step 52 container_host_dependency_audit
  - `d6e97294` fix(backup): l49.2 align mount paths to project-root
  - `8a75a22d` perf(backup): l49.3 list_backups 31.5s → 0.06s + smoke test
  - `7e47fc19` docs(lessons): l49 container host dependency family
  - `673c9644` fix(backup): l49 family yellow sweep 21→0
  - `b9a94715` docs(v6.11): claude.md + pm2 sop l49 完整收尾

- **文件**：
  - Lesson: `wiki/memory/lessons/L49_container_host_dependency_family.md`
  - Registry: `docs/architecture/LESSONS_REGISTRY.md#L49`
  - SOP: `docs/runbooks/pm2-deprecation-sop.md`（Test 4 業務 endpoint smoke）

- **Audit / Smoke test**：
  - `scripts/checks/container_host_dependency_audit.py` (step 52)
  - `scripts/checks/tender_subscription_watchdog_audit.py` (step 53)
  - `scripts/checks/admin_backup_smoke_test.py` (in-container 自動化驗收範本)

- **Toolkit 範本擴散**：
  - `shared-modules/ck-modular-toolkit/checks/container_host_dependency_audit.py`
  - `shared-modules/ck-modular-toolkit/lessons/L49_container_host_dependency_family.md`

- **同類 lessons**：[[L37]] 平時保險反模式 / [[L41]] 跨環境 secret drift / [[L43]] volume mount drift / [[L45]] healthcheck override / [[L48]] cron silent dormant

---

## 維護

- 環境切換類 deployment：強制走 Test 4 業務 endpoint smoke
- 每月 fitness 跑 step 52 / step 53 確認 GREEN
- 跨 repo PM2 → docker 遷移：install ck-modular-toolkit 範本即得整套防禦
