# Docker Desktop 升級 SOP — 不可發生資料遺失

> **建立日期**：2026-05-19（觸發事件：發現 CK_Missive 全用 named volume + Task Scheduler 不在 + 5/16 後 cron 漏跑）
> **狀態**：accepted（升級前必走）
> **強制等級**：升級 Docker Desktop / WSL2 / 切換 backend 前必執行 §3 完整 checklist
> **災難情境**：Named volume 在 Docker Desktop reset / WSL distro unregister / Hyper-V↔WSL2 切換時**完全清空** → 1698 docs + 22k KG entities + 117k mentions + 891 Redis keys 全失

---

## §0 風險矩陣

| 升級動作 | volume 清空風險 | 預估復原時間（無備份） |
|---|---|---|
| Docker Desktop minor 升級（4.x→4.x.y） | 低 | 0h |
| Docker Desktop major 升級（4.x→5.x） | 中 | **不可復原**（無備份時資料永失） |
| WSL2 backend reset / 重裝 | **高** | 不可復原 |
| Hyper-V ↔ WSL2 backend 切換 | **高** | 不可復原 |
| Factory Reset 按鈕 | **必清** | 不可復原 |
| `wsl --unregister docker-desktop-data` | **必清** | 不可復原 |

---

## §1 平時保險（每日自動跑）

### §1.1 重建 Windows Task Scheduler 排程（必做）

5/19 發現現有 Task Scheduler 無 `CK_Missive_Daily_Backup` 任務（5/16 後完全沒跑）。需以 **Administrator** 身分重建：

```powershell
# 在 Administrator PowerShell 跑
cd D:\CKProject\CK_Missive
powershell -ExecutionPolicy Bypass -File scripts\backup\setup_scheduled_task.ps1 -BackupTime "02:00" -RetentionDays 14
```

驗證：
```powershell
Get-ScheduledTask -TaskName "CK_Missive_Daily_Backup" | Get-ScheduledTaskInfo
# LastRunTime / NextRunTime 應出現
```

### §1.2 啟用異地同步

修 `backend/config/remote_backup.json`：

```json
{
  "remote_path": "Z:\\03.專案管控專區\\00.公司公文紀錄\\#systembackup",
  "sync_enabled": true,     // ← 改 true（v6.10 P1 前是 false 14 天）
  "sync_interval_hours": 24,
  "last_sync_time": "...",
  "sync_status": "idle"
}
```

### §1.3 結構性升級：named volume → bind mount

**最徹底的保險**。改 `docker-compose.infra.yml`：

```yaml
# ❌ 現況（high-risk — Docker Desktop reset 會清）
services:
  postgres:
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data  # named volume
volumes:
  postgres_dev_data:
    name: ${COMPOSE_PROJECT_NAME}_postgres_dev_data

# ✅ 目標（host bind mount — Docker Desktop reset 不影響）
services:
  postgres:
    volumes:
      - ./.data/postgres:/var/lib/postgresql/data  # bind mount to host
```

**遷移步驟**（停機 ~5min）：

```bash
# 1. 備份（必跑）
bash scripts/backup/pre_upgrade_backup.sh

# 2. 停容器
docker compose -f docker-compose.infra.yml down

# 3. 把 named volume 內容 copy 到 host
mkdir -p .data/postgres .data/redis
docker run --rm \
    -v ck_missive_postgres_dev_data:/from \
    -v //d/CKProject/CK_Missive/.data/postgres:/to \
    alpine sh -c "cd /from && cp -av . /to"
docker run --rm \
    -v ck_missive_redis_dev_data:/from \
    -v //d/CKProject/CK_Missive/.data/redis:/to \
    alpine sh -c "cd /from && cp -av . /to"

# 4. 編輯 docker-compose.infra.yml 改 bind mount
# 5. 重啟
docker compose -f docker-compose.infra.yml up -d

# 6. 驗證
docker exec ck_missive_postgres_dev psql -U ck_user -d ck_documents -c "SELECT COUNT(*) FROM official_documents;"
# 應顯示 1698
```

**為何 bind mount 比 named volume 安全**：
- bind mount 資料直接在 host filesystem（`D:/CKProject/CK_Missive/.data/`）
- Docker Desktop reset / WSL unregister 不會碰 host filesystem
- 可直接 `7zip` / `robocopy` 備份（不需 docker）
- 跨機器搬遷只需 copy 目錄

**代價**：
- Windows + WSL2 + bind mount + PostgreSQL 在某些版本有 I/O 效能折損（5-15%）
- 但 5/19 測試 79MB pg_dump < 5s，對開發環境無感

---

## §2 升級前 24h 完整 checklist

升級 Docker Desktop / WSL 任何重大變更前，**24 小時內**走完：

- [ ] **L1 健康度確認**：`docker compose ps` 全 healthy，無 unhealthy / Created (failed)
- [ ] **L2 跑緊急備份**：`bash scripts/backup/pre_upgrade_backup.sh`
  - 確認 6 個產出檔（PG dump + PG sql.gz + Redis rdb + 2 volume tar + NAS 同步）
  - 檔案 size 合理（PG dump ≥ 50MB / Redis rdb ≥ 100KB）
- [ ] **L3 NAS 異地同步驗證**：`ls -lh "Z:/03.專案管控專區/.../CK_Missive_PREUPGRADE_<DATE>/"` 確認 5 檔在
- [ ] **L4 restore drill**（每月 1 次）：在 staging 環境跑 `bash scripts/backup/restore_from_volume_tar.sh latest`，確認可 restore
- [ ] **L5 記錄當前版本**：
  ```bash
  docker version > .data/version_before_upgrade.txt
  docker compose version >> .data/version_before_upgrade.txt
  wsl --version >> .data/version_before_upgrade.txt 2>&1
  ```
- [ ] **L6 業務 hot data 確認**：開啟 frontend，建一個 test document，記住 doc_number，升級後驗證仍在
- [ ] **L7 export critical configs**：`.env` + `configs/*.yml` + `backend/config/*.yaml` 拷到 `.data/configs_backup_<TS>/`
- [ ] **L8 暫停寫入**：考慮 `pm2 stop ck-backend` 讓資料庫進入靜止狀態（restore 才確定一致）

---

## §3 升級中監控

升級 Docker Desktop 時：

- [ ] **不要按 "Reset to factory defaults"**（這會清所有 named volume）
- [ ] 升級過程若 popup 「需 reset WSL distro」**取消**，先評估能否保留 volume
- [ ] 若 popup 必須 reset，**先按取消 + 跑 §1.1-§1.3 完整保險**再回來
- [ ] 升級進度條卡住 > 10min 時**不要強關**（強關 = 部分寫入 = volume 損壞）

---

## §4 升級後驗證

```bash
# 1. 確認 volume 仍在
docker volume ls | grep ck_missive
# 應看到 ck_missive_postgres_dev_data + ck_missive_redis_dev_data

# 2. 啟動服務
docker compose -f docker-compose.infra.yml up -d

# 3. 等待 healthy（最多 30s）
sleep 30 && docker compose -f docker-compose.infra.yml ps

# 4. 業務資料驗證
docker exec ck_missive_postgres_dev psql -U ck_user -d ck_documents -c "
SELECT
  (SELECT COUNT(*) FROM official_documents) AS docs,
  (SELECT COUNT(*) FROM users) AS users,
  (SELECT COUNT(*) FROM canonical_entities) AS kg_entities;
"
# 預期：docs ≥ 1698, users > 0, kg_entities > 22000

# 5. Redis 鍵數
docker exec ck_missive_redis_dev redis-cli DBSIZE
# 預期：> 800

# 6. Backend 啟動
pm2 start ck-backend
sleep 5 && curl -s http://localhost:8001/health | head -5

# 7. 跑 fitness smoke
bash scripts/checks/run_fitness.sh 2>&1 | tail -20
```

---

## §5 災難復原 — Volume 已消失

若升級後 `docker volume ls` **看不到** `ck_missive_postgres_dev_data`：

### §5.1 從 volume tar 還原（推薦，bit-perfect）

```bash
bash scripts/backup/restore_from_volume_tar.sh latest
docker compose -f docker-compose.infra.yml up -d
```

### §5.2 從 pg_dump 還原（次選，需重建 schema）

```bash
docker compose -f docker-compose.infra.yml up -d postgres
sleep 10

# 確認 DB exists
docker exec ck_missive_postgres_dev psql -U ck_user -lqt | grep ck_documents

# Custom format restore
docker cp backups/database/ck_missive_PREUPGRADE_<TS>.dump ck_missive_postgres_dev:/tmp/restore.dump
docker exec ck_missive_postgres_dev pg_restore -U ck_user -d ck_documents -c /tmp/restore.dump

# 或 plain SQL restore
gunzip -c backups/database/ck_missive_PREUPGRADE_<TS>.sql.gz | \
    docker exec -i ck_missive_postgres_dev psql -U ck_user -d ck_documents
```

### §5.3 從 NAS 還原（本機備份失效時）

```bash
# 從 NAS 拉回最新 pre-upgrade
cp "Z:/03.專案管控專區/00.公司公文紀錄/#systembackup/CK_Missive_PREUPGRADE_<DATE>/pg_volume_PREUPGRADE_<TS>.tar.gz" \
   backups/volumes/

bash scripts/backup/restore_from_volume_tar.sh <TS>
```

---

## §6 模型 cache 補回（Ollama / vLLM）

模型 cache 是**重下載**而非 restore：

```bash
# Ollama
docker compose -f docker-compose.infra.yml up -d ollama
docker exec ck_missive_ollama_dev ollama pull gemma:8b-instruct-fp16
docker exec ck_missive_ollama_dev ollama pull nomic-embed-text

# vLLM (Qwen2.5-7B-AWQ)
docker compose -f docker-compose.infra.yml up -d vllm
# 預期 5-10 分鐘下載 model
```

預計下載總時間：1-2 小時（11GB + 5GB ≈ 16GB）。

---

## §7 SOP 違反案例（5/19 揭發）

| 違規 | 證據 | 修正 |
|---|---|---|
| Task Scheduler 排程不在 | `Get-ScheduledTask "*CK_Missive*"` 0 hit | §1.1 重建 |
| 5/17/18/19 三天 PG 備份遺失 | `ls backups/database/` 最新 5/16 | §1.1 重建後自動跑 |
| `sync_enabled: false` 14 天 | `cat backend/config/remote_backup.json` | §1.2 改 true |
| Redis 從未備份 | `find . -name "*.rdb"` 0 hit | `pre_upgrade_backup.sh` 已含 |
| 全用 named volume | `docker-compose.infra.yml` volumes section | §1.3 bind mount 升級 |
| 5/12 0B backup 無人察覺 | `ls -la backups/database/` size 欄 | backup script 加 `[[ -s file ]]` 檢查 + Telegram alert |

---

## §8 與既有規範的關係

| 規範 | 角色 | 關係 |
|---|---|---|
| `scripts/backup/db_backup.sh` | 每日 PG 備份 | 本 SOP §1.1 排程重建依賴此腳本 |
| `scripts/backup/pre_upgrade_backup.sh` | 緊急 4 層保險 | 本 SOP §2 L2 主要工具（**新建**）|
| `scripts/backup/restore_from_volume_tar.sh` | 災難復原 | 本 SOP §5.1 主要工具（**新建**）|
| `backend/config/remote_backup.json` | 異地同步配置 | 本 SOP §1.2 |
| ADR-0028 錯誤合約 | silent failure 政策 | 5/12 0B backup 是同類事故 — backup 失敗不該 silent |
| 適配 LR-015 系列 | 「真活宣告 vs 真接通」反模式 | 本 SOP § 違反案例都是同型問題（排程「應該在」但實際不在）|

---

## §9 變更紀錄

| 日期 | 版本 | 變更 |
|---|---|---|
| 2026-05-19 | v1.0 | 初版 — 觸發事件：發現 named volume + cron 漏跑雙重風險 + 不可發生資料遺失要求 |
