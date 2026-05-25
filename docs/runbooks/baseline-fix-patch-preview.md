# P0 Baseline 品質修復 — Patch Preview（待用戶授權）

> **產出日期**：2026-04-24
> **狀態**：待審閱，**未套用**
> **關聯**：ADR-0030（Hermes GO/NO-GO）、`memory/known_issue_baseline_timeout.md`、`docs/runbooks/hermes-model-swap.md`
> **根因**：Ollama GPU semaphore 排隊災情（149 timeout / 16 success = 9.7%）+ `agent-policy.yaml` 把 ollama 設首選

## 診斷證據

| 指標 | 值 | 來源 |
|---|---|---|
| Shadow baseline 成功率 | 47.26% | `scripts/checks/shadow-baseline-report.cjs` |
| Ollama 成功率 | **9.7%**（16/165） | `backend/logs/shadow_trace.db` group by provider |
| Ollama timeout 平均 | 90,140 ms（觸 90s 天花板） | 同上 |
| Ollama success 平均 | 33,417 ms | 同上 |
| Groq 成功率 | 100%（85/85），avg 12,774 ms | 同上 |
| NVIDIA 成功率 | 97.7%（42/43），avg 23,178 ms | 同上 |
| `inference_semaphore` 配置 | `max=3, acquire timeout=90s` | `backend/app/core/inference_semaphore.py:45` |
| `provider_routing.chat/planning/synthesis` | `[ollama, groq, nvidia]`, `prefer_local:true` | `backend/config/agent-policy.yaml:97-106` |

---

## 修復路徑 A：降 Ollama 優先級（**推薦**，最小風險）

### Diff

```diff
# backend/config/agent-policy.yaml
 provider_routing:
   chat:
-    preferred: [ollama, groq, nvidia]
-    prefer_local: true
+    preferred: [groq, nvidia, ollama]
+    prefer_local: false
   planning:
-    preferred: [ollama, groq, nvidia]
-    prefer_local: true
+    preferred: [groq, nvidia, ollama]
+    prefer_local: false
   synthesis:
-    preferred: [ollama, groq, nvidia]
-    prefer_local: true
+    preferred: [groq, nvidia, ollama]
+    prefer_local: false
   ner:
     preferred: [ollama, nvidia, groq]      # 保留（Groq 不支援 NER）
     prefer_local: true
   multimodal:
     preferred: [ollama]                     # 保留（僅 Gemma vision）
   embedding:
     preferred: [ollama]                     # 保留（nomic-embed）
```

### 執行指令

```bash
cd D:\CKProject\CK_Missive
# 編輯 backend/config/agent-policy.yaml 照上面 diff 改
pm2 restart ck-backend --update-env
sleep 10
curl -sf http://localhost:8001/health | head -c 100
```

### 預期效果

- chat/planning/synthesis 流量改走 Groq 首選（12s avg）
- 成功率 47% → 預期 ~90%+（Groq 目前 100%）
- Ollama 仍保留為 NER/multimodal/embedding 主力，semaphore 壓力大減
- Groq 每日配額：目前 `GROQ_DAILY_REQ_LIMIT=1000`；shadow baseline 8 天僅 ~85 groq 呼叫，配額充裕

### 回滾

```bash
cd D:\CKProject\CK_Missive
git checkout backend/config/agent-policy.yaml
pm2 restart ck-backend --update-env
```

### 風險

- Groq free tier 可能某日用完 → fallback 到 NVIDIA（97.7% 成功）→ 最後 Ollama
- Soul fidelity：Groq llama-3.3-70b 約 75%（vs Ollama qwen2.5:7b 85%）— 略降但遠超 gemma4 70%

---

## 修復路徑 B：切換 Ollama 模型 gemma4 → qwen2.5:7b（runbook 已備）

### 執行指令（依 `docs/runbooks/hermes-model-swap.md` §2.1）

```bash
cd D:\CKProject\CK_Missive
sed -i 's/^OLLAMA_MODEL=.*/OLLAMA_MODEL=qwen2.5:7b/' .env
pm2 restart ck-backend --update-env
```

### 預期效果

- Soul fidelity +15 pp（70% → 85%）
- Timeout 問題**仍存在**（同樣 RTX 4060 8GB、同 semaphore 設定）
- 單純 model 切換不解決 9.7% 成功率的核心瓶頸

### 風險

- qwen2.5:7b Q4 ~4.7GB VRAM，比 gemma4 8B Q4 小，semaphore 壓力可能略降
- 但單 request 速度差異不大；根本瓶頸是併發非單速

### 建議

- **單獨 B 不足以解 P0**，建議與 A 合併執行

---

## 修復路徑 C：縮短 inference_semaphore acquire timeout

### Diff

```diff
# backend/app/core/ai_connector.py
         # GPU 並發控制 — 避免多請求同時 OOM (RTX 4060 8GB)
         from app.core.inference_semaphore import get_inference_semaphore
         sem = get_inference_semaphore()
-        async with sem.acquire():
+        async with sem.acquire(timeout=30):  # fail-fast，讓 fallback 更快觸發
             return await self._ollama_completion_inner(
```

### 預期效果

- Ollama 請求排隊 >30s 即 fail，立即 fallback 到 Groq
- p95 latency 從 90s 降至 ~35s（30s semaphore wait + 5s fallback)

### 風險

- `ai_connector._ollama_completion` 呼叫者是否都有 fallback？需補驗證
  - `rag_query_service.py` / `entity_extraction_service.py` 等
- 若無 fallback：request 直接 fail，用戶感知變差
- **建議與 A 合併**：A 先降低 Ollama 壓力，C 做安全網

---

## 推薦組合方案（最平衡）

```
1. 執行路徑 A（yaml 改動）—— 立即解 P0（47% → 90%+）
2. 觀察 2-3 天 baseline
3. 若 soul fidelity 不夠好 → 加執行 B（切 qwen2.5:7b）
4. 若 Ollama 偶發排隊（multimodal/embedding 高峰）→ 加執行 C
```

總耗時：路徑 A 約 5 分鐘（含驗證）

---

## 驗收條件（套用後）

跑 `node scripts/checks/shadow-baseline-report.cjs`，24 小時後：

- [ ] 整體成功率 ≥ 90%
- [ ] web channel 成功率 ≥ 90%
- [ ] p95 latency < 30s
- [ ] timeout error 數 / 日 < 5

若未達，依 A→B→C 順序加策。

---

## 檔案改動清單

| 路徑 | 檔案 | 行數 |
|---|---|---|
| A | `backend/config/agent-policy.yaml` | 4 處小改 |
| B | `.env` | 1 行 |
| C | `backend/app/core/ai_connector.py` | 1 行 |

共 3 檔 6 行改動。
