"""add normalized sender/receiver, keywords, and agency enhancement columns

Revision ID: 20260313a001
Revises: 20260312a001
Create Date: 2026-03-13 11:09:41.923954

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260313a001'
down_revision: Union[str, Sequence[str], None] = '20260312a001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # === documents 表：正規化發文/受文單位 + 副本受文 ===
    op.add_column('documents', sa.Column(
        'normalized_sender', sa.String(200), nullable=True,
        comment='正規化發文單位（去除統編前綴、換行、括號代碼）',
    ))
    op.add_column('documents', sa.Column(
        'normalized_receiver', sa.String(200), nullable=True,
        comment='正規化受文單位（主要受文者，去除多餘格式）',
    ))
    op.add_column('documents', sa.Column(
        'cc_receivers', sa.Text, nullable=True,
        comment='副本受文單位（JSON 陣列字串，管道分隔的多受文者拆分）',
    ))
    op.add_column('documents', sa.Column(
        'keywords', sa.Text(), nullable=True,
        comment='AI 提取關鍵字（JSON 陣列）',
    ))

    op.create_index('ix_documents_normalized_sender', 'documents', ['normalized_sender'])
    op.create_index('ix_documents_normalized_receiver', 'documents', ['normalized_receiver'])

    # === government_agencies 表：增強欄位 ===
    op.add_column('government_agencies', sa.Column(
        'tax_id', sa.String(20), nullable=True,
        comment='統一編號（如 EB50819619）',
    ))
    op.add_column('government_agencies', sa.Column(
        'is_self', sa.Boolean, server_default='false', nullable=False,
        comment='是否為本公司（乾坤測繪）',
    ))
    op.add_column('government_agencies', sa.Column(
        'parent_agency_id', sa.Integer,
        sa.ForeignKey('government_agencies.id', ondelete='SET NULL'),
        nullable=True,
        comment='上級機關 ID（用於階層折疊）',
    ))

    op.create_index('ix_government_agencies_tax_id', 'government_agencies', ['tax_id'], unique=True)

    # === canonical_entities 表：結構化 FK 連結 ===
    op.add_column('canonical_entities', sa.Column(
        'linked_agency_id', sa.Integer,
        sa.ForeignKey('government_agencies.id', ondelete='SET NULL'),
        nullable=True,
        comment='對應的 government_agencies.id（NER 實體 → 結構化機關）',
    ))
    op.add_column('canonical_entities', sa.Column(
        'linked_project_id', sa.Integer,
        sa.ForeignKey('taoyuan_projects.id', ondelete='SET NULL'),
        nullable=True,
        comment='對應的 taoyuan_projects.id（NER 實體 → 結構化工程）',
    ))

    op.create_index('ix_canonical_entities_linked_agency', 'canonical_entities', ['linked_agency_id'])
    op.create_index('ix_canonical_entities_linked_project', 'canonical_entities', ['linked_project_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # canonical_entities
    op.drop_index('ix_canonical_entities_linked_project', 'canonical_entities')
    op.drop_index('ix_canonical_entities_linked_agency', 'canonical_entities')
    op.drop_column('canonical_entities', 'linked_project_id')
    op.drop_column('canonical_entities', 'linked_agency_id')

    # government_agencies
    op.drop_index('ix_government_agencies_tax_id', 'government_agencies')
    op.drop_column('government_agencies', 'parent_agency_id')
    op.drop_column('government_agencies', 'is_self')
    op.drop_column('government_agencies', 'tax_id')

    # documents
    op.drop_column('documents', 'keywords')
    op.drop_index('ix_documents_normalized_receiver', 'documents')
    op.drop_index('ix_documents_normalized_sender', 'documents')
    op.drop_column('documents', 'cc_receivers')
    op.drop_column('documents', 'normalized_receiver')
    op.drop_column('documents', 'normalized_sender')
