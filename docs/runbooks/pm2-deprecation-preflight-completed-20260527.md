# OA-3 PM2 廢除 — Pre-flight 全部完成報告（2026-05-27 18:43）

> **狀態**：✅ 11 項 pre-flight 全綠 / ⚠️ 1 項需 owner elevated PowerShell（Task Scheduler）
> **可從**：階段 2「Docker 接管驗證」開始
> **執行清單**：`docs/runbooks/pm2-deprecation-execution-20260527.md`
> **SOP**：`docs/runbooks/pm2-deprecation-sop.md`

---

## ✅ Pre-flight 完成項（11/12）

| 階段 | 項目 | 狀態 | 證據 |
|---|---|---|---|
| Pre 1 | PM2 配置快照（rollback 用）| ✅ | `C:\Users\User1\Desktop\pm2-deprecation-snapshot-20260527_184100-{list,ck-backend,ck-frontend}.txt`（12 KB total）|
| Pre 2 | Fresh DB dump（fallback 用）| ✅ | `D:\CKProject\CK_Missive\backups\database\ck_missive_pre_pm2_deprecation_20260527_184320.sql` (**241.6 MB / 76 tables / 268 indexes**) |
| 1.1 | docker container `ck_missive_backend` healthy | ✅ | Up 3h+ / image=`production` / restart=always |
| 1.1 | Container `/health` biz_ok | ✅ | docs=1799 / kg=24247 / pool 1/15 / overflow=0 |
| 1.2 | NAS 異地備份 | ✅ | `Z:\#systembackup\CK_Missive_INCIDENT_20260521_volume_mount_drift` |
| 3.3 | cloudflared 3 container restart=unless-stopped | ✅ | missive / pile / tunnel 全綠 |
| 3.4 | docker-compose 5 services restart 政策齊 | ✅ | postgres/redis/backend/frontend `always` + adminer `unless-stopped` |
| 4.1 | Docker Desktop AutoStart | ✅ | settings-store.json `AutoStart=True` |
| 4.3 | Task Scheduler XML 落地 | ✅ | `scripts/deploy/task-scheduler-autostart.xml` |
| - | ecosystem.config.js 含 ck-backend (line 34) + ck-frontend (line 90) | ✅ | 待 3.2 刪 |
| - | 當前 PM2 `ck-backend` (PID 19788) / `ck-frontend` (PID 19844) | ✅ | 3h online |

---

## ⚠️ Pre-flight 待補（1/12）— 需 owner elevated PowerShell

### Task Scheduler `CK_Missive_AutoStart` 匯入

**為何 owner 必做**：
- XML 含 `<UserId>S-1-5-18</UserId>`（SYSTEM）+ `<RunLevel>HighestAvailable</RunLevel>`
- 我非 elevated → 跑 `schtasks /Create` 回 `ERROR: Access is denied`

**Owner 動作（1 min）**：
```powershell
# 以「以系統管理員身分執行」開 PowerShell
schtasks /Create /TN "CK_Missive_AutoStart" `
  /XML "D:\CKProject\CK_Missive\scripts\deploy\task-scheduler-autostart.xml" /F

# 驗證
schtasks /Query /TN "CK_Missive_AutoStart" /FO LIST | Select-Object -First 8
# 預期：見 TaskName / Status: Ready
```

---

## 🎯 Owner 接手點 — 從階段 2 開始

完成上面 1 個 elevated 命令後，整個 OA-3 PM2 廢除可從 **`docs/runbooks/pm2-deprecation-execution-20260527.md` §階段 2** 開始。

### 階段 2 預習（owner 親手，15 min）

```powershell
# 2.1 ⚠️ DESTRUCTIVE — pm2 stop（可逆）
pm2 stop ck-backend ck-frontend
pm2 list | findstr -i "ck-backend\|ck-frontend"
# 預期：status=stopped

# 2.2 驗證 docker 接管（30s 緩衝）
Start-Sleep -Seconds 30
curl http://localhost:8001/health        # 應 200 + biz_ok=true
curl https://missive.cksurvey.tw/health  # 應 200 + biz_ok=true（1-2 min 可能命中 stale）

# 2.3 GO / NO-GO
#   兩個都 200 + biz_ok=true → 繼續階段 3（pm2 delete）
#   任一失敗     → 立即 rollback：pm2 start ck-backend ck-frontend
```

### 階段 3 預習（owner 親手，30 min）

```powershell
# 3.1 🔴 DESTRUCTIVE — pm2 delete（硬刪）
pm2 delete ck-backend ck-frontend
pm2 save

# 3.2 修 ecosystem.config.js — 刪 line 34 + line 90 附近 2 個 entry
# 用編輯器（VS Code / notepad）操作
git diff ecosystem.config.js
```

### 階段 4 預習（owner，45 min）

- **必跑 Test 1**：關機 → 開機（不登入）→ 等 5 min → 外部設備測 `https://missive.cksurvey.tw/health`
- Test 2 / Test 3 driver test：見執行清單

---

## 階段時間規劃建議

| 時段 | 行動 | 預估 |
|---|---|---|
| 22:00 | Owner elevated PS：跑 Task Scheduler import + 階段 2/3 destructive | 1h |
| 23:00 | Test 1 開機驗收（關機 → 不登入 → 等 5 min → 外部測）| 30 min 等待 + 5 min 驗證 |
| 24:00 | Test 2/3 + 寫 diary | 30 min |
| 隔日 | 跑 step 49 + step 51 確認 dormant 真綠 | 5 min |

**總計 owner 時間**：~2.5h 連續（含等待）

---

## Rollback 路徑（已備齊）

```powershell
# 任一階段失敗：
pm2 start ck-backend --env production
pm2 start ck-frontend
pm2 save
Start-Sleep -Seconds 30
curl https://missive.cksurvey.tw/health  # 應恢復 200

# 若 DB 也壞（極端情況）：
docker exec -i ck_missive_postgres psql -U ck_user ck_documents < `
  D:\CKProject\CK_Missive\backups\database\ck_missive_pre_pm2_deprecation_20260527_184320.sql
```

---

## 完成 OA-3 後預期效益

| 議題 | 目前 | OA-3 後 |
|---|---|---|
| 公網真正打到的 backend | PM2 stale code (環境=development) | docker container (production image) |
| Docker container 9 天零流量 | docker `memory_diary_appends_total=0` | docker 正常記錄 / Prometheus metric 活 |
| Step 49 synthetic baseline | 🔴 RED（24h 0/10 success）| 🟢 GREEN（搭配 OA-1 token env） |
| Step 51 tender freshness | 🔴 RED（PCC 49 days stale）| 🟢 GREEN（PCC cron 開始跑）|
| Hot-patch 路徑 | 改 docker 對公網無效 → owner 困惑 | 改 docker 立即生效 |
| 雙 backend 同時 listen 0.0.0.0:8001 | Windows SO_REUSEADDR race | 單一 SSOT |

---

## 結尾備註

Pre-flight 所有非 destructive / 非 elevated 工作完成，全部 16+1 commits 已 stage 完成。Owner 只需：
1. **1 個 elevated 命令**（Task Scheduler import，1 min）
2. 排定夜間 ~2.5h 連續時段執行階段 2-4
3. Test 1 完整關機重啟（不可省 — 開機自動重啟是核心驗收）

> **核心精神**：所有 audit 紅燈在 OA-3 完成之前都是「測 0 流量後的假象」。本次 16+1 commit 預備全部就緒 — destructive 按鈕只在 owner 手上。
