"""update status suspend to not won

將專案狀態「暫停」更新為「未得標」

Revision ID: update_status_suspend
Revises:
Create Date: 2026-01-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'update_status_suspend'
down_revision: Union[str, None] = 'add_calendar_event_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """將「暫停」狀態更新為「未得標」"""
    # 更新 contract_projects 表中的 status 欄位
    op.execute("""
        UPDATE contract_projects
        SET status = '未得標'
        WHERE status = '暫停'
    """)


def downgrade() -> None:
    """還原：將「未得標」狀態更新回「暫停」"""
    op.execute("""
        UPDATE contract_projects
        SET status = '暫停'
        WHERE status = '未得標'
    """)
