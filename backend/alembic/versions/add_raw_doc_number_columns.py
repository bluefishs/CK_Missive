"""add raw doc number columns to dispatch orders

Revision ID: 20260304a002
Revises: 20260304a001
Create Date: 2026-03-04

派工單新增原始文號欄位，供匯入後批次重新關聯公文使用。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '20260304a002'
down_revision = '20260304a001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('taoyuan_dispatch_orders',
        sa.Column('agency_doc_number_raw', sa.String(500), nullable=True,
                   comment='匯入時的機關函文號原始值'))
    op.add_column('taoyuan_dispatch_orders',
        sa.Column('company_doc_number_raw', sa.String(500), nullable=True,
                   comment='匯入時的乾坤函文號原始值'))


def downgrade():
    op.drop_column('taoyuan_dispatch_orders', 'company_doc_number_raw')
    op.drop_column('taoyuan_dispatch_orders', 'agency_doc_number_raw')
