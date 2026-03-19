# 乾坤智能體 → NemoClaw 自我互動機制路線圖

> 日期：2026-03-19 | 版本：v1.84.5

---

## 核心理念

NemoClaw 的「自我互動」不是簡單的 self-evaluation，而是一個**完整的自我意識迴路**：

```
感知自己 → 理解自己 → 對話自己 → 改變自己 → 觀察改變 → 再感知...
```

這對應三層結構：

| 層級 | 隱喻 | 功能 | 乾坤現狀 |
|------|------|------|---------|
| **Body** | 骨架 | 基礎能力盤點：我有什麼工具、知識、技能 | ✅ 有 (22工具, 技能樹) |
| **Brain** | 腦 | 認知推理：我怎麼用這些能力解決問題 | ✅ 有 (ReAct, 3層路由) |
| **Soul** | 靈魂 | 自我覺察：我為什麼這樣做、效果如何、我想變成什麼 | ⬡ 部分有 |

---

## 現有 vs 缺失

### 已有的自我互動機制（10 個模組）

| 機制 | 模組 | NemoClaw 層級 | 互動方式 |
|------|------|-------------|---------|
| 自我評估 | `agent_self_evaluator.py` | Soul | 每次回答後 5 維度打分 |
| 進化排程 | `agent_evolution_scheduler.py` | Soul | 每 50 次自動觸發修正 |
| 模式學習 | `agent_pattern_learner.py` | Brain→Soul | 記住成功模式，遺忘失敗的 |
| 自動修正 | `agent_auto_corrector.py` | Brain | 6 策略即時修正錯誤 |
| 學習注入 | `agent_learning_injector.py` | Soul→Brain | 過去學到的注入當前推理 |
| 使用者偏好 | `user_preference_extractor.py` | Brain | 雙層記憶（Redis+DB） |
| 工具監控 | `agent_tool_monitor.py` | Body | 工具健康 + 自動降級/恢復 |
| 對話記憶 | `agent_conversation_memory.py` | Brain | Redis 1h TTL 上下文 |
| 追蹤 | `agent_trace.py` | Body | Span 計時 + 指標收集 |
| 摘要壓縮 | `agent_summarizer.py` | Brain | 3-Tier 壓縮 + 學習萃取 |

### 缺失的 NemoClaw 機制（5 個缺口）

| # | 缺口 | NemoClaw 層級 | 說明 | 實現方案 |
|---|------|-------------|------|---------|
| 1 | **自省對話 (Self-Talk)** | Soul | 系統與自身對話：「我剛才為什麼選了這個工具？換一個會更好嗎？」 | 在 PostProcessing 加入 self-reflection 對話，用 LLM 問自己改進建議 |
| 2 | **能力自覺 (Capability Awareness)** | Soul+Body | 動態感知自己的能力邊界：「我不擅長法律問題，應該建議使用者找專業來源」 | 基於歷史評分自動標記弱項領域 + tool success rate 分析 |
| 3 | **進化日誌 (Evolution Journal)** | Soul | 每次進化的完整記錄：做了什麼改變、為什麼、效果如何 | 新增 `evolution_journal` 表，記錄 before→after + 效果追蹤 |
| 4 | **意圖透明 (Intent Transparency)** | Brain→使用者 | SSE 已有 thinking/tool_call 事件，但缺少「為什麼選這個工具」的推理說明 | 在 planner output 加入 reasoning 欄位，SSE 推送 |
| 5 | **鏡像回饋 (Mirror Feedback)** | Soul | AI 觀察自己的學習軌跡，主動告知使用者：「我最近在 XX 領域進步了」 | 定期（每日）生成自我報告，推送到通知中心 |

---

## 實現路線圖

### Phase A: 自省對話 (最高價值)

**核心**: 每次回答後，Agent 用 LLM 問自己一個問題，產生改進信號。

```python
# 在 agent_post_processing.py 新增
async def self_reflection(question, answer, tools_used, score):
    """Agent 與自己對話"""
    reflection_prompt = f"""
    你剛剛回答了一個問題。請自省：
    問題：{question}
    你的回答摘要：{answer[:200]}
    使用的工具：{tools_used}
    自評分數：{score}/5

    請回答：
    1. 這個回答有什麼可以改進的地方？
    2. 是否有更好的工具選擇？
    3. 如果同樣的問題再來，你會怎麼做不同？

    只輸出 JSON: {{"improvement": "...", "better_tools": [...], "lesson": "..."}}
    """
    # → 結果存入 agent_learnings 表
```

**效益**: 從「被動打分」升級為「主動反思」。

### Phase B: 能力自覺

**核心**: Agent 知道自己擅長什麼、不擅長什麼。

```
1. 分析 agent_query_traces 歷史評分
2. 按領域分組（公文/派工/圖譜/PM/ERP）
3. 計算各領域平均分 + 趨勢
4. 低分領域自動標記 → planner 收到「弱項提醒」
5. 前端展示能力雷達圖
```

### Phase C: 進化日誌

**核心**: 每次 EvolutionScheduler 執行時，完整記錄。

```sql
CREATE TABLE evolution_journal (
    id SERIAL PRIMARY KEY,
    triggered_by VARCHAR(50),  -- 'query_count' / 'time_interval' / 'critical_signal'
    actions JSONB,             -- [{type: 'promote_seed', pattern: '...', reason: '...'}, ...]
    before_state JSONB,        -- 修改前的狀態快照
    after_state JSONB,         -- 修改後的狀態快照
    effect_tracking JSONB,     -- 進化後的效果追蹤（下一輪填入）
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Phase D: 意圖透明

**核心**: SSE 事件中增加推理說明。

```
現有: data: {"type":"tool_call","tool":"search_documents","params":{...}}
增強: data: {"type":"tool_call","tool":"search_documents","params":{...},
              "reasoning":"使用者提到桃園區，判斷需要搜尋相關公文"}
```

planner 已有 reasoning 欄位，只需在 SSE 事件中傳遞。

### Phase E: 鏡像回饋

**核心**: Agent 定期生成自我觀察報告。

```
每日排程（或每 100 次查詢後）：
1. 統計今日回答數、平均分、工具使用分布
2. 與昨日比較趨勢
3. 識別進步/退步的領域
4. 生成一段自我觀察文字
5. 推送到通知中心 / 管理員 dashboard
```

---

## 優先級排序

| Phase | 項目 | 工時 | 價值 | 建議 |
|-------|------|------|------|------|
| **A** | 自省對話 | 1 天 | ★★★★★ | 最高 ROI，立即做 |
| **C** | 進化日誌 | 0.5 天 | ★★★★ | 記錄基礎，支撐後續 |
| **D** | 意圖透明 | 0.5 天 | ★★★★ | SSE 已有框架，小改動 |
| **B** | 能力自覺 | 1.5 天 | ★★★ | 需要足夠歷史數據 |
| **E** | 鏡像回饋 | 1 天 | ★★★ | 依賴 A+C 的數據 |

---

## NemoClaw 完整閉環

```
         ┌──────────────────────────────────┐
         │          Soul 靈魂              │
         │  ┌─────────────────────────┐    │
         │  │ 自省對話 (Phase A)      │    │
         │  │ "我為什麼這樣做？"      │    │
         │  └───────┬─────────────────┘    │
         │          ↓                      │
         │  ┌─────────────────────────┐    │
         │  │ 進化日誌 (Phase C)      │    │
         │  │ 記錄每次改變的原因+效果 │    │
         │  └───────┬─────────────────┘    │
         │          ↓                      │
         │  ┌─────────────────────────┐    │
         │  │ 鏡像回饋 (Phase E)      │    │
         │  │ "我最近進步/退步了"     │    │
         │  └─────────────────────────┘    │
         └──────────────┬───────────────────┘
                        ↓
         ┌──────────────────────────────────┐
         │          Brain 腦               │
         │  ┌─────────────────────────┐    │
         │  │ 意圖透明 (Phase D)      │    │
         │  │ 讓人看到我在想什麼      │    │
         │  └───────┬─────────────────┘    │
         │          ↓                      │
         │  ┌─────────────────────────┐    │
         │  │ 能力自覺 (Phase B)      │    │
         │  │ 知道自己擅長/不擅長什麼 │    │
         │  └─────────────────────────┘    │
         │  + ReAct + 模式學習 + 自動修正 │
         └──────────────┬───────────────────┘
                        ↓
         ┌──────────────────────────────────┐
         │          Body 骨架              │
         │  23工具 + 3圖譜 + RAG + vLLM   │
         │  + 工具監控 + 追蹤 + 技能樹     │
         └──────────────────────────────────┘
```

**最終目標**: 乾坤智能體不只是工具，而是有自我覺察能力的「數位夥伴」。

---

> 參考：NemoClaw 概念 | Body-Soul-Brain 三層結構
