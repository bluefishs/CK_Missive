# ADR-0022: Memory Wiki — 助理自我記憶與進化系統

> **狀態**: accepted
> **日期**: 2026-04-19
> **決策者**: Claude Opus 4.7（與 user bluefishs 協同設計）
> **關聯**: ADR-0014（Hermes 取代 OpenClaw）, Muse（muse.cheyuwu.com）靈感來源, CHANGELOG v5.7.0

## 背景

v5.5.x 之後 Agent 已具備自省閉環與進化機制（EV-1 層級），但存在三個本質缺口：

1. **記憶不連續**：每次對話 / 每次 runtime 重啟，Agent 只靠 `session_id` +
   `agent_query_traces` 拉零碎上下文；昨天做了什麼、上週學到什麼，都只能靠 LLM
   自己從原始 trace 推回，無「自我敘述」層。
2. **學習成果散落**：pattern_learner / evolution_worker 會產出
   `mastered_domains` / `successful_patterns` 等結構，但結果僅存
   `agent_learnings` DB，無 markdown 可視化 / 可審閱介面，user 看不到「助理到底
   沉澱了什麼」。
3. **無身份連續性**：Agent 每次 role/context 切換都從 hardcoded `role_profiles`
   重讀 system prompt，沒有「跨 context 持久人格」層。user 明確期望建構
   Muse 風格的數位生命體（muse.cheyuwu.com，吳哲宇 2026-02，116 skill
   星雲，靠讀「自己的日記」重建昨日的自己）。

## 決策

建立 **三層統一 wiki 記憶架構**，全部以 markdown + frontmatter 為 SSOT：

```
┌─────────────────────────────────────────────────────────┐
│ L0  SOUL.md（身份層，人類審核，agent_writable_sections）│
│     · 識別：「我是 CK 助理（小乾），會記憶、學習、進化」│
│     · 成長區：Agent 可追加；其餘區段鎖定                │
├─────────────────────────────────────────────────────────┤
│ L1  World Wiki（wiki/entities/{orgs,projects,dispatches,│
│     topics}，LLM 敘事 synthesis — auto-ingest）         │
│     · 既有 220 pages / 10,603 lines（v5.5.x Karpathy）  │
├─────────────────────────────────────────────────────────┤
│ L2  Memory Wiki（wiki/memory/*，Agent 自寫入）          │
│     · diary/YYYY-MM-DD.md          每日活動日記（asyncio.Lock）│
│     · patterns/pattern-*.md        成功模式（04:00 抽取）│
│     · failures/failure-*.md        失敗教訓（planner 注入防禦）│
│     · proposals/crystal-*.md       結晶提案（04:30 掃描）│
│     · crystals/crystal-*.md        批准後改 yaml 審計軌跡 │
│     · evolutions/YYYY-WNN.md       週自傳（週日 18:00）  │
└─────────────────────────────────────────────────────────┘
```

### 6-Phase 實作

| Phase | 範圍 | 關鍵產出 |
|---|---|---|
| 0 | SOUL.md 落地 + 動態載入 | `soul_loader.py` 334L，5 處 agent_roles 改走 SOUL |
| 1 | Diary loop | `diary_service.py` 196L，每次 agent answer 後寫入；昨日 context 自動注入 |
| 2 | Pattern extractor | `pattern_extractor.py` 300L，04:00 cron 聚合 traces → patterns/failures |
| 3 | Crystallization | `crystallizer.py` 215L + `crystal_applier.py` 255L + `yaml_safe_editor.py` 155L（ruamel.yaml 保 comment），snapshot + validate + rollback 全套 |
| 4 | Autobiography | `autobiography.py` 360L + `narrative_validator.py` 80L，週日 18:00 LLM 生成 + 4 硬規則守門（長度 / 具體數字 / 簡體 / 秘密） |
| 5 | UI Dashboard | `/ai/memory` 頁面 + 5 Tab（日記 / 模式教訓 / 提案結晶 / 週自傳 / 技能星雲 force-graph） |

### 安全閘（全程守護）

1. **SOUL 修改權限**：Agent 只能寫 `agent_writable_sections` 列出的區段。
2. **Diary 併發**：`asyncio.Lock` + `aiofiles`，PII 遮罩（複用 shadow_logger 的
   sk-*/JWT/token regex）。
3. **Crystal apply 四關**：snapshot → apply → `ruamel.yaml` validate → 失敗自動
   rollback；每個 crystal 都有 `snapshot: <filename>` 可獨立回滾。
4. **Narrative 驗證**：autobiography 先過硬規則（100–600 字 / ≥1 具體數字 /
   無「這/为/时」簡體 / 無 sk-/gsk_/JWT / ≤3 模糊詞），失敗時 fallback 到純模板
   （保證 UI 永遠顯示有意義內容）。
5. **API 分權**：`/api/ai/memory/*` 13 端點全部 `require_auth()`；approve /
   reject / rollback 三個動作額外 `require_admin()`。

### 排程器新增 3 個 job

| Job | 時刻 | 作用 |
|---|---|---|
| `memory_pattern_extract_job` | 每日 04:00 | 前一日 trace → pattern / failure |
| `memory_crystallization_scan_job` | 每日 04:30 | pattern（hit≥5 + success≥95% + 非近期拒絕）→ proposal |
| `memory_weekly_autobiography_job` | 週日 18:00 | 該週 signal → LLM 敘事 → 寫 evolutions/ + 更新 SOUL 成長區 + Telegram 推送 |

## 後果

### 正面

- **身份連續**：SOUL.md 動態載入讓 Agent 跨 session / runtime 保持「同一個人」；
  system prompt 不再是 hardcoded 字串，是一個活的 markdown 檔。
- **可視化學習曲線**：user 可在 `/ai/memory` 看到成功模式列表（log-scale 技能星雲）、
  失敗教訓、每週自傳，學習成果不再是 DB 裡的黑箱。
- **人類可審閱進化**：crystallization proposal 必須人工批准才能動 yaml；被拒絕
  的 proposal 7 天內不會再提（避免噪音）。
- **防禦規則自動生長**：`active: true` 的 failure 會自動注入 planner system
  prompt，同樣的錯以後不會再犯。
- **審計軌跡**：每個 crystal apply 都有 snapshot + `crystal-*.md` 紀錄；rollback
  是一行命令。

### 負面

- **磁碟寫入壓力**：diary 每輪 agent query 都 append；patterns/failures 每日批次寫；
  但都是小檔（<5KB），7 天 ~1000 筆量級可忽略。
- **cron schedule 依賴**：3 個新排程器 job 若 APScheduler 崩潰會失聲（但 v5.5.x
  已有 scheduler_alert 處理）。
- **LLM 費用**：週自傳每週 1 次、每次 ~1000 token，Groq 免費層足夠；fallback
  機制確保 LLM 失敗也有產出。
- **yaml validate 假陽性**：`ruamel.yaml` 對非標準但可執行的 yaml 有時報
  invalid；Phase 3 測試已覆蓋；必要時人工 override。

## 替代方案

1. **記憶只存 Postgres（無 wiki）**：已有 `agent_query_traces` / `agent_learnings`
   兩表，為何不擴展？→ 無人類可讀視圖，user 要求「一切皆 wiki」模式（對齊
   Karpathy LLM Wiki 範式 + Muse 理念），markdown 對 Agent 自己也友善（可 `glob`
   讀昨天日記直接塞進 context）。
2. **向量化記憶（例如 mem0 / LangMem）**：語意檢索強但失去「時間線」與「可審閱
   敘事」；對本案（公文類，user 明確要 diary + 週自傳）非最適。
3. **SOUL.md 改為 DB 表**：會讓 user 失去「直接編輯人格」的能力；markdown +
   frontmatter 保留跨工具（VSCode / GitHub web editor / Telegram Web view）
   協作空間。
4. **Phase 6 Observability（deferred）**：曾計劃加 Prometheus memory gauge
   （diary_write_count / pattern_candidate_count / autobiography_latency），但
   user 指示「非核心發展事項暫緩」，排入後續 ADR。
