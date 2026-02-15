"""新增作業紀錄鏈式欄位 (document_id, parent_record_id, work_category)

支援鏈式時間軸功能：
- document_id: 統一公文關聯（替代雙欄位 incoming/outgoing）
- parent_record_id: 前序紀錄 ID（自引用外鍵）
- work_category: 新作業類別 (dispatch_notice/work_result/...)

Revision ID: add_chain_fields
Revises: add_dispatch_work_types
Create Date: 2026-02-13
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_chain_fields'
down_revision = 'add_dispatch_work_types'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 新增 document_id — 統一關聯公文（新格式）
    op.add_column('taoyuan_work_records', sa.Column(
        'document_id', sa.Integer(),
        sa.ForeignKey('documents.id', ondelete='SET NULL'),
        nullable=True,
        comment='關聯公文 (新格式，單一)',
    ))

    # 新增 parent_record_id — 鏈式前序紀錄
    op.add_column('taoyuan_work_records', sa.Column(
        'parent_record_id', sa.Integer(),
        sa.ForeignKey('taoyuan_work_records.id', ondelete='SET NULL'),
        nullable=True,
        comment='前序紀錄 ID (鏈式)',
    ))

    # 新增 work_category — 新作業類別
    op.add_column('taoyuan_work_records', sa.Column(
        'work_category', sa.String(50),
        nullable=True,
        comment='作業類別 (dispatch_notice/work_result/meeting_notice/meeting_record/survey_notice/survey_record/other)',
    ))

    # 建立索引
    op.create_index('ix_work_records_document_id', 'taoyuan_work_records', ['document_id'])
    op.create_index('ix_work_records_parent_record_id', 'taoyuan_work_records', ['parent_record_id'])
    op.create_index('ix_work_records_work_category', 'taoyuan_work_records', ['work_category'])


def downgrade() -> None:
    op.drop_index('ix_work_records_work_category', table_name='taoyuan_work_records')
    op.drop_index('ix_work_records_parent_record_id', table_name='taoyuan_work_records')
    op.drop_index('ix_work_records_document_id', table_name='taoyuan_work_records')
    op.drop_column('taoyuan_work_records', 'work_category')
    op.drop_column('taoyuan_work_records', 'parent_record_id')
    op.drop_column('taoyuan_work_records', 'document_id')
