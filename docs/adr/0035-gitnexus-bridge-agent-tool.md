# ADR-0035: GitNexus Bridge — Agent Code Intelligence

> **Status**: proposed
> **Date**: 2026-05-16
> **Deciders**: Owner（待）
> **Related**: ADR-0014（Hermes 取代 OpenClaw）/ ADR-0028（錯誤合約化）
> **Supersedes**: 無
> **Superseded by**: 無

---

## Context

CK_Missive 既有 `ai/code-graph`（Python AST + DB reflection，5,721 entities）只支援語法級分析，缺乏：
- 控制流（execution flow）追蹤
- 自動聚類（community detection）
- 跨函數呼叫鏈（call chain blast radius）
- API 前後端 contract 一致性檢查（route/shape map）

2026-05-15 retro 揭發三大破口（[[arch-pattern-script-existence-not-enforcement]]、
[[arch-pattern-audit-zero-risk-false-negative]]、L29 dict-key drift），共同根因都是
「靜態檢查 coverage 不足 / 影響面不可見」。`tool.get("name")` vs `tool.get("tool")`
8 處 drift 第二次中斷正是因為「沒有工具能在 commit 前看到 8 個影響點」。

GitNexus（github.com/abhigyanpatwari/GitNexus, v1.6.4, PolyForm-Noncommercial-1.0.0）
本次 session 已部署本地（`~/.local/share/gitnexus`），對 CK_Missive 索引產出
**2,852 files / 58,007 nodes / 92,521 edges / 991 communities / 300 execution flows**，
透過 MCP JSON-RPC 暴露 13 個 tools。

## Decision

採方案 C — **Bridge 中介**，**dev/agent-only**：

1. 新建 `backend/app/services/ai/graph/gitnexus_bridge.py`：純 Python 的 MCP client
   wrapper，內部呼叫 `localhost:4747/api/mcp`
2. 暴露 **5 個 Bridge method**（不對應 GitNexus 13 tool 全部）：
   - `code_context(symbol)` — 360° symbol view（呼叫者/被呼叫者/cluster/flow）
   - `change_impact(symbol)` — Blast radius 分析（防 L29 重演）
   - `api_route_map(endpoint=None)` — 前後端 endpoint↔component 映射
   - `api_shape_check(endpoint=None)` — 前後端 schema 一致性檢查
   - `detect_uncommitted_impact()` — pre-commit 級即時影響面
3. 加 Agent tool `gitnexus_query`（5 ops dispatcher）— 註冊到 tool_registry
4. **Dev-only 守護**：
   - env flag `GITNEXUS_BRIDGE_ENABLED`（default `false`）
   - 公網部署 `tunnel_guard` 強制禁用
   - 加 Prometheus metric `gitnexus_bridge_calls_total{op}`
5. **Circuit breaker**：呼叫失敗 5 連敗 → 5 min skip（沿用 R6 模式）

### License 邊界（紅線）

| 用途 | License OK? | 本 ADR 範圍 |
|---|---|---|
| 個人 dev 在 local 用 web UI 探索 | ✅ | ✅ Phase 2a |
| Agent tool 內部呼叫（agent 本身是內部營運工具）| ⚠️ 邊緣 | ✅ Phase 2a（dev-only） |
| 嵌入 missive.cksurvey.tw 公網功能對外提供 | ❌ | **禁止**（tunnel_guard 強制 disable） |
| 用 GitNexus 索引產出做衍生商品 | ❌ | **禁止** |

本 ADR Phase 2a 只授權「dev/internal agent 輔助工具」用途。若未來需擴張到產品功能，
**必須先**：
1. 法務評估 PolyForm-Noncommercial 邊界
2. 或改用 tree-sitter 自建（無 license 限制）

## Architecture

```
┌──────────────────────────────────────────────────────┐
│ Claude Code / Hermes / CK_Missive Agent              │
│   ↓ (agent tool: gitnexus_query)                     │
│ ┌─────────────────────────────────────────────────┐  │
│ │ tool_registry.gitnexus_query(op, **params)      │  │
│ │   ↓ circuit breaker + timeout + dev-only guard │  │
│ │ gitnexus_bridge.code_context() / impact() / ... │  │
│ │   ↓ Python `mcp` SDK (1.26.0)                  │  │
│ │ MCP JSON-RPC streamablehttp_client              │  │
│ └─────────────────────────────────────────────────┘  │
│   ↓ HTTP                                              │
└──────────────────────────────────────────────────────┘
                    ↓ localhost:4747
┌──────────────────────────────────────────────────────┐
│ GitNexus serve (npx gitnexus serve)                  │
│   ↓ SQLite `.gitnexus/lbug` 267MB                    │
│ 58,007 nodes / 92,521 edges / 991 clusters / 300 flow│
└──────────────────────────────────────────────────────┘
```

## Phase Roadmap

### Phase 2a（本 ADR 範圍）— dev/agent-only
- [x] GitNexus 部署 + 索引 CK_Missive（本 session 完成）
- [ ] Bridge service skeleton + 5 methods
- [ ] Agent tool `gitnexus_query` 註冊
- [ ] Unit test（mock MCP response）+ integration test（live server）
- [ ] env flag + tunnel_guard 公網禁用
- [ ] Prometheus metric + alert rule
- [ ] Owner 7 天 dogfooding，寫 evolution doc

### Phase 2b（後續）— 整合 pre-commit / fitness
- pre-commit hook 加 `python -m gitnexus_pre_commit_check`（用 `detect_uncommitted_impact`）
- fitness step 加 `gitnexus_dead_code_audit`（取代手動 0-importer grep）
- 觸發條件：Phase 2a 7 天 dogfooding 成功 + 法務評估通過

### Phase 3（評估後）— ETL 融合（方案 A）
- 視 Phase 2a/2b 成果決定是否把 GitNexus cluster + flow ETL 進 `CanonicalEntity`
- 風險：5,721 → 58,007 entities = 10× 膨脹，pgvector 壓力大
- **不在本 ADR 範圍**

## Consequences

### 正面
- **L29 防護升級**：dict-key drift 改 1 處可立刻看 8 處影響（`change_impact`）
- **前後端 schema 漂移防護**：`shape_check` 取代手動 type-sync skill
- **Dead code 全自動偵測**：取代本 session P0-S1 手動找 3 stub
- **pre-commit 影響面預覽**：每次 commit 前看到 blast radius
- **agent 對 self 的 metacognition**：agent 可查自己的程式碼結構（自省能力）

### 負面 / 風險
- **License 紅線**：PolyForm-Noncommercial 限制商業用途，Phase 2a 嚴守 dev-only
- **單點故障**：GitNexus serve 死掉 → bridge calls 全失敗（已用 circuit breaker 緩解）
- **索引漂移**：GitNexus 索引是 snapshot，code 變動後需 re-analyze（建議 daily cron）
- **規模邊界**：58k nodes 已接近 GitNexus web UI 30k+ tab crash 警告線
- **新依賴**：增加 Python `mcp` 1.26.0 + GitNexus serve daemon 維運負擔
- **延遲**：MCP HTTP roundtrip ~50-200ms per call（已在 timeout 預算內）

### 中性
- **半接通風險**（[[adr-anti-half-wired-sop]]）：Phase 2a 必須 owner 7 天 dogfooding 否則
  自動降回 L3 半接通標記，14 天內補完 fitness 才升 L2

## Anti-Half-Wired Acceptance Criteria（[[adr-anti-half-wired-sop]] 強制）

- [ ] **A. 程式碼接通**：bridge service + agent tool + env flag + tunnel_guard 全鏈
- [ ] **B. 自動驗證**：5+ unit test + 1+ integration test + 1+ Prometheus metric
- [ ] **C. 邊角組合**：tunnel_guard 公網禁用 staff 用戶實測
- [ ] **D. 7 天追蹤**：owner 切到 dev session 用 `gitnexus_query` 跑 5 個典型查詢，寫 diary
- [ ] **E. 文件對齊**：本 ADR + CHANGELOG + skills-inventory + RETRO_20260515_BACKLOG 標完成

## Alternative considered

1. **方案 A（融合 ETL）**：直接把 GitNexus 索引 ETL 進 CK_Missive。**否決**：10× 膨脹 + License 風險加劇
2. **方案 B（並列）**：兩套各自運作不橋接。**降級**：Phase 1 已採並列，Phase 2a 升級為橋接
3. **自建 tree-sitter**：避免 License。**否決理由**：6 個月+ 工程 vs Bridge 1 週工程；GitNexus 已有 991 cluster 計算 + flow 追蹤，自建需另外實作 community detection 算法
4. **完全不導入**：維持現狀。**否決**：retro 三大破口顯示真實需求

## References

- GitNexus repo: github.com/abhigyanpatwari/GitNexus
- Hermes Skill：`hermes-agent/optional-skills/research/gitnexus-explorer/SKILL.md`
- 本 session retro 三大破口：`docs/architecture/RETRO_20260515_BACKLOG.md`
- L29 lesson：`wiki/memory/failures/failure-domain-score-silent-skip.md`
- Python MCP SDK：`pip show mcp` v1.26.0
- License：[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)
