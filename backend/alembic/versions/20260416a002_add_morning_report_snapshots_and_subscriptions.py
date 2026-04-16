"""add morning_report_snapshots + user_morning_report_subscriptions

Revision ID: 20260416a002
Revises: 20260416a001
Create Date: 2026-04-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260416a002'
down_revision: Union[str, Sequence[str], None] = '20260416a001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # B4: 晨報歷史快照 — 每日產生時寫入，供回顧 + LLM 訓練樣本累積
    op.create_table(
        'morning_report_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('report_date', sa.Date(), nullable=False, unique=True, index=True,
                  comment='晨報日期 (Asia/Taipei)，唯一鍵避免同日覆蓋'),
        sa.Column('sections_json', sa.JSON(), nullable=False,
                  comment='generate_report() 原始資料 JSON'),
        sa.Column('summary_text', sa.Text(), nullable=False),
        sa.Column('summary_length', sa.Integer(), nullable=False),
        sa.Column('sections_count', sa.Integer(), nullable=False),
        sa.Column('generator_version', sa.String(length=32), nullable=True,
                  comment='晨報生成器版本，供歷史比對'),
        sa.Column('generated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # B1: 使用者晨報訂閱 — 支援 per-user 分發
    op.create_table(
        'user_morning_report_subscriptions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=True, index=True,
                  comment='關聯用戶，NULL 表示為 admin fallback 訂閱'),
        sa.Column('display_name', sa.String(length=64), nullable=True,
                  comment='訂閱顯示名稱 (如 "專案經理 Aaron")'),
        sa.Column('channel', sa.String(length=32), nullable=False,
                  comment='telegram/line/discord/email'),
        sa.Column('channel_recipient', sa.String(length=128), nullable=False,
                  comment='chat_id / user_id / email'),
        sa.Column('sections', sa.String(length=255), nullable=False,
                  server_default='dispatch,meeting,site_visit,missing',
                  comment='CSV 選取 sections；all 表示全部'),
        sa.Column('handler_filter', sa.String(length=64), nullable=True,
                  comment='僅推送指定承辦人的 dispatch（NULL=不過濾）'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('channel', 'channel_recipient',
                            name='uq_morning_sub_channel_recipient'),
    )


def downgrade() -> None:
    op.drop_table('user_morning_report_subscriptions')
    op.drop_table('morning_report_snapshots')
