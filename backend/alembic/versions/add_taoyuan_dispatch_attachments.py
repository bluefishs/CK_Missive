"""add taoyuan dispatch attachments table

新增桃園派工單附件管理資料表

Revision ID: add_dispatch_attachments
Revises: 133fbad5cf1e
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_dispatch_attachments'
down_revision: Union[str, Sequence[str], None] = '133fbad5cf1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """建立 taoyuan_dispatch_attachments 資料表"""

    op.execute("""
        CREATE TABLE IF NOT EXISTS taoyuan_dispatch_attachments (
            id SERIAL PRIMARY KEY,
            dispatch_order_id INTEGER NOT NULL REFERENCES taoyuan_dispatch_orders(id) ON DELETE CASCADE,
            file_name VARCHAR(255),
            file_path VARCHAR(500),
            file_size INTEGER,
            mime_type VARCHAR(100),
            storage_type VARCHAR(20) DEFAULT 'local',
            original_name VARCHAR(255),
            checksum VARCHAR(64),
            uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        COMMENT ON TABLE taoyuan_dispatch_attachments IS '派工單附件';
        COMMENT ON COLUMN taoyuan_dispatch_attachments.dispatch_order_id IS '關聯派工單ID';
        COMMENT ON COLUMN taoyuan_dispatch_attachments.file_name IS '儲存檔案名稱';
        COMMENT ON COLUMN taoyuan_dispatch_attachments.file_path IS '檔案路徑';
        COMMENT ON COLUMN taoyuan_dispatch_attachments.file_size IS '檔案大小(bytes)';
        COMMENT ON COLUMN taoyuan_dispatch_attachments.mime_type IS 'MIME類型';
        COMMENT ON COLUMN taoyuan_dispatch_attachments.storage_type IS '儲存類型: local/network/s3';
        COMMENT ON COLUMN taoyuan_dispatch_attachments.original_name IS '原始檔案名稱';
        COMMENT ON COLUMN taoyuan_dispatch_attachments.checksum IS 'SHA256 校驗碼';
        COMMENT ON COLUMN taoyuan_dispatch_attachments.uploaded_by IS '上傳者ID';
    """)

    # 建立索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_taoyuan_dispatch_attachments_dispatch_order_id
        ON taoyuan_dispatch_attachments(dispatch_order_id);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_taoyuan_dispatch_attachments_checksum
        ON taoyuan_dispatch_attachments(checksum);
    """)


def downgrade() -> None:
    """移除 taoyuan_dispatch_attachments 資料表"""
    op.execute("DROP TABLE IF EXISTS taoyuan_dispatch_attachments CASCADE;")
