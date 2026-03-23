"""Add vendor_id FK to expense_invoices, erp_vendor_payables, finance_ledgers

Establishes hard FK references from ERP/Finance tables to partner_vendors,
replacing soft string-based references (vendor_code, seller_ban).
Existing vendor_code/seller_ban columns are preserved for backward compatibility.

Backfill: vendor_id is populated from vendor_code matches where possible.

Revision ID: 20260322a003
Revises: 20260322a002
Create Date: 2026-03-22
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "20260322a003"
down_revision = "20260322a002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. erp_vendor_payables: add vendor_id FK
    op.add_column(
        "erp_vendor_payables",
        sa.Column(
            "vendor_id",
            sa.Integer(),
            sa.ForeignKey("partner_vendors.id", ondelete="SET NULL"),
            nullable=True,
            comment="廠商 ID (強參照)",
        ),
    )
    op.create_index("ix_erp_vendor_payables_vendor_id", "erp_vendor_payables", ["vendor_id"])

    # 2. expense_invoices: add vendor_id FK
    op.add_column(
        "expense_invoices",
        sa.Column(
            "vendor_id",
            sa.Integer(),
            sa.ForeignKey("partner_vendors.id", ondelete="SET NULL"),
            nullable=True,
            comment="廠商 ID (由 seller_ban 自動配對)",
        ),
    )
    op.create_index("ix_expense_invoices_vendor_id", "expense_invoices", ["vendor_id"])

    # 3. finance_ledgers: add vendor_id FK
    op.add_column(
        "finance_ledgers",
        sa.Column(
            "vendor_id",
            sa.Integer(),
            sa.ForeignKey("partner_vendors.id", ondelete="SET NULL"),
            nullable=True,
            comment="廠商 ID (應付帳款來源)",
        ),
    )
    op.create_index("ix_finance_ledgers_vendor_id", "finance_ledgers", ["vendor_id"])

    # 4. Backfill: erp_vendor_payables.vendor_id from vendor_code match
    op.execute("""
        UPDATE erp_vendor_payables evp
        SET vendor_id = pv.id
        FROM partner_vendors pv
        WHERE evp.vendor_code = pv.vendor_code
          AND evp.vendor_code IS NOT NULL
          AND evp.vendor_id IS NULL
    """)

    # 5. Backfill: finance_ledgers.vendor_id from erp_vendor_payable source
    op.execute("""
        UPDATE finance_ledgers fl
        SET vendor_id = evp.vendor_id
        FROM erp_vendor_payables evp
        WHERE fl.source_type = 'erp_vendor_payable'
          AND fl.source_id = evp.id
          AND evp.vendor_id IS NOT NULL
          AND fl.vendor_id IS NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_finance_ledgers_vendor_id", table_name="finance_ledgers")
    op.drop_column("finance_ledgers", "vendor_id")

    op.drop_index("ix_expense_invoices_vendor_id", table_name="expense_invoices")
    op.drop_column("expense_invoices", "vendor_id")

    op.drop_index("ix_erp_vendor_payables_vendor_id", table_name="erp_vendor_payables")
    op.drop_column("erp_vendor_payables", "vendor_id")
