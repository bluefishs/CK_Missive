"""新增 query_embedding 欄位到 ai_search_history 表

用於 Layer 2 向量語意意圖匹配：透過查詢向量相似度快速復用已解析意圖。
需要 pgvector 擴展已啟用（由 add_pgvector_embedding 遷移處理）。

Revision ID: add_query_embedding_history
Revises: add_ai_search_history
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_query_embedding_history'
down_revision = 'add_ai_search_history'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增 query_embedding 欄位（冪等設計）"""
    # 檢查 pgvector 擴展是否可用
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
    ))
    if result.scalar() is None:
        import logging
        logging.getLogger("alembic").warning(
            "pgvector 擴展未啟用，跳過 query_embedding 欄位建立。"
            "請先執行 add_pgvector_embedding 遷移或手動啟用 pgvector。"
        )
        return

    # 新增 query_embedding 欄位（冪等）
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'ai_search_history' AND column_name = 'query_embedding'
            ) THEN
                ALTER TABLE ai_search_history ADD COLUMN query_embedding vector(384);
                COMMENT ON COLUMN ai_search_history.query_embedding
                    IS '查詢向量嵌入 (nomic-embed-text, 384 維)';
            END IF;
        END $$;
    """)

    # 建立 ivfflat 索引（加速向量搜尋）
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_search_history_query_embedding
        ON ai_search_history USING ivfflat (query_embedding vector_cosine_ops)
        WITH (lists = 50)
    """)


def downgrade() -> None:
    """移除 query_embedding 欄位與索引"""
    op.execute("DROP INDEX IF EXISTS ix_search_history_query_embedding")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'ai_search_history' AND column_name = 'query_embedding'
            ) THEN
                ALTER TABLE ai_search_history DROP COLUMN query_embedding;
            END IF;
        END $$;
    """)
