"""
19. 電子發票同步模組 (E-Invoice Sync Module)

追蹤財政部大平台電子發票自動同步批次記錄。
每次排程同步產生一筆 SyncLog，記錄查詢區間、結果數量、錯誤訊息。

- EInvoiceSyncLog: 同步批次記錄

Version: 1.0.0
Created: 2026-03-21
"""
from ._base import *


class EInvoiceSyncLog(Base):
    """電子發票同步批次記錄 — 追蹤每次財政部 API 同步結果"""
    __tablename__ = "einvoice_sync_logs"
    __table_args__ = (
        Index("idx_einvoice_buyer", "buyer_ban"),
        Index("idx_einvoice_query_date", "query_start", "query_end"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # 查詢參數
    buyer_ban = Column(String(8), nullable=False, comment="查詢統編")
    query_start = Column(Date, nullable=False, comment="查詢起始日期")
    query_end = Column(Date, nullable=False, comment="查詢結束日期")

    # 同步結果
    status = Column(String(20), nullable=False, server_default="running",
                    comment="running / success / partial / failed")
    total_fetched = Column(Integer, nullable=False, server_default="0",
                           comment="從 API 取得的發票數")
    new_imported = Column(Integer, nullable=False, server_default="0",
                          comment="新匯入系統的發票數")
    skipped_duplicate = Column(Integer, nullable=False, server_default="0",
                               comment="略過的重複發票數")
    detail_fetched = Column(Integer, nullable=False, server_default="0",
                            comment="成功抓取明細的發票數")
    error_message = Column(Text, nullable=True, comment="錯誤訊息")

    # 時間
    started_at = Column(DateTime, server_default=func.now(), comment="同步開始時間")
    completed_at = Column(DateTime, nullable=True, comment="同步完成時間")
