# ADR-0001: Groq 雲端 API 為主、Ollama 本地推論 fallback

> **狀態**: accepted
> **日期**: 2026-02-04
> **決策者**: 開發團隊
> **關聯**: CHANGELOG v1.37.0

## 背景

CK_Missive 公文管理系統需要 LLM 能力來支援多項文件 AI 功能，包括：公文摘要、自動分類、關鍵字提取、搜尋意圖解析（SearchIntentParser）等。在選擇 LLM 供應商時，需要在以下三個面向取得平衡：

1. **速度** — 使用者互動式功能（如 RAG 問答、Agent 查詢）需要低延遲回應
2. **成本** — 專案預算有限，需要控制 API 呼叫費用
3. **離線能力** — 政府機關內網環境可能無法存取外部 API，需要本地推論備援

此外，系統架構需要足夠彈性，以便未來切換模型或供應商時不影響上層業務邏輯。

## 決策

採用**雙層 LLM 架構**，透過 AI Connector 抽象層統一路由：

- **主要路徑**：Groq Cloud API（免費方案，sub-second 延遲）
  - 用於 RAG 串流問答、Agent 規劃、NER 實體提取等高品質需求場景
  - `response_format={"type": "json_object"}` 保證結構化輸出
- **備援路徑**：Ollama 本地推論（NVIDIA RTX 4060 8GB VRAM）
  - 模型：qwen3:4b（`think=false` 停用思考模式）+ nomic-embed-text（Embedding）
  - 用於網路中斷時的降級服務，以及 Embedding 生成（本地優先）
- **抽象層**：`ai_connector.py` 統一封裝 Groq 與 Ollama 的 `chat_completion` 介面
  - `prefer_local` 參數控制優先使用本地或雲端
  - `_THINKING_MODEL_PREFIXES` 自動偵測需要停用思考模式的模型

## 後果

### 正面

- Groq 延遲極低（Agent 2-4 秒完成完整查詢流程），使用者體驗佳
- 網路中斷時自動 fallback 至 Ollama，系統不中斷服務
- AI Connector 抽象層使模型切換只需修改配置，不需改動業務邏輯
- Embedding 使用本地 Ollama（nomic-embed-text），無 API 費用
- Groq 免費方案足以支撐目前使用量

### 負面

- Groq 免費方案有速率限制（RPM/TPM），高流量時可能觸發限流
- Ollama 本地模型（qwen3:4b）品質明顯低於雲端模型，planning 品質不佳（回顯系統提示而非 JSON 計劃），需要空計劃 hints 強制注入機制
- 需要維護兩套整合路徑（Groq SDK + Ollama HTTP），增加維護成本
- Ollama fallback 延遲較高（14-29 秒 vs Groq 2-4 秒）

## 替代方案

| 方案 | 評估結果 |
|------|----------|
| **OpenAI API** | 品質最佳，但無免費方案，長期成本高 |
| **純 Ollama 本地** | 零成本、完全離線，但推論速度慢且小模型品質不足以支撐生產環境 |
| **Azure OpenAI** | 企業級支援，但設定複雜、需要 Azure 訂閱，對小型專案不划算 |
| **單一供應商** | 架構簡單，但失去備援能力與彈性 |

最終選擇 Groq + Ollama 雙層架構，兼顧速度、成本與可靠性。
