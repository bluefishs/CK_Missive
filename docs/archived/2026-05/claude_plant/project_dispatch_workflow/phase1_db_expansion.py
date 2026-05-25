"""
Phase 1: 資料庫擴充 - 新增 TaoyuanWorkRecord 模型
執行方式: Claude CLI 在 CK_Missive 根目錄執行
日期: 2026-02-12
"""
import os
import sys

# === 步驟 1: 新增 TaoyuanWorkRecord 模型到 taoyuan.py ===

WORK_RECORD_MODEL = '''

class TaoyuanWorkRecord(Base):
    """作業歷程紀錄 - 追蹤工程的每個工作里程碑
    
    對應截圖中的「作業事項」欄位：
    派工 → 會勘 → 送件 → 修正 → 審查 → 協議 → 定稿 → 結案
    """
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
        comment="里程碑類型: dispatch/survey/submit_result/revision/review_meeting/negotiation/final_approval/boundary_survey/closed/other")
    description = Column(String(500), comment="事項描述")
    submission_type = Column(String(200), 
        comment="發文類別: 檢送成果(紙本+電子檔)/檢修正後成果 等")
    
    # 時間
    record_date = Column(Date, nullable=False, index=True, comment="紀錄日期(民國轉西元)")
    deadline_date = Column(Date, nullable=True, comment="期限日期")
    completed_date = Column(Date, nullable=True, comment="完成日期")
    
    # 狀態
    status = Column(String(30), default='pending', index=True,
        comment="pending/in_progress/completed/overdue")
    sort_order = Column(Integer, default=0, comment="排序順序")
    
    notes = Column(Text, comment="備註")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    # 關聯關係
    dispatch_order = relationship("TaoyuanDispatchOrder", backref="work_records")
    project = relationship("TaoyuanProject", backref="work_records")
    incoming_doc = relationship("OfficialDocument", foreign_keys=[incoming_doc_id])
    outgoing_doc = relationship("OfficialDocument", foreign_keys=[outgoing_doc_id])
'''

# === 步驟 2: TaoyuanProject 擴充欄位 ===

PROJECT_NEW_COLUMNS = '''
    # 結案批次管理（截圖底部色彩標記）
    batch_close_no = Column(Integer, comment="結案批次(1~5)")
    batch_close_date = Column(Date, comment="結案日期")
    company_submit_info = Column(String(500), comment="公司發文送件資訊")
'''

# === 步驟 3: 新增常數檔案 ===

MILESTONE_CONSTANTS = '''{
    "MILESTONE_TYPES": [
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
        {"value": "other", "label": "其他", "color": "default", "order": 50}
    ],
    "SUBMISSION_TYPES": [
        "檢送成果(紙本+電子檔)",
        "檢送修正後成果(紙本+電子檔)",
        "檢修正後成果(協議市價-電子檔)",
        "檢送成果(電子檔)",
        "檢修正後成果",
        "檢送成果定稿版(繳送)",
        "檢修正後成果(協議市價)",
        "檢修正正後成果(紙本+電子檔)(第2次)"
    ],
    "BATCH_CLOSE_COLORS": {
        "1": "#52c41a",
        "2": "#1890ff",
        "3": "#faad14",
        "4": "#eb2f96",
        "5": "#722ed1"
    }
}
'''

# === 步驟 4: Alembic migration ===

MIGRATION_SQL = '''-- Migration: 新增作業歷程紀錄表 & 工程擴充欄位
-- Date: 2026-02-12

-- 1. 新增 taoyuan_work_records 表
CREATE TABLE IF NOT EXISTS taoyuan_work_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dispatch_order_id INTEGER NOT NULL,
    taoyuan_project_id INTEGER,
    incoming_doc_id INTEGER,
    outgoing_doc_id INTEGER,
    milestone_type VARCHAR(50) NOT NULL,
    description VARCHAR(500),
    submission_type VARCHAR(200),
    record_date DATE NOT NULL,
    deadline_date DATE,
    completed_date DATE,
    status VARCHAR(30) DEFAULT 'pending',
    sort_order INTEGER DEFAULT 0,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dispatch_order_id) REFERENCES taoyuan_dispatch_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (taoyuan_project_id) REFERENCES taoyuan_projects(id) ON DELETE CASCADE,
    FOREIGN KEY (incoming_doc_id) REFERENCES documents(id) ON DELETE SET NULL,
    FOREIGN KEY (outgoing_doc_id) REFERENCES documents(id) ON DELETE SET NULL
);

-- 2. 建立索引
CREATE INDEX IF NOT EXISTS ix_work_records_dispatch ON taoyuan_work_records(dispatch_order_id);
CREATE INDEX IF NOT EXISTS ix_work_records_project ON taoyuan_work_records(taoyuan_project_id);
CREATE INDEX IF NOT EXISTS ix_work_records_milestone ON taoyuan_work_records(milestone_type);
CREATE INDEX IF NOT EXISTS ix_work_records_date ON taoyuan_work_records(record_date);
CREATE INDEX IF NOT EXISTS ix_work_records_status ON taoyuan_work_records(status);

-- 3. 擴充 taoyuan_projects 表
-- SQLite 不支援 IF NOT EXISTS for ALTER TABLE，需檢查後執行
ALTER TABLE taoyuan_projects ADD COLUMN batch_close_no INTEGER;
ALTER TABLE taoyuan_projects ADD COLUMN batch_close_date DATE;
ALTER TABLE taoyuan_projects ADD COLUMN company_submit_info VARCHAR(500);
'''


def main():
    """執行說明 - 請依序處理"""
    print("=" * 60)
    print("Phase 1: 資料庫擴充執行指南")
    print("=" * 60)
    print()
    print("步驟 1: 將 TaoyuanWorkRecord 模型加入")
    print("  檔案: backend/app/extended/models/taoyuan.py")
    print("  位置: 在 TaoyuanDispatchAttachment 類別之後")
    print()
    print("步驟 2: 將 batch_close_no 等欄位加入 TaoyuanProject")
    print("  檔案: backend/app/extended/models/taoyuan.py")
    print("  位置: 在 acceptance_status 欄位之後")
    print()
    print("步驟 3: 執行 Migration SQL")
    print("  檔案: migration.sql (已生成)")
    print()
    print("步驟 4: 更新 __init__.py 確保模型被匯入")
    print()
    print("步驟 5: 重啟後端服務驗證")


if __name__ == "__main__":
    main()
