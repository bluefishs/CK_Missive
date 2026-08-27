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

    # 2026-08-17 owner「編號統整」：對外報價單號。
    # 在此之前報價單**沒有自己的號**，只有邀標案號與成案編號 ——
    # 而客戶回覆時引用的是「你們那張 QT-…」，不是我們內部的案號。
    # ⚠️ 唯一性由遷移建的 **partial index**（`WHERE quotation_no IS NOT NULL`）
    # 保證，這裡刻意不寫 `unique=True` —— 兩邊寫法不同會讓
    # schema 驗證每次啟動都報不一致（本專案反覆記過「同一件事有兩份說法」）。
    quotation_no = Column(String(30), index=True,
                          comment="對外報價單號 QT{年}_{序}；版次變更不換號")
    # 議價後重報是 v2，**單號不變**（客戶引用的是同一張報價單）
    revision = Column(Integer, nullable=False, server_default="1", comment="版次")
    quoted_at = Column(DateTime, comment="報價送出時間；NULL＝還在草稿")

    # 個人管理時期的報價單號（B114-B002 / B115-C017a-0）。
    # 保留它是因為紙本、雲端硬碟檔名、客戶往來信件用的都是這組編號 ——
    # 回簽 PDF 的檔名就長這樣：`回簽報價單_B115-C013-0_朱冠綸_….pdf`，
    # 沒有它就無法把那批檔案掛回系統。
    # 唯一性同樣由遷移建的 partial index 保證（見 20260819a001），這裡不寫 unique。
    legacy_quotation_no = Column(String(64), index=True,
                                 comment="舊案號（個人管理時期），供與紙本／回簽檔對帳")

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
    # 2026-08-16：報價明細（線上報價單）。lazy="selectin" 與其他關聯一致 ——
    # 序列化時觸發 lazy IO 會爆 MissingGreenlet 而被誤標成 409（2026-07-30 踩過）。
    items = relationship("ERPQuotationItem", back_populates="quotation", lazy="selectin",
                         cascade="all, delete-orphan",
                         order_by="ERPQuotationItem.sort_order")


class ERPQuotationItem(Base):
    """報價明細（線上報價單的逐項）—— 2026-08-16

    owner：「線上報價單機制」。

    在此之前 `erp_quotations` **只有彙總金額**（`total_price` 一個數字），
    沒有任何逐項資料 —— 那不是報價單，是成本主檔。
    實測 78 張報價裡 **23 張沒有總價**，因為那個數字只能靠人手填，
    而人手上真正有的是一份逐項的報價內容。

    有了明細之後 `total_price` 由小計加總得出，不再是獨立的一份事實。
    """
    __tablename__ = "erp_quotation_items"

    id = Column(Integer, primary_key=True, index=True)
    quotation_id = Column(Integer, ForeignKey("erp_quotations.id", ondelete="CASCADE"),
                          nullable=False, index=True)

    item_name = Column(String(200), nullable=False, comment="工項名稱")
    spec = Column(String(300), comment="規格/說明")
    unit = Column(String(20), comment="單位（式/處/公頃…）")
    qty = Column(Numeric(12, 2), nullable=False, server_default="1", comment="數量")
    unit_price = Column(Numeric(15, 2), nullable=False, server_default="0", comment="單價")
    # 小計由 qty × unit_price 算出後存下來。
    # **存下來而不是每次算** —— 報價送出後單價可能調整，
    # 而已送出的那份報價金額不該跟著變。
    amount = Column(Numeric(15, 2), nullable=False, server_default="0", comment="小計")
    sort_order = Column(Integer, nullable=False, server_default="0", comment="排序")
    notes = Column(Text, comment="備註")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    quotation = relationship("ERPQuotation", back_populates="items")


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
                         comment="統一編號 (軟參照 partner_vendors.vendor_code；實測全部為 8 碼統編格式)")
    vendor_id = Column(Integer, ForeignKey("partner_vendors.id", ondelete="SET NULL"),
                       nullable=True, index=True, comment="廠商 ID (強參照)")
    billing_id = Column(Integer, ForeignKey("erp_billings.id", ondelete="SET NULL"),
                        nullable=True, index=True, comment="關聯請款期別")
    payable_amount = Column(Numeric(15, 2), nullable=False, comment="應付金額")
    # 2026-08-18：與應收 `erp_billings.billing_period` 對稱。
    # 值域共用 `schemas/erp/billing.py: BillingPeriod` —— 分期就是分期，
    # 沒有理由讓應收的「第一期」與應付的「第一期」是兩份清單。
    payable_period = Column(String(50), nullable=True, comment="期別（第一期／尾款／一次請領…）")
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
