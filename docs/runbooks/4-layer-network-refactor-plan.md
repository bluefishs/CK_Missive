# CK_Missive 4 層分網路重構規劃（step 37 RED → GREEN）

> **版本**：v1.0 / 2026-05-25
> **觸發**：step 37 cross-repo docker network audit RED — `ck_missive_network` 不符 ADR-0043 標準
> **目標**：分網路為 4 層（backend/data/frontend/worker）+ 接 ck_platform_obs_net
> **路線**：v6.11 Sprint 1 W1（2026-05-26~06-02 任一天執行）
> **預估 Effort**：4-5h（不含 owner 跨設備外部驗收）
> **依賴**：必須在 PM2 廢除執行**之前**完成（避免雙 backend 同 port 期間動 network 增加 race 風險）

---

## 1. 現況問題

### 1.1 step 37 audit 訊息

```
🔴 CK_Missive: RED (3 networks, 2 violations, 3 warnings)
    ❌ network 'ck_missive_network' 不符 ck_<repo>_<layer>_net pattern
    ❌ network 'ck_missive_network' 不符 ck_<repo>_<layer>_net pattern
    ⚠️  external '${COMPOSE_PROJECT_NAME}_default' 不符 ck_platform_*_net pattern
    ⚠️  缺 layer: ['backend', 'data', 'frontend', 'worker']（4 層分網路未完整）
    ⚠️  未接 ck_platform_obs_net（觀測棧 scrape）
```

### 1.2 docker-compose.production.yml 現況

```yaml
# 5 services 全在單一 ck_network:
postgres:   networks: [ck_network]    # ← 應在 data
redis:      networks: [ck_network]    # ← 應在 data
backend:    networks: [ck_network]    # ← 應在 backend + data + obs
frontend:   networks: [ck_network]    # ← 應在 frontend + backend (連 backend)
adminer:    networks: [ck_network]    # ← 應在 data（DB 管理工具）

networks:
  ck_network:
    name: ck_missive_network           # ← 命名不符 ck_<repo>_<layer>_net
    driver: bridge
```

### 1.3 安全層級分析

當前所有 service 在同一 broadcast domain，問題：
1. **postgres / redis 對 frontend 暴露**（無需，frontend 應只連 backend）
2. **無法精準限制 obs scrape 範圍**（Prometheus 該只 scrape backend metrics endpoint）
3. **cloudflared 必須 host network**（穿越雙重 NAT）— 但本 repo 是 docker run 不在 compose
4. **adminer 對 backend/frontend 暴露**（無需，只該在 data 對 DB 操作）

---

## 2. 目標架構（ADR-0043 標準）

### 2.1 命名 SSOT

```
pattern: ck_<repo>_<layer>_net
                ────  ─────
                missive | backend / data / frontend / worker
```

4 個層 + 1 個跨 repo obs：

| Network 名 | 用途 | 接哪些 service |
|---|---|---|
| `ck_missive_frontend_net` | 公網入口層（cloudflared / nginx） | frontend |
| `ck_missive_backend_net` | 應用層（FastAPI） | backend, frontend（連 backend）|
| `ck_missive_data_net` | 資料層（DB / cache）| postgres, redis, backend（拿資料）, adminer（DB 管理） |
| `ck_missive_worker_net` | 背景任務層（scheduler / future workers） | backend（cron scheduler 同 process）|
| `ck_platform_obs_net` | 跨 repo 觀測棧（external，Prometheus scrape）| backend（被 scrape） |

### 2.2 Service 多網路接線

```
postgres:    [data]
redis:       [data]
backend:     [backend, data, worker, obs]   ← 4 接點（複雜服務）
frontend:    [frontend, backend]            ← 2 接點（serve + 後端 proxy）
adminer:     [data]
cloudflared: [host network]                 ← 不變（docker run，需 host）
```

### 2.3 流量隔離效果

| 路徑 | 走哪個 network | 預期 |
|---|---|---|
| 公網 → cloudflared → backend | host → backend_net | ✅ 公網不直碰 data |
| frontend nginx → backend `/api/*` | backend_net | ✅ 不暴露 postgres |
| backend → postgres SELECT | data_net | ✅ data 隔離 |
| Prometheus → backend `/metrics` | obs_net (external) | ✅ obs 範圍精準 |
| adminer → postgres | data_net | ✅ DB 管理工具不接 backend |

---

## 3. 風險評估

### 3.1 高風險（必須緩解）

| # | 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|---|
| R1 | backend 多網路後 DNS 解析失敗（無法 ping postgres）| 中 | 業務全停 | 用 `service_name` 而非 `container_name` 連線；先 dry-run docker compose config |
| R2 | postgres restart 後 backend 連不上（startup race）| 中 | 業務啟動失敗 | `depends_on` 加 `condition: service_healthy` |
| R3 | 改 network 觸發 container 全重建 → 累積 in-memory cache 流失（Redis 仍持久化但 backend prometheus counter reset）| 高 | metrics 短暫 0 | 不可避免，接受；事前告知 Grafana 看板會 reset |
| R4 | ck_platform_obs_net 不存在（external 引用失敗）| 中 | container 啟不起 | 先確認 CK_AaaP 端 obs_net 已建立；若無，用 `external: true` 的 fallback 機制（或本 repo 自建後 CK_AaaP 來接）|
| R5 | cloudflared 與 backend 跨網路通訊失敗（cloudflared 用 host network）| 低 | 公網 down | cloudflared 用 `host.docker.internal:8001` 連 backend，不受 network 隔離影響 |
| R6 | adminer 從 backend 移到 data_net 後，從外部訪問 adminer:8080 失敗 | 低 | 開發工具 down | adminer 仍配 `ports: 8080:8080` 對外露 port，網路改變不影響 port mapping |

### 3.2 中風險

| # | 風險 | 緩解 |
|---|---|---|
| R7 | 命名衝突（`ck_missive_data_net` 與其他 repo 同名）| ADR-0043 pattern 已用 repo 前綴避免；額外 grep 所有 repo 確認 |
| R8 | docker-compose v2 對 multi-network 解析較舊 v1 慢 | 接受；production 已 v2 |
| R9 | 用 fitness step 37 + step 38 雙重驗證後再 production deploy | 加入 SOP 第 4 階段 |

### 3.3 低風險（接受）

- 短暫 downtime（docker compose down + up 重建 5 container）— 預期 60-120 秒
- Metrics history 中斷一次 — 接受

---

## 4. 命名標準化規範（補強 ADR-0043）

### 4.1 Pattern 嚴格定義

```
^ck_(?P<repo>[a-z_]+)_(?P<layer>backend|data|frontend|worker)_net$
```

- repo 段允許 lowercase + underscore（例：`missive` / `lvrland_webmap` / `pile`）
- layer 段限定 4 個固定字串
- 後綴 `_net` 強制

### 4.2 跨 repo external network

```
^ck_platform_(?P<purpose>obs|gateway|federation)_net$
```

- `ck_platform_obs_net` — Prometheus scrape（本 repo 接此）
- `ck_platform_gateway_net` — 未來 cloudflared 共用
- `ck_platform_federation_net` — KG federation（CK_AaaP 主管）

### 4.3 禁止使用的命名

- `ck_<repo>_network`（缺 layer，本案 RED 原因）
- `<repo>_default`（docker-compose 預設名，不可信賴）
- `monitoring` / `default` / 任何無 `ck_` 前綴
- 任何含大寫 / dash 的命名

### 4.4 _meta/standards-consumed.yml 同步

每個 repo 在 `_meta/standards-consumed.yml` 宣告：

```yaml
adr_consumed:
  - ck_aaap: 0043  # cross-repo docker network standard
  - ck_aaap: 0044  # single SSOT for docker volumes
network_layers:
  - backend
  - data
  - frontend
  - worker
external_networks:
  - ck_platform_obs_net
```

---

## 5. 執行 SOP（5 階段，4-5h）

### 階段 0 — 前置（30 min）

```bash
# 0.1 確認 ck_platform_obs_net 存在
docker network ls | grep ck_platform_obs_net
# 若無，到 CK_AaaP 建立：
# cd D:/CKProject/CK_AaaP && docker compose -f platform/observability/docker-compose.yml up -d
# 或 fallback：在本 repo 自建（external: false → 改 external: true 加 driver_opts）

# 0.2 完整備份
bash scripts/backup/pre_upgrade_backup.sh

# 0.3 跑當前 fitness baseline
bash scripts/checks/run_fitness.sh > /tmp/fitness_before_4layer.log
```

### 階段 1 — Compose 重構（45 min）

修改 `docker-compose.production.yml`：

```yaml
# 新 networks 區塊
networks:
  ck_missive_frontend_net:
    name: ck_missive_frontend_net
    driver: bridge
  ck_missive_backend_net:
    name: ck_missive_backend_net
    driver: bridge
  ck_missive_data_net:
    name: ck_missive_data_net
    driver: bridge
  ck_missive_worker_net:
    name: ck_missive_worker_net
    driver: bridge
  ck_platform_obs_net:
    name: ck_platform_obs_net
    external: true   # ← Prometheus 端管理

# Service 改接
services:
  postgres:
    networks: [ck_missive_data_net]
  redis:
    networks: [ck_missive_data_net]
  backend:
    networks:
      - ck_missive_backend_net
      - ck_missive_data_net
      - ck_missive_worker_net
      - ck_platform_obs_net
  frontend:
    networks:
      - ck_missive_frontend_net
      - ck_missive_backend_net  # ← 連 backend
  adminer:
    networks: [ck_missive_data_net]
```

驗證：
```bash
docker compose -f docker-compose.production.yml config 2>&1 | head -20
# 預期：parse 成功，無錯
```

### 階段 2 — Dry-run 與驗證（30 min）

```bash
# 2.1 用 dev compose 先試（不動 production）
# 複製設定到 docker-compose.dev.yml 對應修改
# 啟動 dev：docker compose -f docker-compose.dev.yml up -d
# 驗證 backend 能連 postgres：
docker exec ck_missive_backend_dev nc -z postgres 5432

# 2.2 跑 step 37 audit 應已 GREEN
python scripts/checks/network_audit.py --repo $(pwd)
```

### 階段 3 — Production 切換（30 min，必須 owner 在場）

```powershell
# 3.1 停 production stack
docker compose -f docker-compose.production.yml down

# 3.2 確認 network 已不存在
docker network ls | grep ck_missive

# 3.3 重新啟動（會建新 4 networks + 接 obs_net）
docker compose -f docker-compose.production.yml up -d

# 3.4 等 healthcheck（60-120 秒）
docker compose -f docker-compose.production.yml ps

# 3.5 驗證
curl http://localhost:8001/health  # 預期 200 + biz_ok=true
curl https://missive.cksurvey.tw/health  # 預期同
```

### 階段 4 — 觀測棧整合（30 min）

```bash
# 4.1 確認 Prometheus 抓得到 backend metrics
# 在 CK_AaaP 端：
docker exec ck_aaap_prometheus wget -qO- http://ck_missive_backend:8001/metrics | head -10

# 4.2 Grafana panel 確認新 scrape source
# 開 Grafana UI → datasource → query ck_missive_backend job
```

### 階段 5 — 驗收與回退（10 min）

```bash
# 5.1 跑 fitness step 37
bash scripts/checks/run_fitness.sh > /tmp/fitness_after_4layer.log
diff /tmp/fitness_before_4layer.log /tmp/fitness_after_4layer.log | head -20

# 5.2 預期 CK_Missive: RED → GREEN
grep "CK_Missive" /tmp/fitness_after_4layer.log

# 5.3 寫入 diary 紀錄
# wiki/memory/diary/2026-05-XX.md
```

---

## 6. 回退步驟（任一階段失敗）

```bash
# 回退到 backup
docker compose -f docker-compose.production.yml down
git stash    # 暫存 4 層改動
git checkout HEAD~1 -- docker-compose.production.yml
docker compose -f docker-compose.production.yml up -d

# 驗證恢復
curl http://localhost:8001/health
```

`git stash` 內容保留，下次再嘗試前先 review 失敗點。

---

## 7. 完成定義（Done Criteria）

- [ ] `docker-compose.production.yml` networks 區塊有 4 個 `ck_missive_*_net` + 1 個 external `ck_platform_obs_net`
- [ ] 每個 service `networks:` 接線正確（依 §2.2 表）
- [ ] `docker compose config` parse 成功無錯
- [ ] Production stack 重啟後 5 container 全 healthy
- [ ] `/health` local + public 全 200 + biz_ok=true
- [ ] `python scripts/checks/network_audit.py --repo .` 顯示 **CK_Missive: GREEN**
- [ ] Prometheus 能 scrape ck_missive_backend `/metrics`（Grafana panel 真實有資料）
- [ ] `_meta/standards-consumed.yml` 寫入 ADR-0043/0044 consumed
- [ ] 寫入 `wiki/memory/diary/<date>.md` 紀錄
- [ ] 通知其他 4 RED repos（lvrland / pile / DigitalTunnel / Website）參考本範本

---

## 8. 後續工作

### v6.11 Sprint 1 W1 後續
- lvrland_Webmap 升 4 層（4h）
- PileMgmt 升 4 層（2-3h）
- Website 升 4 層（2h）

### v6.11 Sprint 1 W2
- DigitalTunnel 命名對齊（已 4 層只是命名不符）
- 各 repo `_meta/standards-consumed.yml` 補
- Sprint 1 完整 audit + retro

### v6.11 Sprint 2
- 廢 PM2 ck-backend（依 `docs/runbooks/pm2-deprecation-sop.md`）
- 注意：必須 4 層完成後再廢 PM2，避免 race

---

## 9. 已知陷阱

1. **`external: true` 對應 network 必須先存在** — 階段 0.1 不可省
2. **backend 多網路後 prometheus scrape 路徑變化** — Prometheus 端的 target 設定要改成 `ck_missive_backend:8001`（service name 解析在 obs_net）
3. **adminer 從 ck_network 移到 data_net 後，從 host:8080 仍可訪問** — port mapping `8080:8080` 不受 network 改變影響
4. **frontend nginx upstream backend 用 service name 解析** — 需確認 nginx.conf 用 `backend` 名而非 IP
5. **cloudflared 不在 compose（docker run）** — 不受本次改動影響；但若未來移進 compose 需放 `ck_missive_backend_net`
6. **重啟期間公網會斷線 60-120 秒** — 必須選離峰時段（如 owner 自選 22:00 後）

---

## 10. 給其他 repo 參考的 template

完成後 owner / 範本維護者把本文件搬到 `CK_AaaP/runbooks/4-layer-network-refactor-template.md`，供 lvrland / pile / Website / DigitalTunnel 參考執行。

差異點：
- 各 repo 自己的 service name + port mapping
- 若無 frontend → 跳過 frontend_net
- 若無 worker → 仍保留 worker_net（future-proof）

---

> **核心精神**：4 層分網路不是為了 audit GREEN，是為了**安全邊界 + 觀測精準 + 故障隔離**。
> step 37 是 trigger，真正的價值是降低 postgres 對 frontend 暴露的攻擊面。
