# ADR-0006: pgvector 768 維文件向量搜尋

> **狀態**: accepted
> **日期**: 2026-02-25
> **決策者**: 開發團隊
> **關聯**: CHANGELOG v1.62.0

## 背景

CK_Missive 系統中累積了 728 筆公文資料，傳統的關鍵字搜尋（`LIKE` / `ILIKE`）在以下場景表現不佳：

1. **同義詞問題** — 使用者搜尋「環保局」但公文中記載為「環境保護局」，關鍵字搜尋無法匹配
2. **語意理解** — 搜尋「關於噪音的投訴」需要理解語意才能找到標題為「陳情噪音擾鄰案」的公文
3. **模糊查詢** — 使用者可能只記得大概內容，需要模糊匹配能力

同時，系統已有 PostgreSQL 作為主要資料庫，若能在同一資料庫內實現向量搜尋，可避免引入額外基礎設施元件，降低維運複雜度。

## 決策

在 PostgreSQL 16 中啟用 **pgvector 0.8.0** 擴充，實作文件向量搜尋：

- **Embedding 模型**：`nomic-embed-text`（透過 Ollama 本地生成），輸出 **768 維**向量（非 384 維，此為早期誤判已修正）
- **索引策略**：使用 HNSW（Hierarchical Navigable Small World）索引，提供近似最近鄰搜尋，查詢速度遠優於暴力掃描
- **搜尋策略**：Hybrid Search 混合模式
  - 向量語意搜尋為主（cosine similarity）
  - 關鍵字匹配作為排序加權因子
  - 透過 `DocumentQueryBuilder` 統一整合兩種搜尋結果
- **Feature Flag**：`.env` 中的 `PGVECTOR_ENABLED` 控制功能開關，支援漸進式上線
- **ORM 整合**：使用 `column.cosine_distance()` ORM 方法，禁止 `text()` 原生 SQL，確保型別安全

## 後果

### 正面

- 無需額外部署向量資料庫，PostgreSQL 一站式解決關聯查詢與向量搜尋
- 文件資料與向量在同一交易中更新，確保資料一致性
- 已達成 100% Embedding 覆蓋率（728/728 筆文件）
- HNSW 索引在千級資料量下查詢延遲極低（<10ms）
- Ollama 本地生成 Embedding，零 API 費用
- `EmbeddingManager` 提供 LRU 快取與覆蓋率統計，便於監控

### 負面

- pgvector 為 PostgreSQL 擴充，增加資料庫部署依賴（Docker image 需包含此擴充）
- 768 維向量相較 384 維使用更多儲存空間（每筆約 3KB）
- 文件新增或修改時需同步更新 Embedding，增加寫入路徑的複雜度
- Feature Flag 時序問題：`load_dotenv()` 必須在 ORM 模型 import 之前執行，否則 `PGVECTOR_ENABLED` 讀不到值
- Alembic 遷移需先查詢 `pg_available_extensions` 再執行 `CREATE EXTENSION`，避免環境不支援時報錯

## 替代方案

| 方案 | 評估結果 |
|------|----------|
| **Elasticsearch** | 全文搜尋能力強，但需要獨立部署、索引同步、學習 DSL，對 700 筆資料規模而言過於笨重 |
| **Pinecone** | 託管式向量資料庫，免維運，但僅限雲端、有持續費用、政府機關可能有資料外洩疑慮 |
| **ChromaDB** | 輕量級向量資料庫，但需要獨立程序，且與 PostgreSQL 交易無法原子化 |
| **Qdrant** | 功能完善的向量資料庫，但對 700 筆資料規模而言引入過多複雜度 |

最終選擇 pgvector，在現有 PostgreSQL 基礎上擴充向量能力，兼顧簡潔與功能。
