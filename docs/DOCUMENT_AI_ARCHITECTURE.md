# Document AI 架構 — OCR + LLM 混合架構

> **版本**: 1.0.0 | **日期**: 2026-03-29 | **狀態**: 生產就緒

---

## 一、架構總覽

```
                    ┌─────────────────────────────────┐
                    │         Document AI Engine       │
                    └──────────────┬──────────────────┘
                                   │
          ┌────────────┬──────────┼──────────┬────────────┐
          ▼            ▼          ▼          ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌───────┐ ┌───────┐ ┌──────────┐
    │ OCR 層   │ │ 解析層   │ │ NLP層 │ │向量層 │ │ 知識層   │
    │Tesseract │ │pdfplumber│ │LLM NER│ │nomic  │ │ KG 圖譜  │
    │PyMuPDF   │ │python-doc│ │摘要   │ │pgvec  │ │ 聯邦     │
    │cv2+pyzbar│ │直讀 txt  │ │分類   │ │RAG    │ │ 跨域     │
    └──────────┘ └──────────┘ └───────┘ └───────┘ └──────────┘
```

## 二、OCR + LLM 混合策略

### 文字提取管線

```
附件上傳 → 副檔名判斷
  │
  ├── .pdf → pdfplumber.extract_text()
  │           │
  │           ├── 文字 ≥ 400 字/頁 → 直接使用 ✅
  │           └── 文字 < 400 字/頁 → OCR 備援
  │                 └── PyMuPDF render 300DPI → Tesseract (chi_tra+eng) → 取較長結果
  │
  ├── .docx → python-docx 段落提取
  │
  ├── .txt → UTF-8 直讀 (500KB 上限)
  │
  └── 圖片 (.jpg/.png) → Tesseract OCR + EXIF 旋轉修正
```

### 發票 OCR 專用管線

```
發票影像 → cv2 前處理 (灰階+二值化+降噪)
  │
  ├── pyzbar QR 掃描 → MIG 格式解析 (字軌/金額/日期)
  │
  └── Tesseract 全文 OCR → 正則提取 (發票號/金額/稅額/統編)
```

## 三、Document AI 技能圖譜

```
🌳 Document AI 技能樹
│
├── 📄 文字提取 (Text Extraction) ★★★★★
│   ├── ✅ PDF 文字型 — pdfplumber (直接提取)
│   ├── ✅ PDF 掃描型 — Tesseract + PyMuPDF (OCR 備援)
│   ├── ✅ DOCX — python-docx (段落提取)
│   ├── ✅ TXT — UTF-8 直讀
│   └── ✅ 圖片 — Tesseract (chi_tra+eng, 30s timeout)
│
├── 🔍 文件理解 (Document Understanding) ★★★★
│   ├── ✅ 摘要生成 — LLM 摘要 + 串流 SSE
│   ├── ✅ 分類建議 — 9 類公文 + 收發文判斷
│   ├── ✅ 關鍵字提取 — LLM + 快取
│   ├── ✅ 機關匹配 — 語意比對 + 評分
│   └── ✅ 意圖解析 — 規則→向量→LLM 三層
│
├── 🧩 文件分段 (Document Chunking) ★★★★★
│   ├── ✅ 段落分割 — 中文標點 + 英文句號
│   ├── ✅ 滑動窗口 — 2000 字上限, 100 字重疊
│   ├── ✅ 反向合併 — 短 chunk 合併 (>500 字)
│   └── ✅ 附件內容分段 — [附件:xxx] 前綴標記 ← NEW
│
├── 🔢 向量索引 (Vector Indexing) ★★★★
│   ├── ✅ nomic-embed-text 768D — Ollama 本地
│   ├── ✅ LRU 快取 — 500 項, 30 分鐘 TTL
│   ├── ✅ 批次生成 — 5 並行 semaphore
│   ├── ✅ pgvector — PostgreSQL 向量搜尋
│   └── ✅ 附件內容向量化 — 混合索引管線 ← NEW
│
├── 🏷️ 實體識別 (NER) ★★★★
│   ├── ✅ LLM 提取 — org/person/project/location/date/topic
│   ├── ✅ 正規化 — CanonicalEntity 4 階段策略
│   ├── ✅ 關係建立 — EntityRelation (issues/belongs_to...)
│   ├── ✅ 批次排程 — extraction_scheduler 背景執行
│   └── ✅ 知識圖譜入圖 — graph_ingestion_pipeline
│
├── 🎤 語音轉文字 (Voice-to-Text) ★★★
│   ├── ✅ Groq Whisper — large-v3-turbo (主要)
│   ├── ✅ Ollama Whisper — 本地備援
│   └── ✅ LINE 語音 — m4a 自動處理
│
├── 📱 發票辨識 (Invoice Recognition) ★★★★
│   ├── ✅ QR Code — pyzbar + MIG 規格
│   ├── ✅ OCR 全文 — Tesseract 結構化提取
│   ├── ✅ cv2 前處理 — 灰階+二值化+降噪
│   └── ✅ LINE 自動 — 圖片→OCR→費用報銷
│
├── 🔎 語意搜尋 (Semantic Search) ★★★★
│   ├── ✅ RAG v2.4 — Hybrid 檢索 (keyword+vector)
│   ├── ✅ BM25 — tsvector 全文搜尋
│   ├── ✅ 同義詞擴展 — 53 組字典
│   ├── ✅ 重排序 — Hybrid reranker
│   └── 🔮 RAG v3 — 附件內容索引 (本次實作)
│
└── 🔮 未來演進
    ├── 📊 表格辨識 — PDF 表格結構化提取
    ├── 📐 版面分析 — 文件 layout 偵測
    ├── 🖼️ 圖表理解 — 圖片內容 captioning
    └── 📝 手寫辨識 — 手寫中文 OCR
```

## 四、附件內容索引管線 (v1.0.0)

### 架構

```
DocumentAttachment (733 附件)
  │
  ▼ AttachmentContentIndexer
  │
  ├── _extract_text(file_path, ext)
  │     ├── PDF: pdfplumber + OCR 備援 (50 頁上限)
  │     ├── DOCX: python-docx
  │     └── TXT: UTF-8 直讀
  │
  ├── split_into_chunks(text) — 複用 DocumentChunker
  │
  ├── _generate_embeddings(texts) — 複用 EmbeddingManager
  │
  └── → DocumentChunk (document_id, chunk_text, embedding)
        ↓
      RAG 檢索時自動包含附件內容 ✅
```

### API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/ai/embedding/attachment-index` | POST | 附件索引 (單筆/批次) |
| `/ai/embedding/attachment-stats` | POST | 附件索引覆蓋統計 |

### 使用範例

```bash
# 索引單一附件
curl -X POST http://localhost:8001/api/ai/embedding/attachment-index \
  -H "Authorization: Bearer <token>" \
  -d '{"attachment_id": 123}'

# 索引一篇公文的所有附件
curl -X POST http://localhost:8001/api/ai/embedding/attachment-index \
  -d '{"document_id": 456}'

# 批次索引 (背景)
curl -X POST http://localhost:8001/api/ai/embedding/attachment-index \
  -d '{"batch": true, "limit": 100}'
```

## 五、多模態發展路線圖

### Phase 1: 文字多模態 (已完成)
- ✅ PDF/DOCX/TXT 內容提取
- ✅ OCR 備援 (掃描型 PDF)
- ✅ 語音轉文字 (Whisper)
- ✅ QR Code 發票辨識

### Phase 2: 附件內容索引 (本次)
- ✅ 附件內容→chunk→embedding 管線
- ✅ RAG 自動包含附件內容
- ✅ 批次排程端點

### Phase 3: 表格與版面 (規劃中)
- 📊 PDF 表格結構化 (pdfplumber.extract_tables)
- 📐 版面分析 (文件 layout 區域偵測)
- 📋 表格→JSON 結構化資料

### Phase 4: 視覺理解 (遠期)
- 🖼️ 圖表 captioning (VLM 視覺語言模型)
- 📝 手寫中文辨識 (handwriting OCR)
- 🎨 圖文混合理解 (multi-modal RAG)

## 六、依賴套件

| 套件 | 版本 | 用途 |
|------|------|------|
| pytesseract | 0.3.13 | Tesseract OCR Python 介面 |
| pdfplumber | 0.11.7 | PDF 文字提取 + 表格 |
| PyMuPDF (fitz) | 1.26.7 | PDF 頁面渲染 (OCR 備援) |
| Pillow | 12.1.1 | 影像處理 |
| opencv-python | 4.12.0 | 影像前處理 |
| pyzbar | — | QR Code 掃描 |
| python-docx | — | DOCX 解析 |
| pgvector | — | PostgreSQL 向量搜尋 |
