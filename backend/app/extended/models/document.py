# -*- coding: utf-8 -*-
"""
公文管理資料模型
Document management data models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class DocumentType(enum.Enum):
    """文件類型"""
    OUTGOING = "發文"  # 發文
    INCOMING = "收文"  # 收文

class DocumentCategory(enum.Enum):
    """公文類別"""
    LETTER = "函"  # 函
    NOTICE = "會勘通知單"  # 會勘通知單
    MEMO = "簽"  # 簽
    REPORT = "報告"  # 報告
    OTHER = "其他"  # 其他

class DocumentStatus(enum.Enum):
    """收發狀態"""
    PENDING = "待處理"  # 待處理
    PROCESSING = "處理中"  # 處理中
    USER_CONFIRMED = "使用者確認"  # 使用者確認
    RECEIVED_COMPLETED = "收文完成"  # 收文完成
    SENT_COMPLETED = "發文完成"  # 發文完成
    ARCHIVED = "歸檔"  # 歸檔

class DocumentFormat(enum.Enum):
    """發文形式"""
    ELECTRONIC = "電子"  # 電子
    PAPER = "紙本"  # 紙本
    BOTH = "電子+紙本"  # 電子+紙本

class Document(Base):
    """公文文件模型"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, comment="主鍵ID")

    # 基本資訊
    sequence_number = Column(Integer, unique=True, index=True, comment="流水號")
    document_type = Column(Enum(DocumentType), nullable=False, comment="文件類型")
    document_number = Column(String(100), unique=True, index=True, comment="公文字號")

    # 日期資訊
    date = Column(DateTime, comment="日期")
    official_date = Column(String(50), comment="公文日期")
    received_date = Column(DateTime, comment="收文日期")
    system_output_date = Column(DateTime, comment="系統輸出日期")

    # 分類資訊
    category = Column(Enum(DocumentCategory), comment="類別")
    prefix_code = Column(String(20), comment="字")
    number_code = Column(String(20), comment="文號")

    # 內容資訊
    subject = Column(Text, comment="主旨")

    # 單位資訊
    sender_unit = Column(String(200), comment="發文單位")
    receiver_unit = Column(String(200), comment="受文單位")

    # 狀態資訊
    status = Column(Enum(DocumentStatus), comment="收發狀態")
    dispatch_format = Column(Enum(DocumentFormat), comment="發文形式")

    # 其他資訊
    notes = Column(Text, comment="備註")
    project_case = Column(String(200), comment="承攬案件")

    # 系統欄位
    created_at = Column(DateTime, default=datetime.utcnow, comment="建立時間")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新時間")
    created_by = Column(String(100), comment="建立者")
    updated_by = Column(String(100), comment="更新者")

    # 軟刪除
    is_deleted = Column(Boolean, default=False, comment="是否刪除")
    deleted_at = Column(DateTime, comment="刪除時間")

    def __repr__(self):
        return f"<Document(id={self.id}, document_number='{self.document_number}', subject='{self.subject[:50]}...')>"

class DocumentAttachment(Base):
    """公文附件模型"""
    __tablename__ = "document_attachments"

    id = Column(Integer, primary_key=True, index=True, comment="主鍵ID")
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False, comment="公文ID")

    # 附件資訊
    filename = Column(String(255), nullable=False, comment="檔案名稱")
    original_filename = Column(String(255), comment="原始檔案名稱")
    file_path = Column(String(500), comment="檔案路徑")
    file_size = Column(Integer, comment="檔案大小(bytes)")
    file_type = Column(String(50), comment="檔案類型")
    mime_type = Column(String(100), comment="MIME類型")

    # 系統欄位
    created_at = Column(DateTime, default=datetime.utcnow, comment="建立時間")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新時間")
    created_by = Column(String(100), comment="建立者")

    # 軟刪除
    is_deleted = Column(Boolean, default=False, comment="是否刪除")
    deleted_at = Column(DateTime, comment="刪除時間")

    # 關聯
    document = relationship("Document", backref="attachments")

    def __repr__(self):
        return f"<DocumentAttachment(id={self.id}, filename='{self.filename}', document_id={self.document_id})>"

class DocumentLog(Base):
    """公文操作日誌模型"""
    __tablename__ = "document_logs"

    id = Column(Integer, primary_key=True, index=True, comment="主鍵ID")
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False, comment="公文ID")

    # 操作資訊
    action = Column(String(50), nullable=False, comment="操作類型")
    description = Column(Text, comment="操作描述")
    old_status = Column(String(50), comment="舊狀態")
    new_status = Column(String(50), comment="新狀態")

    # 系統欄位
    created_at = Column(DateTime, default=datetime.utcnow, comment="操作時間")
    created_by = Column(String(100), comment="操作者")
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(String(500), comment="用戶代理")

    # 關聯
    document = relationship("Document", backref="logs")

    def __repr__(self):
        return f"<DocumentLog(id={self.id}, action='{self.action}', document_id={self.document_id})>"