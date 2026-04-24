"""Calendar event source tracking (ADR-0026): work_record ↔ calendar 同步

Revision ID: 20260421a002
Revises: 20260421a001
Create Date: 2026-04-21

v5.8.0：document_calendar_events 加 source_type / source_id / dispatch_order_id
讓同一 work_record.deadline_date 可自動映射為 calendar event，避免重複設定。
"""
from alembic import op
import sqlalchemy as sa


revision = '20260421a002'
down_revision = '20260421a001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'document_calendar_events',
        sa.Column(
            'source_type', sa.String(30),
            server_default='document',
            nullable=False,
            comment="事件來源：document | work_record | manual",
        ),
    )
    op.add_column(
        'document_calendar_events',
        sa.Column(
            'source_id', sa.Integer(),
            nullable=True,
            comment="來源 ID（document.id 或 taoyuan_work_records.id）",
        ),
    )
    op.add_column(
        'document_calendar_events',
        sa.Column(
            'dispatch_order_id', sa.Integer(),
            nullable=True,
            comment="派工單 ID（當 source_type=work_record 或無 document 時使用）",
        ),
    )

    op.create_foreign_key(
        'fk_calendar_dispatch_order',
        'document_calendar_events', 'taoyuan_dispatch_orders',
        ['dispatch_order_id'], ['id'],
        ondelete='SET NULL',
    )

    # 同一 source 唯一：避免重複建立
    op.create_index(
        'uq_calendar_source',
        'document_calendar_events',
        ['source_type', 'source_id'],
        unique=True,
        postgresql_where=sa.text("source_type != 'manual' AND source_id IS NOT NULL"),
    )

    op.create_index(
        'ix_calendar_dispatch_order_id',
        'document_calendar_events',
        ['dispatch_order_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_calendar_dispatch_order_id', table_name='document_calendar_events')
    op.drop_index('uq_calendar_source', table_name='document_calendar_events')
    op.drop_constraint('fk_calendar_dispatch_order', 'document_calendar_events', type_='foreignkey')
    op.drop_column('document_calendar_events', 'dispatch_order_id')
    op.drop_column('document_calendar_events', 'source_id')
    op.drop_column('document_calendar_events', 'source_type')
