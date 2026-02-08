"""新增 pgvector 向量嵌入欄位到 documents 表

啟用 pgvector 擴展，新增 embedding 欄位 (384 維)，
並建立 ivfflat 索引以加速向量相似度搜尋。

Revision ID: add_pgvector_embedding
Revises: add_password_reset
Create Date: 2026-02-08
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_pgvector_embedding'
down_revision = 'add_password_reset'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    啟用 pgvector 擴展並新增 embedding 欄位

    步驟：
    1. 啟用 vector 擴展 (CREATE EXTENSION IF NOT EXISTS)
    2. 新增 embedding 欄位 (vector(384))
    3. 建立 ivfflat 索引 (cosine distance)
    """
    # 1. 啟用 pgvector 擴展
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. 新增 embedding 欄位（冪等設計）
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'documents' AND column_name = 'embedding'
            ) THEN
                ALTER TABLE documents ADD COLUMN embedding vector(384);
                COMMENT ON COLUMN documents.embedding IS '文件向量嵌入 (nomic-embed-text, 384 維)';
            END IF;
        END $$;
    """)

    # 3. 建立 ivfflat 索引（用於加速向量搜尋）
    # 注意：ivfflat 需要表中有資料才能建立有效索引
    # lists 參數建議為 sqrt(rows)，100 適用於 ~10000 筆文件
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_documents_embedding
        ON documents USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)


def downgrade() -> None:
    """移除 embedding 欄位與索引"""
    op.execute("DROP INDEX IF EXISTS ix_documents_embedding")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'documents' AND column_name = 'embedding'
            ) THEN
                ALTER TABLE documents DROP COLUMN embedding;
            END IF;
        END $$;
    """)
    # 注意：不移除 vector 擴展，因為其他表可能也在使用
