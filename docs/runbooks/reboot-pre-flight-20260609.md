# 重啟前 Pre-Flight + 重啟後驗收 — 2026-06-09 (v6.15)

> 對齊：reboot-pre-flight-20260602.md / L43 volume drift 防範 / 本日 6 commits (v6.15)
> 主軸：wiki created preserve + failure tracker 收斂 + a18f229167 路由 false-positive 修

## 0. 重啟前快照（2026-06-09 15:20 真實實測）

### Git
- working tree clean（`git status --short` = 0）
- `origin/main..HEAD` 空（全同步，push 至 `33aba6d5`）

### 容器版本 + 健康（實測）
| 容器 | Image | 狀態 | restart policy |
|---|---|---|---|
| ck_missive_backend | `ck-missive-backend:production` | healthy（本日 rebuild）| always |
| ck_missive_frontend | `ck-missive-frontend:production` | healthy | always |
| ck_missive_postgres | `pgvector/pgvector:0.8.0-pg15` | healthy | always |
| ck_missive_redis | `redis:7-alpine` | healthy | always |
| ck_missive_cloudflared | `cloudflare/cloudflared:2026.5.0`（pin✓）| Up | unless-stopped |
| ck-ollama | `ollama/ollama` v0.20.0 | healthy（host:11434）| unless-stopped |

> 全 always/unless-stopped → 重啟後 Docker daemon 自動 boot。
> ⚠️ `ck_missive_ollama_dev`（Created/orphan，非運行）= 無關殘留，可選 `docker rm ck_missive_ollama_dev`。

### 後端代碼烘入驗證（content-level md5 host=container，重啟後從 image boot 故必驗）
- `pattern_extractor.py` ✓ MATCH
- `agent_router.py` ✓ MATCH
- `compiler.py` ✓ MATCH
- image created 2026-06-09T07:08Z（= 本日 v6.15 rebuild）

### DB volume（避 L43 ghost）
- postgres mount = `ck_missive_postgres_dev_data` ✓（真實資料卷，非空殼 `ck_missive_postgres_data`）
- `/health` business_data: documents **1837** / canonical_entities **26643**（GO）

### 前端部署
- frontend image production（4 天前 build；本日無前端 code 變更，無需重 build）

## 1. 本日 6 commits 摘要（v6.15）
- `25398354` 06-08 cron 產出歸檔（wiki 209 重編譯 + SOUL W23 + 儀表板）
- `8c183ca7` CLAUDE 06-09 覆盤 delta
- `5f47f326` **fix(wiki)**: compiler preserve 既有 created（_write_page，17 寫檔收口 + regression 3）
- `b6347d3c` **fix(memory+router)**: failure tracker 收斂（chitchat 過濾 + expire_stale_failures）+ a18f229167 Layer 1.55 doc_related_filter + 退回 713394（regression 26）
- `33aba6d5` chore: expire 7 stale failures（active_failures 13→6）+ cron 副產物
- （CLAUDE.md v6.15 delta + 本 runbook 待 commit）

## 2. 重啟後驗收（5 步 SOP）
```bash
# Test 1: 基礎服務 boot（docker daemon 自動拉起 always 容器）
docker ps --filter name=ck_missive --format '{{.Names}} {{.Status}}'  # 5 容器 + ck-ollama healthy
# Test 2: /health 業務量（防 L43 ghost volume）
curl -s http://localhost:8001/health | grep -o '"documents":[0-9]*'   # 期待 >= 1837
# Test 3: ollama 真活（embedding 768D 依賴）
curl -s http://localhost:11434/api/version                            # 期待 0.20.0
# Test 4: v6.15 新碼 live（路由 false-positive 修）
docker exec ck_missive_backend python -c "import asyncio;from app.services.ai.agent.agent_router import AgentRouter;print([c['name'] for c in (asyncio.run(AgentRouter().route('桃園市工務局相關公文')).plan or {}).get('tool_calls',[])])"
# 期待 ['search_documents']（非 search_across_graphs）
# Test 5: business endpoint smoke + 公網
#   瀏覽器硬重新整理 missive.cksurvey.tw → 登入正常 / kunge 5 tab 不崩
```

## 3. 重啟後若異常 SOP
- 容器未起：`cd D:\CKProject\CK_Missive && docker compose -f docker-compose.production.yml up -d`
- /health 503 或 documents 異常少 → 立查 postgres volume 是否掛回 `ck_missive_postgres_dev_data`（L43）
- ollama 未起：`docker start ck-ollama`（host 端推論依賴）
- 公網 502 → cloudflared 重連需數十秒；逾時 `docker restart ck_missive_cloudflared`

## 4. 仍待 owner / 後續（不影響重啟）
- W23 soul 提案批/退（底層失敗已收斂，可考慮退回裝飾性提案）
- gemma4:e2b 7.2GB VRAM 保溫矛盾（synthesis 零成本最佳槓桿）
- 2 既有 test isolation 修（monkeypatch FAILURES_DIR）
- wiki `created` preserve 生效在下次 recompile（週一 05:00）

---
> **重啟授權狀態**：✅ Pre-Flight 全通過（git 同步 / 6 容器 healthy / restart policy 自動 boot / v6.15 代碼烘入 md5 MATCH / DB 正確卷 1837 docs / cloudflared+postgres pin）
> **重啟後第一步**：跑 Test 1-5，確認自動 boot 全綠 + v6.15 路由修法 live。
