"""add operational account tables

Revision ID: 20260331a002
Revises: 20260331a001
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa

revision = '20260331a002'
down_revision = '20260331a001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'operational_accounts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('account_code', sa.String(30), unique=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(30), nullable=False),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('budget_limit', sa.Numeric(15, 2), server_default='0'),
        sa.Column('department', sa.String(100)),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('owner_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_operational_accounts_account_code', 'operational_accounts', ['account_code'], unique=True)
    op.create_index('ix_operational_accounts_category', 'operational_accounts', ['category'])
    op.create_index('ix_operational_accounts_fiscal_year', 'operational_accounts', ['fiscal_year'])
    op.create_index('ix_operational_accounts_status', 'operational_accounts', ['status'])
    op.create_index('ix_operational_accounts_owner_id', 'operational_accounts', ['owner_id'])

    op.create_table(
        'operational_expenses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('account_id', sa.Integer(),
                  sa.ForeignKey('operational_accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('expense_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('description', sa.String(500)),
        sa.Column('category', sa.String(50)),
        sa.Column('expense_invoice_id', sa.Integer(),
                  sa.ForeignKey('expense_invoices.id', ondelete='SET NULL')),
        sa.Column('asset_id', sa.Integer(),
                  sa.ForeignKey('assets.id', ondelete='SET NULL')),
        sa.Column('approval_status', sa.String(20), server_default='pending'),
        sa.Column('approved_by', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('approved_at', sa.DateTime()),
        sa.Column('created_by', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_operational_expenses_account_id', 'operational_expenses', ['account_id'])
    op.create_index('ix_operational_expenses_expense_invoice_id', 'operational_expenses', ['expense_invoice_id'])
    op.create_index('ix_operational_expenses_asset_id', 'operational_expenses', ['asset_id'])


def downgrade():
    op.drop_table('operational_expenses')
    op.drop_table('operational_accounts')
