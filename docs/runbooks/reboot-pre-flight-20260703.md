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

## 重啟後驗收結果（2026-07-03 11:03，容器 Up ~15min，全通過）

| 步 | 檢查 | 結果 |
|---|---|---|
| 1 | 容器復原 | 5 missive + 3 hermes + ck-ollama **全 healthy**（Docker 自動拉回，未 --force-recreate；NVIDIA hook 正常無需 wsl --shutdown）✅ |
| 2 | 業務量 | docs **1895** ≥ 1894 / KG **34123** ≥ 34123 / biz_ok true ✅（持續成長） |
| 3 | 公網（L76） | `https://missive.cksurvey.tw/api/health` **200**（0.25s）；未見殭屍埠 ✅ |
| 4 | 行事曆顛倒 | `end_date < start_date` = **0**（model 防呆生效）✅；另 2 筆 completed+未到期經查為 deadline=今日18:00 **提早完成之正常業務**（start=end 無顛倒），非回歸 |
| 5 | 異地備份排程 | `CK-Missive-Offsite-Backup` State=**Ready**、LastResult=**0**、NextRun 07-04 03:00 ✅ |

**加驗（本輪修法 live 確認）**：
- **SSO 修 live 到公網**：公網 `/` 實際 serve `main-DUoFppDD.js`（backend bind-mount `frontend/dist`，含 `52053913`）✅。注意 `ck_missive_frontend` nginx 容器內為 05-27 舊 baked `main-9ZTaIa6f.js`，**不在公網路徑上**（已知殘留、無害）。
- **LINE 減量 gate**：`PROACTIVE_LINE_PUSH_ENABLED` 空值（→ 預設 false，吹哨者/派工進度不單推）✅。
- **5 鏈 E2E**：ALL PASS（chain1 1895/34123 · chain2 lessons16/patterns12/proposals8 · chain3 12 tools · chain4 hermes 200 · chain5 bridge skill）✅。
- **cron**：07-03 全 job success（含 fitness_daily / morning_report / governance_dashboard_regen / integration_e2e）✅。
- **git**：8 commits 已全推 origin/main、working tree clean、與 origin 同步 ✅。

## 待 owner 真人複驗（headless 無法代行）
- **SSO**：www.cksurvey.tw 登入 → 進 missive.cksurvey.tw **不再「閃一下又跳回登入」**（`52053913`）。若仍失敗，回報 Network 面板哪個請求 401。
- 行事曆事件編輯：三機制統一為單一「截止日期/時間」、event 1197 可正常編。
