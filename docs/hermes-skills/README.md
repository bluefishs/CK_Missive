# Hermes Skills — CK_Missive

依據 [ADR-0014](../adr/0014-hermes-replace-openclaw.md)，以 NousResearch `hermes-agent`（MIT）取代 OpenClaw 作為通道側 Agent runtime。

## 目錄

```
hermes-skills/
└── ck-missive-bridge/          # 將 Missive 後端作為 Hermes tool
    ├── SKILL.md                # Skill 說明（給 Hermes 載入）
    ├── tools.py                # Hermes 原生 tool 註冊（manifest-driven）
    ├── tool_spec.json          # 單一 bridge 版（備援）
    └── install.sh              # 一鍵安裝到 ~/.hermes/skills/
```

## 整合深度層次

| 層級 | 做法 | 狀態 |
|---|---|---|
| L1 — 單一 Bridge | `query_missive` 轉 `/ai/agent/query_sync` | ✅ `tool_spec.json` |
| L2 — 多工具 | 依 `TOOL_MANIFEST` 拆成 7 個原生 tool | ✅ `tools.py` |
| L3 — Skill 生態互通 | Hermes skill 可讀 Missive KG / agent_trace | 🟡 Phase 2 後啟動 |
| L4 — 學習閉環合流 | Hermes skill self-improvement 寫回 Missive AgentLearning | 🔵 規劃中 |

## Deployment（CK_NemoClaw repo）

```bash
# 1. 安裝 Hermes（在 NemoClaw container 或 host）
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# 2. 設定 LLM 走本機 Ollama Gemma 4
hermes config set llm.provider ollama
hermes config set llm.endpoint http://host.docker.internal:11434
hermes config set llm.model gemma4:8b-q4

# 3. 安裝 CK Missive Bridge skill
cd /path/to/CK_Missive/docs/hermes-skills/ck-missive-bridge
bash install.sh

# 4. 設環境變數
export MISSIVE_BASE_URL=http://host.docker.internal:8001
export MISSIVE_API_TOKEN=<token>

# 5. 啟用 gateway
hermes gateway setup telegram
hermes gateway setup discord
hermes gateway start
```

## API 合約鎖定

下列端點視為 **Hermes 整合 public contract**，任何 breaking change 必須：

1. 走 ADR 流程
2. Deprecation 期 ≥ 30 天
3. 同步更新 `tools.py` 與 `tool_spec.json`

| 端點 | Method | 用途 |
|---|---|---|
| `/api/ai/agent/tools/manifest` | GET | 工具清冊（v1.0） |
| `/api/ai/agent/query_sync` | POST | 通用 Agent 問答 |
| `/api/ai/rag/query` | POST | RAG 檢索 |
| `/api/ai/graph/unified` | POST | 知識圖譜統一查詢 |
| `/api/ai/graph/entity` | POST | 實體查詢 |
| `/api/tender/search` | POST | 標案搜尋 |
| `/api/health` | GET | 健康檢查 |

## 觀測

- Missive 端：`SHADOW_ENABLED=1` 會記錄所有經過的請求（30 天自動清理）
- Hermes 端：`~/.hermes/logs/` 有 tool call trace
- 交叉比對：`request_id` 透過 `X-Hermes-Session` header 串接
