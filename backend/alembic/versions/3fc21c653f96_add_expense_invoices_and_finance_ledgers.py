"""add_expense_invoices_and_finance_ledgers

Revision ID: 3fc21c653f96
Revises: c821513bdfe0
Create Date: 2026-03-21 16:30:13.242069

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3fc21c653f96'
down_revision: Union[str, Sequence[str], None] = 'c821513bdfe0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增費用報銷發票 + 統一帳本 + 發票明細 三表"""
    # 1. expense_invoices — 費用報銷發票
    op.create_table('expense_invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('inv_num', sa.String(length=20), nullable=False, comment='發票號碼 (如 AB12345678)'),
        sa.Column('date', sa.Date(), nullable=False, comment='開立日期 (西元)'),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False, comment='總金額 (含稅)'),
        sa.Column('tax_amount', sa.Numeric(precision=15, scale=2), nullable=True, comment='稅額'),
        sa.Column('buyer_ban', sa.String(length=8), nullable=True, comment='買方統編'),
        sa.Column('seller_ban', sa.String(length=8), nullable=True, comment='賣方統編'),
        sa.Column('case_code', sa.String(length=50), nullable=True, comment='案號 (軟參照)，NULL=一般營運'),
        sa.Column('user_id', sa.Integer(), nullable=True, comment='上傳者/報銷人'),
        sa.Column('category', sa.String(length=50), nullable=True, comment='費用分類'),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False, comment='pending/processed/verified/rejected'),
        sa.Column('source', sa.String(length=20), server_default='manual', nullable=False, comment='qr_scan/manual/api/ocr'),
        sa.Column('source_image_path', sa.String(length=500), nullable=True, comment='原始圖檔路徑'),
        sa.Column('raw_qr_data', sa.Text(), nullable=True, comment='原始 QR Code 字串'),
        sa.Column('notes', sa.String(length=500), nullable=True, comment='備註'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_expense_invoices_id'), 'expense_invoices', ['id'], unique=False)
    op.create_index(op.f('ix_expense_invoices_inv_num'), 'expense_invoices', ['inv_num'], unique=True)
    op.create_index(op.f('ix_expense_invoices_case_code'), 'expense_invoices', ['case_code'], unique=False)

    # 2. finance_ledgers — 統一帳本
    op.create_table('finance_ledgers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_code', sa.String(length=50), nullable=True, comment='案號 (軟參照)，NULL=一般營運支出'),
        sa.Column('source_type', sa.String(length=30), server_default='manual', nullable=False, comment='manual/expense_invoice/erp_billing/erp_vendor_payable'),
        sa.Column('source_id', sa.Integer(), nullable=True, comment='來源記錄 ID'),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False, comment='金額'),
        sa.Column('entry_type', sa.String(length=20), nullable=False, comment='income/expense'),
        sa.Column('category', sa.String(length=50), nullable=True, comment='分類'),
        sa.Column('description', sa.String(length=500), nullable=True, comment='摘要說明'),
        sa.Column('user_id', sa.Integer(), nullable=True, comment='記帳人/經辦人'),
        sa.Column('transaction_date', sa.Date(), server_default=sa.text('CURRENT_DATE'), nullable=False, comment='交易日期'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_finance_ledgers_id'), 'finance_ledgers', ['id'], unique=False)
    op.create_index(op.f('ix_finance_ledgers_case_code'), 'finance_ledgers', ['case_code'], unique=False)

    # 3. expense_invoice_items — 發票品名明細
    op.create_table('expense_invoice_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('item_name', sa.String(length=200), nullable=False, comment='品名'),
        sa.Column('qty', sa.Numeric(precision=10, scale=2), server_default='1', nullable=False, comment='數量'),
        sa.Column('unit_price', sa.Numeric(precision=15, scale=2), nullable=False, comment='單價'),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False, comment='小計'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['expense_invoices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_expense_invoice_items_id'), 'expense_invoice_items', ['id'], unique=False)
    op.create_index(op.f('ix_expense_invoice_items_invoice_id'), 'expense_invoice_items', ['invoice_id'], unique=False)


def downgrade() -> None:
    """移除三表"""
    op.drop_table('expense_invoice_items')
    op.drop_table('finance_ledgers')
    op.drop_table('expense_invoices')
