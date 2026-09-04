"""users 加 phone —— 承辦同仁（服務人員）的聯絡電話

Revision ID: 20260904a002
Revises: 20260904a001
Create Date: 2026-09-04

owner 2026-09-04：「業務同仁依其系統登入資訊對應即可，/staff/:id 增列對應連絡電話」。
正式報價單的服務人員來自承辦指派→使用者，使用者此前只有 email 沒有電話。
"""
from alembic import op
import sqlalchemy as sa

revision = '20260904a002'
down_revision = '20260904a001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('phone', sa.String(length=30), nullable=True, comment='聯絡電話（報價單服務人員）'))


def downgrade() -> None:
    op.drop_column('users', 'phone')
