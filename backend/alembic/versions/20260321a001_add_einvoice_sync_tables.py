"""add_einvoice_sync_tables

新增電子發票同步功能:
- einvoice_sync_logs 表: 同步批次記錄
- expense_invoices 表: 新增 receipt_image_path, mof_invoice_track, mof_period, synced_at 欄位

Revision ID: 20260321a001
Revises: 3fc21c653f96
Create Date: 2026-03-21 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260321a001'
down_revision: Union[str, Sequence[str], None] = '3fc21c653f96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增電子發票同步表 + expense_invoices 欄位擴充"""

    # 1. einvoice_sync_logs — 同步批次記錄
    op.create_table('einvoice_sync_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('buyer_ban', sa.String(length=8), nullable=False, comment='查詢統編'),
        sa.Column('query_start', sa.Date(), nullable=False, comment='查詢起始日期'),
        sa.Column('query_end', sa.Date(), nullable=False, comment='查詢結束日期'),
        sa.Column('status', sa.String(length=20), server_default='running', nullable=False,
                  comment='running / success / partial / failed'),
        sa.Column('total_fetched', sa.Integer(), server_default='0', nullable=False,
                  comment='從 API 取得的發票數'),
        sa.Column('new_imported', sa.Integer(), server_default='0', nullable=False,
                  comment='新匯入系統的發票數'),
        sa.Column('skipped_duplicate', sa.Integer(), server_default='0', nullable=False,
                  comment='略過的重複發票數'),
        sa.Column('detail_fetched', sa.Integer(), server_default='0', nullable=False,
                  comment='成功抓取明細的發票數'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='錯誤訊息'),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True,
                  comment='同步開始時間'),
        sa.Column('completed_at', sa.DateTime(), nullable=True, comment='同步完成時間'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_einvoice_sync_logs_id'), 'einvoice_sync_logs', ['id'], unique=False)

    # 2. expense_invoices — 新增同步相關欄位
    op.add_column('expense_invoices',
        sa.Column('receipt_image_path', sa.String(length=500), nullable=True,
                  comment='收據影本路徑 (報帳員上傳)'))
    op.add_column('expense_invoices',
        sa.Column('mof_invoice_track', sa.String(length=2), nullable=True,
                  comment='財政部發票字軌 (如 AB)'))
    op.add_column('expense_invoices',
        sa.Column('mof_period', sa.String(length=5), nullable=True,
                  comment='發票期別 (如 11404, 民國年+月份)'))
    op.add_column('expense_invoices',
        sa.Column('synced_at', sa.DateTime(), nullable=True,
                  comment='財政部同步時間戳'))


def downgrade() -> None:
    """移除電子發票同步功能"""
    op.drop_column('expense_invoices', 'synced_at')
    op.drop_column('expense_invoices', 'mof_period')
    op.drop_column('expense_invoices', 'mof_invoice_track')
    op.drop_column('expense_invoices', 'receipt_image_path')
    op.drop_index(op.f('ix_einvoice_sync_logs_id'), table_name='einvoice_sync_logs')
    op.drop_table('einvoice_sync_logs')
