"""erp_quotation_items 加 item_no —— 工項項次可自填（1.1／1.2 小項）

Revision ID: 20260904a001
Revises: 20260903a001
Create Date: 2026-09-04

owner 2026-09-04「工項填列彈性，如有小項 1.1、1.2 等填報需求」：
此前項次由列序自動編「一、二、三」，沒有地方放層級。
NULL＝沿用自動編號，所以存量資料與輸出不變。
"""
from alembic import op
import sqlalchemy as sa

revision = '20260904a001'
down_revision = '20260903a001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('erp_quotation_items', sa.Column('item_no', sa.String(length=20), nullable=True,
                  comment='項次（自填，如 1.1；NULL＝自動 一、二、三）'))


def downgrade() -> None:
    op.drop_column('erp_quotation_items', 'item_no')
