"""
營運帳目模組 (Operational Account Management)

非案件帳務的獨立管理：辦公室營運、車輛管理、設備採購、人事費用等。
與案件 ERP (ERPQuotation) 完全獨立的帳務體系。

- OperationalAccount: 帳目主檔 (年度預算單位)
- OperationalExpense: 費用明細 (單筆支出)
"""
from ._base import *


class OperationalAccount(Base):
    """營運帳目主檔"""
    __tablename__ = "operational_accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_code = Column(String(30), unique=True, nullable=False, index=True,
                          comment="帳目編號: OP_{西元年}_{類別碼}_{流水3碼}")
    name = Column(String(200), nullable=False, comment="帳目名稱")
    category = Column(String(30), nullable=False, index=True,
                      comment="類別: office/vehicle/equipment/personnel/maintenance/misc")
    fiscal_year = Column(Integer, nullable=False, index=True, comment="年度 (西元)")
    budget_limit = Column(Numeric(15, 2), default=0, comment="年度預算上限")
    department = Column(String(100), comment="所屬部門")
    status = Column(String(20), default="active", index=True,
                    comment="狀態: active/closed/frozen")
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                      nullable=True, index=True, comment="帳目負責人")
    notes = Column(Text, comment="備註")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    expenses = relationship("OperationalExpense", back_populates="account",
                            lazy="dynamic", cascade="all, delete-orphan")


class OperationalExpense(Base):
    """營運費用明細"""
    __tablename__ = "operational_expenses"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("operational_accounts.id", ondelete="CASCADE"),
                        nullable=False, index=True, comment="帳目 ID")
    expense_date = Column(Date, nullable=False, comment="費用日期")
    amount = Column(Numeric(15, 2), nullable=False, comment="金額")
    description = Column(String(500), comment="摘要說明")
    category = Column(String(50), comment="費用分類: rent/utility/insurance/fuel/repair/salary/other")

    # Optional links
    expense_invoice_id = Column(Integer, ForeignKey("expense_invoices.id", ondelete="SET NULL"),
                                nullable=True, index=True, comment="關聯發票")
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"),
                      nullable=True, index=True, comment="關聯資產")

    # Approval
    approval_status = Column(String(20), default="pending",
                             comment="審批: pending/approved/rejected")
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                         nullable=True, comment="審批人")
    approved_at = Column(DateTime, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, comment="備註")
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    account = relationship("OperationalAccount", back_populates="expenses")
