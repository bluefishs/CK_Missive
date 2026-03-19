"""create ERP module tables (erp_quotations, erp_invoices, erp_billings, erp_vendor_payables)

獨立財務管理模組，零耦合於現有公文/派工系統。

Revision ID: 20260316b002
Revises: 20260316b001
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa

revision = "20260316b002"
down_revision = "20260316b001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === erp_quotations ===
    op.create_table(
        "erp_quotations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("case_code", sa.String(50), nullable=False,
                  comment="案號 (軟參照 pm_cases.case_code)"),
        sa.Column("case_name", sa.String(500), nullable=True,
                  comment="案名 (冗餘，獨立顯示用)"),
        sa.Column("year", sa.Integer(), nullable=True, comment="年度 (民國)"),
        sa.Column("total_price", sa.Numeric(15, 2), nullable=True, comment="總價 (含稅)"),
        sa.Column("tax_amount", sa.Numeric(15, 2), server_default="0", comment="稅額"),
        sa.Column("outsourcing_fee", sa.Numeric(15, 2), server_default="0", comment="外包費"),
        sa.Column("personnel_fee", sa.Numeric(15, 2), server_default="0", comment="人事費"),
        sa.Column("overhead_fee", sa.Numeric(15, 2), server_default="0", comment="管銷費"),
        sa.Column("other_cost", sa.Numeric(15, 2), server_default="0", comment="其他成本"),
        sa.Column("status", sa.String(30), server_default="draft",
                  comment="狀態: draft/confirmed/revised"),
        sa.Column("notes", sa.Text(), nullable=True, comment="備註"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True, comment="建立者"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_erp_quotations_id", "erp_quotations", ["id"])
    op.create_index("ix_erp_quotations_case_code", "erp_quotations", ["case_code"])
    op.create_index("ix_erp_quotations_year", "erp_quotations", ["year"])
    op.create_index("ix_erp_quotations_status", "erp_quotations", ["status"])

    # === erp_invoices ===
    op.create_table(
        "erp_invoices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("erp_quotation_id", sa.Integer(),
                  sa.ForeignKey("erp_quotations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_number", sa.String(50), nullable=False,
                  comment="發票號碼"),
        sa.Column("invoice_date", sa.Date(), nullable=False, comment="發票開立日期"),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False, comment="發票金額 (含稅)"),
        sa.Column("tax_amount", sa.Numeric(15, 2), server_default="0", comment="稅額"),
        sa.Column("invoice_type", sa.String(30), server_default="sales",
                  comment="類型: sales(銷項)/purchase(進項)"),
        sa.Column("description", sa.String(300), nullable=True, comment="發票摘要"),
        sa.Column("status", sa.String(30), server_default="issued",
                  comment="狀態: issued/voided/cancelled"),
        sa.Column("voided_at", sa.DateTime(), nullable=True, comment="作廢時間"),
        sa.Column("notes", sa.Text(), nullable=True, comment="備註"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_erp_invoices_id", "erp_invoices", ["id"])
    op.create_index("ix_erp_invoices_erp_quotation_id", "erp_invoices", ["erp_quotation_id"])
    op.create_index("ix_erp_invoices_invoice_number", "erp_invoices", ["invoice_number"], unique=True)
    op.create_index("ix_erp_invoices_status", "erp_invoices", ["status"])

    # === erp_billings ===
    op.create_table(
        "erp_billings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("erp_quotation_id", sa.Integer(),
                  sa.ForeignKey("erp_quotations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("billing_period", sa.String(50), nullable=True,
                  comment="期別 (第1期/第2期/尾款)"),
        sa.Column("billing_date", sa.Date(), nullable=False, comment="請款日期"),
        sa.Column("billing_amount", sa.Numeric(15, 2), nullable=False, comment="請款金額"),
        sa.Column("invoice_id", sa.Integer(),
                  sa.ForeignKey("erp_invoices.id", ondelete="SET NULL"), nullable=True,
                  comment="關聯發票"),
        sa.Column("payment_status", sa.String(30), server_default="pending",
                  comment="狀態: pending/partial/paid/overdue"),
        sa.Column("payment_date", sa.Date(), nullable=True, comment="實際收款日期"),
        sa.Column("payment_amount", sa.Numeric(15, 2), nullable=True, comment="實際收到金額"),
        sa.Column("notes", sa.Text(), nullable=True, comment="備註"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_erp_billings_id", "erp_billings", ["id"])
    op.create_index("ix_erp_billings_erp_quotation_id", "erp_billings", ["erp_quotation_id"])
    op.create_index("ix_erp_billings_invoice_id", "erp_billings", ["invoice_id"])
    op.create_index("ix_erp_billings_payment_status", "erp_billings", ["payment_status"])

    # === erp_vendor_payables ===
    op.create_table(
        "erp_vendor_payables",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("erp_quotation_id", sa.Integer(),
                  sa.ForeignKey("erp_quotations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vendor_name", sa.String(200), nullable=False, comment="廠商名稱"),
        sa.Column("vendor_code", sa.String(50), nullable=True,
                  comment="廠商代碼 (軟參照 partner_vendors.vendor_code)"),
        sa.Column("payable_amount", sa.Numeric(15, 2), nullable=False, comment="應付金額"),
        sa.Column("description", sa.String(300), nullable=True, comment="項目說明"),
        sa.Column("due_date", sa.Date(), nullable=True, comment="應付日期"),
        sa.Column("paid_date", sa.Date(), nullable=True, comment="實際付款日期"),
        sa.Column("paid_amount", sa.Numeric(15, 2), nullable=True, comment="實際付款金額"),
        sa.Column("payment_status", sa.String(30), server_default="unpaid",
                  comment="狀態: unpaid/partial/paid"),
        sa.Column("invoice_number", sa.String(50), nullable=True, comment="廠商發票號碼"),
        sa.Column("notes", sa.Text(), nullable=True, comment="備註"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_erp_vendor_payables_id", "erp_vendor_payables", ["id"])
    op.create_index("ix_erp_vendor_payables_erp_quotation_id", "erp_vendor_payables", ["erp_quotation_id"])
    op.create_index("ix_erp_vendor_payables_vendor_code", "erp_vendor_payables", ["vendor_code"])
    op.create_index("ix_erp_vendor_payables_payment_status", "erp_vendor_payables", ["payment_status"])


def downgrade() -> None:
    op.drop_table("erp_vendor_payables")
    op.drop_table("erp_billings")
    op.drop_table("erp_invoices")
    op.drop_table("erp_quotations")
