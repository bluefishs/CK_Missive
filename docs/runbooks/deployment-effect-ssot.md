# 部署生效機制 SSOT — 「改什麼 → 怎麼生效」

> **建立**：2026-06-04
> **觸發**：單一 session 內為讓改動生效，對生產 backend 連續 3 次 rebuild+recreate
> （routing → crystallizer → synthesis fallback），暴露「哪類改動需哪種部署動作」
> 缺乏 SSOT，易造成 rebuild churn 或「改了沒生效」的 silent drift。
> **權威來源**：`docker-compose.production.yml` 的 `build` / `volumes` 區段（本檔為其導讀）

---

## 核心判斷：code 是 baked-in image 還是 mount？

| 改動類型 | 容器內路徑來源 | 生效方式 | 公網中斷 |
|---|---|---|---|
| **backend Python**（`backend/app/**`）| **baked in image**（`build: ./backend`，無 mount app/）| `docker compose -f docker-compose.production.yml build backend` → `up -d --force-recreate backend` | **~60s**（start_period）|
| **frontend src**（`frontend/src/**`）| `./frontend/dist:/frontend/dist:ro` → backend serve SPA | `cd frontend && npm run build` | **無**（dist mount 即時生效公網）|
| **fitness / cron scripts**（`scripts/**`）| `./scripts:/app/scripts:ro` | host 改即生效（容器內直讀）| **無** |
| **docs**（ADR 頁等，`docs/**`）| `./docs:/app/docs` | host 改即生效 | **無** |
| **wiki / memory**（`wiki/**`）| `./wiki:/app/wiki` | host 改即生效 | **無** |
| **backend/config**（`remote_backup.json` 等）| `./backend/config:/app/config` | 多數即讀；env 類需 recreate | 視情況 |
| **nginx 前端**（內網 `:3000`）| image `ck-missive-frontend:production` | `docker compose build frontend`（公網不依賴此路）| （內網）|
| **docker-compose.yml / env** | — | `up -d --force-recreate`（對應 service）| ~60s |

> ⚠️ **公網主路 = backend serve SPA**（`./frontend/dist` mount）。`npm run build` 即對公網生效，
> 不需動任何容器；nginx `:3000` container 是內網另一路，公網不依賴。

---

## 操作命令

```bash
# backend Python 改動（需 rebuild + recreate，生產短中斷）
docker compose -f docker-compose.production.yml build backend
docker compose -f docker-compose.production.yml up -d --force-recreate backend

# frontend 改動（公網即時生效，零容器重啟）
cd frontend && npm run build

# scripts / docs / wiki 改動 — host 改完即生效，無需任何指令
```

## 生效後複查 SOP（本 session 實證流程）

```bash
# 1. 容器健康
docker ps --filter name=ck_missive --format "{{.Names}} {{.Status}}"
# 2. backend health（含業務量防禦）
docker exec ck_missive_backend curl -s -o /dev/null -w "%{http_code}" localhost:8001/health
# 3. 公網可達
curl -s -o /dev/null -w "%{http_code}" https://missive.cksurvey.tw/health
# 4. backend 改動 — 容器內 import 驗證（不需 http ready）
MSYS_NO_PATHCONV=1 docker exec ck_missive_backend python -c "from app.xxx import yyy; print('ok')"
```

> ⚠️ **MSYS 路徑陷阱**（Git Bash on Windows）：`docker exec ... python /app/...` 的 `/app/`
> 會被 MSYS 轉成 `C:/Program Files/Git/app/...`。一律加 `MSYS_NO_PATHCONV=1` 前綴。

---

## 減少 rebuild churn 的原則

1. **分類後再動**：先用上表判定改動屬「baked」還是「mount」。mount 類零中斷，可隨時改。
2. **baked 類批次化**：多個 backend Python 改動**合併成一次 rebuild+recreate**，不要逐項 recreate。
3. **cron-only 改動可延後生效**：純 cron script（fitness / crystallizer 等）若經 scripts mount 即時生效；
   若是 backend Python 的 cron 邏輯（baked），且 cron 在凌晨，rebuild 可排到下次自然部署。
4. **改了一定要驗生效**：baked 類改 code 後若忘記 rebuild → running image 與 git HEAD drift（silent）。

---

## 關聯

- `.claude/rules/cross-file-ssot-governance.md`（跨檔資源 SSOT，本檔為「部署生效」維度補充）
- `docs/runbooks/reboot-pre-flight-20260602.md`（重啟前 pre-flight）
- [[feedback_frontend_build_for_public]] / [[feedback_rigor_no_self_inflicted_instability]]（減少 rebuild churn）
