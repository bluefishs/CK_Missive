"""increase dispatch work_type column length to 200

Revision ID: increase_work_type_len
Revises: update_status_suspend
Create Date: 2026-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'increase_work_type_len'
down_revision: Union[str, None] = 'update_status_suspend'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """增加 work_type 欄位長度從 50 到 200，支援多選作業類別"""
    op.alter_column(
        'taoyuan_dispatch_orders',
        'work_type',
        existing_type=sa.String(50),
        type_=sa.String(200),
        existing_nullable=True,
        comment='作業類別(可多選,逗號分隔)'
    )


def downgrade() -> None:
    """縮減 work_type 欄位長度回 50"""
    op.alter_column(
        'taoyuan_dispatch_orders',
        'work_type',
        existing_type=sa.String(200),
        type_=sa.String(50),
        existing_nullable=True,
        comment='作業類別'
    )
