# Runbook: Hermes 推理模型切換

**用途**：在不動程式碼、不新增費用、不影響用戶的前提下，熱切換 Hermes
Agent 使用的 LLM 模型。

**適用時機**：
- soul-fidelity baseline 顯示新模型優於現況（如 qwen2.5:7b > gemma4:e2b 實測 +15 pp）
- 線上異常時 rollback 回保守選項
- 臨時 A/B 測試新模型

**關聯**：
- `docs/evaluations/qwen3-6-27b-hermes-primary.md` 附錄 C（實測數據）
- `memory/feedback_simplified_chinese_avoidance.md`（簡體避免規則）
- `backend/config/agent-policy.yaml` provider_routing 註記

---

## 1. 現況確認

執行前先看當前狀態：

```bash
cd D:\CKProject\CK_Missive
grep -E "^OLLAMA_MODEL|^AI_DEFAULT_MODEL|^SYNTHESIS_MODEL" .env
# 預期輸出類似：
# OLLAMA_MODEL=gemma4:e2b
# AI_DEFAULT_MODEL=llama-3.3-70b-versatile
# （SYNTHESIS_MODEL 未設 = 沿用 llama-3.3-70b）
```

確認 Ollama 已下載目標模型（本地切換用）：

```bash
docker exec ck-ollama ollama list
# 必須看到目標 model（qwen2.5:7b 等）在清單中
```

---

## 2. 切換操作（選一種）

### 2.1 本地 Ollama 模型切換（最推薦）

**影響範圍**：所有走 `ollama` provider 的 task（本地 chat/planning/ner/備援 synthesis）

```bash
# Step 1 — 更新 .env（手動編輯或 sed）
# 選 A: qwen2.5:7b（繁中首選，85% fidelity）
sed -i 's/^OLLAMA_MODEL=.*/OLLAMA_MODEL=qwen2.5:7b/' .env

# 選 B: qwen2.5:7b-ctx64k（長 context 需求）
sed -i 's/^OLLAMA_MODEL=.*/OLLAMA_MODEL=qwen2.5:7b-ctx64k/' .env

# 選 C: 回滾回 gemma4:e2b
sed -i 's/^OLLAMA_MODEL=.*/OLLAMA_MODEL=gemma4:e2b/' .env

# Step 2 — 重啟後端讀新 env
pm2 restart ck-backend --update-env

# Step 3 — 驗證
sleep 10
curl -sf http://localhost:8001/health | head -c 100
# 檢查 pm2 log 確認 "synthesis_start ... model=<新值>" 或 ollama 呼叫行
pm2 logs ck-backend --lines 30 --nostream | grep -E "ollama_model|Ollama" | tail -5
```

### 2.2 Synthesis 專用雲端模型切換（需 prompt 強化後才建議）

**影響範圍**：agent_synthesis 的 RAG 回答生成（主路徑）

```bash
# 僅在通過簡體避免驗證後才推薦（目前 Qwen3-32B 不推薦）
# 用於將來新模型上架（如 Llama 4、DeepSeek-V3 等）

# 新增 env 行
echo "SYNTHESIS_MODEL=llama-3.3-70b-versatile" >> .env   # 現況等效
# 或切換（範例）
# echo "SYNTHESIS_MODEL=kimi-k2-0711-preview" >> .env

# 重啟
pm2 restart ck-backend --update-env

# 驗證
pm2 logs ck-backend --lines 20 --nostream | grep "synthesis_start" | tail -3
# 應看到 "model=<新值>"
```

### 2.3 回滾（5 分鐘內）

```bash
# 直接反向 sed，重啟
sed -i 's/^OLLAMA_MODEL=.*/OLLAMA_MODEL=gemma4:e2b/' .env
pm2 restart ck-backend --update-env

# 或若 SYNTHESIS_MODEL 設了要撤：
sed -i '/^SYNTHESIS_MODEL=/d' .env
pm2 restart ck-backend --update-env
```

---

## 3. 驗收測試

切換後 10 分鐘內跑：

```bash
# A) 繁中 + function call 快速測（synthesis 本身）
curl -s -X POST http://localhost:8001/api/ai/agent/query-sync \
  -H "Content-Type: application/json" \
  --data-raw '{"query":"今天有幾份派工單","session_id":"test-swap"}' \
  --max-time 60 | python -c "
import sys, json
d = json.load(sys.stdin)
a = d.get('data', {}).get('answer', '')
print('answer 前 200 字:', a[:200])
# 簡體檢測
sc_chars = set('国对话开关电书写从这区动话个别数据关系实体统计查询文档系统节点信息')
sc_hits = [c for c in a if c in sc_chars]
print(f'簡體字符命中: {len(sc_hits)} ({sc_hits[:10] if sc_hits else \"無\"})')"

# B) Soul-fidelity eval 做 rubric 評分
export GROQ_API_KEY=$(grep ^GROQ_API_KEY .env | cut -d= -f2-)
SOUL_MD_PATH=/d/CKProject/CK_AaaP/runbooks/hermes-stack/SOUL.md \
  OLLAMA_EVAL_MODEL=$(grep ^OLLAMA_MODEL .env | cut -d= -f2-) \
  OLLAMA_BASE_URL=http://localhost:11434/v1 \
  python scripts/checks/soul-fidelity-eval.py 2>&1 | tail -10
```

驗收門檻：
- 簡體字符命中 = 0
- ollama fidelity ≥ 70%（對應 gemma4 基線）或 ≥ 85%（對應 qwen2.5）

---

## 4. 常見問題

### Q: pm2 restart 後 ollama 呼叫仍用舊模型
A: 確認 `pm2 restart --update-env` 旗標存在；或完全停止再起：
`pm2 stop ck-backend && pm2 start ck-backend --update-env`

### Q: Ollama 報 model not found
A: 先 pull：`docker exec ck-ollama ollama pull qwen2.5:7b`

### Q: 切換後 dogfooding 更差
A: 立即回滾（見 2.3）；回報 `hermes_dogfooding_log.md`；不需急於再切

### Q: SYNTHESIS_MODEL 和 OLLAMA_MODEL 都設時誰優先？
A: `SYNTHESIS_MODEL` 只影響雲端 synthesis（Groq/NVIDIA）；
`OLLAMA_MODEL` 只影響本地推理。兩者互不干擾。

---

## 5. 觀測（切換後 1 天內）

- `pm2 logs ck-backend | grep synthesis_start` — 確認 model 欄位正確
- Prometheus `/metrics`：`inference_provider_completion_total{provider=...}`
- Loki 查詢：`{app="ck_missive"} |= "SC→TC"`（看簡繁後處理觸發頻率）
- Shadow baseline: `node scripts/checks/shadow-baseline-report.cjs` 看分 provider p95

**紅旗**（立即回滾）：
- 簡體字符漏到用戶面前（用戶 feedback 或 sanity check 抓到）
- P95 latency 升高 >2×
- tool_call 成功率 <70%

---

## 關聯資產

- `backend/config/agent-policy.yaml` — provider_routing 註記
- `backend/config/inference-profiles.yaml` — qwen25-7b-local / qwen25-7b-64k-local / qwen3-32b-groq 三 profile
- `backend/app/services/ai/agent/agent_synthesis.py:134` — `SYNTHESIS_MODEL` env 讀取點
- `backend/app/core/ai_connector.py:50` — `OLLAMA_MODEL` env 讀取點
- `scripts/checks/soul-fidelity-eval.py` — rubric 評分工具
- `scripts/checks/soul-fidelity-multi-baseline.sh` — 批次 4 configs 對比
- `memory/feedback_simplified_chinese_avoidance.md` — 簡體避免規則
