"""新增 AI 同義詞管理表

建立 ai_synonyms 表，支援透過 UI 管理同義詞群組，
取代原有靜態 YAML 檔案的同義詞定義。

Revision ID: add_ai_synonyms
Revises: add_password_reset
Create Date: 2026-02-08
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_ai_synonyms'
down_revision = 'add_password_reset'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """建立 ai_synonyms 表（冪等性設計）"""
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_synonyms (
            id SERIAL PRIMARY KEY,
            category VARCHAR(100) NOT NULL,
            words TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)

    # 建立分類索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ai_synonyms_category
        ON ai_synonyms (category);
    """)

    # 建立啟用狀態索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ai_synonyms_is_active
        ON ai_synonyms (is_active);
    """)


def downgrade() -> None:
    """移除 ai_synonyms 表"""
    op.execute("DROP TABLE IF EXISTS ai_synonyms CASCADE;")
