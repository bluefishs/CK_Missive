# 工程 × 派工單 × 作業歷程 整合設計

> **建立日期**: 2026-02-12
> **目標**: 將截圖中的「工程公文歷程追蹤表」數位化，整合現有 Taoyuan 模組
> **原則**: 前端 UI/UX 先行 → 資料庫擴充 → API 服務對接

---

## 一、現有架構分析

### 已存在的模型（backend/app/extended/models/taoyuan.py）
| 模型 | 用途 | 狀態 |
|------|------|------|
| TaoyuanProject | 轄管工程清單（項次 51/52/76）| ✅ 已完成 |
| TaoyuanDispatchOrder | 派工紀錄（派工單號、作業類別）| ✅ 已完成 |
| TaoyuanDispatchProjectLink | 派工-工程 多對多關聯 | ✅ 已完成 |
| TaoyuanDispatchDocumentLink | 派工-公文 關聯（歷程追蹤）| ✅ 已完成 |
| TaoyuanDocumentProjectLink | 公文-工程 直接關聯 | ✅ 已完成 |
| TaoyuanContractPayment | 契金管控（7種作業類別金額）| ✅ 已完成 |
| OfficialDocument | 公文（收文/發文）| ✅ 已完成 |

### 缺少的部分（截圖中的「作業事項」欄位）
截圖顯示每筆機關來文對應的作業里程碑：
- 派工單(辦理查估作業起25日曆天內)
- 會勘紀錄
- 前送修正成果
- 價審會議
- 協議價購會議
- 成果(定稿版)同意核定

**這些是「作業歷程」，需要新增 `TaoyuanWorkRecord` 模型。**

---

## 二、資料關係圖

```
ContractProject (承攬案件: 115年度桃園查估派工)
 │
 ├── TaoyuanProject (工程: 項次51/52/76)
 │    │
 │    ├── TaoyuanDispatchOrder (派工單)
 │    │    ├── TaoyuanDispatchDocumentLink → OfficialDocument (機關來文)
 │    │    ├── TaoyuanDispatchDocumentLink → OfficialDocument (公司發文)
 │    │    ├── TaoyuanContractPayment (契金)
 │    │    └── 【新增】TaoyuanWorkRecord (作業歷程)
 │    │         ├── milestone_type: 派工/會勘/送件/修正/審查/協議/定稿
 │    │         ├── related_incoming_doc_id → 觸發的機關來文
 │    │         ├── related_outgoing_doc_id → 對應的公司發文
 │    │         └── submission_type: 檢送成果(紙本+電子檔) 等
 │    │
 │    └── TaoyuanDocumentProjectLink → OfficialDocument (直接關聯)
 │
 └── batch_close_no (結案批次: 第1~5批)
```

---

## 三、前端 UI/UX 設計

### 3.1 頁面入口
在現有「桃園派工管理」頁面新增「工程歷程」Tab 標籤

### 3.2 工程歷程總覽頁面 (ProjectWorkflowPage)
```
┌─────────────────────────────────────────────────────────┐
│ 🔍 篩選列                                               │
│ [承攬案件▼] [行政區▼] [結案批次▼] [狀態▼] [搜尋工程名稱]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ┌─ 項次51 ──────────────────────────────────────────┐   │
│ │ 桃園市「新屋區中華南路一段(福九路至高鐵南路七段)     │   │
│ │ 道路拓寬工程」地上物查估作業                        │   │
│ │ 📋 批次: 第1批結案  👤 承辦: 李昭德               │   │
│ │                                                    │   │
│ │ Timeline (時間軸)                                   │   │
│ │ ──●──────●──────●──────●──────●──────●──           │   │
│ │   派工   會勘   送件   修正   審查   結案           │   │
│ │   113.11  114.4  114.6  114.7  114.11  114.12      │   │
│ │                                                    │   │
│ │ 📨 機關來文: 15筆  📤 公司發文: 4筆                 │   │
│ │ [展開詳細歷程 ▼]                                    │   │
│ └────────────────────────────────────────────────────┘   │
│                                                         │
│ ┌─ 項次52 ──────────────────────────────────────────┐   │
│ │ ...                                                │   │
│ └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 3.3 工程歷程詳細視圖 (展開後)
使用 Ant Design 的 `Collapse` + `Timeline` + `Table` 組合

```
┌─ 項次51 展開詳細 ────────────────────────────────────────┐
│                                                          │
│ Tab1: 歷程時間軸 | Tab2: 公文明細 | Tab3: 契金管控        │
│                                                          │
│ ═══ Tab1: 歷程時間軸 ═══                                 │
│                                                          │
│ 🟢 113.11.8 派工                                         │
│    ├─ 機關來文: 113.9.9桃工用字第1130038092號             │
│    ├─ 事項: 派工單(辦理查估作業起25日曆天內)               │
│    ├─ 公司發文: 113.11.8乾坤測字第1130000130號            │
│    └─ 發文類別: 檢送成果(紙本+電子檔)                     │
│                                                          │
│ 🔵 114.4.18 會勘                                         │
│    ├─ 機關來文: 114.4.8桃工用字第1140011709號              │
│    ├─ 事項: 羅錦清陳情書(114.4.18查估檢視)                │
│    └─ （無對應發文）                                      │
│                                                          │
│ 🟡 114.12.10 結案                                        │
│    ├─ 機關來文: 114.12.10桃工用字第1140049920號           │
│    ├─ 事項: 土地鑑界會勘紀錄                              │
│    └─ （無對應發文）                                      │
│                                                          │
│ ═══ Tab2: 公文明細 ═══                                   │
│ ┌──────────┬──────────────────────┬─────────────────┐    │
│ │ 收發     │ 文號                  │ 事項            │    │
│ ├──────────┼──────────────────────┼─────────────────┤    │
│ │ 📨機關   │ 113.9.9桃工...092號   │ 派工單          │    │
│ │ 📤公司   │ 113.11.8乾坤...130號  │ 檢送成果        │    │
│ │ 📨機關   │ 113.10.16桃工...216號 │ 通知辦理查估     │    │
│ │ ...      │                      │                 │    │
│ └──────────┴──────────────────────┴─────────────────┘    │
│                                                          │
│ ═══ Tab3: 契金管控 ═══                                   │
│ （現有 TaoyuanContractPayment 資料）                      │
└──────────────────────────────────────────────────────────┘
```

### 3.4 Ant Design 元件對應

| UI 區塊 | Ant Design 元件 | 說明 |
|---------|----------------|------|
| 篩選列 | `Select`, `Input.Search` | 多條件篩選 |
| 工程卡片 | `Collapse.Panel` | 可展開/收合 |
| 進度時間軸 | `Timeline` | 里程碑視覺化 |
| 批次標籤 | `Tag` (color) | 第1~5批顏色區分 |
| 詳細Tab | `Tabs` | 歷程/公文/契金 |
| 公文明細 | `Table` | 排序+篩選 |
| 新增歷程 | `Modal` + `Form` | 彈窗表單 |
| 匯出 | `Button` | XLSX 匯出 |

---

## 四、資料庫擴充設計

### 4.1 新增模型: TaoyuanWorkRecord（作業歷程紀錄）

```python
class TaoyuanWorkRecord(Base):
    """作業歷程紀錄 - 追蹤工程的每個工作里程碑"""
    __tablename__ = "taoyuan_work_records"

    id = Column(Integer, primary_key=True, index=True)
    
    # 關聯
    dispatch_order_id = Column(Integer, 
        ForeignKey('taoyuan_dispatch_orders.id', ondelete='CASCADE'),
        nullable=False, index=True, comment="關聯派工單")
    taoyuan_project_id = Column(Integer,
        ForeignKey('taoyuan_projects.id', ondelete='CASCADE'),
        nullable=True, index=True, comment="關聯工程項次")
    incoming_doc_id = Column(Integer,
        ForeignKey('documents.id', ondelete='SET NULL'),
        nullable=True, index=True, comment="觸發的機關來文")
    outgoing_doc_id = Column(Integer,
        ForeignKey('documents.id', ondelete='SET NULL'),
        nullable=True, index=True, comment="對應的公司發文")
    
    # 作業資訊
    milestone_type = Column(String(50), nullable=False, index=True,
        comment="里程碑類型")
    description = Column(String(500), comment="事項描述")
    submission_type = Column(String(200), 
        comment="發文類別: 檢送成果(紙本+電子檔)/檢修正後成果 等")
    
    # 時間
    record_date = Column(Date, nullable=False, index=True, comment="紀錄日期")
    deadline_date = Column(Date, comment="期限日期")
    completed_date = Column(Date, comment="完成日期")
    
    # 狀態
    status = Column(String(30), default='pending', index=True,
        comment="pending/in_progress/completed/overdue")
    batch_no = Column(Integer, comment="結案批次(1~5)")
    
    notes = Column(Text, comment="備註")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    # 關聯關係
    dispatch_order = relationship("TaoyuanDispatchOrder", 
        backref="work_records")
    project = relationship("TaoyuanProject", 
        backref="work_records")
    incoming_doc = relationship("OfficialDocument", 
        foreign_keys=[incoming_doc_id])
    outgoing_doc = relationship("OfficialDocument", 
        foreign_keys=[outgoing_doc_id])
```

### 4.2 里程碑類型列舉

```python
MILESTONE_TYPES = [
    {"value": "dispatch", "label": "派工", "color": "green", "order": 1},
    {"value": "survey", "label": "會勘", "color": "blue", "order": 2},
    {"value": "site_inspection", "label": "查估檢視", "color": "cyan", "order": 3},
    {"value": "submit_result", "label": "送件/檢送成果", "color": "gold", "order": 4},
    {"value": "revision", "label": "修正成果", "color": "orange", "order": 5},
    {"value": "review_meeting", "label": "審查/價審會議", "color": "purple", "order": 6},
    {"value": "negotiation", "label": "協議價購", "color": "magenta", "order": 7},
    {"value": "final_approval", "label": "定稿核定", "color": "lime", "order": 8},
    {"value": "boundary_survey", "label": "土地鑑界", "color": "geekblue", "order": 9},
    {"value": "closed", "label": "結案", "color": "red", "order": 99},
    {"value": "other", "label": "其他", "color": "default", "order": 50},
]
```

### 4.3 發文類別列舉

```python
SUBMISSION_TYPES = [
    "檢送成果(紙本+電子檔)",
    "檢送修正後成果(紙本+電子檔)",
    "檢修正後成果(協議市價-電子檔)",
    "檢送成果(電子檔)",
    "檢修正後成果",
    "檢送成果定稿版(繳送)",
]
```

### 4.4 TaoyuanProject 擴充欄位

```sql
-- 在 taoyuan_projects 新增結案批次欄位
ALTER TABLE taoyuan_projects ADD COLUMN batch_close_no INTEGER COMMENT '結案批次(1~5)';
ALTER TABLE taoyuan_projects ADD COLUMN batch_close_date DATE COMMENT '結案日期';
ALTER TABLE taoyuan_projects ADD COLUMN company_submit_date VARCHAR(100) COMMENT '公司發文送件日期描述';
ALTER TABLE taoyuan_projects ADD COLUMN company_submit_doc_type VARCHAR(200) COMMENT '送件文件類型';
```

---

## 五、API 設計

### 5.1 新增端點

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/taoyuan/projects/{id}/workflow` | 取得工程完整歷程 |
| GET | `/api/taoyuan/workflow/records` | 查詢作業歷程（支援篩選）|
| POST | `/api/taoyuan/workflow/records` | 新增作業歷程紀錄 |
| PUT | `/api/taoyuan/workflow/records/{id}` | 更新作業歷程 |
| DELETE | `/api/taoyuan/workflow/records/{id}` | 刪除作業歷程 |
| GET | `/api/taoyuan/projects/workflow-summary` | 工程歷程總覽（含統計）|
| POST | `/api/taoyuan/workflow/import` | 從 Excel 匯入歷程資料 |
| GET | `/api/taoyuan/workflow/export` | 匯出歷程報表 XLSX |

### 5.2 回應格式範例

```json
// GET /api/taoyuan/projects/51/workflow
{
  "project": {
    "id": 1,
    "sequence_no": 51,
    "project_name": "桃園市「新屋區中華南路一段...」道路拓寬工程",
    "sub_case_name": "地上物查估作業",
    "batch_close_no": 1,
    "status": "已結案"
  },
  "dispatches": [
    {
      "id": 10,
      "dispatch_no": "TY-114-001",
      "work_type": "01.地上物查估作業",
      "work_records": [
        {
          "id": 1,
          "milestone_type": "dispatch",
          "milestone_label": "派工",
          "record_date": "2024-11-08",
          "incoming_doc": {
            "doc_number": "桃工用字第1130038092號",
            "doc_date": "2024-09-09"
          },
          "outgoing_doc": {
            "doc_number": "乾坤測字第1130000130號",
            "doc_date": "2024-11-08"
          },
          "description": "派工單(辦理查估作業起25日曆天內)",
          "submission_type": "檢送成果(紙本+電子檔)",
          "status": "completed"
        }
      ]
    }
  ],
  "summary": {
    "total_incoming_docs": 15,
    "total_outgoing_docs": 4,
    "milestones_completed": 6,
    "current_stage": "closed"
  }
}
```

---

## 六、實施階段

### Phase 1: 資料庫擴充（Claude CLI 執行）
1. 新增 TaoyuanWorkRecord 模型
2. 擴充 TaoyuanProject 欄位
3. 建立 Alembic migration
4. 新增里程碑/發文類別常數

### Phase 2: 後端 API（Claude CLI 執行）
1. 新增 WorkRecord Schema
2. 新增 WorkRecord Repository
3. 新增 WorkRecord Service
4. 新增 API Endpoints
5. Excel 匯入/匯出服務

### Phase 3: 前端頁面（Claude CLI 執行）
1. 新增前端常數 (milestoneTypes, submissionTypes)
2. 新增 workflowApi.ts
3. 建立 ProjectWorkflowPage 頁面
4. 建立 WorkflowTimeline 元件
5. 建立 WorkRecordModal 表單
6. 路由與導航整合

### Phase 4: 資料匯入與驗證
1. 從截圖中的 Excel 匯入既有歷程資料
2. 驗證資料完整性
3. 結案批次標記
