# Reboot Pre-Flight Checklist — 2026-07-03（v6.22）

> 本輪重點：行事曆日期顛倒根治（含 model 防呆＋backend rebuild）／三建立機制統一截止日期／異地備份改 Windows 排程復活／LINE 推播減量／SSO「閃一下又跳回登入」修。

## Pre-Flight 結果（重啟前，全通過）

| 項 | 檢查 | 結果 |
|---|---|---|
| ① | git working tree | **clean** ✅（8 commits 本輪，見下） |
| ② | DB volume（L43 防呆） | `ck_missive_postgres_dev_data`（真實庫，非空殼）✅ |
| ③ | 容器 restart policy | backend/postgres/redis/frontend=`always`、cloudflared=`unless-stopped` → 重啟自動復原 ✅ |
| ④ | 業務量基線 | **docs 1894 / KG 34123 / biz_ok True**（重啟後須 ≥ 此值） |
| ⑤ | 前端部署 | dist bind-mount `main-DUoFppDD.js`（含 SSO 修）公網 200 ✅ |
| ⑥ | backend image | 已 rebuild（含行事曆 sync 修＋model 防呆＋LINE gate），baked 存活重啟 ✅ |
| ⑦ | 異地備份排程 | `CK-Missive-Offsite-Backup` Ready + StartWhenAvailable、次次 07-04 03:00、LastResult 0 ✅ |
| ⑧ | PM2 | dump 已無無效 offsite job（改 Windows 排程）；showcase/tunnel 照舊 ✅ |

## 本輪 commits（8，本地）
```
242b596f chore(memory): 07-03 diary
32ad873b docs: v6.22 CLAUDE 里程碑 + 異地備份改 Windows 排程
52053913 fix(sso): 修「閃一下又跳回登入」
32aad984 feat(line): 推播減量合併
b690191a feat(backup): 異地備份 NAS 同步
0685aa0d feat(calendar): 三機制統一截止日期
c4c47887 fix(calendar): 修日期顛倒
fdb55dc2 chore(memory): 覆盤 cron 同步
```

## 重啟後驗收 SOP（5 步）

1. **容器復原**：`docker ps` → 5 missive 容器 healthy（Docker 自動拉回，**勿 --force-recreate**）。若 ck-ollama GPU 起不來（NVIDIA hook 崩潰）→ `wsl --shutdown` 重啟 Docker 引擎（非 `docker restart`）。
2. **業務量**：`curl http://localhost:8001/health` → docs ≥ 1894 / KG ≥ 34123 / biz_ok true。
3. **公網（L76）**：`curl https://missive.cksurvey.tw/api/health` → 200。不通則 `docker restart ck_missive_backend`（Windows 殭屍埠轉發）。
4. **行事曆**：`SELECT count(*) FROM document_calendar_events WHERE end_date < start_date;` → **0**（model 防呆生效）。
5. **異地備份排程**：`Get-ScheduledTaskInfo CK-Missive-Offsite-Backup` → State Ready；03:00 後查 `logs/backup/offsite-sync-nas.log` 末行「異地同步完成」。

## 待 owner 真人複驗（headless 無法代行）
- **SSO**：www.cksurvey.tw 登入 → 進 missive.cksurvey.tw **不再「閃一下又跳回登入」**（`52053913`）。若仍失敗，回報 Network 面板哪個請求 401。
- 行事曆事件編輯：三機制統一為單一「截止日期/時間」、event 1197 可正常編。
