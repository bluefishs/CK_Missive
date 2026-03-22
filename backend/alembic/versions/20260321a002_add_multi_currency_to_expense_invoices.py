"""add multi-currency columns to expense_invoices

Revision ID: 20260321a002
Revises: 20260322a001
Create Date: 2026-03-21

Phase 5-4: 多幣別支援 — currency, original_amount, exchange_rate
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '20260321a002'
down_revision = '20260322a001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('expense_invoices', sa.Column(
        'currency', sa.String(3), nullable=False, server_default='TWD',
        comment='幣別 (ISO 4217: TWD/USD/CNY/JPY/EUR)',
    ))
    op.add_column('expense_invoices', sa.Column(
        'original_amount', sa.Numeric(15, 2), nullable=True,
        comment='原始幣別金額 (非 TWD 時填入)',
    ))
    op.add_column('expense_invoices', sa.Column(
        'exchange_rate', sa.Numeric(10, 6), nullable=True,
        comment='匯率 (original_amount × exchange_rate = amount)',
    ))


def downgrade() -> None:
    op.drop_column('expense_invoices', 'exchange_rate')
    op.drop_column('expense_invoices', 'original_amount')
    op.drop_column('expense_invoices', 'currency')
