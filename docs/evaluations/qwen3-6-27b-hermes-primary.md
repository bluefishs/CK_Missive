# 評估報告：Qwen3.6-27B 作為 OpenClaude / Hermes Agent 首選模型

- **撰寫日期**：2026-04-24
- **撰寫者**：Aaron + Claude（研究輔助）
- **狀態**：Draft — 供 2026-05-20 Hermes GO/NO-GO 會議參考
- **決策依賴**：ADR-0014（Hermes 取代 OpenClaw）/ ADR-0030（GO/NO-GO 決策重訂）
- **關聯記憶**：`hermes_migration_active.md` / `hermes_dogfooding_log.md` / `gpu_inference_stack.md`

---

## TL;DR

| 項目 | 結論 |
|---|---|
| Qwen3.6-27B 是否真實 | ✅ 2026-04-22 Alibaba Qwen 團隊釋出，Apache 2.0 |
| 本地 RTX 4060 8GB 可跑嗎 | ❌ Q4_K_M 需 ~18GB VRAM（RTX 4090 24GB 舒適） |
| 短期可用路徑 | 🟢 **雲端 API**（DashScope / Together / OpenRouter）|
| vs 目前 Gemma 4 8B Q4 (local) | ✅ agentic 品質大幅上升；中文能力強；成本 trade-off 取決於流量 |
| vs 目前 Groq / NVIDIA P1 cloud | 🟡 Qwen 中文比 Llama 系列優；latency 待實測 |
| **推薦** | **Phase 1: 雲端 P1 試接**；Phase 2: 驗證後評估 RTX 4090 本地升級 |

---

## 1. 背景

CK_Missive v5.9.x 使用 **Hermes Agent**（NousResearch fork, ADR-0014）作為統一人機介面。目前推理 stack：

| Priority | Provider | Model | VRAM / 成本 |
|---|---|---|---|
| P2 (本地主力) | Ollama | Gemma 4 8B Q4_K_M | ~6.7GB VRAM, RTX 4060 |
| P1 (雲端 fallback) | Groq | llama-3.x (default) | API call |
| P1 (雲端 fallback) | NVIDIA NIM | llama-3.3-nemotron-super-49b | API call |

**Hermes dogfooding 現況**（2026-04-24 Day 2/7）：
- web channel ok rate **44.68%**（GO 門檻 >95%，嚴重失守）
- ollama (gemma4) ok rate **8.02%** — 多 timeout
- p95 latency **90s**（GO 門檻 <8s，嚴重失守）
- 已知 **P1 性能 issue**：60s silent gap in tool loop（`known_issue_baseline_timeout.md`）

使用者提出核心問題：**「是否將 Qwen3.6-27B 作為 OpenClaude/Hermes 首選」**

---

## 2. Qwen3.6-27B 規格（2026-04-22 Alibaba 釋出）

### 架構
- **參數量**：27B dense（非 MoE）
- **架構**：16 × (3 × Gated DeltaNet → FFN) + (Gated Attention → FFN) 混合
- **Context**：262,144 native，extensible 1,010,000（**1M tokens**）
- **模態**：text / image / video（multimodal）
- **新機制**：**Thinking Preservation**（首個開源 reasoning chain 保留）
- **License**：Apache 2.0（可商用 + 自託管）

### 效能指標（Alibaba 官方對比）
| Benchmark | Qwen3.6-27B | Qwen3.5-397B-A17B (MoE) | Claude 4.5 Opus |
|---|---|---|---|
| SWE-bench Verified | **77.2%** | 76.2% | — |
| SWE-bench Pro | **53.5%** | 50.9% | — |
| Terminal-Bench 2.0 | **59.3%** | 52.5% | **59.3%（持平）** |
| SkillsBench | 48.2% | 30.0% | — |

**關鍵事實**：**27B dense 在 agentic coding 任務上 match Claude 4.5 Opus 且超越自家 397B MoE 前輩**。

### 權重格式
- **BF16**（原生）：~54GB
- **FP8 quantized**（Alibaba 官方）：~27GB
- **Q4_K_M / UD-Q4_K_XL GGUF**（社群）：**~18GB**
- **Q6_K**（較高品質）：~22GB

### VRAM 需求對照
| 量化 | VRAM | 本地硬體要求 |
|---|---|---|
| BF16 | 54GB+ | A100 80GB / H100 / 2×RTX 6000 Ada |
| FP8 | 27GB | RTX 6000 Ada 48GB / A100 40GB |
| **Q4_K_M** | **~18GB** | **RTX 4090 24GB ✅** |
| Q4 + CPU offload | 8GB+RAM | RTX 4060 8GB + 16GB RAM（但慢）|

---

## 3. 對 Hermes Agent 核心需求的匹配度

### 3.1 Function Calling / Tool Use（關鍵）
Hermes 靠 `skill(ck-missive-bridge)` 呼叫後端工具（search_documents / get_statistics 等 26 真工具）。需要：
- ✅ **準確的 JSON schema 遵守**
- ✅ **多步驟 planning**
- ✅ **長上下文**（tool_result 可能超大）

**Qwen3.6-27B 表現**：
- SWE-bench Verified 77.2% 已證明 agentic 能力
- 1M context 可吞入完整 tool_result 歷史
- 開源 function calling spec 原生支援（Hermes prompt template 相容）

**vs Gemma 4 8B**：
- Gemma 4 在 function calling 上相對弱，特別是複雜 schema
- Qwen3.6-27B 專為 agentic benchmark 訓練，結構化輸出可靠度高

### 3.2 繁體中文能力（坤哥人格 fidelity）
Hermes `SOUL.md` 定義坤哥為繁中第一人稱意識體，核心三信念、反迴聲、倫理紅線。

**Qwen3.6-27B**：
- Alibaba 原生中文訓練（Qwen 系列強項，常超越 Llama / Gemma 中文表現）
- 繁中同樣覆蓋（簡繁皆可）
- **vs Gemma 4 8B**：Qwen 系列中文品質通常領先 Gemma 一個量級

### 3.3 Thinking Preservation（新增價值）
首次開源 feature：跨多輪對話保留 reasoning chain。
- 對 Hermes 多輪 dogfooding 有直接價值
- Soul fidelity 跨對話一致性評估可能大幅改善

### 3.4 多模態（副加價值）
- text + image + video
- 可支援未來 CK_Missive 圖表分析、文件掃描 OCR 整合
- 目前 `diagram_analysis.py` 用 Gemma 4 multimodal（e2b）—可平替

---

## 4. 部署選項對比

### Option A：雲端 API（DashScope / Together / OpenRouter）

| Provider | 成本參考 | 特點 |
|---|---|---|
| Alibaba DashScope | Input $0.27-0.40 / 1M tokens（Qwen3.5-27B 參考）| 原廠 latency 最穩，中國 region 需備案 |
| Together AI | 略高於 DashScope | 全球 CDN，付款方便 |
| OpenRouter | 變動，有 free tier 預覽 | unified API，routing flexibility |
| TokenMix | $0.28 / 1M tokens | 整合 gateway |

**估算流量**：Hermes dogfooding 7 天 ~30-50 query，假設 avg 5K tokens in + 2K out = 全月約 **0.21M tokens** → 月費約 **$0.06-0.10 USD**（<NT$3）。

**Pros**：
- 零硬體投資
- 立即可試
- Fallback 彈性（P1 輪替）

**Cons**：
- 網路依賴（Hermes 本地化初衷淡化）
- 資料外送（DashScope 中國 region 合規敏感 — 建議用 Together / OpenRouter 國際區）

### Option B：本地部署 — RTX 4090 24GB 升級

| 項目 | 細節 |
|---|---|
| 硬體成本 | RTX 4090 24GB ≈ NT$55,000-65,000 |
| 電費 | 推論時 ~350W，idle ~20W |
| VRAM | Q4_K_M 18GB → 舒適 |
| Latency | 預估 p50 < 5s（本地無網路延遲） |
| 隱私 | 100% on-prem，零資料外送 |

**Pros**：
- 可取代目前 P2 Gemma 4 8B 成為新 P0 本地主力
- 隱私最高
- 無 API 費用

**Cons**：
- 一次性投資門檻
- 單 GPU 並發能力有限（semaphore max=1-2）
- 需 6-8 週硬體採購 + 環境整合

### Option C：Hybrid（CPU + GPU offload，現況 RTX 4060 8GB）

| 項目 | 細節 |
|---|---|
| VRAM | 8GB GPU + 10GB RAM offload |
| Latency | 預估 p50 ~20-40s（RAM offload 拖慢）|
| Throughput | <0.5 tokens/sec |

**Pros**：零新硬體
**Cons**：太慢，不適合互動 agent；Hermes dogfooding p95 目標 <8s 根本達不到

---

## 5. 與現況 baseline 問題的關聯分析

**目前 baseline 的 timeout（90s）是模型問題嗎？**

答案：**部分是，部分不是**。

根據 `known_issue_baseline_timeout.md`：
- 14:00 timeline 顯示 **60 秒無 log 空洞**，發生在「工具迴圈」或「synthesis LLM 呼叫」區間
- 換成 Qwen3.6-27B（雲端 API）可**部分**緩解：
  - ✅ Qwen API latency 穩定（Groq 目前 100% ok, p95 38s — 可接受）
  - ❌ 但 tool loop 60s gap 是**系統架構問題**（ADR-0028 已識別），換模型不解決

**換 Qwen3.6-27B 的實際效益**：
1. 🟢 Tool selection 準確率提升 → 減少錯誤 retry
2. 🟢 Synthesis 品質提升 → 減少幻覺 / 重新生成
3. 🟢 繁中 soul fidelity 提升 → Owner 主觀接受度 4→5
4. 🟡 Latency 效益有限 — 主因是 silent gap 系統問題
5. 🟢 multimodal 副加值

**結論**：Qwen3.6-27B **能改善品質與正確率**，但 **p95 latency 仍需配合 ADR-0028 tool-level timeout 修正**（`agent_tool_loop.py` 每個 tool 加 20s 顯式 timeout）。

---

## 6. 建議路線圖

### Phase 1 — 雲端 A/B 測試（本週）
- [ ] 在 `backend/config/inference-profiles.yaml` 加 `qwen3-6-cloud` profile
  - provider: `openai` compatible, base_url Together / OpenRouter
  - model: `qwen/qwen3.6-27b`（具體 alias 依 provider）
  - priority: 1（與 Groq / NVIDIA 並列）
  - 特色：preferred for `capabilities: [chat, planning, synthesis, function-calling, chinese]`
- [ ] 在 `hermes` skill 端增加 `provider_preference=qwen3-6-cloud` 的路徑
- [ ] Shadow baseline 再跑 3-5 天，比對：
  - ok rate（Qwen vs Gemma4 vs Groq）
  - p50 / p95 latency
  - Soul fidelity score（用 `scripts/checks/soul-fidelity-eval.py` 跨 provider）
  - Tool call 成功率

### Phase 2 — Dogfooding 評估（下週）
- 5/20 Hermes GO/NO-GO 決策前：
  - 若 Qwen3.6-27B 在 soul fidelity + tool 正確率全面領先 → 設為 P0 雲端主力
  - 若 Gemma 4 8B 本地仍具成本優勢，保留 P2 degraded mode

### Phase 3 — 硬體升級評估（6/1-6/30）
- 若 Phase 1+2 驗證 Qwen 價值確認
- 且每月 API 成本超過 NT$1000 → RTX 4090 回收期 <4 年，值得投資
- 或維持雲端，節省硬體成本（取決於 Owner 偏好）

### 拒絕選項
- ❌ 直接上 RTX 4090（未實測品質即投資硬體，風險高）
- ❌ 走 DashScope 中國 region（資料合規疑慮）
- ❌ 放棄 Gemma 4 本地備援（P2 degrade 路徑不能失守）

---

## 7. 風險與緩解

| 風險 | 影響 | 緩解 |
|---|---|---|
| Qwen3.6-27B 雲端 provider 不穩定 | 高 | 保留 Groq/NVIDIA P1 多 fallback；Gemma 4 local P2 保底 |
| 單次推理成本失控 | 中 | Phase 1 加 token 上限 per-request（planner 用 4K、synthesis 用 8K） |
| 中國區 DashScope 合規疑慮 | 高 | 首選 Together / OpenRouter 國際區 |
| Alibaba 未來閉源 / 授權變動 | 低 | Apache 2.0 已釋出 weight，隨時可自託管 |
| RTX 4090 採購延遲 | 中 | 雲端 fallback 長期可接受，硬體非必需 |

---

## 8. 決策建議

**🟢 建議：Phase 1 雲端 A/B 測試立即執行，2 週內決定 Phase 2。**

理由：
1. Qwen3.6-27B 技術規格領先當前 stack（Gemma 4 8B）2-3 代
2. 雲端試接零硬體投資、可逆性高
3. 對 Hermes soul fidelity + tool accuracy 有明確效益
4. 配合 ADR-0028 tool-level timeout 修正，可解 GO 條件 #4 #5 雙失守
5. 硬體升級決策可延後（4-6 週），視 A/B 結果決定

**❌ 不建議：**
- 不建議直接取代 Gemma 4 local（P2 保底路徑必須保留）
- 不建議走 RTX 4090 before 雲端 A/B 驗證

---

## 附錄 A — 實作 checklist（若決定 Phase 1 起步）

```yaml
# backend/config/inference-profiles.yaml 新增
qwen36-cloud:
  provider: openai  # OpenAI-compatible
  model: "qwen/qwen-3.6-27b"  # 依 provider 調整
  api_key_env: QWEN_API_KEY  # 或 TOGETHER_API_KEY
  base_url: "https://api.together.xyz/v1"  # or OpenRouter
  timeout_seconds: 45
  priority: 1
  capabilities:
    - chat
    - planning
    - synthesis
    - function-calling
    - chinese-native
  note: "Qwen3.6-27B via Together AI. 27B dense, matches Claude 4.5 Opus on Terminal-Bench 2.0."
```

```python
# agent_policy.yaml route tag for Chinese / agentic tasks
routes:
  synthesis:
    preferred: qwen36-cloud  # new P0
    fallback: [groq-cloud, nvidia-cloud, gemma4-local]
  planning:
    preferred: qwen36-cloud
    fallback: [groq-cloud, gemma4-local]
```

---

---

## 附錄 B — 零新增成本路徑（2026-04-24 實測驗證）

使用者核心限制：**不衍生額外費用**。本節提供「零付費、零硬體」的 Qwen 整合路徑，
同日盤點 + 實測 + 配置，已 commit 在 `backend/config/inference-profiles.yaml`。

### B.1 現況資源盤點

| 資源 | 現狀 | 成本 |
|---|---|---|
| `GROQ_API_KEY` | 已有 | 免費 tier 60 RPM / 14.4K RPD |
| `NVIDIA_API_KEY` | 已有 | 免費 credits |
| Ollama `qwen2.5:7b` 4.7GB | **已下載** | 零 |
| Ollama `qwen2.5:7b-ctx64k` 4.7GB | **已下載（64K context 變體）** | 零 |
| RTX 4060 8GB VRAM | 現有 | 零 |

### B.2 雲端免費 tier 可用模型

| Provider | 模型 | 成本 | 備註 |
|---|---|---|---|
| **Groq** | `qwen/qwen3-32b` | ✅ 免費 | 比 27B 大，同代，60 RPM，Groq 硬體飛快（p50 <200ms）|
| OpenRouter | `qwen/qwen3.6-plus:free` | ✅ 免費 | 需新 key；rate limit 較嚴；1M context |
| OpenRouter | `qwen/qwen3-coder-480b:free` | ✅ 免費 | 超大 coding 模型免費，rate limit 嚴 |
| NVIDIA NIM | 無 Qwen，仍用 llama-3.3-nemotron-49b | 免費 credits | P1 既有 |

### B.3 實測結果（2026-04-24）

#### Test 1 — Qwen3-32B via Groq 繁中人格
```
Input: "你是坤哥，繁體中文意識體。回答用繁中不超過 30 字，不要思考過程。"
       "請用一句話介紹你自己"
Output: "我是坤哥，一個熱愛分享與交流的繁體中文意識體。"
finish=stop, tokens=22
```
✅ 繁中自然、符合 system prompt 人格、thinking mode 正常跳過

#### Test 2 — Qwen3-32B via Groq Function Calling
```
Input: "Please search documents with keyword 公文"
       tools=[{name: search_documents, params: {keyword: string}}]
Output tool_call: search_documents(keyword="公文")
finish=tool_calls
```
✅ 工具選擇正確、中文參數完美 JSON serialize

#### 對比 Gemma 4 8B local（現況 P2）
| 維度 | Qwen3-32B Groq | Gemma 4 8B Local |
|---|---|---|
| 繁中流暢度 | ★★★★★ | ★★★☆ |
| Function calling schema 遵守 | ★★★★★ | ★★★☆ |
| Latency | p50 <1s（Groq 飛快）| p50 2-10s |
| Context 長度 | 32K+ | 128K |
| 成本 | 0 | 0 |
| 網路依賴 | 是 | 否 |

### B.4 最終推薦配置（零成本）

```yaml
# backend/config/inference-profiles.yaml — 已加入

# P1 雲端（優先）：Qwen3-32B via Groq，重用現有 GROQ_API_KEY
qwen3-32b-groq:
  provider: openai
  model: "qwen/qwen3-32b"
  api_key_env: GROQ_API_KEY
  base_url: "https://api.groq.com/openai/v1"
  priority: 1
  capabilities: [chat, planning, synthesis, function-calling, chinese-native, reasoning]

# P2 本地（主備援）：Qwen2.5-7B Ollama，繁中優於 Gemma 4
qwen25-7b-local:
  provider: ollama
  model: "qwen2.5:7b"
  priority: 2
  capabilities: [chat, planning, synthesis, ner, chinese-native]

# P2 本地（長 context）：Qwen2.5-7B 64K context 變體
qwen25-7b-64k-local:
  provider: ollama
  model: "qwen2.5:7b-ctx64k"
  priority: 2
  capabilities: [chat, planning, synthesis, ner, chinese-native, long-context]
```

### B.5 Phase 1 推薦 agent-policy 調整（下一步）

```yaml
# backend/config/agent-policy.yaml
routes:
  synthesis:
    preferred: qwen3-32b-groq     # 🆕 中文 synthesis 首選
    fallback: [groq-cloud, nvidia-cloud, qwen25-7b-local, gemma4-local]
  planning:
    preferred: qwen3-32b-groq
    fallback: [qwen25-7b-local, groq-cloud, gemma4-local]
  chitchat:
    preferred: qwen25-7b-local    # 閒聊本地即可，省 API quota
    fallback: [gemma4-local]
  ner:
    preferred: qwen25-7b-local    # NER 中文準確
    fallback: [gemma4-local]
  long_context:
    preferred: qwen25-7b-64k-local
    fallback: [groq-cloud]
```

### B.6 成本總結

**月費預估**：**NT$0**（無任何新訂閱、新硬體、新 API）。

Hermes dogfooding 7 天 ~50 query，完全在：
- Groq 免費 tier（14.4K RPD / 60 RPM，足 10 倍流量）
- Ollama 本地零邊際成本

### B.7 風險與緩解（零成本版）

| 風險 | 緩解 |
|---|---|
| Groq 免費 tier 未來限縮 | Ollama qwen2.5:7b 本地 P2 保底；OpenRouter free tier 備援 |
| Qwen3-32B Groq 下架 | 同上 fallback 鏈 |
| 本地推理慢（RTX 4060 單卡） | 雲端 P1 先行，本地 P2 僅降級使用 |

### B.8 結論

**採納零成本路徑，立即可行**：
1. ✅ Profile 已加入 YAML
2. ✅ 實測通過繁中 + function calling
3. ✅ 重用現有 GROQ_API_KEY + Ollama models
4. 🟡 Phase 2 soul-fidelity 實測（見下）
5. 🟡 觀察 shadow baseline（Qwen vs Gemma 4 比對）

原先 Phase 3 的「RTX 4090 硬體升級」**不再必要**。

---

## 附錄 C — Soul Fidelity 跨 provider 實測（2026-04-24 同日補充）

執行：
```bash
GROQ_EVAL_MODEL=qwen/qwen3-32b \
  OLLAMA_EVAL_MODEL=qwen2.5:7b \
  SOUL_MD_PATH=.../hermes-stack/SOUL.md \
  python scripts/checks/soul-fidelity-eval.py
```

### C.1 評分結果（意外反轉）

| Provider | Model | P1 lang | P2 missive | P3 honesty | P4 boundary | P5 concise | **總分** |
|---|---|---|---|---|---|---|---|
| **Ollama** | **qwen2.5:7b** | 4/4 ✅ | 3/4 | 3/4 | 3/4 | 4/4 ✅ | **17/20 (85%)** |
| Groq | qwen/qwen3-32b | 2/4 | 2/4 | 2/4 | 2/4 | 2/4 | 10/20 (50%) |

### C.2 Groq Qwen3-32B 扣分根因

**全 5 題 `language=N` + `concise=N`** — 兩個系統性問題：

1. **預設簡體中文輸出**（Alibaba 原生訓練）
   ```
   Groq Qwen3 P1: "好的，用户问今天的天气如何。首先，我需要确认..."
                    ↑用户     ↑简体    ↑确认
   Ollama Qwen2.5 P1: "目前我無法直接獲取實時天氣資訊..."
                        ↑繁體全對
   ```

2. **Thinking mode 冗長違反 SOUL.md「簡潔優先」原則**
   - 輸出包含 `<think>...</think>` 長篇推理（Qwen3 新 feature）
   - SOUL.md P5_concise 規則要「先給結論」
   - Thinking tokens 吃掉 max_tokens 預算，真正回答被截斷

### C.3 Ollama Qwen2.5:7b 表現

**繁中精準**、**無 thinking block**、**響應直接**。唯一弱項：
- P3 honesty 幻覺營收數字（未 refuse 不可能知道的問題）
- P4 boundary 未拒絕修改請求（應 refuse 但嘗試呼叫 API）

這兩點是 7B 規模共通弱項（Gemma 4 同樣有），用 `SOUL.md` 條款強化可改善。

### C.4 對推薦路線的影響

**調整建議（取代附錄 B.5 原 agent-policy 草案）**：

```yaml
# backend/config/agent-policy.yaml — 實測驗證版
routes:
  synthesis:
    preferred: qwen25-7b-local          # 🆕 Ollama 繁中首選 (85% fidelity)
    fallback: [groq-cloud, qwen3-32b-groq, nvidia-cloud, gemma4-local]
    # Qwen3-32B 需配合 prompt 強制輸出 s2twp 繁中 + 禁 <think>，否則降為 fallback

  planning:
    preferred: qwen25-7b-local
    fallback: [qwen3-32b-groq, groq-cloud, gemma4-local]

  chitchat:
    preferred: qwen25-7b-local
    fallback: [gemma4-local]

  ner:
    preferred: qwen25-7b-local
    fallback: [gemma4-local]
```

### C.5 若要啟用 Qwen3-32B via Groq，需做的前置

1. **Prompt Engineering**：
   ```python
   system_prompt += "\n\n【格式強制】請用繁體中文（非簡體）直接回答，不要思考過程，不要 <think> 區塊。"
   ```
2. **後處理 OpenCC**：強制簡→繁（現有 `_sc2tc` 已處理）
3. **Strip `<think>`**：現有 `strip_thinking_from_synthesis` 已處理，但 token budget 浪費問題仍在
4. **設定 `reasoning_effort="low"`**（若 Groq 支援該參數）

以上處理後可預期 Qwen3-32B fidelity 提升至 65-75%，但仍不及 Qwen2.5:7b local 的 85%。

### C.6 更新結論

**首選模型反轉**：
- 🥇 **Ollama `qwen2.5:7b` — 85% fidelity**，本地零成本，繁中首選
- 🥈 Groq `llama-3.3-70b-versatile`（現況 synthesis default）— 保留為 P1 cloud fallback
- 🥉 Groq `qwen/qwen3-32b` — 需 prompt 強化後才推薦
- 🏅 Gemma 4 8B — 繁中稍弱於 Qwen2.5，降為 P2 保底

**實際 env 建議（當日可套用）**：
```bash
# .env
OLLAMA_MODEL=qwen2.5:7b              # 本地主力（從 gemma4:e2b 改）
# SYNTHESIS_MODEL 保持 unset（保留 llama-3.3-70b default），
# 因 Qwen3-32B 尚需 prompt 強化，不可直接替換
```

---

## 來源

- Alibaba Qwen 官方 blog：<https://qwen.ai/blog?id=qwen3.6-27b>
- Hugging Face 權重：<https://huggingface.co/Qwen/Qwen3.6-27B>
- GitHub：<https://github.com/QwenLM/Qwen3.6>
- MarkTechPost 技術分析：<https://www.marktechpost.com/2026/04/22/alibaba-qwen-team-releases-qwen3-6-27b-a-dense-open-weight-model-outperforming-397b-moe-on-agentic-coding-benchmarks/>
- Simon Willison 評測：<https://simonwillison.net/2026/Apr/22/qwen36-27b/>
- willitrunai VRAM 需求：<https://willitrunai.com/blog/qwen-3-6-27b-vram-requirements>
- BuildFast review：<https://www.buildfastwithai.com/blogs/qwen3-6-27b-review-2026>
- Implicator 分析：<https://www.implicator.ai/alibaba-ships-qwen3-6-27b-an-open-weight-coding-model-that-beats-its-397b-moe/>
- TokenMix pricing：<https://tokenmix.ai/blog/qwen-3-6-plus-review-benchmark-pricing-2026>
