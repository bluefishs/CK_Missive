"""
17. 費用報銷發票模組 (Expense Invoice Module)

員工拍照上傳/手動登錄的消費憑證，以 case_code 為跨模組軟參照橋樑。
非專案支出時 case_code 為 NULL（一般營運）。

- ExpenseInvoice: 報銷發票主檔
- ExpenseInvoiceItem: 發票品名明細

Version: 1.0.0
Created: 2026-03-21
"""
from ._base import *


class ExpenseInvoice(Base):
    """費用報銷發票 — 員工拍照上傳/手動登錄的消費憑證"""
    __tablename__ = "expense_invoices"

    id = Column(Integer, primary_key=True, index=True)
    inv_num = Column(String(20), unique=True, index=True, nullable=False,
                     comment="發票號碼 (如 AB12345678)")
    date = Column(Date, nullable=False, comment="開立日期 (西元)")
    amount = Column(Numeric(15, 2), nullable=False, comment="總金額 (含稅)")
    tax_amount = Column(Numeric(15, 2), nullable=True, comment="稅額")
    buyer_ban = Column(String(8), nullable=True, comment="買方統編")
    seller_ban = Column(String(8), nullable=True, comment="賣方統編")

    # 跨模組橋樑
    case_code = Column(String(50), nullable=True, index=True,
                       comment="案號 (軟參照 pm_cases / erp_quotations)，NULL=一般營運")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                     nullable=True, comment="上傳者/報銷人")

    # 分類與狀態
    category = Column(String(50), nullable=True,
                      comment="費用分類: 交通/餐費/設備/文具/差旅/其他")
    status = Column(String(20), nullable=False, server_default="pending",
                    comment="pending / processed / verified / rejected")
    source = Column(String(20), nullable=False, server_default="manual",
                    comment="qr_scan / manual / api / ocr / mof_sync")
    source_image_path = Column(String(500), nullable=True, comment="原始圖檔路徑")
    receipt_image_path = Column(String(500), nullable=True,
                                comment="收據影本路徑 (報帳員上傳)")
    raw_qr_data = Column(Text, nullable=True, comment="原始 QR Code 字串 (除錯用)")
    notes = Column(String(500), nullable=True, comment="備註")
    mof_invoice_track = Column(String(2), nullable=True,
                               comment="財政部發票字軌 (如 AB)")
    mof_period = Column(String(5), nullable=True,
                        comment="發票期別 (如 11404, 民國年+月份)")
    synced_at = Column(DateTime, nullable=True,
                       comment="財政部同步時間戳")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="expense_invoices")
    items = relationship("ExpenseInvoiceItem", back_populates="invoice",
                         cascade="all, delete-orphan")
    ledger_entries = relationship(
        "FinanceLedger",
        primaryjoin="and_(ExpenseInvoice.id == foreign(FinanceLedger.source_id), "
                    "FinanceLedger.source_type == 'expense_invoice')",
        back_populates="expense_invoice",
        viewonly=True,
    )


class ExpenseInvoiceItem(Base):
    """費用發票明細 (品名/數量/單價)"""
    __tablename__ = "expense_invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("expense_invoices.id", ondelete="CASCADE"),
                        nullable=False, index=True)

    item_name = Column(String(200), nullable=False, comment="品名")
    qty = Column(Numeric(10, 2), nullable=False, server_default="1", comment="數量")
    unit_price = Column(Numeric(15, 2), nullable=False, comment="單價")
    amount = Column(Numeric(15, 2), nullable=False, comment="小計")

    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    invoice = relationship("ExpenseInvoice", back_populates="items")
