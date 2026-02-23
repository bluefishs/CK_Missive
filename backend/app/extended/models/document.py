"""
3. 公文模組 (Document Module)

- OfficialDocument: 公文
- DocumentAttachment: 公文附件
"""
from ._base import *


class OfficialDocument(Base):
    """公文模型 - 與資料庫 schema 完整對齊"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    auto_serial = Column(String(50), index=True, comment="流水序號 (R0001=收文, S0001=發文)")
    doc_number = Column(String(100), index=True, comment="公文文號")
    doc_type = Column(String(10), index=True, comment="公文類型 (收文/發文)")
    subject = Column(String(500), comment="主旨")
    sender = Column(String(200), index=True, comment="發文單位")
    receiver = Column(String(200), index=True, comment="受文單位")
    doc_date = Column(Date, index=True, comment="發文日期 (西元)")
    receive_date = Column(Date, comment="收文日期 (西元)")
    status = Column(String(50), index=True, comment="處理狀態")
    category = Column(String(100), index=True, comment="收發文分類")

    delivery_method = Column(String(20), index=True, default="電子交換", comment="發文形式")
    has_attachment = Column(Boolean, default=False, comment="是否含附件")

    contract_project_id = Column(Integer, ForeignKey('contract_projects.id'), nullable=True, comment="關聯的承攬案件ID")
    sender_agency_id = Column(Integer, ForeignKey('government_agencies.id'), nullable=True, comment="發文機關ID")
    receiver_agency_id = Column(Integer, ForeignKey('government_agencies.id'), nullable=True, comment="受文機關ID")

    send_date = Column(Date, comment="發文日期")
    title = Column(Text, comment="標題")
    content = Column(Text, comment="說明")
    cloud_file_link = Column(String(500), comment="雲端檔案連結")
    dispatch_format = Column(String(20), default="電子", comment="發文形式")

    assignee = Column(String(500), comment="承辦人（多人以逗號分隔）")
    notes = Column(Text, comment="備註")
    ck_note = Column(Text, comment="簡要說明(乾坤備註)")

    created_at = Column(DateTime, server_default=func.now(), comment="建立時間")
    updated_at = Column(DateTime, server_default=func.now(), comment="更新時間")

    # 向量嵌入欄位 (pgvector)
    if Vector is not None:
        embedding = deferred(Column(
            Vector(384),
            nullable=True,
            comment="文件向量嵌入 (nomic-embed-text, 384 維)",
        ))

    # 關聯關係
    contract_project = relationship("ContractProject", back_populates="documents", lazy="select")
    sender_agency = relationship("GovernmentAgency", foreign_keys=[sender_agency_id], back_populates="sent_documents", lazy="select")
    receiver_agency = relationship("GovernmentAgency", foreign_keys=[receiver_agency_id], back_populates="received_documents", lazy="select")
    calendar_events = relationship("DocumentCalendarEvent", back_populates="document", cascade="all, delete-orphan", passive_deletes=True)
    attachments = relationship("DocumentAttachment", back_populates="document", cascade="all, delete-orphan", passive_deletes=True)


class DocumentAttachment(Base):
    """公文附件模型 - 與資料庫實際 schema 對齊"""
    __tablename__ = 'document_attachments'
    id = Column(Integer, primary_key=True, autoincrement=True, comment="附件唯一識別ID")
    document_id = Column(Integer, ForeignKey('documents.id', ondelete="CASCADE"), nullable=False, comment="關聯的公文ID")

    file_name = Column(String(255), comment="檔案名稱")
    file_path = Column(String(500), comment="檔案路徑")
    file_size = Column(Integer, comment="檔案大小(bytes)")
    mime_type = Column(String(100), comment="MIME類型")

    storage_type = Column(String(20), default='local', comment="儲存類型: local/network/s3")
    original_name = Column(String(255), comment="原始檔案名稱")
    checksum = Column(String(64), index=True, comment="SHA256 校驗碼")
    uploaded_by = Column(Integer, ForeignKey('users.id', ondelete="SET NULL"), comment="上傳者 ID")

    created_at = Column(DateTime, server_default=func.now(), comment="建立時間")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新時間")

    document = relationship("OfficialDocument", back_populates="attachments")

    @property
    def filename(self):
        return self.file_name

    @filename.setter
    def filename(self, value):
        self.file_name = value

    @property
    def content_type(self):
        return self.mime_type

    @content_type.setter
    def content_type(self, value):
        self.mime_type = value

    @property
    def uploaded_at(self):
        return self.created_at
