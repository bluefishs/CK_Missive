# v6.14 整合優化議題 — 坤哥學習閉環 × Hermes 能力對應 × LINE 對話機制

> 彙整日：2026-06-01（v6.13 重啟前）
> 性質：本日三面向工作彙整 + 優化議題（grounded 真實數據，非空泛規劃）
> 對齊 owner：「坤哥整體學習閉環 與 Hermes agents 對應能力本日彙整優化議題 以及 line 對話機制」

---

## 0. 核心洞察 — 三者收斂於同一結構斷層「能力 ⇄ 路由」

Missive agent 內部有 **23 個工具**（含 ERP/finance/contract/asset/billing），但：

| 層 | 實際暴露/路由 | 真實證據 |
|---|---|---|
| **Hermes bridge** | 只暴露 **9** 工具（document/dispatch/entity/stats/federated/kunge_snapshot），**全文件/派工導向** | `tools_manifest.py` 9 個 name |
| **intent_rules.yaml** | 只路由 document/dispatch/date | grep `請款\|erp\|帳款\|標案\|tender` = **全空** |
| **agent tool_registry** | 23 工具含 `get_unpaid_billings`/`get_financial_summary`/`get_expense_overview`/`get_contract_summary`/`get_asset_*` | tool_definitions.py |

**結論**：能力豐富（23）、但**對外暴露窄（9）+ 路由偏（document/dispatch）** → ERP/請款/標案/財務查詢觸不到對應工具 → **owner 體感「LINE 只答派工、無法正常應答」的單一結構根因**。三面向的優化其實是同一條路線。

---

## 1. 坤哥整體學習閉環

### 本日彙整（已辦）
- **鏈路**：diary(41) → pattern_extract(04:00) → patterns(10) → crystallize(04:35) → proposals → crystal_applier(admin gate) → crystals(**2**)
- **2 crystal-intent proposal 誠實 defer 標 superseded**（不造假 — 空 pattern 被安全閘擋 + tool_preference 無消費端 + 缺來源 query）
- **memory_loop RED → GREEN**：counter 誠實化（proposals 改依 status:pending；autobiography 改查 evolutions 真實路徑 W17-W22=6）
- **health**：`pattern_to_crystal_ratio=0.2`（2/10，改善自 0）/ `pending_proposals_count=0` / 唯一 ⚠️ `crystallizer_alert: pattern→crystal 斷`
- db：agent_learnings **841** / traces 55（7d）

### 優化議題
| ID | 議題 | 真因 | 等級 |
|---|---|---|---|
| **L1** | crystal-intent 真實化 | crystallizer 只存 `tool_sequence` 不存來源 query；`tool_preference` 無消費端 | v6.14 |
| **L2** | crystallizer dry-run → 低風險類型 auto-apply | `CRYSTAL_AUTO_APPLY_MODE` 目前 dry-run，proposed 0 | v6.14 |
| **L3** | pattern_to_crystal_ratio 0.2 → ≥0.5 | 依賴 L1 解（intent_rule 真實可結晶） | 目標 |

**L1 真解**：升 `pattern_extractor` 在抽 pattern 時**一併保存觸發 query 文字** → crystallizer 生成的 proposal 有真實 regex `pattern` → 並在 `rule_engine`/planner 建 `tool_preference` bias 消費端 → 結晶才能真實改路由（同時解 LINE #1 路由偏窄）。

---

## 2. Hermes agents 對應能力

### 本日彙整（已辦）
- **kunge_snapshot endpoint**（`/api/ai/kunge/snapshot`）+ **5 鏈 Integration E2E**（4+ 次連跑全綠）+ tools_manifest 公開 kunge_snapshot
- chain_4 hermes_container（host.docker.internal:8642）status 200

### 缺口（真實數據）
- **bridge 9 暴露 vs agent 23 內部** → ERP/finance/contract/asset/billing **全未暴露給 Hermes**
- **上游（hermes-stack repo）**：CKProject CLAUDE.md 記載 ck-* skill 未進 meta profile `.skills_prompt_snapshot.json` → gateway 對話入口無法 dispatch（與模型強弱無關）

### 優化議題
| ID | 議題 | 真因 | 等級 |
|---|---|---|---|
| **H1** | bridge 補暴露 ERP/finance/tender 工具 | tools_manifest 9 個全 document 導向 | v6.14（純加、安全） |
| **H2** | hermes meta profile 註冊 ck-* skill | snapshot 不含 ck-* → agent 看不到 tool | 上游 hermes-agent session |
| **H3** | bridge 工具 schema 對齊 agent tool_registry（SSOT） | 兩處工具清單各自維護易漂移 | v6.14 |

---

## 3. LINE 對話機制

### 本日彙整（已辦）
- **#2 chitchat trace answer_preview NULL 修**（`agent_orchestrator.py` chitchat 短路路徑補 trace._answer_preview/_length）
- **line bot timeout 25→28s**（owner 報「查詢處理時間較長」）

### 4 真因（commit 13eea9d7 揭發）
| # | 真因 | 狀態 |
|---|---|---|
| #1 | intent_rules 缺 ERP/tender 路由 → 「未付請款」走 search_documents | 🔴 待 LN1 |
| #2 | chitchat trace answer_preview NULL | ✅ 本日修 |
| #3 | Groq 429（30min 6 次）→ NVIDIA fallback 慢 | 🔴 待 LN3 |
| #4 | 「未付請款」simulation 6ms / 0 tools / 空 answer（silent return） | 🔴 待 LN2 深查 |

### 優化議題
| ID | 議題 | 真因 | 等級 |
|---|---|---|---|
| **LN1** | intent_rules 補 ERP/tender/finance 規則 | grep 確認全空；對應工具 `get_unpaid_billings` 等已存在 | v6.14（需測試） |
| **LN2** | #4 silent return 深查 | rate_limiter 拒 or routing 異常 silent return | v6.14（唯讀深查可先做） |
| **LN3** | Groq quota 升級 / fast-path | 429 高頻 fallback NVIDIA | owner（quota）|

---

## 4. 統一優化路線（v6.14 Sprint 建議優先序）

> 三面向的「能力 ⇄ 路由」斷層是同一條線，建議**一個 Sprint 一起解**：

1. **【P0 核心】H1 + LN1 同批**：bridge 補暴露 ERP/finance/tender 工具 + intent_rules 補對應路由規則 → 一次解決「LINE/Hermes 只答派工」（H1 純加安全；LN1 需 false-positive 測試）
2. **【P0 深查】LN2**：「未付請款」6ms silent return 真因（唯讀可先做，不改 code）
3. **【P1 閉環】L1**：pattern_extractor 補捕 query 文字 + planner tool_preference 消費端 → crystal-intent 可真實結晶（連帶 L3 ratio 提升）
4. **【P1 上游】H2**：hermes meta profile 註冊 ck-* skill（hermes-agent session）
5. **【P2 治理】H3 + L2**：bridge↔registry SSOT 對齊 + crystallizer 低風險 auto-apply
6. **【owner】LN3 / #3**：Groq quota 升級

---

## 5. 可安全自主辦理 vs owner/上游

| 可安全自主（assistant） | owner/上游/較大 |
|---|---|
| **H1** bridge 補暴露工具（純加 tools_manifest 條目） | **H2** hermes meta profile（上游 repo） |
| **LN2** silent return 唯讀深查 | **LN3/#3** Groq quota（owner 帳號） |
| **LN1** intent_rules 補規則（需 false-positive 測試，依 adr-anti-half-wired SOP） | **L1** pattern_extractor + 消費端（routing 改動，需測試） |

> **守則**：LN1/L1 涉 routing 改動，依 `adr-anti-half-wired-sop.md` 守則 — 加 intent keyword 必跑 false-positive 驗證（N≥100 樣本 + unit test 鎖定），不可 production blind 試（對齊 hermes skill dispatching 教訓）。

---

> **本檔性質**：v6.14 整合優化議題彙整（grounded：9 vs 23 工具 / intent grep 空 / 4 LINE 真因 / 學習閉環 health）
> **下批起點**：P0 H1+LN1 同批（能力暴露 + 路由規則一起補）
> **核心精神**：能力早就有（23 工具），缺的是「對外暴露 + 路由對應」——這是接通問題，不是能力問題。
