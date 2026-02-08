"""新增 MFA 雙因素認證欄位

在 users 表新增 mfa_enabled、mfa_secret、mfa_backup_codes 欄位，
支援 TOTP 雙因素認證 (Google Authenticator / Microsoft Authenticator)。

Revision ID: add_mfa_fields
Revises: merge_heads_for_mfa
Create Date: 2026-02-08
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_mfa_fields'
down_revision = 'merge_heads_for_mfa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column(
        'mfa_enabled',
        sa.Boolean(),
        nullable=False,
        server_default='false',
        comment='是否啟用 TOTP MFA',
    ))
    op.add_column('users', sa.Column(
        'mfa_secret',
        sa.String(64),
        nullable=True,
        comment='TOTP secret (base32 encoded)',
    ))
    op.add_column('users', sa.Column(
        'mfa_backup_codes',
        sa.Text(),
        nullable=True,
        comment='備用碼 (JSON 格式, SHA-256 hashed)',
    ))


def downgrade() -> None:
    op.drop_column('users', 'mfa_backup_codes')
    op.drop_column('users', 'mfa_secret')
    op.drop_column('users', 'mfa_enabled')
