"""add_contact_note_to_dispatch

Revision ID: a1b2c3d4e5f6
Revises: 78a02098c4cd
Create Date: 2026-01-20

新增「聯絡備註」欄位到派工紀錄表 (taoyuan_dispatch_orders)
對應原始需求欄位 #13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '78a02098c4cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增 contact_note 欄位"""
    op.add_column('taoyuan_dispatch_orders',
        sa.Column('contact_note', sa.String(500), nullable=True, comment='聯絡備註'))


def downgrade() -> None:
    """移除 contact_note 欄位"""
    op.drop_column('taoyuan_dispatch_orders', 'contact_note')
