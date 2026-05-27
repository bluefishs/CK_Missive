# CK_Missive 公文管理系統 - Claude Code 配置

> **專案代碼**: CK_Missive
> **技術棧**: FastAPI + PostgreSQL + React + TypeScript + Ant Design + Ollama/Groq
> **版本**: v6.11 完成（2026-05-27）/ OA-3 PM2 廢除 + L49 family 5 案修法 + fitness 52 step + admin smoke test
> **最後更新**: 2026-05-28
>
> **近期重大里程碑**：
> - **v6.11 OA-3 PM2 廢除 + L49 Container Host Dependency Family**（2026-05-27 → 28 / 8 commits / 自動化驗收 10/10 PASS）：
>   - **觸發鏈**：OA-3 PM2 廢除階段 2-3（5/27 19:04 移除 ck-backend/ck-frontend）後 3h 內 owner 連環報 4 個業務頁面故障
>   - **L49 family 5 案揭發**（PM2 native → docker container 環境切換破口）：
>     - **L49.1** `admin/backup` 顯示「Docker 環境不可用」：container 內無 docker CLI（PM2 時 host 內建）
>       → backend Dockerfile 加 postgresql-client，pg_dump 改走 docker network `postgres:5432` 直連（commit `28df958d`）
>     - **L49.2** `files/storage-info` HTTP 500：`rglob('*')` 遇 Windows mount 長中文檔名 OSError 中斷
>       → `_scan_files` while+try/except 容錯，回傳 `scan_errors` 計數（commit `27efffc7`）
>     - **L49.3** `files/{id}/download` HTTP 404：DB 內 `file_path = '2026\05\doc_xxx\...'` Windows backslash 進 Linux container `os.path.exists` 必 false
>       → `files/common.py:resolve_attachment_path()` SSOT helper，所有 download/management/pm/taoyuan/documents 散戶就地收口（commit `27efffc7` / `673c9644`）
>     - **L49.4** `admin/backup` 顯示 0 紀錄「歷史皆消失」誤判：compose mount target（`./backend/backups:/backups`）與 service 內部 `self.project_root / "backups"` 路徑不對齊
>       → 改 `./backups:/app/backups` + `./logs/backup:/app/logs/backup` 對齊 service Path() 計算（commit `d6e97294`）
>     - **L49.5** `backup/list` ReadTimeout 31.5s frontend 顯示「資料載入失敗」：8 個 attachment dir × ~4s rglob 全掃
>       → attachment metadata 改讀 `manifest_*.json`（O(1)，~10ms），list_backups **31.5s → 0.06s 提升 525x**（commit `8a75a22d`）
>   - **治理立法**：
>     - **Fitness step 52** `container_host_dependency_audit.py`：偵測 docker CLI subprocess（RED）+ rglob 無容錯 / file_path 未 normalize（YELLOW）—— 首跑揭發 21 YELLOW，sweep 後 **0 YELLOW GREEN ✓**
>     - **自動化驗收範本** `scripts/checks/admin_backup_smoke_test.py`：從 DB 撈 admin user，user_sessions 找/插 active jti，settings.SECRET_KEY 簽合法 JWT，逐打 10 endpoint 對照 expected status + validator（取代人工 F5）
>     - **L49 lesson** + `LESSONS_REGISTRY.md` 完整保存（family meta-pattern）
>     - **OA-3 SOP 補丁**：環境切換必加 in-container business endpoint smoke（非單純 process up / 4 層自動重啟）
>     - **Layer 4 self-elevating installer** `scripts/deploy/install-task-scheduler.ps1`：取代 owner 5/27 19:00「elevated PS 失敗 silent」陷阱
>   - **自動化驗收結果（10/10 PASS）**：
>     - `auth/me` 200 / `backup/environment-status` 200 pg_dump_available=true
>     - `backup/list` 200 in 0.06s / `backup/scheduler/status` running=true / 下次 2026-05-28 02:00
>     - `files/1263/download` 200 真實下載 163,734 bytes ✓
>   - **跨 repo 範本擴散**：Showcase / PileMgmt / lvrland 可仿照（待 ck-modular-toolkit sync step 52）
>   - 詳見：[[L49_container_host_dependency_family]] / `docs/architecture/LESSONS_REGISTRY.md#L49`
>
> **歷史里程碑**：
> - **v6.10.3 L43 Volume Mount Drift 災難級事故恢復**（2026-05-21 下午 4h / 4 commits）：
>   - **觸發事件**：owner Google login 後業務 API 連環 500（calendar / dispatch / digital-twin）
>     → 起初誤判 3 欄 schema drift，盤點時揭發**整個 DB 不對**（17 tables vs 75 tables 預期）
>   - **L43 根因揭發**（與 L41 同型，5 重 silent fallback 疊加）：
>     - `docker-compose.production.yml:216` 寫 `name: ck_missive_postgres_data`（空殼 17 tables/502 docs）
>     - `docker-compose.dev.yml` / `infra.yml` / `pre_upgrade_backup.sh:33` 都用 `ck_missive_postgres_dev_data`（真實 75 tables/1788 docs/24061 KG）
>     - 4 個檔案 × 2 套 volume 命名，**無 enforce 一致性**機制 → 5/21 ~04:00 切 production compose 時 silent 掛錯 volume，dormant ~10h
>     - 5 重 silent layer：postgres init.sql 不報錯 / alembic 推進不需資料 / /health 只驗 connection / Prometheus 無 row count alert / session-start hook 顯示 healthy
>   - **Plan A 10 步完整恢復**（14:30~14:35）：
>     - 雙 dump 備份（122K 空殼 + 77M 真實）+ MD5 雙端驗證一致
>     - compose volume 改 `ck_missive_postgres_dev_data` + `external: true`
>     - 真實 DB 補跑 alembic `20260521a001` (department/position 欄位)
>     - backend 0 UndefinedColumn / business endpoints 200
>   - **5 層防禦落地**：
>     - **alembic migration** `20260521a001` (commit `e1d7d3e7`) — idempotent ADD COLUMN IF NOT EXISTS
>     - **`/health` business_data_present 503 防禦**（commit `097cdf68`）：row count < threshold → cloudflared healthcheck fail → 流量不打進壞 instance
>     - **雙路徑驗證 live**：200 (1788/24061 ok) / 503 (threshold=99999 forced) / 公網 PM2 restart 後 biz_ok=true docs=1789 kg=24061
>     - **fitness step 38** `docker_compose_volume_consistency.py`（commit `ad4451b8`）：偵測同邏輯 volume 跨 compose drift（含 ${COMPOSE_PROJECT_NAME} 展開）— **首跑揭發 redis 同型 chronic drift** 留 v6.11 Sprint
>     - **NAS 異地備份**（commit `acbd3e49`）：`Z:/.../#systembackup/CK_Missive_INCIDENT_20260521_volume_mount_drift/` MD5 雙端一致
>   - **架構級議題揭發**（split-commit 過程意外發現）：
>     - 公網 `missive.cksurvey.tw` 透過 cloudflared `host.docker.internal:8001` 命中 **PM2 native uvicorn (PID 37564)**，不是 docker container
>     - 兩 backend 同時 listen 0.0.0.0:8001（Windows SO_REUSEADDR）
>     - hot-patch docker container 對公網無效，必須 `pm2 restart ck-backend` 才生效
>     - 列入 v6.11 Sprint 1：廢 PM2 改純 docker 或廢 docker 改純 PM2，二選一統一 SSOT
>   - **新增 1 條 lesson**：L43 volume mount drift silent fail（與 L41 同列「跨檔 SSOT」治理失效教材）
>   - **新增 1 個 fitness step**：step 38 docker_compose_volume_consistency
>   - **新增 5 commits**：e1d7d3e7 / ad4451b8 / acbd3e49 / 097cdf68（+ 4e8caf94 是 ck-sso-js 上午）
>   - 詳見：[[session_20260521_l43_volume_drift_recovery]] / [[lesson_l43_volume_mount_drift_silent_fail]]
>
> - **v6.10.1 + v6.10.2 慢性 Bug 大掃除**（2026-05-19~20 兩日 / 4 commits / +4299 lines）：
>   - **觸發事件**：用戶 5/20 報 dispatch=158「公文 2 筆」chronic bug（5/18 已修但 5/20 復發）
>   - **L39 揭發**：invalidate `[dispatch-orders]` vs useQuery `[taoyuan-dispatch-orders]` queryKey drift
>     → 全 codebase audit 揭發 **12 個 silent dead invalidate**（同 L29 dict-key 反模式）
>   - **L39 修法軌跡**：baseline 12 → 0（**達 v7.0 目標**）
>     - admin-users / adminUsers 4 處 → SSOT
>     - document-*-links 改 useQuery（imperative load 架構性重構）
>     - dispatch-orders 4 處 legacy cleanup + navigation drift fix
>     - audit regex 升級支援 `useQuery<TypeParam>()` 泛型（揭發 6 個誤判）
>     - pre-commit hook 加 step 35 enforce 防回退
>   - **Calendar 大規模 dormant 急救**：
>     - 公文 2479 看不到行事曆 → 揭發 **883/984 (90%) NULL owner**
>     - RLSPort `_alias_user_filter` 加 NULL fallback → 100% 可見
>     - 10 筆 date 顛倒 SWAP 修法 + Pydantic `model_validator` 防呆
>     - 5 schemas 採用 `validate_date_ordering` SSOT helper
>     - 4 處 frontend `.toISOString()` → `.format()` 修時區漂移
>   - **2 大反轉認知更新**（Pattern Z 第 N 次）：
>     - L29 真實「**5/8 domain 真活**」（之前用錯 redis key pattern 誤判 silent dead）
>     - autobiography 「**4 週 W17-W20 真活**」（之前 cwd 錯誤誤判半年 0 檔）
>   - **新增 3 條 lessons**：L37 覆盤報告反模式 / L38 平時保險反模式 / L39 queryKey drift
>   - **新增 2 個 fitness step**：step 35 queryKey_drift_audit / step 36 autobiography_freshness
>   - **Docker volume 不可發生資料遺失 SOP**：4 層緊急備份 + NAS 異地（269+272MB）+ runbook 9 段
>   - **ck-auth v2.0 BREAKING 預備**：install.sh `--no-frontend` 預設啟用避 5/25 lvrland 試用 LR-015 重演
>   - **策略級體檢 v1.0 → v1.2**：`docs/architecture/RETRO_20260519_strategic_health_check.md`
>   - 詳見：4 commits 順序 `adcafeb4 → d8882f73 → e1827e42 → 455971ea`
>
> - **v6.10 P1 真模組化**（2026-05-18 下午 — 8 輪 dynamic /loop 收尾）：
>   - **起因**：用戶批評「多次強調模組化卻無依此方向；連登入機制都無法模組與服務化」
>   - **Phase A 命名規約 SSOT**：`NAMING_CONVENTIONS.md` v1.0（8 大規約）+ fitness step 31（baseline 26）
>   - **Phase B 12 Bounded Context Facades**：59 public methods 涵蓋 12 contexts
>     - 4 Ports (RLSPort / AuditPort / MessagingPort / CachePort)
>     - 4 Default Adapters
>     - 12 Facades: Calendar/Integration/Wiki/AI/Memory/ERP/Contract/Document/Notification/Agency/Vendor/Audit
>     - `backend/app/services/contracts/` 24 .py / ~1500 lines
>   - **Phase C ck-auth 跨 repo packaging**：
>     - `shared-modules/ck-auth/` 26 檔 / portability score 1.000
>     - `install.sh` 自動 dry-run + portability audit
>     - **lvrland_Webmap dry-run: 19/23 (83%)** ✓
>     - **CK_PileMgmt dry-run: 21/23 (91%)** ✓
>     - 平均 **87% 跨 repo 可移植性**
>   - **Phase D 命名一致性 sweep**：env_namespace 42 → 26 warnings（-38%）
>   - **新 Fitness 27 → 32 step**（5 新 baseline 監控）：
>     - step 28 paths_sloppy_calc_guard (baseline 0 ✓)
>     - step 29 contracts_only_import_guard (baseline 84)
>     - step 30 module_portability_audit
>     - step 31 naming_convention_audit
>     - step 32 facade_only_check (含 facade 修法指引)
>   - **新文件 3 份**：NAMING_CONVENTIONS / CONTRACTS_LAYER_GUIDE / ADR-0036
>   - **ADR-0036** Bounded Context Contract Layer（accepted, L2）
>   - **paths.py SSOT 49→0**（100% 完修 + strict CI exit 0）
>   - **揭發潛伏 path bug 2 處**（kb_embedding / skill_evolution Wave 8 漂移）
>   - **批評反證**：12 Facades 真活 + ck-auth 87% portable + install.sh 三件套真活
>   - 詳見：`docs/adr/0036-bounded-context-contract-layer.md`
>
> - **v6.10 候選**（2026-05-16~18 整合治理交付）：
>   - **三層交付架構**：散修補丁 → 標準文件 → 自動化流水線（avoid dis-integrated）
>   - **13 散修補丁全綠**（32 unit test PASS）：C1 pre-commit 3 守護救「假基線」/ S1 刪 3 stub / F1 移除 3 死 nav / C2 ToolCall schema 永久封死 L29 dict drift / 改善 1 cross-graph router rule / 改善 2 CRYSTAL_AUTO_APPLY_MODE=live / 改善 3 條件式 KG 注入閘門
>   - **4 份標準文件**：
>     - **ADR-0035** GitNexus Bridge — Phase 2a dev-only（License 紅線管控）
>     - **OPTIMIZATION_PIPELINE.md** — 10 條優化環節連通圖（dis-integrated 防範）
>     - **MODULARIZATION_STANDARDS_v1.md** — 13 章節落地前 checklist
>     - **CAPABILITY_GOVERNANCE.md** — 三層健康度模型（E×U×O）+ A/B/C 決策矩陣
>   - **自動化流水線 skeleton**：
>     - `capability_usage_audit.py` fitness step 23（揭發 107 dead findings + dead_ui_detector 147 候選）
>     - `optimization_pipeline_orchestrator.py` 每日 cron 03:00 跑 5 step 合成 digest
>     - `run_fitness.sh` 步數 22→27（加 step 23-27: capability_audit / adr_lifecycle / dead_ui / lessons_drift / service_line_count）+ [N/27] header 統一
>     - `install-template-to.sh` 擴 3 新類（standards / pipeline / capability）跨 repo 一鍵部署
>   - **GitNexus 部署**：58,007 nodes / 92,521 edges / 991 clusters / 300 flows（dev-only）
>   - **2 新 lessons** 入 LESSONS_REGISTRY：
>     - L30: 環節不連通就是浪費（pipeline integration as priority）
>     - L31: ROI = entities × usage_rate（建表不等於用表）
>   - **真實 dead 發現**：90 manual+skill tools dead / 14 KG entity types / 3 memory loops 全死 / shadow p95=64.6s
>   - 詳見：`wiki/memory/diary/2026-05-16.md` Owner Session Addendum
> - **v6.9**（5 輪 dynamic /loop，2026-05-08 → 05-12）：
>   - **11 項真修法 + 3 項 Agent false alarm 校準**（L26 穿透式驗證落地）
>   - **L29 lesson**：「坤哥自我成長中斷」第二次（L21 後）—— `tool.get("name")` dict key bug + TOOL_DOMAIN_MAP 涵蓋率 19/98 < 25% + silent except 三重疊加。修法 + restart 後 domain_scores 0/8 → **5/8 PASS**
>   - **觀測棧增量**：3 新 Prometheus counter（metrics_populate_errors / memory_diary_append_failures / provider_circuit_state）+ 3 條 alert rule。**R3 首次重啟即揭發 1 次 shadow_baseline silent fail**
>   - **R1 SSE stream hard cutoff**：sse_utils 加 asyncio.timeout 60s，解 p95=58s 接近 stream_e2e 60s 邊界（影響 5/20 ADR-0030 投票）
>   - **R6 Provider Circuit Breaker**：新 module + 整合進 ai_connector 5 fallback 點（Groq/NVIDIA 連續失敗 5 次 → 5min skip，省 retry 浪費）
>   - **R11 Hallucination Hard Penalty**：entity_alignment < 0.5 → overall × 0.5（取代 signal-only），打破 L24「53 patterns 全 success≥0.95」失衡
>   - **R4 ADR-0025 dormant bug 歸零**：audit step 21 揭發 + 修 2 處（document_calendar/stats + tender bookmarks 3 處）→ **audit 從 2 risks → 0 risks**
>   - **R8 schema SSOT 遷移**：17/34（user_alias 3 + security 4 + tender 10）
>   - **3 份 runbook**：Telegram 永封 / CF Tunnel 故障 / Prometheus alerting 降級
>   - **Fitness 20 → 22 step**（+ step 21 alias_rls_audit + step 22 domain_score_freshness）
>   - **LESSONS_REGISTRY 加 L29**（dict key contract drift × 涵蓋率 × silent except 三重疊加教材）
>   - **75+ regression tests 全綠** | 0 TSC | alias_rls_audit 0 risks ⚠️ **5/18 校正：偵測 pattern 過窄 detection coverage = 0%；實 RLS 覆蓋率 2/34 repository（contract + document），32 repo 仍裸 user_id 比對。詳見 RETRO_20260515_BACKLOG 破口 2**
>   - 詳見：`.claude/CHANGELOG.md` v6.9 章節
> - **v6.8**（36 commits，2026-05-04，5 小時內完成）：
>   - **v3.0 覆盤主軸 9 task** 全 done（W0/Q1/Q2/Q3/F14/F15/M1/I5+/A2）
>   - **5/04 認證事故鏈 10 fix**（auth_disabled / CSRF middleware / refresh schema /
>     interceptor user_info gate / SPA index.html no-cache）
>   - **M1 v7.0 4 指標完整鏈**：lite report → Prometheus gauge → Alert → Grafana panel
>   - **I5+ wiki topics 9/9 backlog**（vendor / weekly heatmap / ADR / ERP / lessons /
>     observability / SOUL evolution / multi-channel / integration health）
>   - **F25-F27 wiki+observability 修復**：13/14 OK + shadow_baseline 救活
>     （p95=58s 揭露 ADR-0030 baseline 真實警訊）
>   - **fitness 14 → 16 step**（+F14 integration_liveness +F15 LINE notify watchdog）
>   - **acceptance test 11/11 PASS**（`bash scripts/checks/v6_8_acceptance.sh`）
>   - 詳見：`docs/release/v6.8.md` + `docs/architecture/SYSTEM_INTEGRATION_REVIEW_v3.md`
> - **v5.10.0 ~ v5.10.2**（42 commits，2026-04-27~04-28）：
>   - Wave 1-8 services DDD 遷移完整收斂（73 檔 / 12 bounded contexts / 0 regression）
>   - LESSONS_REGISTRY v1.0（22 條 lessons L01~L22 — 跨 session 知識傳承 SSOT）
>   - 4 detector 治理三件組（agent_evolution / lessons_drift / dead_ui / notify_consumers）
>   - CROSS_REPO_REFERENCE_GUIDE v1.0（FQID 5 大類別 + SemVer + 7 consumer registry）
>   - Playbook v2.0 → v2.2（7 SOP + 1 anti-pattern）
>   - Fitness 6 → 7 step（加 agent_evolution_health）
>   - install-template-to.sh 12 fitness 檔跨 repo 一鍵部署
>   - PR template + consumers.yml 規範化貢獻回流
>   - Bug fixes: 派工總覽 morning-status 即時刷新 + 認證整合 UI 接通
> - **v5.9.3 ~ v5.9.9**（37 commits）：ADR-0028~0033 + Qwen 零成本整合 + KG 100% / Wiki 85% / SLO SSOT
> - **ADR 治理**（ADR-0029）：Active 16 / Archived 14 / Removed 1（adr_lifecycle_check 2026-05-16 實跑）
> - **Hermes GO/NO-GO**（ADR-0030）：v6.8 F26 救活 shadow_baseline → real **p95=58s 警訊**
>   接近 60s 邊界。5/20 用 `docs/adr/0020-hermes-role-decision-proposal-v3.md` 三方案投票
> - **坤哥為唯一意識體入口**（ADR-0023 + ADR-0031）：/kunge 7 tabs 統一
> - **Source Repo 自我治理閉環**：發現→記錄→驗證→範本化→註冊→通知→回流
> - **v7.0 baseline 量化**（v6.8 取代「成熟度 %」）：
>   - `v7_channel_diversity = 1`（target ≥ 4）— line only
>   - `v7_reference_density_diary_pct = 1.1%`（target ≥ 50%）
>   - `v7_reference_density_critique_pct = 100%` ✓
>   - `v7_soul_drift_lines = 57`（target ≤ 5）— Missive vs AaaP
>   - `v7_provider_fidelity_gap_pct` = (待 owner 跑 soul-fidelity-eval.py)

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
missive.cksurvey.tw   →  公文系統 (UI + API)，已上線
hermes.cksurvey.tw    →  Hermes Agent gateway (Phase 1 後啟用)
lvrland.cksurvey.tw   →  土地查估 (Phase 2+)
pile.cksurvey.tw      →  基樁管理 (Phase 2+)
kg.cksurvey.tw        →  聯邦知識圖譜 Hub (選用)
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
- 資料庫: PostgreSQL 16 (Docker, port 5434)
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
docker compose -f docker-compose.infra.yml up -d      # 基礎設施
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8001
cd frontend && npm run dev
pm2 start ecosystem.config.js

# === 公網部署 ===
bash scripts/deploy/deploy-public.sh     # 一鍵：build → restart → verify

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
