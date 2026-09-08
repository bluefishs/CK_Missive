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
    # ⭐ 2026-09-08 owner：「小記已含稅，故報價單需增列勾選『總價是否含稅』」。
    # 對應總表 K 欄「稅內含」——匯入器讀了它卻只丟進 notes。
    #   true  ⇒ 工項小計即為總價（不再 ×1.05），tax_amount 不另計
    #   false ⇒ 工項小計是未稅，總價 ＝ 小計 × 1.05
    # 預設 false 沿用現行行為；存量不動（要不要標含稅是逐案的事實，不能用一句 SQL 猜）。
    tax_included = Column(Boolean, nullable=False, server_default="false",
                          comment="總價是否已含稅（總表 K 欄「稅內含」）")

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
    #: 報價單的種類（2026-09-02 晚）。同一張表裝了三種東西，先前只靠 case_code 的段落分辨：
    #:   tender          — 01 委辦招標：標案建案時開的 draft，投標用（owner 08-17）
    #:   contract        — 02 承攬報價：人工報價、XLS 匯入，owner 的「115 報價單彙整總表」只對這一種
    #:   finance_anchor  — 成案時系統自動建的 0 元掛點，只為了讓請款／發票有地方掛
    #: 推導規則單一來源＝`services/erp/quote_kind.py`；migration 回填用同一條規則。NULL＝存量未分類。
    quote_kind = Column(String(20), nullable=True, index=True, comment="tender/contract/finance_anchor")
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

    item_no = Column(String(20), comment="項次（自填，如 1.1；NULL＝自動 一、二、三）")  # 2026-09-04
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
    notes = Column(Text, comment="備註（系統訊息，例「系統自動補建」）")

    # ⭐ 2026-09-08：總表的「發票明細」工作表本來就有這四項，而系統沒有欄位存
    # ⇒ 只能塞在備註文字裡（「發票抬頭:樂昱建設有限公司 統編:92602248」），搜尋不到也對不了帳。
    #
    # ⚠️ 聯式**不影響稅額**：owner 提供的實體發票 EE15019500（買受人桃園市政府工務局）
    # 是二聯式而課稅別勾應稅。此前 UI 把兩者混成一個選項（「免稅／零稅率（二聯式）」），
    # 照那個標籤選會讓機關的二聯式發票被記成免稅、少掉 5% 的稅。
    invoice_kind = Column(String(10), nullable=True,
                          comment="發票種類：triplicate=三聯式／duplicate=二聯式")
    #: 買受人**不等於**委託單位：那五案的委託單位是鎮泓，而抬頭有蔡蕙宇（個人）與樂昱建設。
    buyer_name = Column(String(200), nullable=True, comment="發票抬頭（買受人）")
    buyer_tax_id = Column(String(20), nullable=True, comment="買受人統編；二聯式可為空")
    #: 與 `notes` 分開 —— 這是**寫在發票上的字**（例「訂購編號：XD-QA0132-00 台銀」），
    #: 而 notes 裝的是系統訊息。混在一起，任一方都會被另一方污染。
    invoice_remark = Column(String(200), nullable=True, comment="發票備註（印在發票上）")
    #: 來源（2026-09-03）：manual／xls_import／auto_from_billing——此前靠 notes 前綴分辨
    source = Column(String(24), nullable=True, comment="manual/xls_import/auto_from_billing")

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
    # 2026-09-07：結算方式 —— 「已收款但沒有發票」不一定是缺漏，也可能是**約定不開票或互抵**。
    # 沒有這個欄位時，那兩種情境只能寫在備註裡，於是稽核永遠把它們報成缺漏（weekly 104 ⑪）。
    settlement_type = Column(String(20), nullable=False, server_default="invoice", index=True,
                             comment="結算方式: invoice=開立發票 / offset=互抵 / no_invoice=約定不開票")
    settlement_note = Column(String(300), nullable=True, comment="互抵／不開票的依據與對象")
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

class ERPInvoiceAllocation(Base):
    """一張發票分攤到多個案（2026-09-07）。

    owner：「同一發票對應多案件……應如何處理」。原本 `erp_invoices` 只有單一 `erp_quotation_id`，
    一張發票跨兩案就**表達不出來** —— 人只能挑一個案掛上去，另一個案在帳上看不到那筆收入。

    規則：**有分攤時以分攤為準，沒有分攤時沿用發票本身的 `erp_quotation_id`**（相容既有 155 張）。
    分攤合計必須等於發票金額 —— 那是這張表存在的意義，不允許「分一半就不管了」。
    """

    __tablename__ = "erp_invoice_allocations"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("erp_invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    erp_quotation_id = Column(Integer, ForeignKey("erp_quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    billing_id = Column(Integer, ForeignKey("erp_billings.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Numeric(15, 2), nullable=False, comment="該案分攤金額（含稅）")
    tax_amount = Column(Numeric(15, 2), nullable=True, comment="該案分攤稅額")
    notes = Column(String(300), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
