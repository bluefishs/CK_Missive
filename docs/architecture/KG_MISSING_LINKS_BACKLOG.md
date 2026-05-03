# KG ↔ Wiki 未連結 entity 處置建議 v1.0

> **建立**：2026-05-03（v6.7 Phase E2）
> **目的**：列剩餘無 kg_entity_id 的 wiki entity，按證據強度提建議處置（owner 決策用）
> **承接**：
> - I4 wiki↔KG 6 entities backfill（v6.6, commit `4919c55a`）：215/219 = 98.2%
> - v6.7 E2 加 1 alias（勞動部動力 typo）：216/219 = 98.6%
> **跨 repo FQID**：`CK_Missive#KG_MISSING_LINKS_BACKLOG_v1.0`

---

## 0. 一頁式現況

| 來源 wiki entity | 狀態 | 建議 | 依據 |
|---|---|---|---|
| 勞動部動力發展署中彰投分署 | ✅ **已處理（v6.7 E2）** | typo fix → KG alias 38041 | KG 已存在「勞動部勞動力發展署中彰投分署」（id=38041, type=org），純 typo |
| 社團法人中華民國全國中小企業總會 | ⏸ pending owner | **archive 候選** | KG 僅有「全國創新創業總會」（id=106414，不同組織），1 doc 提及 |
| 臺中市112年度都市計畫樁測釘、埋設及數值地形測量工程委託技術服務案 | ⏸ pending owner | **ingest 候選** | KG 有 110/111/113 年度（id 14860/14773/14806），112 年度遺漏 |
| 臺北市一口氣英語教育基金會 | ⏸ pending owner | **archive 候選** | KG 完全無對應，1 doc 提及（疑似邊緣 entity） |

**進度**：215/219 → 216/219 = **98.6%**（剩 3 個待 owner 決策）

---

## 1. 已處理：勞動部動力發展署中彰投分署（v6.7 E2 執行）

**處置**：typo fix — KG 加 alias

```sql
-- 已執行於 2026-05-03
INSERT INTO entity_aliases (alias_name, canonical_entity_id, source, confidence)
VALUES ('勞動部動力發展署中彰投分署', 38041, 'manual_typo_fix_v6.7_E2', 0.95);
-- alias.id = 931
```

**Wiki frontmatter 同步**：
```diff
title: 勞動部動力發展署中彰投分署
+ kg_entity_id: 38041
```

**為何 typo**：「動力發展署」為「**勞**動力發展署」漏字。原 wiki 由 wiki_compiler 從 documents.sender/receiver 自動產出，源 doc 也帶 typo。alias 同時補 KG search 容錯能力。

---

## 2. 待 owner 決策：3 個 entity 處置建議

### 2.1 社團法人中華民國全國中小企業總會 — 建議 **archive**

**證據**：
- KG `canonical_entities` 完全無此名稱
- 模糊匹配 KG 中只有「**全國創新創業總會**」（id=106414, org）— 不同組織
- documents 表只 1 筆提及

**理由**：
- 證據不足（單筆提及不到 ingest 標準 — 通常需 ≥3 筆）
- 不該強行對應到「創新創業總會」（語意失真）
- 可能源公文是過路抄送，並非長期業務對象

**處置動作**（待 owner confirm）：
```bash
# 將 wiki 頁移到 archived 子目錄
mv wiki/entities/社團法人中華民國全國中小企業總會.md \
   wiki/entities/_archived/
# 或標記 frontmatter
echo 'archived: true' >> wiki/entities/...
```

### 2.2 臺中市 112 年度都市計畫樁測釘、埋設及數值地形測量工程委託技術服務案 — 建議 **ingest**

**證據**：
- KG 有同系列 110/111/113 年度（id 14860/14773/14806，全為 type=project）
- 112 年度為「序列缺口」— 業務連續性看，應該存在
- documents 表 1 筆提及，標題有「112 年度」字樣

**理由**：
- 系列其他 3 年都在 KG，112 年度遺漏可能是 project 建檔漏洞
- 可呼叫現有 `dispatch_kg_ingest.py` 補建檔（純新增）
- 風險低（增 1 個 project entity，不破壞既有）

**處置動作**（待 owner confirm）：
```python
# 跑 dispatch_kg_ingest 範圍指定 112 年度
python scripts/sync/dispatch_kg_ingest.py \
    --filter-year 112 --project-name '臺中市112年度都市計畫樁測釘...'
```

### 2.3 臺北市一口氣英語教育基金會 — 建議 **archive**

**證據**：
- KG 完全無對應
- documents 表只 1 筆提及（疑似行政公告抄送，非業務對象）
- wiki 頁建立時間早（2026-04-13），但 19 docs 的補編未涵蓋此 entity

**理由**：
- 與本公司業務（測繪 / 公文）無直接關係
- 單筆提及門檻不足
- 留著 wiki 頁會擾亂 RAG 檢索（誤命中率高，相關度低）

**處置動作**（待 owner confirm）：同 2.1

---

## 3. 統計與觀察（v6.7 E2 執行後）

| 指標 | v6.6 結束 | v6.7 E2 後 | v6.7 E2 + owner 決策後 |
|---|---|---|---|
| Wiki↔KG 連結率 | 98.2%（215/219）| **98.6%（216/219）** | 預估 99.1%（archive 2 + ingest 1 → 217/218）|
| 真未連結 | 4 | 3 | 0 |
| typo aliases | 0 | 1 | 1 |

---

## 4. 為何寫這份文件而非直接執行

**用戶硬性約束**：「不要過度工程 / 不要拖延 / 重要決策先 confirm 再動」。

- alias 是純新增，零破壞性 → 直接執行
- archive / ingest 是「移檔 / 新增 KG row」 → 影響 RAG 結果與 owner 認知，必須先 confirm

**Owner 1 次決策範本**（推薦在下次 Hermes 對話用）：
> 看 `KG_MISSING_LINKS_BACKLOG.md`，3 個建議：
> - 中華民國全國中小企業總會：archive ✓
> - 臺中市 112 年度：ingest ✓
> - 一口氣英語：archive ✓
> 全部執行。

回 yes 後我會跑相應 sync 腳本 + commit。

---

## 5. 預防再發生

**根因**：wiki_compiler 從 documents 自動產 entity 頁，但門檻過低（1 doc 即建頁）→ 累積邊緣 entity。

**預防方案（v6.8 候選）**：
- wiki_compiler 加 `--min-doc-count` 門檻（預設 ≥ 3）
- 已 compile 但 doc_count 降到 < 3 的 entity 移到 `_archived/`
- 月度 fitness 加 step 15「wiki entity 邊緣偵測」（doc_count < 3 + KG 連結 < 30 天）

不在本 v6.7 範圍，列為 v6.8 候選。

---

## 6. 與其他文件的關係

- `KG_WIKI_INTEGRATION_REVIEW.md`：本文補 §4.1 I4 後續細項
- `SYSTEM_INTEGRATION_REVIEW_v2.md`：軸 B 連結率追蹤的具體案例
- `LESSONS_REGISTRY.md`：可加 L26「entity ingest 門檻 < 3 doc 的反模式」

---

> **Wiki↔KG 連結率不是越高越好，是「相關度與真實度的反映」。**
> **archive 邊緣 entity 比硬塞連結更誠實。**
