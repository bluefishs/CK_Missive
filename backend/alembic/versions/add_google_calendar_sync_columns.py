"""add google calendar sync columns to document_calendar_events

Revision ID: add_google_sync_cols
Revises:
Create Date: 2026-01-08

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_google_sync_cols'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 新增 google_event_id 欄位
    op.add_column(
        'document_calendar_events',
        sa.Column('google_event_id', sa.String(255), nullable=True, comment='Google Calendar 事件 ID')
    )

    # 新增 google_sync_status 欄位
    op.add_column(
        'document_calendar_events',
        sa.Column('google_sync_status', sa.String(50), server_default='pending', comment='同步狀態: pending/synced/failed')
    )

    # 建立索引
    op.create_index('ix_document_calendar_events_google_event_id', 'document_calendar_events', ['google_event_id'])


def downgrade() -> None:
    op.drop_index('ix_document_calendar_events_google_event_id', 'document_calendar_events')
    op.drop_column('document_calendar_events', 'google_sync_status')
    op.drop_column('document_calendar_events', 'google_event_id')
