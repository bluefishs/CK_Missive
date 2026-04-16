"""add work_type_id to work_records + deadline to dispatch_work_types

Revision ID: 20260416a003
Revises: 20260416a002
Create Date: 2026-04-16

Phase 2 方案 A：work_record 歸屬到具體 work_type，支援 per-type 進度追蹤。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260416a003'
down_revision: Union[str, Sequence[str], None] = '20260416a002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # work_records 加 work_type_id（nullable，向後相容）
    op.add_column(
        'taoyuan_work_records',
        sa.Column('work_type_id', sa.Integer(),
                  sa.ForeignKey('taoyuan_dispatch_work_types.id', ondelete='SET NULL'),
                  nullable=True, index=True,
                  comment='所屬作業類別 (nullable=舊紀錄未歸屬)')
    )

    # dispatch_work_types 加 deadline（per-type 期限）
    op.add_column(
        'taoyuan_dispatch_work_types',
        sa.Column('deadline', sa.Date(), nullable=True,
                  comment='此作業類別的交付期限')
    )


def downgrade() -> None:
    op.drop_column('taoyuan_dispatch_work_types', 'deadline')
    op.drop_column('taoyuan_work_records', 'work_type_id')
