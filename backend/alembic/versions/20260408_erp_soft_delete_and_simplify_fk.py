"""erp: quotation soft delete + remove billing.invoice_id circular FK

1. ADD COLUMN erp_quotations.deleted_at (nullable DateTime, indexed)
2. DROP COLUMN erp_billings.invoice_id (circular FK removed;
   Invoice→Billing via erp_invoices.billing_id is the single direction)

Revision ID: 20260408a001
Revises: 20260406a001
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260408a001'
down_revision = '20260406a001'
branch_labels = None
depends_on = None


def upgrade():
    # --- Task 1: ERPQuotation soft delete ---
    op.add_column(
        'erp_quotations',
        sa.Column(
            'deleted_at',
            sa.DateTime(),
            nullable=True,
            comment='軟刪除時間 (NULL=未刪除)',
        ),
    )
    op.create_index(
        'ix_erp_quotations_deleted_at',
        'erp_quotations',
        ['deleted_at'],
    )

    # --- Task 2: Remove circular FK billing.invoice_id ---
    # Drop the index first, then the FK constraint and column
    op.drop_index('ix_erp_billings_invoice_id', table_name='erp_billings')
    op.drop_constraint(
        'erp_billings_invoice_id_fkey',
        'erp_billings',
        type_='foreignkey',
    )
    op.drop_column('erp_billings', 'invoice_id')


def downgrade():
    # --- Restore billing.invoice_id ---
    op.add_column(
        'erp_billings',
        sa.Column(
            'invoice_id',
            sa.Integer(),
            sa.ForeignKey('erp_invoices.id', ondelete='SET NULL'),
            nullable=True,
            comment='關聯發票',
        ),
    )
    op.create_index(
        'ix_erp_billings_invoice_id',
        'erp_billings',
        ['invoice_id'],
    )

    # --- Remove deleted_at ---
    op.drop_index('ix_erp_quotations_deleted_at', table_name='erp_quotations')
    op.drop_column('erp_quotations', 'deleted_at')
