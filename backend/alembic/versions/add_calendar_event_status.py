"""add calendar event status column

Revision ID: add_calendar_event_status
Revises:
Create Date: 2026-01-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_calendar_event_status'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add status column to document_calendar_events table."""
    # 檢查欄位是否已存在
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'document_calendar_events' AND column_name = 'status'
    """))
    if result.fetchone() is None:
        op.add_column(
            'document_calendar_events',
            sa.Column('status', sa.String(50), server_default='pending',
                      comment='事件狀態: pending/completed/cancelled')
        )
        print("Added 'status' column to document_calendar_events")
    else:
        print("Column 'status' already exists, skipping")


def downgrade() -> None:
    """Remove status column from document_calendar_events table."""
    op.drop_column('document_calendar_events', 'status')
