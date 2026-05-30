# Container Deployment SOP (L51.7.1, 2026-05-30)

> **狀態**: enforced — fitness step 60 自動檢查
> **觸發**: L51 incident #8 — docker cp 修法不持久，image 內 5 防護層舊版 36h silent disabled
> **關聯**: `INCIDENT_REPORT_20260529_LINE_NOTIFY_OUTAGE.md` §10.6 / `.claude/rules/cross-file-ssot-governance.md`

---

## 1. 為何需要這份 SOP

### 1.1 事故時序（L51 incident #8）

```
2026-05-29 13:07  commit 5d03562f — messaging_default.py 加 Prometheus Counter
2026-05-29 13:08  docker cp messaging_default.py → container (驗證 OK)
2026-05-29 ??:??  docker compose restart 後 docker cp 修法 silent 遺失
2026-05-30 09:30  ScheduleWakeup 複查發現 messaging_push_total 完全沒在 /metrics
                  → 揭發 image 內 messaging_default 是舊版（無 Counter）
2026-05-30 10:00  rebuild image 解
                  → 期間 36h 內所有 push 應該 inc counter 但完全沒寫進去
```

### 1.2 為何 docker cp 不可持久

| Docker 操作 | docker cp 修法狀態 |
|---|---|
| `docker exec` / `docker logs` | 保留 |
| `docker compose restart` | **保留**（reload 同 container）|
| `docker compose up -d` 同 image | 保留 |
| `docker compose up -d --force-recreate` | **遺失** |
| `docker compose down + up -d` | **遺失** |
| `docker compose build + up -d` (new image) | **遺失** |
| 容器被 OOM kill 自動重起 | 取決於 restart policy |

→ 任何「從 image 重起 container」都會抹掉 docker cp 修法

### 1.3 影響規模

L51 期間 docker cp 過的檔（已驗證 5/30 已 rebuild 對齊）：
- `messaging_default.py` (5 防護層)
- `scheduler.py` (cron jobs)
- `business_recommendation.py` (v2 SQL)
- `enrichment_review.py` (review queue API)
- `search.py` (PCC 連結)
- `auth/common.py` + `auth/profile.py` (L49.17)
- `tender/metrics.py` (Prometheus counter)

**任何 docker cp 都需要 rebuild image 才算真正落地**。

---

## 2. 標準部署流程（強制 6 步驟）

### 2.1 平常開發 → production

```bash
# 1. 編輯 code
$EDITOR backend/app/services/...

# 2. 本地驗證
python -m py_compile backend/path/to/file.py

# 3. Commit code（保 git 紀錄）
git add ...
git commit -m "..."

# 4. Build image（含新 commit）
docker compose -f docker-compose.production.yml build backend

# 5. Up -d (用新 image 起新 container)
docker compose -f docker-compose.production.yml up -d backend

# 6. 驗證（必跑 fitness step 60）
python scripts/checks/container_image_freshness_check.py
# 期望: 全部 ✓ MATCH

# 7. (optional) Push code
git push origin main
```

### 2.2 緊急修法（docker cp 暫態）

⚠️ docker cp 只可用於：
- 緊急 hotfix 驗證
- 不影響 production 業務的小調整
- 1 hour 內必須跟 rebuild 後 deploy

```bash
# 1. docker cp 修法
MSYS_NO_PATHCONV=1 docker cp ./fixed.py ck_missive_backend:/app/path/to/file.py

# 2. 立刻 commit + rebuild + redeploy（不可拖）
git add ... && git commit ...
docker compose -f docker-compose.production.yml build backend
docker compose -f docker-compose.production.yml up -d backend

# 3. 驗 fitness step 60 確認對齊
python scripts/checks/container_image_freshness_check.py
```

**絕對禁止**：
- ❌ docker cp 後不 rebuild 就放著
- ❌ 多人協作時其他人 docker compose down/up 抹掉 docker cp
- ❌ 用「docker cp 跑通」當作 PR merge 條件

---

## 3. 防護機制（已落地）

### 3.1 Fitness step 60 — container_image_freshness_check

```bash
python scripts/checks/container_image_freshness_check.py
```

對 11 個 critical 檔做 md5 比對 host vs container。
**任何 drift → RED**，提示「docker cp 未跟 rebuild」。

### 3.2 Pre-deploy git hook（建議性）

可考慮加 `.git/hooks/pre-push`：
```bash
#!/bin/sh
# 警告：commit 但 image 未 rebuild
LAST_COMMIT=$(git log -1 --pretty=%ai -- backend/)
IMAGE_BUILT=$(docker inspect ck-missive-backend:production \
              --format '{{.Created}}' 2>/dev/null)
if [ -n "$IMAGE_BUILT" ] && [ "$LAST_COMMIT" \> "$IMAGE_BUILT" ]; then
    echo "⚠ backend/ commit 後尚未 rebuild image"
    echo "  建議: docker compose build backend && up -d backend"
fi
```

### 3.3 Monthly fitness function

`scripts/checks/run_fitness.sh` step 60 已加入，每月架構覆盤即跑。

---

## 4. 連帶教訓（寫入 lessons）

### L51 incident #8 升級為通用原則：

> **「修法部署成功」不等於「修法真活」**
> — 必須驗證 container 內檔內容 = host code

| 部署層 | 驗證方式 |
|---|---|
| commit | `git log --oneline -1` |
| image build | `docker images ck-missive-backend:production` |
| container 起 | `docker ps` |
| **container 內檔** | **`fitness step 60` md5 比對** ← 之前缺這層 |
| 業務邏輯真活 | manual test or smoke test |
| 觀測閉環 | metric + history table |

---

## 5. 對齊 cross-file-ssot-governance（第 6 類）

`.claude/rules/cross-file-ssot-governance.md` 既有 5 類跨檔資源：
1. Secrets (.env vs Docker Secrets)
2. Volumes
3. Ports
4. Endpoints
5. Network names

**新增第 6 類**：
6. **Container image content vs Source code**
   - SSOT：git HEAD 內 `backend/` 目錄
   - Audit script：`container_image_freshness_check.py`
   - Fitness step：60
   - 違反風險：silent dormant 36h+（L51 同型）

---

## 6. 落地檢查清單（給 PR Reviewer）

每個觸碰 backend container 的 PR 必檢：

- [ ] 程式碼變動已 `git commit`
- [ ] `docker compose build backend` 已跑
- [ ] `docker compose up -d backend` 已跑
- [ ] `python scripts/checks/container_image_freshness_check.py` 全 ✓
- [ ] 業務 smoke test 通過（如改 endpoint）
- [ ] 觀測指標真活（如改 metric counter）

---

## 7. Refs

- L51 incident: `INCIDENT_REPORT_20260529_LINE_NOTIFY_OUTAGE.md` §10.6 + 啟示 #8
- Fitness step 60: `scripts/checks/container_image_freshness_check.py`
- 跨檔 SSOT: `.claude/rules/cross-file-ssot-governance.md`
- Sprint 1+2+3 commits: `a8c27319` `8aab4d18` `2971482b`
