"""Allow null document_id in calendar events

允許行事曆事件不關聯公文，支援獨立事件建立

Revision ID: allow_null_doc_id
Revises: add_dispatch_format_and_attachment
Create Date: 2026-01-06
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'allow_null_doc_id'
down_revision = 'add_dispatch_format_and_attachment'
branch_labels = None
depends_on = None


def upgrade():
    """修改 document_calendar_events 表的 document_id 欄位為可空"""
    # 1. 移除原本的外鍵約束（如果存在）
    try:
        op.drop_constraint(
            'document_calendar_events_document_id_fkey',
            'document_calendar_events',
            type_='foreignkey'
        )
    except Exception:
        pass  # 如果約束不存在，忽略錯誤

    # 2. 修改欄位為可空
    op.alter_column(
        'document_calendar_events',
        'document_id',
        existing_type=sa.Integer(),
        nullable=True
    )

    # 3. 重新建立外鍵約束（使用 SET NULL 刪除行為）
    op.create_foreign_key(
        'document_calendar_events_document_id_fkey',
        'document_calendar_events',
        'documents',
        ['document_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    """還原 document_id 為必填欄位"""
    # 1. 移除外鍵約束
    op.drop_constraint(
        'document_calendar_events_document_id_fkey',
        'document_calendar_events',
        type_='foreignkey'
    )

    # 2. 將 NULL 值設為預設值（防止資料遺失）
    op.execute("""
        UPDATE document_calendar_events
        SET document_id = (SELECT id FROM documents LIMIT 1)
        WHERE document_id IS NULL
    """)

    # 3. 修改欄位為必填
    op.alter_column(
        'document_calendar_events',
        'document_id',
        existing_type=sa.Integer(),
        nullable=False
    )

    # 4. 重新建立外鍵約束（使用 CASCADE 刪除行為）
    op.create_foreign_key(
        'document_calendar_events_document_id_fkey',
        'document_calendar_events',
        'documents',
        ['document_id'],
        ['id'],
        ondelete='CASCADE'
    )
