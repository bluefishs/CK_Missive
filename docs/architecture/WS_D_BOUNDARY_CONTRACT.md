# WS-D 邊界契約 — Hermes(gateway) ⇄ Missive(業務腦) 委派規格

> **建立**：2026-06-12（覆盤推薦 C 聯邦分層後草擬）
> **範圍**：本文 = **CK_Missive 側契約規格**（Missive 已提供的保證）。
> **CK_AaaP / CK_Hermes caller 側實作 = owner**（另開該 repo session；本 repo 不動）。
> **權威背景**：`CONSCIOUSNESS_INTEGRATION_ANALYSIS.md §10`（推薦 C）+ monorepo CLAUDE.md「WS-D 甲」+ ADR-CK-003。

---

## 1. 問題與分工原則

Hermes baseline NO-GO 的硬傷是 **p95 47.9s**——因為 Hermes 在自己的 meta-LLM 迴圈裡「重做」業務推理（每請求重建 AIAgent + ~20k token prompt）。

**WS-D 原則**：業務問題**不該進 Hermes 慢迴圈**，應**委派**給 Missive 的確定性快路徑。

| 層 | 負責 | 不負責 |
|---|---|---|
| **Hermes gateway** | 多通道接入、Meta 人格、意圖**分類**（這是不是業務問題）、把業務問題**轉發**、非業務的閒聊/跨平臺仲裁 | 業務推理本身（公文/派工/財務/標案/KG 查詢）|
| **Missive 業務腦** | 業務查詢的確定性路由 + KG-RAG + 忠實答案 | 多通道接入、跨平臺仲裁、Meta 人格 |

---

## 2. Missive 側已提供的契約（caller 可依賴）

### 2.1 委派入口

| 項目 | 值 |
|---|---|
| HTTP 端點 | `POST /api/ai/agent/query`（`backend/app/api/endpoints/ai/agent_query_sync.py:281`）|
| 認證 | `X-Service-Token` header（env `MCP_SERVICE_TOKEN`，輪替 `_PREV`）→ `require_scope("read:agent")` |
| 入參 | `{ "question": "<中文原問>", ... }`（v0 legacy / v1 schema 皆容）|
| 公網 | 經 cloudflared，內網用 `host.docker.internal:8001` |
| Skill 包 | `docs/hermes-skills/ck-missive-bridge/`（`tools.py` / `tool_spec.json` / `SKILL.md`）|

### 2.2 快路徑保證（為何 6.4s）

Missive 端 `agent_router` 對業務問題走**確定性路由、不進 LLM 規劃迴圈**：

| Layer | 命中 | 範例 |
|---|---|---|
| 1 | chitchat 短路 | 「你好」 |
| 1.5 | 規則引擎快路由 | 高 confidence 意圖 |
| 1.55 | 「[實體]相關公文」守衛 | 「桃園市工務局相關公文」 |
| 1.6 | 跨域查詢快路徑 | search_across_graphs |
| 1.7 | finance/tender 單域 | 「未付請款」 |

→ 命中即直呼後端工具（如 `get_statistics`）+ 忠實轉述，**實測 ~6.4s、100% 無捏造**（對比 meta 迴圈 70%/175s）。

### 2.3 回應契約

- `success: true/false` + `answer`（繁中、忠實、查不到就說查不到，不杜撰）
- `tools_used: [...]`（走了哪些後端工具，可驗證非幻覺）
- 倫理底線由 Missive SOUL `wiki/SOUL.md` 保證（財務不杜撰/PII mask/append-only）

---

## 3. caller（Hermes）側待辦 — **owner 在 CK_Hermes 執行**

> 本 repo 不動；以下為規劃，供 owner 另開 CK_Hermes session。

1. **意圖分類前置**：在 Hermes 接到 LINE/TG 訊息時，先輕量判斷「是否業務問題」（關鍵字/小模型分類），**是 → 直接 call §2.1 端點**、**否 → 走 Hermes 自己的 Meta 迴圈**（閒聊/跨平臺）。
2. **業務問題不進 meta-LLM 迴圈**：避免 20k token prompt 重建；轉發只帶「中文原問」。
3. **逾時/失敗回退**：Missive 端逾時則回 Hermes 一句明確「查詢逾時，請稍後再試」，不在 Hermes 端用 LLM 補洞（守倫理紅線「財務不杜撰」）。
4. **既有資產**：現行 skill 已用 `terminal: query.py agent_query --question`（~50-75% 命中）；WS-D 是把「業務判斷 + 委派」前移，提高命中與速度。

---

## 4. 驗收（達標 = Hermes baseline 朝 GO 移動）

| 指標 | 現況 | WS-D 後目標 |
|---|---|---|
| 業務查詢 p95 | 47.9s（meta 迴圈）| < 8s（走委派快路徑）|
| 業務查詢正確率 | ~70%（meta 迴圈）| ~100%（確定性路由）|
| Hermes baseline | 2/5 NO-GO | p95 條件達標 → 3/5+ |

> Missive 側**無需新工程**——快路徑已存在（§2.2）。WS-D 的工作量在 Hermes caller 側的「分類 + 委派」。本文鎖定 Missive 契約不變，讓 owner 在 CK_Hermes 安心實作。

---

## 5. 不在本契約範圍（避免 scope drift）

- 不改 Missive `agent_router` 既有 Layer（已夠快）。
- 不把 Hermes 邏輯內嵌 Missive（方向單向：Hermes→Missive）。
- 不做整檔 SOUL sync（兩層 persona 本就不同；核心不變量補齊見 `HERMES_SOUL_CORE_INVARIANT_PLAN.md`）。
