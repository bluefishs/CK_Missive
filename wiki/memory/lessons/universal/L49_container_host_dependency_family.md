---
title: L49 — Container Host Dependency Family (PM2 → Docker 5 重 silent regression)
type: lesson
date: 2026-05-27
fqid: CK_Missive#L49
family: container-host-dependency
related: [L37, L41, L43, L45, L48]
---

# L49 — Container Host Dependency Family

> **日期**：2026-05-27 19:00 → 23:30（~4.5 小時診斷 + 修法）
> **觸發**：OA-3 PM2 廢除階段 2-3 完成後業務頁面連環故障
> **規模**：5 個獨立但同 family 反模式 / 6 commits / 250+ lines fix

---

## 5 案速覽

| 案 | endpoint / 議題 | 表面症狀 | 根因 | commit |
|---|---|---|---|---|
| L49.1 | `admin/backup status` | "Docker 環境不可用" | container 無 `docker` CLI（PM2 native 時 host 內建）| `28df958d` |
| L49.2 | `files/storage-info` | HTTP 500 | `rglob('*')` 遇 Windows mount 長中文檔名 OSError 中斷 | `27efffc7` |
| L49.3 | `files/{id}/download` | HTTP 404 | DB 內 `file_path` Windows `\` 進 Linux container `os.path.exists` 必 false | `27efffc7` |
| L49.4 | `admin/backup` 顯示 0 紀錄 | 「歷史紀錄皆消失」誤判 | compose mount target ≠ service 內部 `self.project_root` path 計算 | `d6e97294` |
| L49.5 | `backup/list` ReadTimeout | 「資料載入失敗」 | 31.5s 慢（8 attachment dir × 4s rglob），frontend axios timeout | `8a75a22d` |

## 為何「平時覆盤經驗多」仍出包

owner 質疑：「為何那麼多覆盤經驗與優化程序還搞錯」。

answer：L41-L48 family 已立法（`cross-file-ssot-governance.md`），但**沒覆蓋「環境切換」這條垂直破口**：

| family 既有規範 | L49 漏洞 |
|---|---|
| L41 跨 repo secret SSOT | 沒處理「host CLI 工具假設」 |
| L43 跨 compose volume SSOT | 沒處理「mount target ↔ service Path() 對齊」 |
| L45 compose vs Dockerfile healthcheck | 沒處理「user-facing endpoint 在 container 真活感」 |
| L48 cron silent dormant | 沒處理「endpoint 200 但業務超時 = silent fail」|

L49 = **這四條規範未覆蓋的「環境切換業務感受層」破口**。

## 治理修法（v6.12 立法）

### 1. Fitness step 52 — Container Host Dependency Audit

`scripts/checks/container_host_dependency_audit.py`：
- **RED**：`subprocess.run(['docker', ...])` / `shutil.which('docker')` / `/var/run/docker.sock`
- **YELLOW**：`rglob('*')` 無 OSError 容錯 / `attachment.file_path` 直接 `os.path.exists`

首跑揭發 23 YELLOW（backup/attachment_backup.py + remote_syncer.py + scheduler.py rglob + documents/delete + ai/document indexer 等散戶）。

### 2. In-container smoke test 範本

`scripts/checks/admin_backup_smoke_test.py`：

從 DB 撈 admin → user_sessions 找/插 active jti → settings.SECRET_KEY 簽合法 JWT → 帶 1.2s 間隔避 rate limit → 逐一打 10 個關鍵 endpoint → 對照 expected status + 業務 validator。

**這是「自我瀏覽器級驗收」範本**，取代人工反覆 F5。其他 repo 環境切換時可 copy 這個模式。

### 3. files/common.py SSOT helper

`resolve_attachment_path(stored_path)` — 任何讀 DB 內 file_path 都過這個 helper：
- 跨平台 `\\` → `os.sep`
- 自動 join UPLOAD_BASE_DIR
- L49 family 整代散戶集中收口

### 4. OA-3 PM2 廢除 SOP 補丁

廢 PM2 / 切 docker 等環境遷移類操作，pre-flight 必加：

```yaml
- name: in-container business endpoint smoke
  required: true
  script: docker exec <backend> python scripts/checks/<repo>_smoke_test.py
  expects: 100% PASS
  覆蓋: admin/* + files/* + auth/me + 排程器狀態
```

純 process up / 4 層自動重啟驗證 **不夠**。

---

## Sealed Knowledge

1. **環境切換的隱式依賴破口無法靠 unit test 攔截** — 因為 unit test mock 掉所有 OS 互動
2. **fitness step 全綠 ≠ 系統真活** — fitness 只測「狀態」，business endpoint smoke 才測「業務感受」
3. **endpoint 200 + 31s ≠ 成功** — 用戶等不到就是失敗（L49.5 揭發）
4. **DB 內存路徑字串必跨平台** — 永遠 normalize 後再用
5. **`rglob` 對 host mount 路徑都要假設可能 OSError** — Windows 長中文檔名 mount 進 Linux 是 chronic 失血源

## 引用

- LESSONS_REGISTRY: `docs/architecture/LESSONS_REGISTRY.md#L49`
- commits: `28df958d` `27efffc7` `2ef95477` `8cdc03d2` `d6e97294` `8a75a22d`
- audit script: `scripts/checks/container_host_dependency_audit.py` (step 52)
- smoke test: `scripts/checks/admin_backup_smoke_test.py`
- 相關 lessons: [[L37]] [[L41]] [[L43]] [[L45]] [[L48]]
