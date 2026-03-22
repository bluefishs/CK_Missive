"""
18. 統一帳本模組 (Finance Ledger Module)

全公司所有收支的最終記錄，以 case_code 為跨模組軟參照橋樑。
資料來源：ExpenseInvoice 報銷 / ERPBilling 收款 / 手動記帳。

- FinanceLedger: 統一帳本

Version: 1.0.0
Created: 2026-03-21
"""
from ._base import *


class FinanceLedger(Base):
    """統一帳本 — 全公司所有收支的最終記錄

    source_type + source_id 構成多態參照：
    - manual: 手動記帳 (source_id=NULL)
    - expense_invoice: 報銷發票自動入帳
    - erp_billing: ERPBilling 收款入帳
    - erp_vendor_payable: 廠商付款入帳
    """
    __tablename__ = "finance_ledgers"

    id = Column(Integer, primary_key=True, index=True)

    # 跨模組橋樑
    case_code = Column(String(50), nullable=True, index=True,
                       comment="案號 (軟參照)，NULL=一般營運支出")

    # 來源追蹤 (多態參照)
    source_type = Column(String(30), nullable=False, server_default="manual",
                         comment="manual / expense_invoice / erp_billing / erp_vendor_payable")
    source_id = Column(Integer, nullable=True,
                       comment="來源記錄 ID (對應 source_type 的表)")

    # 金額與分類
    amount = Column(Numeric(15, 2), nullable=False, comment="金額")
    entry_type = Column(String(20), nullable=False,
                        comment="income / expense")
    category = Column(String(50), nullable=True,
                      comment="分類: 外包/人事/設備/交通/餐費/管銷/雜支/收款...")
    description = Column(String(500), nullable=True, comment="摘要說明")

    # 經辦人
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                     nullable=True, comment="記帳人/經辦人")

    # 時間
    transaction_date = Column(Date, nullable=False, server_default=func.current_date(),
                              comment="交易日期")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_ledger_case_date", "case_code", "transaction_date"),
        Index("idx_ledger_source", "source_type", "source_id"),
    )

    # Relationships
    user = relationship("User", back_populates="finance_ledgers")
    expense_invoice = relationship(
        "ExpenseInvoice",
        primaryjoin="and_(foreign(FinanceLedger.source_id) == ExpenseInvoice.id, "
                    "FinanceLedger.source_type == 'expense_invoice')",
        back_populates="ledger_entries",
        viewonly=True,
        uselist=False,
    )
