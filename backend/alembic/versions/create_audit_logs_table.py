"""create audit_logs table

Revision ID: create_audit_logs
Revises:
Create Date: 2026-01-08

此 Migration 建立審計日誌表，用於追蹤所有資料變更
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'create_audit_logs'
down_revision = None  # 請根據實際情況設定前一個 revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('table_name', sa.String(100), nullable=False, comment='被修改的表格'),
        sa.Column('record_id', sa.Integer(), nullable=False, comment='被修改的記錄 ID'),
        sa.Column('action', sa.String(20), nullable=False, comment='操作類型: CREATE/UPDATE/DELETE'),
        sa.Column('changes', sa.Text(), nullable=True, comment='變更內容 JSON'),
        sa.Column('user_id', sa.Integer(), nullable=True, comment='操作者 ID'),
        sa.Column('user_name', sa.String(100), nullable=True, comment='操作者名稱'),
        sa.Column('source', sa.String(50), default='API', comment='來源: API/SYSTEM/IMPORT'),
        sa.Column('ip_address', sa.String(50), nullable=True, comment='操作者 IP'),
        sa.Column('is_critical', sa.Boolean(), default=False, comment='是否為關鍵欄位變更'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='建立時間'),
        sa.PrimaryKeyConstraint('id')
    )

    # 建立索引以加速查詢
    op.create_index('idx_audit_logs_table_record', 'audit_logs', ['table_name', 'record_id'])
    op.create_index('idx_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_is_critical', 'audit_logs', ['is_critical'])


def downgrade() -> None:
    op.drop_index('idx_audit_logs_is_critical', table_name='audit_logs')
    op.drop_index('idx_audit_logs_user_id', table_name='audit_logs')
    op.drop_index('idx_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('idx_audit_logs_table_record', table_name='audit_logs')
    op.drop_table('audit_logs')
