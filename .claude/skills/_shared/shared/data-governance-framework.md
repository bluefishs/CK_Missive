# Data Governance Framework Skill

**技能名稱**：資料治理框架
**用途**：建立一套確保資料品質、完整性、一致性與可追溯性的頂層設計原則與實施策略。
**適用場景**：新資料源接入、資料清理與驗證、建立資料分析的信任基礎。

---

## 1. 核心原則

1.  **資料即資產 (Data as an Asset)**：資料與程式碼同等重要，必須以嚴謹的工程方法進行管理。
2.  **單一真實來源 (Single Source of Truth, SSOT)**：任何一筆資料都應有其明確、可信的來源。避免在系統中存在多個衝突的資料版本。
3.  **品質始於源頭 (Quality at the Source)**：資料品質的控管應在資料進入系統的第一時間點就開始，而不是在事後清理。
4.  **可追溯性 (Traceability)**：任何資料都應能追溯其來源、經歷的轉換過程，直至最終的呈現。這就是資料血緣 (Data Lineage)。
5.  **文件化與共識 (Documentation & Consensus)**：資料的定義、格式與業務邏輯必須被清楚地文件化，並成為團隊共識。

---

## 2. 資料字典 (Data Dictionary)

資料字典是實現資料治理的基石，它為所有團隊成員提供了一份關於資料庫結構的、人類可讀的「活文件」。

### 2.1 實施策略

*   **目標**：建立一個名為 `docs/DATA_DICTIONARY.md` 的 Markdown 文件，此文件由程式自動產生，並在每次 CI/CD 流程中自動更新。
*   **技術實現**：
    1.  建立一個 Python 腳本 `scripts/generate_data_dictionary.py`。
    2.  此腳本會載入所有 SQLAlchemy 的 models (`Base.metadata`)。
    3.  遍歷 `metadata.tables`，讀取每個資料表、欄位的名稱、資料類型、約束（如主鍵、外鍵、是否可為空），以及最重要的——`comment` 屬性。
    4.  將這些資訊格式化為 Markdown 表格並寫入 `docs/DATA_DICTIONARY.md`。

### 2.2 開發者 SOP

*   **強制要求**：當開發者在 SQLAlchemy model 中新增或修改一個欄位時，**必須**為該欄位提供一個清晰、業務導向的 `comment` 描述。

**範例 (`backend/app/models/land_parcel.py`)**:
```python
class LandParcel(Base):
    __tablename__ = 'land_parcels'
    __table_args__ = {'comment': '宗地基本資料表'}

    id = Column(Integer, primary_key=True, comment='內部唯一識別 ID')
    basereg = Column(String, index=True, comment='地政事務所登記之宗地編號')
    land_value = Column(Integer, comment='公告土地現值 (元/平方公尺)')
    # ... 其他欄位 ...
```
*   **CI/CD 整合**：將 `python scripts/generate_data_dictionary.py` 加入 `.github/workflows/ci.yml` 中，確保文件永遠保持最新。

---

## 3. 資料品質儀表板 (Data Quality Dashboard)

建立一個視覺化的儀表板來監控全系統的資料品質狀況。

### 3.1 儀表板位置

*   建議在前端應用中建立一個新的管理頁面 `/admin/data-quality`。

### 3.2 應監控的關鍵指標 (KPIs)

*   **地址標準化成功率**：`real_estate_transactions` 表中，`standardized_address` 欄位非空的紀錄百分比。
*   **座標完整率**：`land_parcels` 或 `real_estate_transactions` 表中，`latitude` / `longitude` 或 `geometry` 欄位為空的紀錄數量。
*   **資料匯入錯誤統計**：從 `data_import_logs` (假設有此表) 中，統計不同類型匯入任務的失敗次數與常見錯誤原因。
*   **Pydantic 驗證失敗紀錄**：在資料寫入前，攔截 Pydantic model 的 `ValidationError`，並將其彙總統計。
*   **孤兒數據檢測**：外鍵關聯為空（本應存在）的紀錄數量，例如，一個 `transaction` 紀錄卻沒有對應的 `land_parcel`。

### 3.3 SOP

*   應指派資料管理員或開發者**每週**檢查此儀表板。
*   儀表板上的指標應可點擊，直接連結到需要修正的資料列表，以實現快速修復。

---

## 4. 資料血緣 (Data Lineage)

資料血緣用於追蹤資料的生命週期。

### 4.1 實施策略 (分階段)

#### 階段一：來源追蹤 (Source Tracking)

*   **目標**：記錄資料的原始來源。
*   **實作**：
    *   在需要追蹤來源的資料表（如 `real_estate_transactions`）中，新增以下欄位：
        *   `source_type` (String, e.g., 'file_upload', 'api_ingestion', 'manual_entry')
        *   `source_identifier` (String, e.g., 'lvr_a_113_q2.csv', 'tgos_api_v1')
        *   `imported_at` (DateTime, 預設為當前時間)
        *   `imported_by_user_id` (Integer, Foreign Key to `users.id`)

#### 階段二：轉換追蹤 (Transformation Tracking) - (未來目標)

*   **目標**：記錄資料在系統內部被處理與轉換的過程。
*   **概念實作**：
    *   建立一個 `data_lineage` 資料表。
    *   當一個任務（例如，一個 Celery worker）根據一筆來源資料 A 生成了一筆新資料 B 時，在此表中記錄一筆：
        `(output_table, output_record_id, source_table, source_record_id, transformation_name, timestamp)`
    *   **範例**：`(land_parcels, 101, raw_lvr_data, 556, 'standardize_address_and_create_parcel', '2025-12-26 15:00:00')`
    *   這將允許我們回答「這筆宗地資料是從哪個 LVR 原始檔案來的？」這類複雜問題。

---
**建立日期**：2025-12-26
**最後更新**：2025-12-26
