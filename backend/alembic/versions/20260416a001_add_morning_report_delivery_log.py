"""add morning_report_delivery_log

Revision ID: 20260416a001
Revises: 20260409a001
Create Date: 2026-04-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260416a001'
down_revision: Union[str, Sequence[str], None] = '20260409a001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'morning_report_delivery_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('report_date', sa.Date(), nullable=False, index=True,
                  comment='晨報所屬日期 (Asia/Taipei)'),
        sa.Column('channel', sa.String(length=32), nullable=False,
                  comment='通道：telegram/line/discord/manual'),
        sa.Column('recipient', sa.String(length=128), nullable=True,
                  comment='收件人識別 (chat_id / user_id / email)'),
        sa.Column('status', sa.String(length=16), nullable=False, index=True,
                  comment='success / failed / skipped'),
        sa.Column('error_msg', sa.Text(), nullable=True),
        sa.Column('summary_length', sa.Integer(), nullable=True,
                  comment='推送內容字元數'),
        sa.Column('sections_count', sa.Integer(), nullable=True,
                  comment='包含多少 sections 有內容'),
        sa.Column('trigger_source', sa.String(length=16), nullable=False,
                  server_default='scheduler',
                  comment='scheduler / manual / api'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Index('ix_morning_report_delivery_log_date_channel',
                 'report_date', 'channel'),
    )


def downgrade() -> None:
    op.drop_index('ix_morning_report_delivery_log_date_channel',
                  table_name='morning_report_delivery_log')
    op.drop_table('morning_report_delivery_log')
