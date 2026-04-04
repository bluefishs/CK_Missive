"""add attribution_type to expense_invoices

Revision ID: 20260404a001
Revises: 7d912ff05830
Create Date: 2026-04-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '20260404a001'
down_revision: Union[str, Sequence[str], None] = '7d912ff05830'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('expense_invoices', sa.Column(
        'attribution_type', sa.String(20), nullable=False,
        server_default='none', comment='歸屬類型: project/operational/none'))
    op.add_column('expense_invoices', sa.Column(
        'operational_account_id', sa.Integer(), nullable=True,
        comment='營運帳目 (attribution_type=operational)'))
    op.create_foreign_key(
        'fk_expense_operational_account',
        'expense_invoices', 'operational_accounts',
        ['operational_account_id'], ['id'],
        ondelete='SET NULL')
    op.create_index('ix_expense_invoices_attribution_type', 'expense_invoices', ['attribution_type'])
    # 回填：有 case_code 的設為 project
    op.execute("UPDATE expense_invoices SET attribution_type = 'project' WHERE case_code IS NOT NULL")


def downgrade() -> None:
    op.drop_index('ix_expense_invoices_attribution_type', 'expense_invoices')
    op.drop_constraint('fk_expense_operational_account', 'expense_invoices', type_='foreignkey')
    op.drop_column('expense_invoices', 'operational_account_id')
    op.drop_column('expense_invoices', 'attribution_type')
