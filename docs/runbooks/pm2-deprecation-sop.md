# PM2 廢除 SOP（純 Docker + 開機自動重啟）

> **版本**：v1.0 / 2026-05-25
> **觸發**：L43 事故揭發公網 cloudflared 命中 PM2 native uvicorn 而非 docker container
> **目標**：廢除 CK_Missive 的 PM2 ck-backend + ck-frontend，改為純 docker compose
> **路線**：v6.11 Sprint 1 W1（2026-05-26~06-02 任一天執行）
> **預估 Effort**：3-4h（含 owner 親自開機驗收）
> **必要 owner 參與**：階段 1、3、4 全程，階段 2 docker 接管驗證

---

## 為何要廢 PM2

### 當前架構問題

```
公網 missive.cksurvey.tw
  → cloudflared (host.docker.internal:8001)
  → 命中 PM2 native uvicorn (PID 動態, watch&reload=✘)

localhost:8001 (本機 dev)
  → docker port mapping
  → ck_missive_backend container (production image)

兩者同時 listen 0.0.0.0:8001（Windows SO_REUSEADDR 允許）
host 從不同來源解析的 socket 命中順序不同
```

### L43 事故教訓（2026-05-21）

- 所有 `docker cp main.py + restart` 對公網**完全無效**
- 必須 `pm2 restart ck-backend` 才生效（且 watch&reload=✘ 不會自動）
- hot-patch docker 後 owner 看不到效果 → 認為「修法失敗」→ 浪費 4 小時 debug

### 廢 PM2 後的單一 SSOT

```
公網 missive.cksurvey.tw
  → cloudflared (host.docker.internal:8001)
  → ck_missive_backend container (production image, restart:always)

localhost:8001 (本機 dev)
  → 同上（docker port mapping）

單一 backend instance, hot-patch 與 deploy 路徑一致
```

---

## 階段 1 — 前置檢查（owner 親自，10 min）

### 1.1 確認 docker container 健康

```powershell
# 1. 確認 docker container 已啟動且 healthy
docker ps --filter "name=ck_missive_backend" --format "table {{.Names}}\t{{.Status}}"
# 預期：ck_missive_backend  Up X minutes (healthy)

# 2. 確認 docker container 內 /health 真活
docker exec ck_missive_backend curl -fsS http://localhost:8001/health | findstr biz_ok
# 預期：含 "biz_ok":true
```

### 1.2 確認備份完整

```powershell
# 公網斷線風險時的回退依據
ls D:\CKProject\CK_Missive\backups\database\
# 確認近期有 pre_upgrade dump (>= 2026-05-21)

# 同步檢查 NAS 異地備份
ls Z:\03.專案管控專區\00.公司公文紀錄\#systembackup\CK_Missive_INCIDENT_20260521*
```

### 1.3 預先記錄當前 PM2 配置

```powershell
pm2 list > $env:USERPROFILE\Desktop\pm2-list-before-deprecation.txt
pm2 describe ck-backend > $env:USERPROFILE\Desktop\pm2-ck-backend-config.txt
pm2 describe ck-frontend > $env:USERPROFILE\Desktop\pm2-ck-frontend-config.txt
```

---

## 階段 2 — Docker 接管驗證（dry-run，15 min）

### 2.1 暫停 PM2（不刪除）

```powershell
pm2 stop ck-backend ck-frontend
pm2 list
# 預期：ck-backend / ck-frontend status=stopped
```

### 2.2 立即驗證 docker 接管

```powershell
# 等 30 秒讓 cloudflared 重新 establish connection（cloudflared 自帶 retry）
Start-Sleep -Seconds 30

# Layer 1: localhost docker
curl http://localhost:8001/health
# 預期：200 + biz_ok=true

# Layer 2: 公網
curl https://missive.cksurvey.tw/health
# 預期：200 + biz_ok=true (注意：可能仍命中 PM2 stopped socket，需 1-2 min)

# Layer 3: 從外部設備（手機 4G 網路 / 同事電腦）測 https://missive.cksurvey.tw/
# 預期：登入頁正常顯示
```

### 2.3 失敗回退

若 Layer 2/3 失敗：
```powershell
pm2 start ck-backend ck-frontend
# 等 30 秒
curl https://missive.cksurvey.tw/health
# 若恢復 → 確認問題並 debug；不繼續廢除
```

若 Layer 2 成功：繼續階段 3。

---

## 階段 3 — 正式廢除 + 配置（30 min）

### 3.1 刪除 PM2 entries

```powershell
pm2 delete ck-backend ck-frontend
pm2 save
# 預期：PM2 list 中不再有 ck-backend / ck-frontend
#       但保留 ck-showcase-* / ck-tunnel-frontend / ck-sso-health（其他 repo）
```

### 3.2 修 ecosystem.config.js

```javascript
// D:\CKProject\CK_Missive\ecosystem.config.js
// 刪除 apps 陣列中的：
//   { name: 'ck-backend', ... }
//   { name: 'ck-frontend', ... }
// 保留其他 entries
```

### 3.3 配置 cloudflared restart policy

```powershell
# docker run 起的 container 需手動加 restart policy
docker update --restart=unless-stopped ck_missive_cloudflared
docker update --restart=unless-stopped pile-cloudflared
docker update --restart=unless-stopped ck-tunnel-cloudflared

# 驗證
docker inspect ck_missive_cloudflared --format '{{.HostConfig.RestartPolicy.Name}}'
# 預期：unless-stopped
```

### 3.4 確認 docker-compose 已配 restart: always

```yaml
# docker-compose.production.yml 已有（無需修改）：
postgres:   restart: always
redis:      restart: always
backend:    restart: always
frontend:   restart: always
adminer:    restart: unless-stopped
```

---

## 階段 4 — 開機自動重啟機制（45 min，含驗收）

### Layer 1 — Docker Desktop 開機自動啟動（5 min）

```
Docker Desktop GUI → Settings → General
  ☑ Start Docker Desktop when you sign in to your computer
  Apply & Restart
```

### Layer 2 — Container restart policy（已於階段 3.3/3.4 完成）

### Layer 3 — Windows Task Scheduler 備援（20 min）

建立 Task `CK_Missive_AutoStart`：

> ✅ **XML 檔案已落地**：`scripts/deploy/task-scheduler-autostart.xml`
> 不需手動建檔；直接到 §匯入 步驟即可。內容如下供 review：

```xml
<!-- 已存在於 D:\CKProject\CK_Missive\scripts\deploy\task-scheduler-autostart.xml -->
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>CK_Missive auto-start on boot (v6.11 PM2 deprecation)</Description>
    <Author>CK_Missive</Author>
    <URI>\CK_Missive\AutoStart</URI>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
      <Delay>PT30S</Delay>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <ExecutionTimeLimit>PT15M</ExecutionTimeLimit>
    <Priority>5</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-ExecutionPolicy Bypass -NoProfile -Command "Start-Sleep 60; docker compose -f D:\CKProject\CK_Missive\docker-compose.production.yml up -d 2>&amp;1 | Tee-Object D:\CKProject\CK_Missive\backups\autostart.log"</Arguments>
      <WorkingDirectory>D:\CKProject\CK_Missive</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

**匯入**：
```powershell
schtasks /Create /TN "CK_Missive_AutoStart" /XML "D:\CKProject\CK_Missive\scripts\deploy\task-scheduler-autostart.xml" /F
```

**測試（不重開機）**：
```powershell
schtasks /Run /TN "CK_Missive_AutoStart"
Start-Sleep -Seconds 60
docker ps --filter "name=ck_missive_backend"
```

### Layer 4 — Health Watchdog（10 min，可選但建議）

```powershell
# 已有 scripts/health/health-watchdog.sh
# 建立 Task Scheduler entry 每 2 分鐘跑：
schtasks /Create /TN "CK_Missive_HealthWatchdog" /TR "bash D:\CKProject\CK_Missive\scripts\health\health-watchdog.sh" /SC MINUTE /MO 2 /F
```

### 完整驗收（10 min，必跑）

```
Test 1: 完整重啟測試（必須過）
  - 關機 → 開機（不登入）→ 等 5 min
  - 從外部設備訪問 https://missive.cksurvey.tw/health
  - 預期：200 + business_data.ok=true

Test 2: 單 container 重啟（必須過）
  - docker kill ck_missive_backend
  - 預期：restart policy 自動拉起，30s 內 healthy

Test 3: Docker Desktop 異常恢復（建議過）
  - 手動關閉 Docker Desktop
  - 預期：Task Scheduler 偵測 / Watchdog Layer 4 重拉
```

---

## 回退步驟（若任一階段失敗）

```powershell
# 1. 恢復 PM2
pm2 start ck-backend --env production
pm2 start ck-frontend
pm2 save

# 2. 驗證
curl https://missive.cksurvey.tw/health

# 3. 回退 docker-compose 與 cloudflared restart policy（可不動，無害）

# 4. 記錄事故並評估
# 寫入 wiki/memory/failures/failure-pm2-deprecation-<date>.md
```

---

## 完成定義（Done Criteria）

- [ ] `pm2 list` 中無 ck-backend / ck-frontend
- [ ] `ecosystem.config.js` 已移除對應 apps
- [ ] `docker-compose.production.yml` 5 services 全 `restart: always` 或 `unless-stopped`
- [ ] `ck_missive_cloudflared` + `pile-cloudflared` + `ck-tunnel-cloudflared` 全 restart=unless-stopped
- [ ] Docker Desktop 設「Start when sign in」
- [ ] Task Scheduler `CK_Missive_AutoStart` 啟用且測過
- [ ] Test 1-3 全過
- [ ] 寫入 wiki/memory/diary/<date>.md 記錄
- [ ] 寫入 docs/adr/0047 PM2 廢除（或合併 ADR-0017 Phase 1C）

---

## 已知陷阱

1. **Cloudflare Tunnel connection slot 釋放慢**：PM2 stop 後 cloudflared 可能仍命中 stale connection 1-2 min，需耐心等
2. **Docker Desktop 啟動延遲**：開機後 30-60s 才完成 init，Task Scheduler 加 30s delay 是必要
3. **User 未登入時 Docker Desktop 不啟動**：BootTrigger + RunLevel HighestAvailable + UserId S-1-5-18（SYSTEM）必須三個都對
4. **`docker compose up -d` 沒換新 image**：開機自動拉起的是已 build 的 image；deploy 時還是要手動 `--build`

---

## 後續工作

- v6.11 Sprint 1 W2：建議寫 `scripts/deploy/deploy-via-docker.ps1` 取代 `scripts/dev/dev-start.ps1` 的 PM2 模式
- v6.11 Sprint 2：CLAUDE.md / .claude/rules/* 拿掉 PM2 ck-backend 引用
- v6.12：考慮把 cloudflared 移進 docker-compose 統一管理（目前 docker run 各自分散）
