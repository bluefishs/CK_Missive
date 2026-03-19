"""add ner_pending flag to documents

Revision ID: 20260313a003
Revises: 20260313a001
Create Date: 2026-03-13 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260313a003'
down_revision: Union[str, Sequence[str], None] = '20260313a001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 新增 ner_pending 欄位，預設 true（所有文件待處理）
    op.add_column('documents', sa.Column(
        'ner_pending', sa.Boolean(), server_default='true', nullable=False,
        comment='是否待 NER 提取',
    ))
    op.create_index('ix_documents_ner_pending', 'documents', ['ner_pending'])

    # 將已有 NER 提及的公文標記為已完成（ner_pending = false）
    op.execute("""
        UPDATE documents SET ner_pending = false
        WHERE id IN (
            SELECT DISTINCT document_id FROM document_entity_mentions
        )
    """)


def downgrade() -> None:
    op.drop_index('ix_documents_ner_pending', 'documents')
    op.drop_column('documents', 'ner_pending')
