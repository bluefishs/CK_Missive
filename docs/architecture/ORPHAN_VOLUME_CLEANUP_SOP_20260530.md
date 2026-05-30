# Orphan Volume 清理 SOP — 2026-05-30

> **觸發**：fitness step 38 (`docker_compose_volume_consistency.py`) 揭發 5 個 orphan volume
> **狀態**：待 owner approve（涉及 volume 刪除不可逆）
> **設計理念**：對齊 L43 教訓 — volume 刪除前必先 backup + 雙端驗證

---

## 5 個 Orphan Volume 真實內容

| Volume | 容量 | 內容 | 風險等級 | 建議動作 |
|---|---|---|---|---|
| `ck_missive_backend_logs_dev` | **62.9M** | api.log / database.log / errors.log | 🟢 LOW | 直接刪除（純 dev log）|
| `ck_missive_backend_uploads_dev` | 4K | 空 | 🟢 LOW | 直接刪除 |
| `ck_missive_frontend_logs_dev` | 4K | 空 | 🟢 LOW | 直接刪除 |
| `ck_missive_nim_dev_cache` | **5.8G** | huggingface / local_cache / ngc | 🟡 MED | 確認 NIM 不再使用後刪除（節省 5.8G）|
| `ck_missive_postgres_data` | **63.6M** | PG_VERSION / base / global | 🔴 HIGH | L43 災難案例 — 必須先 tar 備份 + 雙端驗證後再刪 |

---

## 清理 SOP（依風險等級分階段）

### 階段 1：低風險 3 volume 直接清理

```bash
# 1. 先 tar 備份到 host (即使空也保留 audit 跡證)
mkdir -p backup/orphan_volumes_20260530
for v in ck_missive_backend_logs_dev ck_missive_backend_uploads_dev ck_missive_frontend_logs_dev; do
  docker run --rm \
    -v "${v}:/d:ro" \
    -v "$(pwd)/backup/orphan_volumes_20260530:/backup" \
    alpine tar czf "/backup/${v}.tar.gz" -C /d .
done

# 2. 刪除
for v in ck_missive_backend_logs_dev ck_missive_backend_uploads_dev ck_missive_frontend_logs_dev; do
  docker volume rm "$v"
done

# 3. 驗證
docker volume ls | grep "ck_missive_backend_logs_dev\|ck_missive_backend_uploads_dev\|ck_missive_frontend_logs_dev"
# 預期: 無輸出
```

### 階段 2：中風險 NIM cache 確認後清理

**前置確認**：
```bash
# 確認 NIM 不再使用
grep -r "NIM_BASE\|nvidia.*nim" backend/app/ --include="*.py" 2>&1 | head -5
# 確認 .env 內 NIM_* 是否仍 active
grep "NIM" .env
```

若確認 NIM 已停用：
```bash
# 5.8G 大 → 跳過 tar (太耗時)，直接刪
docker volume rm ck_missive_nim_dev_cache
```

若仍使用 → 加進 docker-compose.yml 收編：
```yaml
volumes:
  nim_cache:
    external: true
    name: ck_missive_nim_dev_cache
```

### 階段 3：高風險 postgres_data 必經 L43 SOP

**前置條件**（任一不滿足 → STOP）：

- [ ] 確認當前 production 用 `ck_missive_postgres_dev_data`（L43 已修）
- [ ] `docker_compose_volume_consistency.py` 重跑確認 `ck_missive_postgres_data` 仍 orphan
- [ ] 該 volume 內無業務資料（L43 災難來源）

**操作 SOP**：
```bash
# 1. tar 備份（必走 — L43 災難級教訓）
mkdir -p backup/orphan_volumes_20260530
docker run --rm \
  -v "ck_missive_postgres_data:/d:ro" \
  -v "$(pwd)/backup/orphan_volumes_20260530:/backup" \
  alpine tar czf "/backup/ck_missive_postgres_data.tar.gz" -C /d .

# 2. MD5 雙端驗證
md5sum backup/orphan_volumes_20260530/ck_missive_postgres_data.tar.gz

# 3. 用 alpine 看 PG_VERSION 確認版本
docker run --rm -v "ck_missive_postgres_data:/d:ro" alpine cat /d/PG_VERSION

# 4. 若版本對齊既有備份策略且 owner 確認 → 刪
docker volume rm ck_missive_postgres_data

# 5. 7 天後重 audit 確認 row_count 真實不變
curl -s http://localhost:8001/health | python -c "import sys,json; d=json.load(sys.stdin); print(d['business_data'])"
# 預期 documents 1809 / canonical_entities 24535 不變
```

---

## 自動化偵測（fitness step 配套）

`scripts/checks/docker_compose_volume_consistency.py` 已偵測 orphan。
本批不新增 step，留 SOP 文件待 owner approve 後執行。

清理完成後再跑：
```bash
python scripts/checks/docker_compose_volume_consistency.py --strict
# 預期 0 orphan
```

---

## 預估效益

| 階段 | 釋出空間 | 風險 | 工時 |
|---|---|---|---|
| 階段 1（3 空 volume） | ~63MB | 🟢 LOW | 5 min |
| 階段 2（NIM cache） | 5.8GB | 🟡 MED | 10 min |
| 階段 3（postgres）| ~64MB | 🔴 HIGH | 30 min（含驗證） |
| **合計** | **~5.9GB** | 混合 | ~45 min |

---

## 失敗回滾 SOP

若刪除後業務異常：
```bash
# 用 tar 還原
docker volume create <name>
docker run --rm \
  -v "<name>:/d" \
  -v "$(pwd)/backup/orphan_volumes_20260530:/backup:ro" \
  alpine tar xzf "/backup/<name>.tar.gz" -C /d
```

---

## 對齊 L43 教訓核心

L43 揭發 5 重 silent fallback：
1. compose 雙軌 volume name
2. postgres init.sql 不報錯
3. alembic 不需資料
4. healthcheck 不檢業務量
5. Prometheus 無 row count alert

本 SOP 對齊：
- 階段 3 強制 `/health` business_data 驗證（對應 L43 防禦層 2）
- tar + MD5 雙端驗證（對應 L43 修法 SOP）
- 7 天後重 audit row_count（對應 L43 防禦層 4）

---

## Owner Action 必要決策

| 決策點 | 選項 |
|---|---|
| 是否執行階段 1 | approve / hold |
| 是否執行階段 2 NIM | approve / 收編 / hold |
| 是否執行階段 3 postgres | approve（含 L43 SOP）/ hold |

請 owner 透過 LINE 回覆執行範圍。

---

> **核心精神**：volume 刪除不可逆。對齊 v6.12 第 4 句立法「修法不可逆，60 天 trial 是保險」。
> 本 SOP 用 tar 備份代替 60 天 trial — 可立即驗證，可立即回滾。
