# 附件元件收斂：盤點與替換規劃

> 建立：2026-08-19
> 觸發：owner「每筆報價單呈現可參照公文模式提供上傳與預覽機制，統一整體系統
> 　　　呈現與程式維護，降低異質同工機制」「共用附件區元件，以及類似高度
> 　　　重複如公文模組樣板等」「先 1 再逐步推展，但陸續朝模組與模板架構執行，
> 　　　可先盤點與替換規劃」

---

## 1. 盤點（實測，不是印象）

| 檔案 | 行數 | 上傳 | 列表 | 預覽 | 刪除 | 端點 |
|---|---:|:--:|:--:|:--:|:--:|---|
| `pmCase/QuotationRecordsTab` | 227 | ✓ | ✓ | ✓ | ✓ | `PM.ATTACHMENTS_*` |
| `document/tabs/DocumentAttachmentsTab` | 291 | ✓ | ✓ | ✓ | ✓ | 公文附件 |
| `contractCase/tabs/AttachmentsTab` | 250 | | ✓ | | | 承攬案件 |
| `document/operations/FileUploadSection` | 171 | ✓ | | ✓ | | 公文建立流程 |
| `document/operations/ExistingAttachmentsList` | 138 | | ✓ | ✓ | ✓ | 公文編輯 |
| `certification/AttachmentPreview` | 137 | ✓ | | ✓ | ✓ | 憑證 |
| `CertificationFormPage` | 260 | | | ✓ | | 憑證表單 |
| `ERPExpenseCreatePage` | 516 | ✓ | | | | 核銷（收據影像） |
| `ReceiveDocumentCreatePage` | 168 | ✓ | | | | 收文建立 |
| **合計** | **2,158** | | | | | |

### 三類，不是一類

盤點揭露一件事：**這 9 處不是同一件事的 9 個副本**。

| 類別 | 特徵 | 成員 | 可否共用 |
|---|---|---|---|
| **A. 案件附件區** | 以 `case_code` 關聯、四項功能齊全、獨立分頁 | QuotationRecordsTab、（報價單詳情） | ✅ 已收斂 |
| **B. 表單內的上傳欄** | 嵌在建立/編輯表單裡、**檔案還沒送出**、與表單狀態綁在一起 | FileUploadSection、ERPExpenseCreatePage、ReceiveDocumentCreatePage、CertificationFormPage | ⚠️ 形狀不同 |
| **C. 已存在附件的管理** | 綁定各自的資料模型（`DocumentAttachment` vs `CaseAttachment`） | DocumentAttachmentsTab、ExistingAttachmentsList、AttachmentsTab、AttachmentPreview | 🔶 需先統一型別 |

**B 類不該硬收斂**：表單內的上傳是「檔案暫存在前端、隨表單一起送出」，
與 A 類「上傳即落地」是不同的生命週期。強行共用會做出一個要靠旗標
切換兩種行為的元件——那比兩份程式碼更難維護。

---

## 2. 已完成（2026-08-19）

### 抽取而非新寫

`QuotationRecordsTab` 是**唯一四項功能都齊全**的一份，所以把它參數化搬到
`components/common/AttachmentPanel.tsx`，原分頁改為薄包裝（行為不變、零風險）。

**新寫一個共用元件等於製造第 10 份** —— 這是盤點之後才看得出來的事。

| 項目 | 狀態 |
|---|---|
| `types/attachment.ts`（`CaseAttachment` SSOT + doc_type 標籤/顏色） | ✅ |
| `components/common/AttachmentPanel.tsx`（參數化：title/uploadTitle/accept/showDocType） | ✅ |
| `pmCase/QuotationRecordsTab` 改薄包裝（227 → 34 行） | ✅ |
| 報價單詳情頁新增「附件」分頁 | ✅ |

⚠️ **queryKey 刻意保持 `['pm-case-attachments', caseCode]` 不變** ——
換 key 會讓既有頁面的快取失效鏈斷掉（本專案有 queryKey drift 導致
invalidate 靜靜失效的紀錄，L39）。

---

## 3. 替換規劃（逐步推展）

### 階段二：承攬案件（2026-08-19 執行，⚠️ **原規劃是錯的**）

**原本寫的**：「`AttachmentsTab` 只有列表一項功能（250 行卻只做一件事），
替換後功能反而變多」。

**實際看過之後：那個判斷錯了，照著做會弄壞既有功能。**

承攬案件的「附件紀錄」顯示的是**來自關聯公文的附件**：

- 資料由父層傳入（`attachments` / `groupedAttachments` / `onDownloadAll`）
- 依公文**分組展開**（groupedColumns + expandedColumns）
- 可**整包下載**某一筆公文的所有附件
- **不是**以 `case_code` 查 `pm_case_attachments`

它與 `AttachmentPanel` 是**兩種業務語意**，不是同一件事的兩個副本。

#### 實際做法：並列，不是替換

同一個分頁下兩區：

```
關聯公文附件   ← 原有（依公文分組、整包下載）
案件附件       ← 新增（case_code 關聯：系統輸出的報價單、客戶回簽）
```

量測支持這個決定：88 件承攬案件中**只有 2 件**有 PM 附件（共 4 筆）——
但**匯入回簽後就會有**（5 個回簽檔會依 case_code 掛上）。
所以承攬案件確實需要看得到案件附件，只是不能用取代的方式給。

**這是「驗證優先於收斂」的又一個實例**：規劃寫在紙上時看起來合理，
打開檔案才發現兩者根本不是同一件事。

### 階段三：公文附件（高風險，需獨立一輪）

公文的三個檔案（`DocumentAttachmentsTab` 291 + `ExistingAttachmentsList` 138
+ `FileUploadSection` 171 = **600 行**）是**每天在用的核心路徑**。

遷移前必須先處理兩件事：

1. **型別不同**：公文用 `DocumentAttachment`（有 `original_filename`、
   關聯 `document_id`），案件用 `CaseAttachment`（關聯 `case_code`）。
   要嘛讓 `AttachmentPanel` 泛型化，要嘛在公文側做一層映射。
   **泛型化比較危險** —— 一個要同時服務兩種資料模型的元件，
   最後會長成一堆 `if (mode === 'document')`。
2. **端點不同**：公文附件有自己的上傳/下載/刪除端點與權限規則。

**建議做法**：不強求同一個元件，而是**共用底層的表現層**
（`getFileIcon`／`formatFileSize`／`isPreviewable`／預覽 Modal），
各自保留資料層。那是真正重複的部分（約 60 行 × 4 處），
而資料層本來就該不同。

⚠️ **不要為了「看起來統一」而讓兩種資料模型擠進一個元件** ——
本專案已有「強抽＝過度抽象」的紀錄（v6.27 的 sso_bridge、
v6.26 的 HH-2 應收/應付 rollup，兩次都是驗證後決定不抽）。

### 階段四：B 類（表單內上傳）

**建議不做**，除非出現第 5 處。理由見 §1「B 類不該硬收斂」。
若真要做，共用的應該是「檔案選取 + 大小/類型驗證」這一小段，
不是整個上傳區。

---

## 4. 判準（沿用本專案既有的）

1. **先盤點再收斂** —— 這一輪若沒盤點就直接寫共用元件，會做出第 10 份，
   而最完整的那一份（QuotationRecordsTab）會被忽略。
2. **驗證優先於收斂** —— 看起來像重複的，可能是三類不同的東西。
3. **不製造要靠旗標切換行為的元件** —— 那比兩份程式碼更難維護。
4. **共用的是真正重複的部分**（表現層的 60 行），不是整個檔案。
