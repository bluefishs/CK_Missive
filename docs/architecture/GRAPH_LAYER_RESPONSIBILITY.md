# 圖譜分層職責 — 兩張關係表的分工

> **建立**：2026-08-03
> **觸發**：盤點「`entity_relations` 是不是死表、要不要收斂」時，發現它不是死表，
> 而是**兩層管線的上游**。過程中一度誤判並在 ORM docstring 寫了「已停止寫入、
> 請改用另一張」——**那是錯的**，本文為正式定義，避免下一次又走一遍同樣的彎路。

## 結論先講

**兩張關係表不是重複，是同一條管線的兩層。** 不要合併，也不要把其中一張當成廢棄品。

| | `entity_relations` | `entity_relationships` |
|---|---|---|
| **層級** | 文件級 — 某份公文「提到」的關係 | canonical 級 — 圖譜中確立的關係 |
| **端點** | `source_entity_name` / `target_entity_name`（**字串**） | `source_entity_id` / `target_entity_id`（**外鍵**） |
| **附帶欄位** | `document_id`、`confidence`、`extracted_at` | `weight`、`document_count`、`valid_from`、`invalidated_at` |
| **寫入者** | NER：`extract_entities_for_document` | `GraphIngestionPipeline`（聚合下層）<br>＋ 程式碼／DB／ERP 結構 ingest |
| **ORM** | `models/entity.py::EntityRelation` | `models/knowledge_graph.py::EntityRelationship` |
| **典型 relation_type** | manages / receives / issues / approves / located_in | 上列全部 **＋** imports / calls / has_method / defines_class / serves_route / maps_to |

## 資料流

```
公文文本
   │  NER（LLM 抽 entities + relations）
   ▼
entity_relations              ← 文件級：這份公文說了什麼
   │  GraphIngestionPipeline
   │    · 正規化實體名 → canonical entity
   │    · 合併同義實體、累計 weight / document_count
   ▼
entity_relationships          ← canonical 級：圖譜確立的事實
   ▲
   │  另外三條直接進 canonical 的路徑（不經文件層）：
   └── code_graph AST ingest（imports / calls / has_method / serves_route）
       db_graph_refresh（maps_to：ORM __tablename__ → db_table）
       erp_graph_ingest
```

**判斷寫哪張表的規則**：資料是「從某份文件裡讀出來的」→ 文件層；
是「系統結構本身的事實」（程式碼、schema、ERP 單據關聯）→ 直接進 canonical 層。

## 指標與監控該看哪一張

- **KG 邊數**（`kg_edges_total`）→ **canonical 層**。
  2026-08-03 前它讀的是文件層，於是 48 天固定在 2162，卻因為「有數字」而看起來正常。
- **producer registry** 的「程式圖譜關係」→ canonical 層 + `relation_label='code_graph'`。
- 文件層目前**沒有獨立監控**：它的健康度反映在「NER 是否抽得出關係」，
  而那一層的靜默失效正是 2026-08-03 修掉的（見下）。

## 2026-08-03 修掉的缺陷與**尚未補的存量**

### 已修
NER 的 system prompt 有兩段格式規範，欄位名不一致（`relation` vs `relation_type`），
validator 只讀前者 → **每一條關係都被靜默丟棄**。`document_entities` 一路正常增長，
`entity_relations` 自 2026-06-16 起零新增，而 job 始終回 success。

### ⚠️ 尚未補：存量公文的關係要 backfill
`ExtractionScheduler._process_batch` 對**已有 `document_entities` 的公文一律跳過**
（`reason: 已有提取結果`），而跳過就不會走到聚合管線。目前 NER 覆蓋率 99.1%
（1954/1971），所以：

- **新公文**：欄位名修好後會正常抽出關係並入圖 ✅
- **存量公文**：永遠 skip，**關係不會自動補回來** ❌

canonical 層業務語意關係最後更新停在 **2026-06-02**、僅 328 筆，即為此故
（同期程式結構關係 7835 筆、每日更新）。

補法是對存量公文 `force=True` 重抽，但那是 ~1971 次 LLM 呼叫，
需要 owner 決定執行時機（建議離峰、分批，並先用少量樣本確認關係抽取品質）。

## 不要再做的事

- ❌ 把兩張表合併或刪除其中一張 —— 它們是兩層，不是兩份
- ❌ 看到某張表「很久沒更新」就斷定它廢棄了 —— 先查它的**上游寫入路徑是否還活著**
- ❌ 讓程式結構關係流經文件層 —— 那層的語意是「某份文件提到」，程式碼沒有文件來源
