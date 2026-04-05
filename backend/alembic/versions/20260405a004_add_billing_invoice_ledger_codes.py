"""add billing_code, invoice_ref, ledger_code (ADR-0013 Phase 2)

Revision ID: 20260405a004
Revises: 20260405a003
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260405a004"
down_revision = "20260405a003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- ERPBilling: billing_code ---
    op.add_column(
        "erp_billings",
        sa.Column("billing_code", sa.String(20), nullable=True, comment="系統請款編碼 BL_{yyyy}_{NNN}"),
    )
    op.create_index("ix_erp_billings_billing_code", "erp_billings", ["billing_code"], unique=True)

    # --- ERPInvoice: invoice_ref ---
    op.add_column(
        "erp_invoices",
        sa.Column("invoice_ref", sa.String(20), nullable=True, comment="系統發票參照碼 IV_{yyyy}_{NNN}"),
    )
    op.create_index("ix_erp_invoices_invoice_ref", "erp_invoices", ["invoice_ref"], unique=True)

    # --- FinanceLedger: ledger_code ---
    op.add_column(
        "finance_ledgers",
        sa.Column("ledger_code", sa.String(20), nullable=True, comment="帳本編碼 FL_{yyyy}_{NNNNN}"),
    )
    op.create_index("ix_finance_ledgers_ledger_code", "finance_ledgers", ["ledger_code"], unique=True)

    # --- Backfill existing rows with sequential codes ---
    # ERPBilling: BL_{year}_NNN based on created_at year
    op.execute("""
        UPDATE erp_billings
        SET billing_code = sub.code
        FROM (
            SELECT id,
                   'BL_' || EXTRACT(YEAR FROM created_at)::TEXT || '_' ||
                   LPAD(ROW_NUMBER() OVER (
                       PARTITION BY EXTRACT(YEAR FROM created_at)
                       ORDER BY created_at, id
                   )::TEXT, 3, '0') AS code
            FROM erp_billings
            WHERE billing_code IS NULL
        ) sub
        WHERE erp_billings.id = sub.id
    """)

    # ERPInvoice: IV_{year}_NNN based on created_at year
    op.execute("""
        UPDATE erp_invoices
        SET invoice_ref = sub.code
        FROM (
            SELECT id,
                   'IV_' || EXTRACT(YEAR FROM created_at)::TEXT || '_' ||
                   LPAD(ROW_NUMBER() OVER (
                       PARTITION BY EXTRACT(YEAR FROM created_at)
                       ORDER BY created_at, id
                   )::TEXT, 3, '0') AS code
            FROM erp_invoices
            WHERE invoice_ref IS NULL
        ) sub
        WHERE erp_invoices.id = sub.id
    """)

    # FinanceLedger: FL_{year}_NNNNN based on created_at year
    op.execute("""
        UPDATE finance_ledgers
        SET ledger_code = sub.code
        FROM (
            SELECT id,
                   'FL_' || EXTRACT(YEAR FROM created_at)::TEXT || '_' ||
                   LPAD(ROW_NUMBER() OVER (
                       PARTITION BY EXTRACT(YEAR FROM created_at)
                       ORDER BY created_at, id
                   )::TEXT, 5, '0') AS code
            FROM finance_ledgers
            WHERE ledger_code IS NULL
        ) sub
        WHERE finance_ledgers.id = sub.id
    """)


def downgrade() -> None:
    op.drop_index("ix_finance_ledgers_ledger_code", table_name="finance_ledgers")
    op.drop_column("finance_ledgers", "ledger_code")

    op.drop_index("ix_erp_invoices_invoice_ref", table_name="erp_invoices")
    op.drop_column("erp_invoices", "invoice_ref")

    op.drop_index("ix_erp_billings_billing_code", table_name="erp_billings")
    op.drop_column("erp_billings", "billing_code")
