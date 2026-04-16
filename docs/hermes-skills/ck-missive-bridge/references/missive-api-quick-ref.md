# Missive API Quick Reference

> 供 Hermes Agent 內部 context 參考，不需用戶閱讀。

## 認證

- **Bearer Token**: `Authorization: Bearer <MISSIVE_API_TOKEN>`
- **Service Token**: `X-Service-Token: <MISSIVE_API_TOKEN>`（跨服務聯邦用）
- 所有端點均為 POST（資安政策，防 URL 快取洩漏）

## Base URL

- 本機: `http://127.0.0.1:8001/api`
- Docker: `http://host.docker.internal:8001/api`
- 公網: `https://missive.cksurvey.tw/api`

## 端點速查

### 通用查詢

| 端點 | 用途 | 參數 |
|---|---|---|
| `POST /api/ai/agent/query_sync` | 通用領域查詢（公文+案件+ERP+標案） | `{"question": "...", "session_id": "...", "channel": "hermes"}` |
| `POST /api/ai/agent/tools` | 取得 tool manifest | `{}` |

### RAG 語意搜尋

| 端點 | 用途 | 參數 |
|---|---|---|
| `POST /api/ai/rag/query` | 公文語意搜尋（pgvector 768D） | `{"query": "...", "top_k": 5}` |

### 知識圖譜

| 端點 | 用途 | 參數 |
|---|---|---|
| `POST /api/v1/ai/graph/entity/search` | 實體模糊搜尋 | `{"query": "...", "entity_type": "person/company/government/project"}` |
| `POST /api/v1/ai/graph/entity/detail` | 實體詳情 + 別名 | `{"entity_id": "..."}` |
| `POST /api/v1/ai/graph/entity/neighbors` | K-hop 鄰居展開 | `{"entity_id": "...", "hops": 1}` |
| `POST /api/v1/ai/graph/entity/shortest-path` | 兩實體最短路徑 | `{"source_id": "...", "target_id": "..."}` |
| `POST /api/v1/ai/graph/entity/timeline` | 實體時序脈絡 | `{"entity_id": "..."}` |
| `POST /api/v1/ai/graph/unified-search` | 多圖譜同時搜尋 | `{"query": "..."}` |

### KG 聯邦

| 端點 | 用途 | 參數 |
|---|---|---|
| `POST /api/ai/federation/search` | 跨域聯邦搜尋（Missive + LvrLand + Tunnel） | `{"query": "...", "domains": [...]}` |
| `POST /api/ai/federation/contribute` | 跨域貢獻實體 | `{"entity": {...}, "domain": "..."}` |

### 文件 / 案件

| 端點 | 用途 | 參數 |
|---|---|---|
| `POST /api/v1/documents-enhanced/list` | 公文列表查詢（含分頁） | `{"filters": {...}, "page": 1, "per_page": 20}` |
| `POST /api/v1/projects/list` | 承攬案件列表 | `{"filters": {...}}` |
| `POST /api/v1/projects/{id}/detail` | 案件詳情 | path param: id |

### 回應格式

```json
{
  "success": true,
  "items": [...],
  "pagination": {"page": 1, "per_page": 20, "total": 100},
  "error": null
}
```

Agent query_sync 回應：
```json
{
  "answer": "案號 CK2026003 目前於施工中...",
  "sources": [{"type": "document", "id": "...", "title": "..."}],
  "trace_id": "..."
}
```
