"""add asset management tables

Revision ID: 20260331a001
Revises: d2a6fc75e0d0
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa

revision = '20260331a001'
down_revision = 'd2a6fc75e0d0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'assets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('asset_code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('brand', sa.String(100)),
        sa.Column('model', sa.String(100)),
        sa.Column('serial_number', sa.String(100)),
        sa.Column('purchase_date', sa.Date()),
        sa.Column('purchase_amount', sa.Numeric(15, 2), server_default='0'),
        sa.Column('current_value', sa.Numeric(15, 2)),
        sa.Column('depreciation_rate', sa.Numeric(5, 2), server_default='0'),
        sa.Column('expense_invoice_id', sa.Integer(),
                  sa.ForeignKey('expense_invoices.id', ondelete='SET NULL')),
        sa.Column('case_code', sa.String(50)),
        sa.Column('status', sa.String(30), server_default='in_use'),
        sa.Column('location', sa.String(200)),
        sa.Column('custodian', sa.String(100)),
        sa.Column('notes', sa.Text()),
        sa.Column('created_by', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_assets_asset_code', 'assets', ['asset_code'])
    op.create_index('ix_assets_category', 'assets', ['category'])
    op.create_index('ix_assets_status', 'assets', ['status'])
    op.create_index('ix_assets_case_code', 'assets', ['case_code'])
    op.create_index('ix_assets_expense_invoice_id', 'assets', ['expense_invoice_id'])

    op.create_table(
        'asset_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('asset_id', sa.Integer(),
                  sa.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action', sa.String(30), nullable=False),
        sa.Column('action_date', sa.Date(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('cost', sa.Numeric(15, 2), server_default='0'),
        sa.Column('expense_invoice_id', sa.Integer(),
                  sa.ForeignKey('expense_invoices.id', ondelete='SET NULL')),
        sa.Column('from_location', sa.String(200)),
        sa.Column('to_location', sa.String(200)),
        sa.Column('operator', sa.String(100)),
        sa.Column('notes', sa.Text()),
        sa.Column('created_by', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_asset_logs_asset_id', 'asset_logs', ['asset_id'])
    op.create_index('ix_asset_logs_action', 'asset_logs', ['action'])
    op.create_index('ix_asset_logs_expense_invoice_id', 'asset_logs', ['expense_invoice_id'])


def downgrade():
    op.drop_table('asset_logs')
    op.drop_table('assets')
