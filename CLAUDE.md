# CK_Missive 公文管理系統 - Claude Code 配置

> **專案代碼**: CK_Missive
> **技術棧**: FastAPI + PostgreSQL + React + TypeScript + Ant Design + Ollama/Groq
> **版本**: v6.65（2026-08-29）/ ⭐⭐⭐**案號體系全庫收斂**：249 筆 legacy 轉 CK 建案制（三表殘留 0）＋15 筆「長得像 PM 卻沒有上游建案」的假案號改 GN；85 筆乾淨成案，而**51 筆機械成案後查出同名同年既有案已整批撤回**——守衛的「同委託單位」條件會被名稱變體騙過（技師本人 vs 事務所、啓/啟相容字）＋⭐⭐**帳本 AR 虛增 1,681 萬**（2 筆毫秒級重複入帳＋1 筆零額）—— 冪等只靠應用層 check-then-insert，0.05 秒的併發就穿過去；已修資料＋加部分唯一索引，**對帳歸零 22,435,123 兩側相等**，而那個對帳告警**連發 5 天無人看**（已接進晨報第 0 段）＋⭐⭐**民國/西元家族一次抓到四例**（client-accounts／vendor-accounts／財務總覽／發票彙總的年度篩選**從來沒有作用過**）——土壤是各端點紀年契約不一，同一支 service 兩種收法＋⭐**A38 完整閉環**：放大器（generator closed）與觸發器（檔名 UTF-8 位元組 > NAME_MAX）都修，**02:00 無人值守實證 attachments 120 → 1,559**＋⭐**owner 走的是內網 :3000 而我一直在驗公網** —— 同一份程式碼兩份事實，frontend 容器改掛 `dist` 收斂（A29 定案）＋⚠️ **我自己的三個「退出碼 0 但什麼都沒發生」**：`docker exec` 少 `-i`（stdin 空跑）／RAISE 用 `%%` 帶參數（PL/pgSQL 編譯期報錯使交易永遠回滾）／`--apply` 印了計畫卻沒實作寫入—— 判準：**寫入後要用新查詢自我複驗，不信任自己的輸出**
> （更早版本的一行摘要同樣在 `docs/MILESTONES_ARCHIVE.md`）
> **最後更新**: 2026-08-29
>
> **近期重大里程碑**：已移至 [`docs/MILESTONES_ARCHIVE.md`](docs/MILESTONES_ARCHIVE.md)
> （2026-08-27，v6.59–v6.61 共 46,981 字元；更早的 64 條 08-24 已先移入）。
> **搬移不是刪除**——內容完整保留，只是不再每個 session 載入一遍。
> 教訓的權威來源是 [`docs/architecture/LESSONS_REGISTRY.md`](docs/architecture/LESSONS_REGISTRY.md)。

---

## 專案概述

CK_Missive 是一套企業級公文管理系統，搭載 Hermes Agent 智慧助理：

1. **公文管理** - 收發文登錄、流水序號自動編排、附件管理
2. **行事曆整合** - 公文截止日追蹤、Google Calendar 雙向同步、批次操作
3. **邀標/報價管理** - 案件建案(case_code)、報價紀錄上傳、承攬狀態追蹤、成案觸發
4. **承攬案件管理** - 成案專案(project_code)、人員配置、里程碑/甘特圖、公文關聯
5. **委託單位/協力廠商** - vendor_type 分離管理、inline 新增、ERP 關聯
6. **AI 代理人** - 26 真工具、自省閉環、主動推薦、Hermes Agent gateway (via ck-missive-bridge skill)
7. **ERP 財務模組** - 費用報銷、統一帳本、財務彙總、電子發票同步
8. **知識圖譜** - Code-graph 5,721 實體、DB/TS/Python AST 入圖

### 多專案架構 (v5.5.6, 2026-04-15 重整)

```
CK_Missive          (本專案·核心) — 公文 AI 引擎 + Hermes Agent 公網入口
CK_lvrland_Webmap   (兄弟專案)    — 土地查估 Webmap (Phase 2+ 接入)
CK_PileMgmt         (兄弟專案)    — 基樁管理 (Phase 2+ 接入)

[已廢止]
CK_OpenClaw         → ADR-0014 Hermes Agent 取代（2026-05-12 歸檔）
CK_NemoClaw         → ADR-0015 Cloudflare Tunnel 取代（2026-05-12 歸檔）
```

### 平台級 Subdomain 策略 (ADR-0016)

```
missive.cksurvey.tw     →  公文系統 (UI + API)，已上線
hermes.cksurvey.tw      →  Hermes Agent gateway (Phase 1 後啟用)
lvrland.cksurvey.tw     →  土地查估，🟢 已上線（SSO 整合）
pilemgmt.cksurvey.tw    →  基樁管理，🟢 已上線（SSO 整合）⚠️ 實際 hostname；規劃曾標 pile.cksurvey.tw 但未部署
digitaltwin.cksurvey.tw →  數位孿生/隧道，🟢 已上線（SSO 整合）
kg.cksurvey.tw          →  聯邦知識圖譜 Hub (選用)
```

> **架構原則**: Cloudflare Tunnel 統一公網入口；Cloudflare Access SSO 跨專案；
> 各專案獨立 DB；Hermes 共用 gateway 跨專案聯邦。零費用全 Free 方案。

### LINE / Telegram 多頻道整合（via Hermes Agent Gateway）

```
LINE 小花貓Aroan → Hermes Agent → skill(ck-missive-bridge) → Missive Agent API
Telegram @Aaron_ckbot → Hermes Agent → skill(ck-missive-bridge) → Missive Agent API
Discord → Interactions Endpoint → Missive Agent API (直連)
```

- Hermes 部署指南: `CK_AaaP/runbooks/hermes-stack/`
- Skill 定義: `docs/hermes-skills/ck-missive-bridge/`
- **重點**: Skill 中 API URL 必須用 `host.docker.internal:8001`（不是 `localhost`）
- **重點**: LINE webhook 需要公網 HTTPS，由 Cloudflare Tunnel 提供

> **歷史**: OpenClaw 整合已於 ADR-0014 廢止（2026-05-12），由 Hermes Agent 取代。
> 舊運維指南: `docs/LINE_OPENCLAW_OPERATIONAL_GUIDE.md`（僅供參考）

---

## 規範索引

> 以下規範位於 `.claude/rules/`，啟動時**自動載入**，無需手動引用。

| 規範檔案 | 說明 |
|---------|------|
| `skills-inventory.md` | Skills / Commands / Agents 完整清單 |
| `hooks-guide.md` | Hooks 自動化配置與協議 |
| `ci-cd.md` | CI/CD 工作流 |
| `auth-environment.md` | 認證與環境檢測規範 |
| `development-rules.md` | 開發強制規範 (SSOT, 型別, API, 服務層, DI) |
| `architecture.md` | 專案結構總覽（索引） |
| `architecture-backend.md` | 後端：Models/Services/API/Repositories |
| `architecture-frontend.md` | 前端：Pages/Hooks/型別/錯誤處理 |
| `directory-structure.md` | `.claude/` 配置目錄結構 |
| `security.md` | 安全規範 |
| `testing.md` | 測試規範 |

### 其他重要文件

| 文件 | 說明 |
|------|------|
| `.claude/MANDATORY_CHECKLIST.md` | ⚠️ 強制性開發檢查清單 (開發前必讀) |
| `.claude/DEVELOPMENT_GUIDELINES.md` | 開發指引與常見錯誤 |
| `.claude/CHANGELOG.md` | 完整版本更新記錄 |

### 架構標準化（v5.9.6 ~ v5.9.8, 2026-04-25）

| 文件 | 說明 |
|------|------|
| `docs/architecture/STANDARD_REFERENCE.md` | 📘 **跨 repo 架構標準** — DDD/SSOT/Hermes/觀測棧 12 章 + §13 AI-Native UX |
| `docs/architecture/SERVICE_CONTEXT_MAP.md` | 🗂 services/ 頂層 85 散戶 × 16 bounded context 映射（漸進 DDD）|
| `docs/architecture/CONSCIOUSNESS_INTEGRATION_ANALYSIS.md` | 🧠 坤哥意識體 5 整合面向 + O1-O6 路線（v5.9.7/v5.9.8 落地紀錄）|
| `docs/architecture/WIKI_KG_BACKFILL_STRATEGY.md` | 📋 Wiki↔KG 三方案 ROI（已執行 X，連結率 30%→86%）|
| `docs/ops/baseline-fix-patch-preview.md` | ⚙️ Hermes baseline 修復 patch 預覽（Patch A+B 三路徑）|
| `scripts/checks/run_fitness.sh` | 🧪 本地 fitness runner — **6 step**（零 CI 費用）|
| `scripts/checks/service_dir_entropy.py` | 📊 services/ 頂層散戶比例（閾值 20%）|
| `scripts/checks/config_dead_reader_scan.py` | 🔍 yaml config dead reader 偵測（含 module function）|
| `scripts/checks/soul_mirror_drift_check.py` | 🔄 SOUL.md 跨 repo drift（fitness step 3）|
| `scripts/checks/wiki_kg_link_audit.py` | 🔗 Wiki↔KG 連結率 by entity_type（fitness step 4）|
| `scripts/checks/kg_embedding_coverage_check.py` | 🎯 KG pgvector 覆蓋率（fitness step 5）|
| `scripts/sync/sync_soul_to_hermes.sh` | 🔁 SOUL.md 跨 repo 手動同步（--apply gate）|
| `scripts/sync/dispatch_kg_ingest.py` | 🆕 方案 X Phase 1 — dispatch → KG ingest |
| `scripts/sync/backfill_wiki_*.py` | 🆕 wiki frontmatter 補 kg_entity_id（dispatch/project）|
| `scripts/sync/backfill_kg_embeddings_all.py` | 🎯 KG embedding 通用 backfill（critical/types/all 模式）|
| `/arch-fitness` slash command | 本地月度架構覆盤觸發 |

### v5.9.8 落地里程碑

- ✅ Wiki↔KG 連結率 **30% → 86%**（dispatch 0% → 100%, project 56% → 86%）
- ✅ KG pgvector embedding 業務 entity **0% → 100%**（10,792 筆 / 5 分鐘 / zero cost）
- ✅ SOUL.md 跨 repo 同步（CK_Missive ↔ CK_AaaP）+ Soul fidelity groq 75% → 80%
- ✅ ADR-0030 GO 條件 4/5 達標（#5 P95 待 5/20 會議重訂方案）

---

## 快速連結

### 開發環境
- 後端 API: http://localhost:8001/docs
- 前端開發: http://localhost:3000
- 資料庫: PostgreSQL **15.14**（image `pgvector/pgvector:0.8.0-pg15`，Docker，**127.0.0.1:5434** 僅本機）
  <!-- 2026-08-10 更正：原記「PostgreSQL 16」與實際不符。這不是無害的筆誤 ——
       備份是 backend 容器的 pg_dump 17.10 產生的，而伺服器是 15.14，
       dump 裡帶著 15 認不得的 transaction_timeout，帶 ON_ERROR_STOP 還原會中止。
       版本記載錯誤會讓人在災難當下判斷錯誤。詳見 docs/runbooks/disaster-recovery.md §4 -->
- 客戶端工具版本落差（**還原時會咬人**）：postgres 容器 psql 15.14／backend 容器 pg_dump·psql **17.10**
- ~~NemoClaw 監控塔: http://localhost:9000~~ — **廢止** (ADR-0015)
- vLLM 本地推理: http://localhost:8000 (Docker, Qwen2.5-7B-AWQ)
- Ollama: http://localhost:11434 (Docker, nomic-embed)

### 常用命令
```powershell
# === 推薦：統一管理腳本 ===
.\scripts\dev\dev-start.ps1              # 混合模式啟動（推薦）
.\scripts\dev\dev-start.ps1 -Status      # 查看所有服務狀態
.\scripts\dev\dev-start.ps1 -Restart     # 重啟 PM2 服務
.\scripts\dev\dev-start.ps1 -FullDocker  # 全 Docker 模式
.\scripts\dev\dev-stop.ps1               # 停止所有服務
.\scripts\dev\dev-stop.ps1 -KeepInfra    # 僅停 PM2，保留 DB/Redis

# === 手動啟動 ===
docker compose -f docker-compose.infra.yml --profile tunnel up -d
# ⚠️ `--profile tunnel` 不可省：`cloudflared` 有 `profiles: ['tunnel']`，
#    不帶它 `up -d` **不會把公網入口建回來**（`config --services` 也不列它）。
#    `restart: unless-stopped` 只救重啟，救不了「容器被移除」。
#    2026-08-26 由 CK_AaaP 指出容器不在 `config --services` 裡而查出。
      # 基礎設施
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8001
cd frontend && npm run dev
pm2 start ecosystem.config.js

# === 公網部署 ===
bash scripts/deploy/deploy-public.sh     # v2.0.0 一鍵：前端 build → 後端 image build（帶 build 身分）
                                         #   → 換容器 → health → 驗 runtime commit → 驗公網 200
                                         # 只改前端：bash scripts/deploy/deploy-public.sh --frontend-only

# === 驗證 ===
cd frontend && npx tsc --noEmit          # TypeScript 檢查
cd backend && python -m py_compile app/main.py  # Python 語法檢查

# === Skills/知識地圖 ===
node .claude/scripts/validate-all.cjs            # Skills/Agents 格式驗證
node .claude/scripts/generate-index.cjs          # 索引重建
node .claude/scripts/generate-knowledge-map.cjs  # 知識地圖生成（全量重建）
node .claude/scripts/generate-knowledge-map.cjs --diff      # 差異報告（Heptabase 增量更新）
node .claude/scripts/generate-knowledge-map.cjs --if-stale  # 僅在源檔案更新時重建
node .claude/scripts/promote-learned-patterns.cjs # 學習模式升級
```

---

## 整合來源

本配置整合以下最佳實踐：

- [claude-code-showcase](https://github.com/ChrisWiles/claude-code-showcase) - Skills/Hooks/Agents/Commands 架構
- [superpowers](https://github.com/obra/superpowers) (v4.0.3) - TDD、系統化除錯、子代理開發
- [everything-claude-code](https://github.com/affaan-m/everything-claude-code) - 生產級工作流自動化

**核心理念**: 測試驅動開發 | 系統化優於臨時性 | 簡潔為首要目標 | 證據優於聲稱

---

> 配置維護: Claude Code Assistant | 版本: v1.86.0
