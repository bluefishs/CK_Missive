# Reboot Acceptance Checklist — 4 層自動重啟驗收

> **建立日期**：2026-05-28 (v6.11 OA-3 PM2 廢除完整收尾)
> **目的**：取代「fitness step GREEN = 系統真活」假象，**業務 endpoint smoke 才是 ground truth**

---

## 重啟前 pre-flight check（owner 5 min）

```powershell
# 1. 確認 git 狀態 clean + 已 push
cd D:\CKProject\CK_Missive
git status              # 預期 working tree clean
git log -1 --format=%H  # 記下 HEAD commit hash 供事後核對

# 2. 確認 5 services healthy
docker ps --filter "name=ck_missive" --format "{{.Names}}: {{.Status}}"

# 3. 業務 endpoint smoke（10/10 PASS 才能放心重啟）
docker cp scripts/checks/admin_backup_smoke_test.py ck_missive_backend:/tmp/smoke.py
docker exec ck_missive_backend python /tmp/smoke.py

# 4. 確認 frontend dist 最新
ls -la frontend/dist/index.html
# 預期 mtime 對應最後 npm run build
```

---

## 4 層自動重啟確認狀態

| Layer | 機制 | 確認命令 | 5/28 狀態 |
|---|---|---|---|
| L1 | Docker Desktop autostart | `Get-ItemProperty HKCU:\Software\Microsoft\Windows\CurrentVersion\Run` | ✓ |
| L2 | compose `restart: always` × 4 + `unless-stopped` × 1 | `grep restart docker-compose.production.yml` | ✓ |
| L3 | cloudflared `restart=unless-stopped` | `docker inspect ck-tunnel-cloudflared` | ✓ |
| L4 | Task Scheduler `\CK_Missive\AutoStart` | `schtasks /Query /TN "\CK_Missive\AutoStart"` | 待 elevated 重建 |

**L4 復原命令**（owner elevated PowerShell 任何時候可跑，覆寫既有）：

```powershell
$trigger = New-ScheduledTaskTrigger -AtStartup
$trigger.Delay = "PT30S"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument '-ExecutionPolicy Bypass -NoProfile -Command "Start-Sleep 60; Set-Location ''D:\CKProject\CK_Missive''; docker compose -f docker-compose.production.yml up -d 2>&1 | Tee-Object ''D:\CKProject\CK_Missive\backups\autostart.log''"' -WorkingDirectory "D:\CKProject\CK_Missive"
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
$timeLimit = New-TimeSpan -Minutes 15
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable -ExecutionTimeLimit $timeLimit
Register-ScheduledTask -TaskPath "\CK_Missive\" -TaskName "AutoStart" -Trigger $trigger -Action $action -Principal $principal -Settings $settings -Description "CK_Missive Layer 4" -Force
Get-ScheduledTask -TaskPath "\CK_Missive\" -TaskName "AutoStart"
```

> **重要**：L1+L2+L3 已足夠 99% 場景。L4 是「萬一 Docker Desktop 自啟失敗」的 backup safety net。
> 即使 L4 暫未 ready，**不阻塞重啟驗證**。

---

## 重啟動作

1. **Save all work** —— git 已 clean + push 完畢
2. **Windows 開始 → 電源 → 重新啟動**
3. **不要登入** —— L1 開機自啟 Docker Desktop，不需 user login（L1 設在 HKCU 但 Windows 登入 Docker Desktop 才會啟動）

   **Wait** — HKCU = HKEY_CURRENT_USER → 必須 login 該 user 才會 trigger autostart。
   實際上 owner 需要登入 User1 才會啟動 Docker Desktop。

   調整：**重啟 + 登入 User1**（自動啟動 Docker Desktop）

---

## 重啟後驗收 Test 1（建議 owner 等 5 分鐘讓服務全起）

```powershell
# Step 1: 等待 90 秒讓 Docker Desktop + container 全起
# (Docker Desktop ~30s 啟動 + compose 拉 container ~30s + healthcheck ~30s)
Start-Sleep -Seconds 90

# Step 2: 確認 5 services
docker ps --filter "name=ck_missive" --format "{{.Names}}: {{.Status}}"
# 預期：5 個 services 都 Up + healthy

# Step 3: 業務 endpoint 真活
curl -sS http://localhost:8001/health | ConvertFrom-Json | Select-Object status, environment, business_data, pool
# 預期：status=healthy, environment=production, business_data.ok=true

# Step 4: 公網真活
curl -sS https://missive.cksurvey.tw/health | ConvertFrom-Json | Select-Object status, environment, business_data
# 預期：跟 Step 3 一致

# Step 5: 完整 smoke test（含 admin auth + 10 endpoint）
docker cp scripts/checks/admin_backup_smoke_test.py ck_missive_backend:/tmp/smoke.py
docker exec ck_missive_backend python /tmp/smoke.py
# 預期：10/10 PASS
```

---

## 失敗回退路徑

| 症狀 | 處理 |
|---|---|
| Docker Desktop 沒啟動 | 手動雙擊 Docker Desktop 圖示 → 30s 後重跑 Step 2-5 |
| Container 啟動但 backend unhealthy | `docker logs ck_missive_backend --tail 100` 看錯誤 |
| `/health` 200 但 `business_data.ok=false` | DB schema drift / volume mount 議題 (L43 family) |
| 公網 cksurvey.tw 不通但本機 OK | cloudflared 異常 → `docker logs ck-tunnel-cloudflared` |
| smoke test 任一 FAIL | 對照 [[L49_container_host_dependency_family]] 修法 |

---

## 業務 endpoint smoke test 10 項清單

| # | Endpoint | Expected | 驗證內容 |
|---|---|---|---|
| 1 | `POST /api/auth/me` | 200 | JWT 認證通過 |
| 2 | `POST /api/backup/environment-status` | 200 | `pg_dump_available=true` |
| 3 | `POST /api/backup/list` | 200 | db_count ≥ 1 |
| 4 | `POST /api/backup/status` | 200 | `status="active"` |
| 5 | `POST /api/backup/config` | 200 | `backup_directory` exists |
| 6 | `POST /api/backup/scheduler/status` | 200 | `running=true` |
| 7 | `POST /api/backup/remote-config` | 200 | NAS Z: config 持久化（L49.5 修） |
| 8 | `POST /api/backup/logs` | 200 | history entries |
| 9 | `POST /api/files/storage-info` | 200 | `total_files ≥ 100` |
| 10 | `POST /api/files/{id}/download` | 200 | 真實 binary 下載 |

---

## v6.11 收尾里程碑

```
19 commits 5/27→28，已 push origin

L49 family 完整收尾（11 案）:
  L49.1 backup docker CLI → pg_dump 直連
  L49.2 storage-info OSError 容錯
  L49.3 files/{id}/download 跨平台分隔符
  L49.4 backup mount path align
  L49.5 attachment OSError + perf 31.5s→0.06s
  L49.6 csrf race + header self-heal
  L49.7 task scheduler XML UTF-16 BOM
  L49.8 ps1 UTF-8 BOM (20 檔 sweep)
  L49.9 config mount + idempotent delete
  L49.10 frontend backup timeout + 409 handling
  L49.11 header race (useState lazy init)

新 fitness step: 52 / 53 / 54
新 ADR: 0045 (L49 family environment switch SSOT)
新 lessons: L49 入 LESSONS_REGISTRY
跨 repo 範本: ck-modular-toolkit 16 audits + 2 lessons

業務數據 全 healthy:
  docs=1799 / kg=24420 / 6 db backup / 8 attachment backup
  backup scheduler running / 下次 02:00
  smoke test 10/10 PASS
```

---

> **owner 重啟前最後確認**：上面 pre-flight 4 步全綠 → 直接重啟。
> 重啟後等 90 秒跑 Test 1 5 步驗收。
