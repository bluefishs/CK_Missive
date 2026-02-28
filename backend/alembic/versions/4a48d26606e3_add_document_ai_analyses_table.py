"""add document_ai_analyses table

Revision ID: 4a48d26606e3
Revises: d2cde3d44189
Create Date: 2026-02-28 17:38:45.332224

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4a48d26606e3'
down_revision: Union[str, Sequence[str], None] = 'd2cde3d44189'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增 document_ai_analyses 表 — AI 分析結果持久化"""
    op.create_table('document_ai_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False, comment='公文 ID（一文一記錄）'),
        sa.Column('summary', sa.Text(), nullable=True, comment='AI 生成摘要'),
        sa.Column('summary_confidence', sa.Float(), nullable=True, comment='摘要信心度 0.0-1.0'),
        sa.Column('suggested_doc_type', sa.String(length=50), nullable=True, comment='AI 建議公文類型'),
        sa.Column('doc_type_confidence', sa.Float(), nullable=True, comment='類型信心度'),
        sa.Column('suggested_category', sa.String(length=20), nullable=True, comment='AI 建議收發類別'),
        sa.Column('category_confidence', sa.Float(), nullable=True, comment='類別信心度'),
        sa.Column('classification_reasoning', sa.Text(), nullable=True, comment='分類判斷理由'),
        sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="關鍵字陣列 ['kw1','kw2']"),
        sa.Column('keywords_confidence', sa.Float(), nullable=True, comment='關鍵字信心度'),
        sa.Column('llm_provider', sa.String(length=20), nullable=True, comment='LLM 提供者: groq/ollama'),
        sa.Column('llm_model', sa.String(length=100), nullable=True, comment='使用的模型名稱'),
        sa.Column('processing_ms', sa.Integer(), nullable=True, comment='總處理耗時 (ms)'),
        sa.Column('source_text_hash', sa.String(length=64), nullable=True, comment='輸入文本 SHA256（用於偵測公文修改後過期）'),
        sa.Column('analysis_version', sa.String(length=20), nullable=True, comment='分析版本'),
        sa.Column('status', sa.String(length=20), nullable=True, comment='狀態: pending/processing/completed/partial/failed'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='失敗時的錯誤訊息'),
        sa.Column('is_stale', sa.Boolean(), nullable=True, comment='公文內容變更後是否已過期'),
        sa.Column('analyzed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='分析完成時間'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_doc_ai_analysis_analyzed_at', 'document_ai_analyses', ['analyzed_at'], unique=False)
    op.create_index('ix_doc_ai_analysis_status', 'document_ai_analyses', ['status'], unique=False)
    op.create_index(op.f('ix_document_ai_analyses_document_id'), 'document_ai_analyses', ['document_id'], unique=True)
    op.create_index(op.f('ix_document_ai_analyses_id'), 'document_ai_analyses', ['id'], unique=False)
    op.create_index(op.f('ix_document_ai_analyses_is_stale'), 'document_ai_analyses', ['is_stale'], unique=False)


def downgrade() -> None:
    """移除 document_ai_analyses 表"""
    op.drop_index(op.f('ix_document_ai_analyses_is_stale'), table_name='document_ai_analyses')
    op.drop_index(op.f('ix_document_ai_analyses_id'), table_name='document_ai_analyses')
    op.drop_index(op.f('ix_document_ai_analyses_document_id'), table_name='document_ai_analyses')
    op.drop_index('ix_doc_ai_analysis_status', table_name='document_ai_analyses')
    op.drop_index('ix_doc_ai_analysis_analyzed_at', table_name='document_ai_analyses')
    op.drop_table('document_ai_analyses')
