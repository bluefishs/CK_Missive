"""建立 pm_case_attachments 報價紀錄附件表

Revision ID: 20260324a003
Revises: 20260324a002
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa

revision = '20260324a003'
down_revision = '20260324a002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'pm_case_attachments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('case_code', sa.String(50), nullable=False, index=True,
                   comment='建案案號'),
        sa.Column('file_name', sa.String(255), nullable=False, comment='檔名'),
        sa.Column('file_path', sa.String(500), nullable=False, comment='儲存路徑'),
        sa.Column('file_size', sa.Integer(), comment='檔案大小 (bytes)'),
        sa.Column('mime_type', sa.String(100), comment='MIME 類型'),
        sa.Column('original_name', sa.String(255), comment='原始檔名'),
        sa.Column('checksum', sa.String(64), index=True, comment='SHA256'),
        sa.Column('uploaded_by', sa.Integer(),
                   sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text(), comment='備註'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('pm_case_attachments')
