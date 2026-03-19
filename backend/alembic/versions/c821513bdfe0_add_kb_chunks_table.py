"""add_kb_chunks_table

Revision ID: c821513bdfe0
Revises: 7e898cff87c7
Create Date: 2026-03-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c821513bdfe0'
down_revision: Union[str, Sequence[str], None] = '7e898cff87c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'kb_chunks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('file_path', sa.String(length=500), nullable=False, comment='相對路徑 e.g. knowledge-map/api/overview.md'),
        sa.Column('filename', sa.String(length=200), nullable=False, comment='檔案名稱'),
        sa.Column('section_title', sa.String(length=500), nullable=True, comment='章節標題'),
        sa.Column('content', sa.Text(), nullable=False, comment='分段文字內容'),
        sa.Column('chunk_index', sa.Integer(), server_default='0', comment='同檔案內的分段索引'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='建立時間'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), comment='更新時間'),
        comment='知識庫 Markdown 文件分段 Embedding 表',
    )
    op.create_index('ix_kb_chunks_file_path', 'kb_chunks', ['file_path'])
    op.create_index('ix_kb_chunks_file_path_idx', 'kb_chunks', ['file_path', 'chunk_index'])

    # Add pgvector embedding column if extension is available
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
    ))
    if result.fetchone():
        op.execute(
            "ALTER TABLE kb_chunks ADD COLUMN embedding vector(768)"
        )
        op.execute(
            "COMMENT ON COLUMN kb_chunks.embedding IS 'nomic-embed-text 768D 向量嵌入'"
        )


def downgrade() -> None:
    op.drop_table('kb_chunks')
