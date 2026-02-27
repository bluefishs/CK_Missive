# Architecture Decision Records (ADR)

本目錄記錄 CK_Missive 專案的重要架構決策。每筆 ADR 回答三個問題：
**為什麼做這個決定？做了什麼？帶來什麼後果？**

## 狀態說明

| 狀態 | 含義 |
|------|------|
| `proposed` | 提案中，尚未實作 |
| `accepted` | 決策已確定，已實作或實作中 |
| `deprecated` | 已排定移除 |
| `superseded` | 被新的 ADR 取代 |
| `removed` | 程式碼已從專案移除 |
| `rejected` | 考慮過但未採用 |

## ADR 索引

| # | 標題 | 狀態 | 日期 |
|---|------|------|------|
| [0001](0001-groq-primary-ollama-fallback.md) | Groq 為主、Ollama 本地 fallback | accepted | 2026-02-04 |
| [0002](0002-httponly-cookie-csrf-auth.md) | httpOnly Cookie + CSRF + Token Rotation 認證 | accepted | 2026-01-10 |
| [0003](0003-internal-network-auth-bypass.md) | 內網 IP 免認證策略 | accepted | 2026-01-10 |
| [0004](0004-ssot-type-architecture.md) | 前後端型別 SSOT 架構 | accepted | 2026-01-17 |
| [0005](0005-mixed-mode-deployment.md) | 混合部署模式（Docker infra + PM2 app） | accepted | 2026-02-03 |
| [0006](0006-pgvector-document-embeddings.md) | pgvector 768D 文件向量搜尋 | accepted | 2026-02-25 |
| [0007](0007-four-layer-ai-architecture.md) | AI 四層架構（規則→向量→LLM→合併） | accepted | 2026-02-26 |
| [0008](0008-repository-flush-only-strategy.md) | Repository flush-only 交易策略 | accepted | 2026-02-24 |
| [0009](0009-agent-rule-based-self-correction.md) | Agent 規則式自動修正（非 LLM 修正） | accepted | 2026-02-26 |
| [0010](0010-qwen3-4b-local-llm.md) | qwen3:4b 取代 llama3.1:8b 本地模型 | accepted | 2026-02-26 |
| [0011](0011-ai-config-db-crud-removed.md) | AI 配置 DB CRUD 移除（超前開發教訓） | removed | 2026-02-27 |

## 建立新 ADR

1. 複製 [TEMPLATE.md](TEMPLATE.md)
2. 命名為 `NNNN-short-title.md`（四位數序號 + kebab-case）
3. 填寫背景、決策、後果
4. 更新本檔案的索引表
5. 或使用 `/adr new "標題"` 命令自動建立
