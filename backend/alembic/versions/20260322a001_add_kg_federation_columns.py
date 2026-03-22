"""add_kg_federation_columns

跨專案知識圖譜聯邦 (KG Federation):
- canonical_entities 新增: source_project, external_id, external_meta
- entity_relationships 新增: source_project
- 新增 unique constraint + index

Revision ID: 20260322a001
Revises: 20260321a001
Create Date: 2026-03-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '20260322a001'
down_revision: Union[str, None] = '20260321a001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === canonical_entities: 新增聯邦欄位 ===
    op.add_column('canonical_entities', sa.Column(
        'source_project', sa.String(50), nullable=False,
        server_default='ck-missive',
        comment='來源專案: ck-missive | ck-lvrland | ck-tunnel',
    ))
    op.add_column('canonical_entities', sa.Column(
        'external_id', sa.String(255), nullable=True,
        comment='來源專案的原始 ID (UUID/land_no14/etc)',
    ))
    op.add_column('canonical_entities', sa.Column(
        'external_meta', JSONB, nullable=True,
        server_default='{}',
        comment='來源專案的附加元資料 (座標/嚴重度/分區/etc)',
    ))

    # Index on source_project
    op.create_index(
        'ix_canonical_entity_source_project',
        'canonical_entities', ['source_project'],
    )
    # Composite index for federation lookups
    op.create_index(
        'ix_canonical_entity_source_ext',
        'canonical_entities', ['source_project', 'external_id'],
    )
    # Unique constraint: same external entity cannot be contributed twice
    op.create_unique_constraint(
        'uq_source_ext_type',
        'canonical_entities',
        ['source_project', 'external_id', 'entity_type'],
    )

    # === entity_relationships: 新增聯邦欄位 ===
    op.add_column('entity_relationships', sa.Column(
        'source_project', sa.String(50), nullable=False,
        server_default='ck-missive',
        comment='建立此關係的來源專案',
    ))
    op.create_index(
        'ix_entity_relationship_source_project',
        'entity_relationships', ['source_project'],
    )


def downgrade() -> None:
    # entity_relationships
    op.drop_index('ix_entity_relationship_source_project', table_name='entity_relationships')
    op.drop_column('entity_relationships', 'source_project')

    # canonical_entities
    op.drop_constraint('uq_source_ext_type', 'canonical_entities', type_='unique')
    op.drop_index('ix_canonical_entity_source_ext', table_name='canonical_entities')
    op.drop_index('ix_canonical_entity_source_project', table_name='canonical_entities')
    op.drop_column('canonical_entities', 'external_meta')
    op.drop_column('canonical_entities', 'external_id')
    op.drop_column('canonical_entities', 'source_project')
