# v6.11 整合優化程序 (Integrated Governance Procedure)

> **狀態**: enforced — v6.11 收尾整合
> **作用域**: 從 L51 LINE 事故起，整合所有 L51.x 議題的治理規範
> **觸發**: Owner 要求「持續推進與整合優化程序」
> **生效**: 2026-05-30

---

## 1. v6.11 議題全景（L51 事故樹）

L51 一個 LINE 訊息事故引爆，揭發 8 層潛伏問題並完成系統性治理：

```
L51   LINE 通報 silent disabled 40h
├── L51.1 (root cause): docker-compose 缺 LINE_* env
├── L51.2: 影響範圍 29 個 env vars 補全
├── L51.3: PCC 雙連結 + ezbid→PCC 碼映射
├── L51.4: 業務推薦 v2 整合訂閱關鍵字
├── L51.5: /tender/recommend 統一 v2 SQL
├── L51.6: 排除財物類 + frontend 三重信號 tag
├── L51.7: 坤哥服務鏈覆盤 + 15 任務 Sprint 1-3
│   ├── Sprint 1 (6/6): v7 metric 修 / SOUL sync / cron / fitness
│   ├── Sprint 2 (5/6): scripts mount / LINE→Web / autobiography hook / diary density / critique prompt
│   └── Sprint 3 (1/3): 坤哥週學習摘要 cron
└── L51.7.1: docker cp 不持久 incident #8 → SOP + fitness step 60
```

---

## 2. 完整資產清單

### 2.1 Fitness Steps（60 步，本批 +3）

| Step | 名稱 | 觸發 |
|---|---|---|
| 57 | container env alignment audit | L51.1 |
| 58 | agent_query starvation | L51.7 Sprint 1 |
| 59 | diary density audit | L51.7 Sprint 2 |
| **60** | **container image freshness** | **L51.7.1** |

### 2.2 Audit Scripts（本批 +4）

| Script | 目的 |
|---|---|
| `container_env_alignment_audit.py` | host .env vs compose env |
| `agent_query_starvation_check.py` | shadow baseline 24h n=0 偵測 |
| `diary_density_audit.py` | diary entry entity tag % |
| `container_image_freshness_check.py` | image vs source md5 比對 |

### 2.3 Cron Jobs（本批 +3）

| Cron | 時程 | 用途 |
|---|---|---|
| `tender_dashboard_warm` | 每 5 min | dashboard cache 預熱 |
| `crystal_review_overdue` | 週日 09:30 | proposals 死局防護 |
| `kunge_weekly_learning_summary` | 週日 11:00 | 坤哥學到什麼摘要 |
| `line_weekly_pulse` | 週日 10:00 | LINE 鏈活體確認 |

### 2.4 SOP / Governance Docs（本批 +5）

| Doc | 主軸 |
|---|---|
| `INCIDENT_REPORT_20260529_LINE_NOTIFY_OUTAGE.md` | 11 章 + 8 啟示 |
| `TENDER_PCC_COVERAGE_AUDIT_20260529.md` | PCC budget 100% NULL 警示 |
| `KUNGE_AGENT_CHAIN_REVIEW_20260530.md` | 5 層架構 + 3 路線提案 |
| `KUNGE_FOLLOWUP_PLAN_20260530.md` | 3 件 v6.12 推遲 |
| `CONTAINER_DEPLOYMENT_SOP.md` | 強制 6 步驟部署 |

### 2.5 Tables（本批 +2）

| Table | 用途 |
|---|---|
| `tender_recommendation_history` | LINE 推送觀測閉環（揭發 L51 真因）|
| `tender_match_review` | enrichment MEDIUM admin review queue |

### 2.6 Prometheus Metrics（本批 +5+）

| Metric | 用途 |
|---|---|
| `messaging_push_total{channel, result}` | 15 labels (3 ch × 5 result) |
| `tender_recommendations_total{result}` | LINE 推送 4 result |
| `tender_recommendations_last_run_timestamp` | cron 真活 |
| `tender_page_view_total{page}` | 7 page L31 ROI 治理 |
| `v7_channel_diversity` (修法後) | 從 messaging_push_total 取 |

---

## 3. 治理流程（強制 SOP）

### 3.1 標準部署 6 步驟（CONTAINER_DEPLOYMENT_SOP.md 規範）

```bash
1. edit code
2. python -m py_compile (本地語法檢查)
3. git commit (保 history)
4. docker compose build {service}  # rebuild image
5. docker compose up -d {service}   # 用新 image 起 container
6. python scripts/checks/container_image_freshness_check.py  # 驗 fitness 60
```

### 3.2 新 env var 6 步驟（incident report §7）

```
1. .env (實際值)
2. .env.example (範本)
3. docker-compose.production.yml backend.environment
4. docker-compose.dev.yml (若有)
5. docker exec backend env | grep VAR (驗注入)
6. startup probe (critical config 缺失即 raise)
```

### 3.3 跨檔 SSOT 治理（cross-file-ssot-governance.md，6 類）

| # | 資源 | SSOT 位置 |
|---|---|---|
| 1 | Secrets | `.env` |
| 2 | Volumes | `docker-compose.production.yml name:` |
| 3 | Ports | `Dockerfile EXPOSE` |
| 4 | Endpoints | `frontend/src/api/endpoints/*.ts` |
| 5 | Network names | `docker-compose.production.yml networks:` |
| **6** | **Container image content**（L51.7.1 新增）| **git HEAD `backend/`** |

### 3.4 ADR 升級 L1 → L2 SOP（adr-anti-half-wired-sop.md）

| 級別 | 要求 |
|---|---|
| L1 | 決策紀錄 |
| L2 | 主路徑實作 + fitness audit + unit test 鎖核心 + 7d owner check-in |
| L3 | 半接通風險（已實作但無自動驗證） |
| L4 | 高風險 + 邊角 + 無驗證 |

範例：ADR-0046 L1 → L2 升級（34 unit tests 鎖定 false positive guard）

---

## 4. 維運程序時間表

### 4.1 每日

| 時間 | Job |
|---|---|
| 00:30 | 夜間吹哨者（含派工進度 LINE Flex）|
| 03:30 | ezbid → PCC enrichment |
| 04:30 | KG embedding 回填 |
| 04:45 | Embedding warmup |
| 08:00 | 每日晨報 LINE 推送 |
| 09:00 | 業務推薦 LINE 推送 (6 筆) |
| 09:00/14:00/20:00 | synthetic baseline inject |
| 22:00 | daily self-reflection LINE |
| 每 5 min | tender dashboard warm |
| 每 1 hr | ezbid 快取刷新 |

### 4.2 每週

| 時間 | Job |
|---|---|
| 週日 09:30 | crystal review overdue alarm |
| 週日 10:00 | LINE weekly pulse |
| 週日 11:00 | **坤哥這週學到什麼**（新）|
| 週日 18:00 | autobiography → SOUL sync reminder |
| 週一 06:00 | anti_echo + critique starvation prompt |

### 4.3 每月

```bash
bash scripts/checks/run_fitness.sh        # 60 step 全跑
bash scripts/checks/run_fitness.sh --strict  # 嚴格模式
```

關鍵 step 觀察：
- step 3 (SOUL drift) — 跨 repo 一致性
- step 4 (Wiki↔KG link audit) — 連結率 ≥86%
- step 5 (KG embedding 覆蓋率) — 91%+
- step 57 (container env alignment) — 0 RED
- step 58 (agent_query starvation) — shadow baseline 累積
- step 59 (diary density) — ≥30% 目標
- step 60 (container image freshness) — 11/11 match

### 4.4 每季

| 任務 | 內容 |
|---|---|
| ADR audit | active 數量治理（目標 ≤16）|
| Lessons review | LESSONS_REGISTRY 跨 session 知識傳承 |
| v7.0 baseline | 4 指標達標檢視 |
| Hermes baseline | ADR-0030 重訂（v6.12 P3.15）|

---

## 5. 觀測閉環優先級（L51 教訓）

### 5.1 silent failure 防護順序

```
Tier 1 (最強，必做):
  - 業務 history table (取代 Redis 過期就消失)
  - Prometheus counter 預宣告全 labels (避「metric 不存在」假象)
  - error_msg 文字級紀錄 (取代 boolean)

Tier 2 (強，重要功能):
  - fitness step 自動偵測 (取代靠人發現)
  - weekly pulse 活體確認 (連續 N 週 silent → owner 察覺)
  - cron 內 startup +15s 立即 trigger (避 first hit cold)

Tier 3 (建議):
  - startup probe (critical config 缺失即 critical log)
  - audit script 月跑
  - cross-repo sync 主動 push
```

### 5.2 silent failure 修法 SOP

當揭發 silent failure 時：

```
1. 列出受影響鏈 (不只觸發者，全 root cause 鏈)
2. fitness step 自動偵測同類事故
3. observability 改善（history table / metric / alarm）
4. SOP doc 寫進規範
5. cross-file-ssot-governance 加新類別（若是跨檔資源）
6. 7d 後 owner check-in 確認真活
```

L51 範例：
- 受影響鏈: 5 條 LINE push（不只 business_recommendation）
- fitness: step 57 container env audit
- observability: tender_recommendation_history table
- SOP: env var 6 步驟同步檢查清單
- cross-file: 第 6 類 container image content
- check-in: 7d 後查 v7_channel_diversity 是否 ≥1

---

## 6. v6.11 收尾里程碑

| 項目 | 數值 |
|---|---|
| Fitness steps | 60（從 v6.10 的 32 增到 60，本批 +3）|
| 跨檔 SSOT 類別 | 6（本批 +1）|
| Audit scripts | 38 個（本批 +4）|
| Cron jobs | ~25 個（本批 +3）|
| Critical incident reports | 1 (L51) |
| 完整 SOP docs | 5 |
| Lessons accumulated | L41-L51 family 共 8 條 |
| ADR active | 16（治理區間內）|

---

## 7. v6.12 規劃（推遲議題）

### 7.1 P1.7 — 12 facade importer 收口（≥3 per facade）

工作量 ~3 天，目標：9/12 facades 從 1 importer → ≥3

### 7.2 P3.14 — /kunge UX 重設計

工作量 ~1-2 週，目標：啟動 agent_query 7d ≥10

### 7.3 P3.15 — Hermes baseline 重訂

需 4 週累積數據（依賴 synthetic_baseline_inject 持續累積）

### 7.4 其他

- pre-push git hook 落地（image staleness 警告）
- PR template 加 deploy verification checklist
- alertmanager rule（messaging_push_failure_rate >50%/1h）

---

## 8. 結語：觀測閉環邊際價值

L51 一個 LINE 訊息事故，從「6 筆 silent failure」開始：

```
business_recommendation cron 6/6 error
    ↓ 觀測閉環揭發
全 LINE push 鏈 silent disabled 40h
    ↓ 擴大盤點
6 條鏈受影響
    ↓ 真因追查
docker-compose 缺 8 個 LINE_* env
    ↓ 治理動作回退
OA-3 PM2 廢除引爆
    ↓ 防護完整化
fitness step 57 container env audit
    ↓ 再次發現
docker cp 不持久 → 5 防護層 36h silent
    ↓ SOP 落地
fitness step 60 container image freshness
    ↓ 整合
v6.11 治理流程升級
```

**單一 design choice（tender_recommendation_history table）連帶解了 5+ 個潛伏問題**。

未來新功能上線前的設計問題：
- **「如果這個失敗了，下一個人怎麼知道？」**

這就是觀測閉環的核心價值。

---

## 9. Refs

- L51 主修法: `706b2e22` → `14c38e15`（18 個 commits）
- 完整 commit log: `git log --oneline 706b2e22..HEAD`
- Fitness 全跑: `bash scripts/checks/run_fitness.sh`
- 治理規範:
  - `.claude/rules/cross-file-ssot-governance.md`
  - `.claude/rules/adr-anti-half-wired-sop.md`
  - `docs/architecture/CONTAINER_DEPLOYMENT_SOP.md`
- 事故報告: `docs/architecture/INCIDENT_REPORT_20260529_LINE_NOTIFY_OUTAGE.md`
- v6.12 路線: `docs/architecture/KUNGE_FOLLOWUP_PLAN_20260530.md`
