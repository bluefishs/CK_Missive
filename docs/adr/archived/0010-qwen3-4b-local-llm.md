# ADR-0010: qwen3:4b 取代 llama3.1:8b 作為本地 LLM

> **狀態**: accepted
> **日期**: 2026-02-26
> **決策者**: 開發團隊
> **關聯**: CHANGELOG v1.71.0

## 背景

專案最初使用 llama3.1:8b 處理本地 LLM 任務（NER 實體提取、意圖解析、Agent 規劃）。在 RTX 4060（8GB VRAM）上，llama3.1:8b 存在以下問題：

- **推論速度慢**：每次請求 5-10 秒，影響使用者體驗
- **JSON 輸出不穩定**：成功解析率約 60%，頻繁產生格式錯誤的 JSON
- **VRAM 佔用過高**：約 7GB，幾乎佔滿顯存，無法同時載入 embedding 模型
- **中文能力不足**：llama3.1 系列對中文支援有限，公文領域表現更差

需要一個更小、更快的模型，在 8GB VRAM 限制下仍能可靠地產生結構化 JSON 輸出，且具備良好的中文理解能力。

## 決策

切換至 qwen3:4b（40 億參數，約 2.5GB VRAM），並搭配以下優化措施：

- **`format="json"` 參數**：Ollama 原生 JSON 模式，強制輸出有效 JSON
- **`think=false` 參數**：停用 Chain-of-Thought 思考過程，減少約 60% 的輸出 token
- **思考模型自動偵測**：`_THINKING_MODEL_PREFIXES = ["qwen3", "deepseek-r1"]`，自動識別並抑制思考 token
- **API 格式統一**：Groq API 的 `response_format={"type":"json_object"}` 自動映射為 Ollama 的 `format="json"`
- **後處理管線**：`_strip_thinking_from_synthesis()` 5 階段白名單法清除殘留思考內容

## 後果

### 正面

- **NER 提取加速**：5 秒 → 1.9 秒（提升 62%）
- **JSON 解析成功率**：~60% → ~95%（搭配 `format="json"`）
- **VRAM 使用大幅降低**：~7GB → ~3GB，騰出空間給 nomic-embed-text embedding 模型
- **`think=false` 消除思考 token 洩漏**：輸出乾淨，無需額外清理
- **中文理解品質良好**：qwen3 系列原生支援中文，公文領域表現優於 llama3.1

### 負面

- **複雜推理能力下降**：4B 參數模型在多步驟推理任務中不如 8B 模型
- **英文能力較弱**：雖非本專案主要需求，但未來國際化時可能成為限制
- **Agent 規劃品質降低**：需搭配 ADR-0009 規則式自動修正引擎補償
- **`think=false` 犧牲推理深度**：對簡單任務無影響，但複雜查詢可能產生較淺層的回答
- **模型版本鎖定風險**：qwen3 系列更新可能改變 JSON 輸出行為

## 替代方案

| 模型 | 評估結果 |
|------|----------|
| phi-3（3.8B） | 中文支援不佳，公文領域表現差 |
| gemma2:9b | 9B 參數在 8GB VRAM 下無法與 embedding 模型共存 |
| mistral:7b | 中文支援有限，JSON 模式不如 qwen3 穩定 |
| llama3.2:3b | 不支援 `format="json"` 結構化輸出 |
| 持續使用 llama3.1:8b | 速度與 JSON 穩定性問題無法接受 |
| 僅使用 Groq 雲端 | 喪失離線能力，違反系統韌性設計原則 |
