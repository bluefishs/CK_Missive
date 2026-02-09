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
    1. 嘗試啟用 vector 擴展 (若不可用則跳過整個遷移)
    2. 新增 embedding 欄位 (vector(384))
    3. 建立 ivfflat 索引 (cosine distance)
    """
    # 1. 檢查 pgvector 擴展是否可安裝（不觸發交易失敗）
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"
    ))
    if result.scalar() is None:
        import logging
        logging.getLogger("alembic").warning(
            "⚠️ pgvector 擴展不可用，跳過 embedding 欄位建立。"
            "如需語意搜尋功能，請使用 pgvector/pgvector:pg15 Docker 映像。"
        )
        return

    # 啟用 pgvector 擴展
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
