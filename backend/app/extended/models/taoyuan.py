"""
7. 桃園查估派工管理系統 (Taoyuan Dispatch Module)

- TaoyuanProject: 轄管工程清單
- TaoyuanDispatchOrder: 派工紀錄
- TaoyuanDispatchProjectLink: 派工-工程關聯
- TaoyuanDispatchDocumentLink: 派工-公文關聯
- TaoyuanDocumentProjectLink: 公文-工程關聯
- TaoyuanContractPayment: 契金管控
- TaoyuanDispatchAttachment: 派工單附件
"""
from ._base import *


class TaoyuanProject(Base):
    """轄管工程清單 - 縣府原始工程資料"""
    __tablename__ = "taoyuan_projects"

    id = Column(Integer, primary_key=True, index=True)
    contract_project_id = Column(Integer, ForeignKey('contract_projects.id'), nullable=True, index=True, comment="關聯承攬案件")

    # 縣府原始資料
    sequence_no = Column(Integer, comment="項次")
    review_year = Column(Integer, index=True, comment="審議年度")
    case_type = Column(String(50), comment="案件類型")
    district = Column(String(50), index=True, comment="行政區")
    project_name = Column(String(500), nullable=False, index=True, comment="工程名稱")
    start_point = Column(String(200), comment="工程起點")
    start_coordinate = Column(String(100), comment="起點坐標(經緯度)")
    end_point = Column(String(200), comment="工程迄點")
    end_coordinate = Column(String(100), comment="迄點坐標(經緯度)")
    road_length = Column(Float, comment="道路長度(公尺)")
    current_width = Column(Float, comment="現況路寬")
    planned_width = Column(Float, comment="計畫路寬")
    public_land_count = Column(Integer, comment="公有土地筆數")
    private_land_count = Column(Integer, comment="私有土地筆數")
    rc_count = Column(Integer, comment="RC數量")
    iron_sheet_count = Column(Integer, comment="鐵皮屋數量")
    construction_cost = Column(Float, comment="工程費")
    land_cost = Column(Float, comment="用地費")
    compensation_cost = Column(Float, comment="補償費")
    total_cost = Column(Float, comment="總經費")
    review_result = Column(String(100), comment="審議結果")
    urban_plan = Column(String(200), comment="都市計畫")
    completion_date = Column(Date, comment="完工日期")
    proposer = Column(String(100), comment="提案人")
    remark = Column(Text, comment="備註")

    # 派工關聯欄位
    sub_case_name = Column(String(200), comment="分案名稱")
    case_handler = Column(String(50), comment="案件承辦")
    survey_unit = Column(String(100), comment="查估單位")

    # 總控表進度欄位
    land_agreement_status = Column(String(100), comment="土地協議進度")
    land_expropriation_status = Column(String(100), comment="土地徵收進度")
    building_survey_status = Column(String(100), comment="地上物查估進度")
    actual_entry_date = Column(Date, comment="實際進場日期")
    acceptance_status = Column(String(100), comment="驗收狀態")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    # 關聯關係
    contract_project = relationship("ContractProject", backref="taoyuan_projects")
    dispatch_links = relationship("TaoyuanDispatchProjectLink", back_populates="project", cascade="all, delete-orphan")
    document_links = relationship("TaoyuanDocumentProjectLink", back_populates="project", cascade="all, delete-orphan")


class TaoyuanDispatchOrder(Base):
    """派工紀錄"""
    __tablename__ = "taoyuan_dispatch_orders"

    id = Column(Integer, primary_key=True, index=True)
    contract_project_id = Column(Integer, ForeignKey('contract_projects.id'), nullable=True, index=True, comment="關聯承攬案件")

    dispatch_no = Column(String(50), unique=True, nullable=False, index=True, comment="派工單號")
    agency_doc_id = Column(Integer, ForeignKey('documents.id'), nullable=True, comment="關聯機關公文")
    company_doc_id = Column(Integer, ForeignKey('documents.id'), nullable=True, comment="關聯乾坤公文")

    project_name = Column(String(500), comment="工程名稱/派工事項")
    work_type = Column(String(200), index=True, comment="作業類別(可多選,逗號分隔)")
    sub_case_name = Column(String(200), comment="分案名稱/派工備註")
    deadline = Column(String(200), comment="履約期限")
    case_handler = Column(String(50), comment="案件承辦")
    survey_unit = Column(String(100), comment="查估單位")
    cloud_folder = Column(String(500), comment="雲端資料夾")
    project_folder = Column(String(500), comment="專案資料夾")
    contact_note = Column(String(500), comment="聯絡備註")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    # 關聯關係
    contract_project = relationship("ContractProject", backref="dispatch_orders")
    agency_doc = relationship("OfficialDocument", foreign_keys=[agency_doc_id])
    company_doc = relationship("OfficialDocument", foreign_keys=[company_doc_id])
    project_links = relationship("TaoyuanDispatchProjectLink", back_populates="dispatch_order", cascade="all, delete-orphan")
    document_links = relationship("TaoyuanDispatchDocumentLink", back_populates="dispatch_order", cascade="all, delete-orphan")
    payment = relationship("TaoyuanContractPayment", back_populates="dispatch_order", uselist=False, cascade="all, delete-orphan")
    attachments = relationship("TaoyuanDispatchAttachment", back_populates="dispatch_order", cascade="all, delete-orphan", passive_deletes=True)
    work_type_links = relationship("TaoyuanDispatchWorkType", back_populates="dispatch_order", cascade="all, delete-orphan", passive_deletes=True)


class TaoyuanDispatchProjectLink(Base):
    """派工-工程關聯（多對多）"""
    __tablename__ = "taoyuan_dispatch_project_link"
    __table_args__ = (
        UniqueConstraint('dispatch_order_id', 'taoyuan_project_id', name='uq_dispatch_project'),
    )

    id = Column(Integer, primary_key=True, index=True)
    dispatch_order_id = Column(Integer, ForeignKey('taoyuan_dispatch_orders.id', ondelete='CASCADE'), nullable=False, index=True)
    taoyuan_project_id = Column(Integer, ForeignKey('taoyuan_projects.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    # 關聯關係
    dispatch_order = relationship("TaoyuanDispatchOrder", back_populates="project_links")
    project = relationship("TaoyuanProject", back_populates="dispatch_links")


class TaoyuanDispatchDocumentLink(Base):
    """派工-公文關聯（歷程追蹤）"""
    __tablename__ = "taoyuan_dispatch_document_link"
    __table_args__ = (
        UniqueConstraint('dispatch_order_id', 'document_id', name='uq_dispatch_document'),
    )

    id = Column(Integer, primary_key=True, index=True)
    dispatch_order_id = Column(Integer, ForeignKey('taoyuan_dispatch_orders.id', ondelete='CASCADE'), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)
    link_type = Column(String(20), nullable=False, index=True, comment="agency_incoming/company_outgoing")
    created_at = Column(DateTime, server_default=func.now())

    # 關聯關係
    dispatch_order = relationship("TaoyuanDispatchOrder", back_populates="document_links")
    document = relationship("OfficialDocument")


class TaoyuanDocumentProjectLink(Base):
    """公文-工程關聯（多對多）

    用於將公文直接關聯到桃園工程，不經過派工單
    """
    __tablename__ = "taoyuan_document_project_link"
    __table_args__ = (
        UniqueConstraint('document_id', 'taoyuan_project_id', name='uq_document_project'),
    )

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)
    taoyuan_project_id = Column(Integer, ForeignKey('taoyuan_projects.id', ondelete='CASCADE'), nullable=False, index=True)
    link_type = Column(String(20), nullable=True, comment="關聯類型：agency_incoming/company_outgoing")
    notes = Column(String(500), nullable=True, comment="關聯備註")
    created_at = Column(DateTime, server_default=func.now())

    # 關聯關係
    document = relationship("OfficialDocument")
    project = relationship("TaoyuanProject", back_populates="document_links")


class TaoyuanContractPayment(Base):
    """契金管控紀錄"""
    __tablename__ = "taoyuan_contract_payments"
    __table_args__ = (
        UniqueConstraint('dispatch_order_id', name='uq_payment_dispatch_order'),
    )

    id = Column(Integer, primary_key=True, index=True)
    dispatch_order_id = Column(Integer, ForeignKey('taoyuan_dispatch_orders.id', ondelete='CASCADE'), nullable=False, index=True)

    # 7種作業類別的派工日期/金額
    work_01_date = Column(Date, comment="01.地上物查估-派工日期")
    work_01_amount = Column(Float, comment="01.地上物查估-派工金額")
    work_02_date = Column(Date, comment="02.土地協議市價查估-派工日期")
    work_02_amount = Column(Float, comment="02.土地協議市價查估-派工金額")
    work_03_date = Column(Date, comment="03.土地徵收市價查估-派工日期")
    work_03_amount = Column(Float, comment="03.土地徵收市價查估-派工金額")
    work_04_date = Column(Date, comment="04.相關計畫書製作-派工日期")
    work_04_amount = Column(Float, comment="04.相關計畫書製作-派工金額")
    work_05_date = Column(Date, comment="05.測量作業-派工日期")
    work_05_amount = Column(Float, comment="05.測量作業-派工金額")
    work_06_date = Column(Date, comment="06.樁位測釘作業-派工日期")
    work_06_amount = Column(Float, comment="06.樁位測釘作業-派工金額")
    work_07_date = Column(Date, comment="07.辦理教育訓練-派工日期")
    work_07_amount = Column(Float, comment="07.辦理教育訓練-派工金額")

    # 彙總欄位
    current_amount = Column(Float, comment="本次派工金額")
    cumulative_amount = Column(Float, comment="累進派工金額")
    remaining_amount = Column(Float, comment="剩餘金額")
    acceptance_date = Column(Date, comment="完成驗收日期")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    # 關聯關係
    dispatch_order = relationship("TaoyuanDispatchOrder", back_populates="payment")


class TaoyuanDispatchWorkType(Base):
    """派工單-作業類別關聯（M:N 正規化）

    將原本 DispatchOrder.work_type 的逗號分隔字串正規化為獨立關聯表。
    向後相容：DispatchOrder.work_type 欄位保留，新增時同步寫入兩處。
    """
    __tablename__ = "taoyuan_dispatch_work_types"
    __table_args__ = (
        UniqueConstraint('dispatch_order_id', 'work_type', name='uq_dispatch_work_type'),
    )

    id = Column(Integer, primary_key=True, index=True)
    dispatch_order_id = Column(Integer,
        ForeignKey('taoyuan_dispatch_orders.id', ondelete='CASCADE'),
        nullable=False, index=True)
    work_type = Column(String(100), nullable=False, index=True,
        comment="作業類別名稱 (如：01.地上物查估作業)")
    sort_order = Column(Integer, default=0, comment="排序順序")
    created_at = Column(DateTime, server_default=func.now())

    # 關聯關係
    dispatch_order = relationship("TaoyuanDispatchOrder", back_populates="work_type_links")


class TaoyuanDispatchAttachment(Base):
    """派工單附件模型"""
    __tablename__ = 'taoyuan_dispatch_attachments'

    # 主鍵與外鍵
    id = Column(Integer, primary_key=True, autoincrement=True)
    dispatch_order_id = Column(
        Integer,
        ForeignKey('taoyuan_dispatch_orders.id', ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="關聯派工單ID"
    )

    # 基本附件資訊
    file_name = Column(String(255), comment="儲存檔案名稱")
    file_path = Column(String(500), comment="檔案路徑")
    file_size = Column(Integer, comment="檔案大小(bytes)")
    mime_type = Column(String(100), comment="MIME類型")

    # 擴充欄位
    storage_type = Column(String(20), default='local', comment="儲存類型: local/network/s3")
    original_name = Column(String(255), comment="原始檔案名稱")
    checksum = Column(String(64), index=True, comment="SHA256 校驗碼")
    uploaded_by = Column(
        Integer,
        ForeignKey('users.id', ondelete="SET NULL"),
        nullable=True,
        comment="上傳者ID"
    )

    # 系統欄位
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 關聯關係
    dispatch_order = relationship("TaoyuanDispatchOrder", back_populates="attachments")



class TaoyuanWorkRecord(Base):
    """作業歷程紀錄 - 追蹤工程的每個工作里程碑

    v2: 新增鏈式時間軸支援
    - document_id: 統一公文關聯（替代雙欄位）
    - parent_record_id: 前序紀錄（鏈式）
    - work_category: 新作業類別
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
        nullable=True, index=True, comment="觸發的機關來文 (舊格式)")
    outgoing_doc_id = Column(Integer,
        ForeignKey('documents.id', ondelete='SET NULL'),
        nullable=True, index=True, comment="對應的公司發文 (舊格式)")

    # v2 鏈式欄位
    document_id = Column(Integer,
        ForeignKey('documents.id', ondelete='SET NULL'),
        nullable=True, index=True, comment="關聯公文 (新格式，單一)")
    parent_record_id = Column(Integer,
        ForeignKey('taoyuan_work_records.id', ondelete='SET NULL'),
        nullable=True, index=True, comment="前序紀錄 ID (鏈式)")
    work_category = Column(String(50), nullable=True, index=True,
        comment="作業類別 (dispatch_notice/work_result/meeting_notice/meeting_record/survey_notice/survey_record/other)")

    # 批次結案欄位
    batch_no = Column(Integer, nullable=True, index=True,
        comment="批次序號 (第幾批結案，如 1,2,3...)")
    batch_label = Column(String(50), nullable=True,
        comment="批次標籤 (如：第1批結案、補充結案)")

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
        comment="pending/in_progress/completed/overdue/on_hold")
    sort_order = Column(Integer, default=0, comment="排序順序")

    notes = Column(Text, comment="備註")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    # 關聯關係
    dispatch_order = relationship("TaoyuanDispatchOrder", backref="work_records")
    project = relationship("TaoyuanProject", backref="work_records")
    incoming_doc = relationship("OfficialDocument", foreign_keys=[incoming_doc_id])
    outgoing_doc = relationship("OfficialDocument", foreign_keys=[outgoing_doc_id])
    document = relationship("OfficialDocument", foreign_keys=[document_id])
    parent_record = relationship("TaoyuanWorkRecord", remote_side=[id],
        backref="child_records")
