"""add voucher_type to expense_invoices

Revision ID: 20260404b001
Create Date: 2026-04-04
"""
from alembic import op
import sqlalchemy as sa

revision = '20260404b001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'expense_invoices',
        sa.Column('voucher_type', sa.String(20), nullable=False,
                  server_default='invoice',
                  comment='憑證類型: invoice/receipt/ticket/utility/other')
    )
    # 放寬 inv_num unique 約束為 (voucher_type, inv_num) 組合唯一
    # 但先保留原有 unique 避免破壞


def downgrade() -> None:
    op.drop_column('expense_invoices', 'voucher_type')
