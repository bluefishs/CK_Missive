"""
15. 財務管理模組 (ERP/Finance Module)

獨立於現有公文/派工系統，以 case_code 為跨模組軟參照橋樑。
未來可整包拆分為獨立 FastAPI 服務。

- ERPQuotation: 報價/成本主檔
- ERPInvoice: 發票管理
- ERPBilling: 請款管理
- ERPVendorPayable: 廠商應付管理

Version: 1.0.0
Created: 2026-03-16
"""
from ._base import *


class ERPQuotation(Base):
    """報價/成本主檔 — ERP 模組核心實體"""
    __tablename__ = "erp_quotations"

    id = Column(Integer, primary_key=True, index=True)
    case_code = Column(String(50), nullable=False, index=True,
                       comment="建案案號 (軟參照 pm_cases.case_code)")
    project_code = Column(String(100), nullable=True, index=True,
                          comment="成案專案編號 (成案後同步，對應 contract_projects.project_code)")
    case_name = Column(String(500), comment="案名 (冗餘，獨立顯示用)")
    year = Column(Integer, index=True, comment="年度 (民國)")

    # 金額
    total_price = Column(Numeric(15, 2), comment="總價 (含稅)")
    tax_amount = Column(Numeric(15, 2), default=0, comment="稅額")

    # 成本拆解
    outsourcing_fee = Column(Numeric(15, 2), default=0, comment="外包費")
    personnel_fee = Column(Numeric(15, 2), default=0, comment="人事費")
    overhead_fee = Column(Numeric(15, 2), default=0, comment="管銷費")
    other_cost = Column(Numeric(15, 2), default=0, comment="其他成本")
    budget_limit = Column(Numeric(15, 2), nullable=True, comment="預算上限")

    # 狀態
    status = Column(String(30), default="draft", index=True,
                    comment="狀態: draft/confirmed/revised")
    notes = Column(Text, comment="備註")

    # 建立者
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                        nullable=True, index=True, comment="建立者")

    deleted_at = Column(DateTime, nullable=True, index=True,
                        comment="軟刪除時間 (NULL=未刪除)")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 關聯
    invoices = relationship("ERPInvoice", back_populates="quotation", lazy="selectin",
                            cascade="all, delete-orphan")
    billings = relationship("ERPBilling", back_populates="quotation", lazy="selectin",
                            cascade="all, delete-orphan")
    vendor_payables = relationship("ERPVendorPayable", back_populates="quotation", lazy="selectin",
                                   cascade="all, delete-orphan")


class ERPInvoice(Base):
    """發票管理"""
    __tablename__ = "erp_invoices"

    id = Column(Integer, primary_key=True, index=True)
    erp_quotation_id = Column(Integer, ForeignKey("erp_quotations.id", ondelete="CASCADE"),
                              nullable=False, index=True)

    invoice_number = Column(String(50), unique=True, nullable=False, index=True,
                            comment="發票號碼")
    invoice_ref = Column(String(20), unique=True, nullable=True, index=True,
                         comment="系統發票參照碼 IV_{yyyy}_{NNN}")
    invoice_date = Column(Date, nullable=False, comment="發票開立日期")
    amount = Column(Numeric(15, 2), nullable=False, comment="發票金額 (含稅)")
    tax_amount = Column(Numeric(15, 2), default=0, comment="稅額")
    invoice_type = Column(String(30), default="sales",
                          comment="類型: sales(銷項)/purchase(進項)")
    description = Column(String(300), comment="發票摘要")
    status = Column(String(30), default="issued", index=True,
                    comment="狀態: issued/voided/cancelled")
    voided_at = Column(DateTime, nullable=True, comment="作廢時間")
    notes = Column(Text, comment="備註")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 請款期別關聯 (optional, one-way: Invoice → Billing)
    billing_id = Column(Integer, ForeignKey("erp_billings.id", ondelete="SET NULL"),
                        nullable=True, index=True, comment="關聯請款期別")

    # 關聯
    quotation = relationship("ERPQuotation", back_populates="invoices")
    billing = relationship("ERPBilling", foreign_keys=[billing_id], viewonly=True)


class ERPBilling(Base):
    """請款管理"""
    __tablename__ = "erp_billings"

    id = Column(Integer, primary_key=True, index=True)
    erp_quotation_id = Column(Integer, ForeignKey("erp_quotations.id", ondelete="CASCADE"),
                              nullable=False, index=True)

    billing_code = Column(String(20), unique=True, nullable=True, index=True,
                          comment="系統請款編碼 BL_{yyyy}_{NNN}")
    billing_period = Column(String(50), comment="期別 (第1期/第2期/尾款)")
    billing_date = Column(Date, nullable=False, comment="請款日期")
    billing_amount = Column(Numeric(15, 2), nullable=False, comment="請款金額")

    # 收款追蹤
    payment_status = Column(String(30), default="pending", index=True,
                            comment="狀態: pending/partial/paid/overdue")
    payment_date = Column(Date, nullable=True, comment="實際收款日期")
    payment_amount = Column(Numeric(15, 2), nullable=True, comment="實際收到金額")
    notes = Column(Text, comment="備註")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 關聯
    quotation = relationship("ERPQuotation", back_populates="billings")
    # 反向: 本期關聯的發票和應付 (one-way: Invoice.billing_id → Billing)
    linked_invoices = relationship("ERPInvoice", foreign_keys="ERPInvoice.billing_id", viewonly=True)
    linked_payables = relationship("ERPVendorPayable", foreign_keys="ERPVendorPayable.billing_id", viewonly=True)


class ERPVendorPayable(Base):
    """廠商應付管理"""
    __tablename__ = "erp_vendor_payables"

    id = Column(Integer, primary_key=True, index=True)
    erp_quotation_id = Column(Integer, ForeignKey("erp_quotations.id", ondelete="CASCADE"),
                              nullable=False, index=True)

    vendor_name = Column(String(200), nullable=False, comment="廠商名稱")
    vendor_code = Column(String(50), nullable=True, index=True,
                         comment="廠商代碼 (軟參照 partner_vendors.vendor_code)")
    vendor_id = Column(Integer, ForeignKey("partner_vendors.id", ondelete="SET NULL"),
                       nullable=True, index=True, comment="廠商 ID (強參照)")
    billing_id = Column(Integer, ForeignKey("erp_billings.id", ondelete="SET NULL"),
                        nullable=True, index=True, comment="關聯請款期別")
    payable_amount = Column(Numeric(15, 2), nullable=False, comment="應付金額")
    description = Column(String(300), comment="項目說明")

    # 付款追蹤
    due_date = Column(Date, nullable=True, comment="應付日期")
    paid_date = Column(Date, nullable=True, comment="實際付款日期")
    paid_amount = Column(Numeric(15, 2), nullable=True, comment="實際付款金額")
    payment_status = Column(String(30), default="unpaid", index=True,
                            comment="狀態: unpaid/partial/paid")
    invoice_number = Column(String(50), nullable=True, comment="廠商發票號碼")
    notes = Column(Text, comment="備註")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 關聯
    quotation = relationship("ERPQuotation", back_populates="vendor_payables")
    vendor = relationship("PartnerVendor", foreign_keys=[vendor_id])
    billing = relationship("ERPBilling", foreign_keys=[billing_id], viewonly=True)
