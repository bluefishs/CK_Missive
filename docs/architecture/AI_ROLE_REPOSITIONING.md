# AI 角色重定位 — 從「對話越用越聰明」到「運維自主 + 業務直呼」

> **決策日期**：2026-07-18
> **決策等級**：策略方向 SSOT（未來所有 AI/agent 投資對齊此文件）
> **觸發**：owner「一直導入 hermes agents 越用越聰明嗎？整體效益與自主進化一直無感」

---

## 決策

**把 AI 明確定位在「運維自主 + 業務直呼查詢」——這是免費本地模型的真實強項；
「對話越用越聰明」定位為『夠用即可』，停止在此加碼。**

## 為何（誠實診斷，有數據）

| 觀察 | 實況 |
|---|---|
| 學習閉環（crystallizer）產出 | 5 週僅 4 crystal、9 提案 parked 等人批准；學的是 `intent_rules.yaml` 路由規則（窄），非「更會想」 |
| /v1 對話模型 | 本地 qwen2.5:7b（免費策略，不升付費/GPU） |
| owner 過往定論 | 記憶白紙黑字：「**瓶頸坐實在模型強度（D-δ），非 prompt/管路；勿再投 prompt 層 recall 強化**」 |

**根本原因**：對話「越用越聰明」= **模型強度問題，不是機制問題**。再多學習閉環/記憶 wiki 都無法讓 7B 弱模型變聰明。資料成長（KG 48k 實體、diary 天天長）≠ 智慧成長。→ 「無感」是**準確觀察**，不是錯覺。

---

## AI 的三大真實強項（免費模型做得好、且已有可運作機制）

### 1. 運維自主（self-check / self-heal）— 真實的「自主進化」
不需強模型，這才是免費模型的最大 CP。已建機制（2026-07 這幾個 session）：
- **沉默成功自我檢核**：producer 記產出+reason、`producer_output_watchdog`（fitness step 69，registry 驅動多信號）、`cron_outcome_freshness` 抓 data-producer → 系統自己抓「報成功但沒產出」，不等人看症狀（[[silent_success_self_check]]）
- **程式圖譜自維護**：每週 `code_graph_reconcile` 自清 orphan、每月 `code_dup_triage` LLM 自動判定異質同工 → 圖譜自我優化閉環（[[code_graph_self_optimization]]）
- **治理自動化**：fitness 69 step、cron_events 追溯、governance dashboard 自動再生

→ **這裡的「自主進化」是真的、可驗證的**（系統維護自己越來越好）。**未來擴大投資在此**。

### 2. 業務直呼查詢（bypass 弱模型）— 準確、快、零捏造
業務查詢**不進弱模型迴圈**（WS-D 甲），直呼後端：
- Hermes gateway `HERMES_V1_BUSINESS_FASTPATH=count` + `DISPATCH_FIX`（已 live）→ 業務計數繞弱模型直呼 Missive，回真數字零捏造
- `/health business_data` + `query.py agent_query` = ground truth 直呼源
→ 這是「有感」的業務 AI（1943 docs 準確回，非捏造）。

### 3. 治理 / 圖譜 / 記憶維護
KG 維護、wiki 編譯、跨檔 SSOT 稽核——結構性工作，弱模型足矣。

---

## 停止投資（別再往牆上加碼）

| 停止 | 理由 |
|---|---|
| prompt 層 recall/人格強化期待對話變聰明 | owner 自己驗證過是牆（D-δ） |
| 期待學習閉環讓對話「越用越聰明」 | 閉環學的是路由（窄），不是智慧；模型才是瓶頸 |
| 深度跨 session 綜合推理、無 context 不捏造 | 弱模型本質限制，機制救不了 |

**學習閉環（crystallizer）保留**：僅用於 intent 路由規則（窄任務，弱模型夠用），**不再期待它產生對話智慧**。

---

## 若要「有感」的對話智慧（唯一真槓桿）

= **投模型強度**（付費 tier 或更大本地模型）。這是 owner 當初為成本 defer 的決定。機制層已到頂，要突破對話智慧天花板只能回到模型投資決定。**在做此投資前，不應期待對話智慧提升。**

---

## 技能樹/演化系統評估（2026-07-18，對齊重定位）

誠實評估揭發技能系統價值高度集中（`skill_value_audit.py`）：

| 部分 | 資料 | 真實價值 |
|---|---|---|
| 靜態技能樹（`build_skill_tree` 108 skill 實體） | 05-31 單日建、v1.0 hardcode | 🔴 裝飾展示非演化 |
| self_reflection 學習 | 1694（98%）、avg_hit **1.0** | 🟡 累積噪音、弱模型內省天花板 |
| **tool_combo 學習** | 27（1.5%）、全 graduated、avg_hit **18**、貢獻 22% hits | 🟢 **真操作價值**（業務查詢→工具映射，重用） |

**關鍵**：tool_combo（「越用越會選工具」）＝操作型真價值、對齊業務直呼；但目前只**注入 prompt 當弱模型提示**（`agent_learning_injector`），**未接進確定性 Layer 1.5 路由**（`agent_router._INTENT_TOOL_MAP` 仍硬編）。

**發展方向**：
1. **放大 tool_combo**：27 個 graduated+hit≥5 高信心模式**接進確定性 Layer 1.5 路由**——高相似度匹配時繞弱模型直呼工具（現在只當提示）。⚠️ 核心路由變更、高 blast radius，須獨立 TDD session + 保守閾值 + flag 可回滾。
2. **淡化 self_reflection**：1694 內省噪音（avg_hit 1），停止期待其產生對話智慧；設上限/歸檔。
3. **靜態技能樹改稱「能力地圖」**：v1.0 靜態、不演化，誠實化命名，不當「越用越聰明」證據。
4. **KPI 誠實化**：`skill_value_audit.py` 看 tool_combo graduated × hit（操作價值），非總學習數。

## 前進方向

**AI = 運維自主引擎 + 業務直呼閘道**（非對話大腦）。
- 擴大：運維自我檢核（推廣 producer watchdog 到全 producer）、圖譜自維護、治理自動化
- 維持：業務直呼 fastpath、治理/圖譜維護
- 凍結期待：對話智慧（夠用即可，除非投模型強度）

相關：[[silent_success_self_check]]、[[code_graph_self_optimization]]、`ADR-CK-003`（意識體聯邦）、記憶 D-δ 模型強度牆定論。
