# ADR CK_Missive#0044: Docker Volume Name SSOT（compose `name:` 對齊 + Orphan 治理）

> **狀態**: accepted — 2026-05-22（step 38 已存在 + L43 fix + ghost cleanup 完成）
> **日期**: 2026-05-22
> **決策者**: @bluefishs（v6.11 候選）
> **接通完整度**: L2（含 fitness step 38 自動驗證 + ghost cleanup runbook）
> **關聯**:
> - L43 lesson: volume mount drift silent fail
> - L45 lesson（隱式）: frontend healthcheck override（L43 family 第 4 case）
> - ADR CK_AaaP#0043: 跨 repo Docker Network Standard（三件套同模式）
> - 配套 fitness step 38: `scripts/checks/docker_compose_volume_consistency.py`
> - 配套 registry: `docs/architecture/volume-registry.md`

---

## 背景

### L43 事故觸發（2026-05-21）

`docker-compose.production.yml` 寫 `name: ck_missive_postgres_data`（空殼 17 tables）
而 `dev.yml` / `infra.yml` 寫 `name: ck_missive_postgres_dev_data`（真實主庫 75 tables / 1788 docs）。
切換 production compose 啟動時 postgres 掛到空殼，業務 API 全 500，dormant ~10 小時。

詳見 [[lesson_l43_volume_mount_drift_silent_fail]] + `wiki/memory/diary/2026-05-21.md`。

### L45（隱式）— Frontend Healthcheck Override（2026-05-22）

`docker-compose.production.yml` 用 `wget http://localhost:80` override 了 Dockerfile 正確的
`wget http://127.0.0.1:3000/nginx-health`，造成 nginx 真實 serve 但 healthcheck 永遠 fail
（FailingStreak=36 / 18 分鐘 unhealthy）。屬「跨檔 SSOT 失效」family 第 4 case
（前 3：L41 secret / L43 volume / L44 auth state）。

### 5/22 Orphan Audit 揭發

`docker volume ls` vs `compose declared` 對比後揭發本 repo 5 個 candidate orphan：
- `CK_Missive_postgres_data`（63MB，2025-09 早期大寫前綴遺留）— **已 cleanup**
- `ck_missive_redis_dev_data`（512K，5/21 dev cache 殘留）— **已 cleanup**
- `ck_missive_postgres_data`（小寫，5/21 incident 17 tables 空殼）— **incident 證物，待 owner 確認**
- `ck_missive_backend_logs_dev` / `backend_uploads_dev` / `frontend_logs_dev` / `nim_dev_cache`
  — dev compose 在用但 audit prefix 規則 false positive，列入 allowlist 待強化

---

## 決策

### 1. Volume `name:` 對齊 SSOT

**所有 compose 內同邏輯 volume 必須顯式宣告 `name:` 並對齊跨 compose 一致**：

```yaml
# ✅ Good - 跨 compose 同 logical key 對齊
# docker-compose.production.yml
volumes:
  postgres_data:
    name: ck_missive_postgres_dev_data   # 對齊 dev/infra
    external: true                        # 防 compose down 誤殺

# docker-compose.dev.yml
volumes:
  postgres_dev_data:
    name: ck_missive_postgres_dev_data   # 同 name
```

```yaml
# ❌ Bad - 同邏輯但 name 不同（L43 反模式）
# production
volumes:
  postgres_data:
    name: ck_missive_postgres_data         # 空殼
# dev
volumes:
  postgres_dev_data:
    name: ck_missive_postgres_dev_data     # 真實
```

### 2. 禁止依賴 compose project_name 自動生成

`COMPOSE_PROJECT_NAME` env var 大小寫變體會產生 ghost（5/22 揭發 `CK_Missive_postgres_data`
大寫 prefix orphan 即此模式）。**統一顯式 `name:`** 而非 fallback `<project>_<alias>` 自動生成。

### 3. Orphan Governance 三步驟

| 階段 | 做什麼 | 工具 |
|---|---|---|
| 偵測 | fitness step 38 跑（每月 / pre-commit / 大重構前）| `docker_compose_volume_consistency.py` |
| 留底 | tar 壓縮 + MD5 + README + NAS 異地（仿 5/22 模式）| `backup/ghost_volume_cleanup_<date>/` |
| 刪除 | `docker volume rm <name>` | docker CLI |

### 4. Backup-before-Delete 強制

刪除任何 named volume（不論大小）前必須：
1. `docker run --rm -v <name>:/d:ro -v <backup>:/out alpine tar czf /out/<name>.tar.gz -C / d`
2. MD5 雙端驗證
3. README.md 記錄理由 + 還原指令
4. NAS 異地（若 > 1MB）

範本：`backup/ghost_volume_cleanup_20260522/README.md`

### 5. Healthcheck 也適用 SSOT 原則（L45 延伸）

Dockerfile 內的 HEALTHCHECK 是 SSOT；compose 不應 override 除非有明確理由。
若 override，必須與 Dockerfile 邏輯等價（同 port / 同 path / 同 timeout）。
建議：**compose 不寫 healthcheck**，讓 Dockerfile HEALTHCHECK 生效。

---

## 後果

### 正面
- L43 同型事故結構性防範（fitness step 38 跑 → drift 立 fail）
- Orphan 可治理：5/22 cleanup 2 個 ghost（63MB + 512K）+ tar 留底 + NAS
- 命名一致性提升：禁止大小寫變體 / 強制顯式 `name:`
- Healthcheck SSOT（L45 延伸）：避免 compose override 反模式
- 跨 repo 可複製範本：install-template-to.sh 加 ADR-0044 模式

### 負面
- orphan detection 在 dev 環境 false positive（dev compose 用但 production compose 沒，
  step 38 預設掃所有 compose 聚合 declared set 可緩解，但仍需 allowlist 機制）
- backup-before-delete 增加 ops effort（小 volume 也要 tar）
- 強制顯式 `name:` 需審視所有 existing compose（一次性遷移成本）

---

## §How to Apply（強制；v6.11+ 新 volume 採用）

### A. 程式碼接通完整度
- [x] 標準文件（本 ADR）
- [x] `scripts/checks/docker_compose_volume_consistency.py`（step 38）含 orphan detection
- [x] `docs/architecture/volume-registry.md`（本 repo volume 盤點 + 歷史 ghost 紀錄）
- [x] `backup/ghost_volume_cleanup_20260522/`（cleanup 範本）
- [ ] `scripts/install-template-to.sh` 加 ADR-0044 範本部署（v6.11 W1）

### B. 自動驗證機制
- [x] step 38 跑於 `scripts/checks/run_fitness.sh`（月度 / 大重構前）
- [x] step 38 加 `--strict` flag（orphan + drift 都 exit 2）
- [ ] pre-commit hook 加 step 38（任何 docker-compose*.yml 改動觸發；v6.11 W2）
- [ ] Prometheus alert: `docker_volume_orphan_count > 0 for 7d`（v6.11 W2）

### C. 邊角組合識別
- [x] 同邏輯 volume 跨 compose `name:` 不對齊（L43 範例）
- [x] `COMPOSE_PROJECT_NAME` 大小寫變體產生 ghost（5/22 範例）
- [x] compose healthcheck override Dockerfile HEALTHCHECK（L45 範例）
- [ ] PM2 + Docker 雙 backend 共用 host port（next_session_resume §架構級議題；ADR-0045 規劃）

### D. 上線後 7 天追蹤
- [x] 2026-05-22 audit 跑 → 5 candidate orphan 揭發 → 2 個 cleanup 完成
- [ ] 2026-05-29 audit 跑 → 確認 0 新 orphan + step 38 GREEN
- [ ] frontend healthcheck commit 後 7 天無 false alarm 復發
- [ ] 任何新 service 加入 docker-compose.production.yml 必跑 step 38

### E. 文件對齊
- [x] 本 ADR
- [x] `docs/architecture/volume-registry.md`
- [ ] CHANGELOG v6.11 章節記 ADR-0044 + 5/22 ghost cleanup（owner 決定 commit 後）
- [ ] CK_AaaP REGISTRY.md 加引用（若採跨 repo 範本）

---

## 與其他 ADR 關係

| ADR | 關係 |
|---|---|
| CK_AaaP#0043 | 同三件套模式（ADR + registry + audit）；ADR-0044 為 volume 版 |
| CK_Missive#0028 | 錯誤合約化 — L43/L45 silent failure 屬此政策延伸 |
| CK_Missive#0029 | ADR Lifecycle — 本 ADR 加入 active 計數（5/22 後 17 active） |
| ADR-0045（規劃中） | PM2 vs Docker backend 二選一（架構級 SSOT 議題） |

---

## Sealed Knowledge

1. **跨檔資源命名 SSOT** 必走 ADR + Registry + Audit Script 三件套
   （L41/L43/L45 共同根因；ADR-0043 為 network 版，本 ADR 為 volume 版）
2. **「健康」必須帶業務語意**（row count / response 完整性 / endpoint 真活）
   — 不是 process 存在 / connection ok / container Up
3. **Backup 不救命名 drift** — 備份救「資料消失」，不救「掛錯 volume」；
   命名 SSOT 才是根本對策
4. **Compose override Dockerfile HEALTHCHECK 是反模式**（L45 sealed）— 預設讓 Dockerfile 生效
