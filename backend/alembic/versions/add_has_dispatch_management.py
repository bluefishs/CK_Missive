"""add has_dispatch_management to contract_projects

Revision ID: add_dispatch_mgmt
Revises: 20260304a002
Create Date: 2026-03-05
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_dispatch_mgmt'
down_revision = '20260304a002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'contract_projects',
        sa.Column('has_dispatch_management', sa.Boolean(), server_default='false', comment='啟用派工管理功能')
    )
    # 將現有桃園查估派工案件標記為啟用
    op.execute("""
        UPDATE contract_projects
        SET has_dispatch_management = true
        WHERE project_name ILIKE '%桃園%' AND project_name ILIKE '%查估%'
    """)


def downgrade() -> None:
    op.drop_column('contract_projects', 'has_dispatch_management')
