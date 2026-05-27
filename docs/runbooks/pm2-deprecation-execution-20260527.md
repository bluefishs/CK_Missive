# OA-3 PM2 廢除 — Owner 一鍵執行清單（2026-05-27 pre-flight 通過）

> **基於**：[`pm2-deprecation-sop.md`](pm2-deprecation-sop.md) v1.0
> **Pre-flight 完成**：2026-05-27 18:35（claude assistant）
> **狀態**：✅ 大部分 ready / ⚠️ 2 項待補（見下）/ 🔴 1 destructive 等 owner 親手
> **預估 owner 時間**：3-4h（含開機驗收等待）

---

## ⚠️ Pre-flight 揭發的 2 個待補項（owner 開工前必做）

### 待補 1 — Task Scheduler `CK_Missive_AutoStart` 未匯入（Layer 3 critical）

```powershell
schtasks /Create /TN "CK_Missive_AutoStart" /XML "D:\CKProject\CK_Missive\scripts\deploy\task-scheduler-autostart.xml" /F
```

**驗證**：
```powershell
schtasks /Query /TN "CK_Missive_AutoStart" /FO LIST | Select-Object -First 8
# 預期：見到 TaskName / Status: Ready
```

### 待補 2 — DB 最新 backup 是 5/21（6 天前）— 建議新增 fresh dump

```powershell
# 跑 fresh 備份（同 pre_upgrade_backup.sh 邏輯）
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$out = "D:\CKProject\CK_Missive\backups\database\ck_missive_pre_pm2_deprecation_$ts.sql"
docker exec ck_missive_postgres pg_dump -U ck_user -d ck_documents -F p -f /tmp/dump.sql
docker cp ck_missive_postgres:/tmp/dump.sql $out
docker exec ck_missive_postgres rm /tmp/dump.sql
Get-Item $out | Select-Object Name, Length, LastWriteTime
# 預期：ck_missive_pre_pm2_deprecation_*.sql ~77MB
```

---

## Pre-flight ✅ 已通過項目（不需 owner 動作）

| 項目 | 狀態 | 證據 |
|---|---|---|
| docker container `ck_missive_backend` healthy | ✅ Up 3h+ | image=`ck-missive-backend:production`, restart=always |
| Container `/health` biz_ok | ✅ True | docs=1799, kg=24247, pool=1/15 healthy, overflow=0 |
| Docker Desktop AutoStart | ✅ True | settings-store.json `AutoStart=True` |
| docker-compose restart policy | ✅ 5/5 | postgres/redis/backend/frontend `restart: always` + adminer `unless-stopped` |
| cloudflared restart policy（3 container）| ✅ 3/3 | `ck_missive_cloudflared` / `pile-cloudflared` / `ck-tunnel-cloudflared` 全 `unless-stopped` |
| Task Scheduler XML 檔 | ✅ 落地 | `scripts/deploy/task-scheduler-autostart.xml` 存在 |
| NAS 異地備份 | ✅ 存在 | `Z:\#systembackup\CK_Missive_INCIDENT_20260521_volume_mount_drift` |
| ecosystem.config.js 有 ck-backend/frontend 條目 | ✅ Line 34/90 | 待階段 3.2 刪 |
| PM2 ck-backend / ck-frontend 運行中 | ✅ 3h online | PID 19788 / 19844 |

---

## 階段 1 — 前置紀錄（owner 5 min）

```powershell
# 1.1 記錄當前 PM2 配置（為 rollback 預備）
pm2 list > $env:USERPROFILE\Desktop\pm2-list-before-deprecation.txt
pm2 describe ck-backend > $env:USERPROFILE\Desktop\pm2-ck-backend-config.txt
pm2 describe ck-frontend > $env:USERPROFILE\Desktop\pm2-ck-frontend-config.txt
ls $env:USERPROFILE\Desktop\pm2-*.txt
# 預期：3 個 txt 落地桌面
```

---

## 階段 2 — Docker 接管驗證（dry-run，owner 親手，15 min）

### 2.1 ⚠️ DESTRUCTIVE — 暫停 PM2（可逆）

```powershell
pm2 stop ck-backend ck-frontend
pm2 list | findstr -i "ck-backend\|ck-frontend"
# 預期：status=stopped
```

### 2.2 驗證 docker 接管（30 秒緩衝）

```powershell
Start-Sleep -Seconds 30

# Layer 1: localhost docker
curl http://localhost:8001/health
# 預期：200 + biz_ok=true

# Layer 2: 公網
curl https://missive.cksurvey.tw/health
# 預期：200 + biz_ok=true
#       注意：可能仍命中 PM2 stopped socket，等 1-2 min 再試
```

### 2.3 GO / NO-GO 判斷

- **若兩個 200 + biz_ok=true** → 繼續階段 3
- **若 Layer 2 失敗** → **立即回退**：
  ```powershell
  pm2 start ck-backend ck-frontend
  Start-Sleep -Seconds 30
  curl https://missive.cksurvey.tw/health
  ```
  並停止 OA-3，寫 `wiki/memory/failures/failure-pm2-deprecation-attempt-20260527.md`

---

## 階段 3 — 正式廢除 + 配置（owner 親手，30 min）

⚠️ **以下為 destructive 不可逆操作**（除非 pm2 重建 + ecosystem 還原）

### 3.1 🔴 DESTRUCTIVE — 刪除 PM2 entries

```powershell
pm2 delete ck-backend ck-frontend
pm2 save
pm2 list
# 預期：list 中無 ck-backend / ck-frontend，但保留：
#   ck-showcase-backend / ck-showcase-frontend / ck-tunnel-frontend / ck-sso-health
```

### 3.2 修 ecosystem.config.js（刪 2 個 entries）

```powershell
# 用編輯器打開 D:\CKProject\CK_Missive\ecosystem.config.js
# 刪除 apps 陣列中的：
#   { name: 'ck-backend', ... }       (line 34 附近)
#   { name: 'ck-frontend', ... }      (line 90 附近)
#
# Git diff 應該只有兩個物件被移除
git diff ecosystem.config.js
```

### 3.3 cloudflared restart policy（已 ready，可跳過）

```powershell
# Pre-flight 已確認 3 個 cloudflared 全 unless-stopped
# 此步驟僅作驗證
foreach ($n in @("ck_missive_cloudflared", "pile-cloudflared", "ck-tunnel-cloudflared")) {
    $p = docker inspect $n --format '{{.HostConfig.RestartPolicy.Name}}'
    Write-Host "$n : $p"
}
# 預期：3 個 unless-stopped
```

---

## 階段 4 — 開機自動重啟驗收（owner，45 min）

### 4.1 Layer 3 Task Scheduler 匯入（5 min）

```powershell
# 待補 1 命令（若 pre-flight 已跑可跳過）
schtasks /Create /TN "CK_Missive_AutoStart" /XML "D:\CKProject\CK_Missive\scripts\deploy\task-scheduler-autostart.xml" /F

# 測試（不重開機）
schtasks /Run /TN "CK_Missive_AutoStart"
Start-Sleep -Seconds 60
docker ps --filter "name=ck_missive_backend"
# 預期：container 仍 healthy（或 reload）
```

### 4.2 Test 1: 完整重啟（**必過**，30 min）

> ⚠️ 預留 30 min — 包含關機重啟 + 等 Docker Desktop init + 外部設備測試

```
1. 關機（Shutdown，不只 Restart）
2. 開機後 NOT 登入系統（測 BootTrigger 是否在 SYSTEM 帳號下也跑）
3. 等 5 min
4. 從外部設備（手機 4G / 同事電腦 / iPad）開 https://missive.cksurvey.tw/health
   預期：200 + business_data.ok=true
5. 登入桌面，跑驗證命令：
   docker ps --filter "name=ck_missive_backend"
   curl http://localhost:8001/health
   curl https://missive.cksurvey.tw/health
```

### 4.3 Test 2: Container 重啟（必過，2 min）

```powershell
docker kill ck_missive_backend
Start-Sleep -Seconds 30
docker ps --filter "name=ck_missive_backend"
# 預期：自動拉起，healthy
```

### 4.4 Test 3: Layer 4 Health Watchdog（建議過，5 min）

```powershell
# 若還沒建立：
schtasks /Create /TN "CK_Missive_HealthWatchdog" `
  /TR "bash D:\CKProject\CK_Missive\scripts\health\health-watchdog.sh" `
  /SC MINUTE /MO 2 /F

# 確認運行
schtasks /Query /TN "CK_Missive_HealthWatchdog"
```

---

## 完成定義（Done Criteria）

- [ ] `pm2 list` 中無 ck-backend / ck-frontend
- [ ] `ecosystem.config.js` 已移除對應 apps（git diff 驗證）
- [ ] docker-compose 5 services 全 `restart: always` 或 `unless-stopped` ✅ pre-flight 已驗
- [ ] 3 cloudflared `restart=unless-stopped` ✅ pre-flight 已驗
- [ ] Docker Desktop AutoStart=True ✅ pre-flight 已驗
- [ ] Task Scheduler `CK_Missive_AutoStart` 啟用且測過
- [ ] Test 1（外部設備測公網）過
- [ ] Test 2（docker kill 自動重啟）過
- [ ] Test 3（Health Watchdog） — 建議過
- [ ] 寫入 `wiki/memory/diary/2026-05-27.md` 記錄
- [ ] **owner 體感確認**：訪問 https://missive.cksurvey.tw/ 操作核心業務功能流暢

---

## 回退步驟（任一階段失敗）

```powershell
# 1. 恢復 PM2
pm2 start ck-backend --env production
pm2 start ck-frontend
pm2 save

# 2. 驗證
curl https://missive.cksurvey.tw/health
# 若恢復 200 → rollback 完成
# 若仍失敗 → 從 backups\database\ck_missive_pre_pm2_deprecation_*.sql restore

# 3. 寫事故紀錄
wiki\memory\failures\failure-pm2-deprecation-attempt-<date>.md
```

---

## 後續工作（owner 完成 OA-3 後）

1. **MEMORY.md 更新**：Project line 補 PM2 廢除完成，刪除 P0-3
2. **CLAUDE.md / .claude/rules**：移除 PM2 ck-backend / ck-frontend 相關引用
3. **step 49 重跑**：確認 synthetic_baseline 從 🔴 RED → 🟢 GREEN（搭配 OA-1 docker MCP_SERVICE_TOKEN env）
4. **step 51 重跑**：tender freshness 跑出 PCC 新筆數 < 3 天
5. **寫 ADR-0047 / 合併 ADR-0017 Phase 1C**：PM2 廢除事後文件
6. **scripts/dev/dev-start.ps1**：移除 PM2 模式，改純 docker

---

## 已知陷阱（per SOP §已知陷阱）

1. **Cloudflare Tunnel connection slot 釋放慢**：PM2 stop 後 cloudflared 可能仍命中 stale connection 1-2 min — 階段 2.2 必須耐心等
2. **Docker Desktop 啟動延遲**：開機後 30-60s 才完成 init — Task Scheduler 加 30s delay 是必要
3. **User 未登入時 Docker Desktop 可能不啟動**：BootTrigger + RunLevel HighestAvailable + UserId S-1-5-18 三項必對（XML 已配，但 Layer 1 Docker Desktop 端有時需登入觸發）→ Test 1 必須做
4. **`docker compose up -d` 沒換新 image**：開機自動拉起的是已 build 的 image — 未來 deploy 仍需手動 `--build`

---

## 結尾備註

本清單將 SOP v1.0 + 本次 pre-flight 結果 + 待補項合一。Owner 可直接從「待補項」開始，順序按階段 1→4 推進。每步前後皆有驗證命令，destructive 步驟（pm2 stop / delete）標 ⚠️ / 🔴。

> **核心精神**：PM2 廢除完成後，整套 audit 紅燈才有意義。在那之前所有 fitness / Prometheus 看到的都是 docker 接收 0 流量後的「假象世界」。
