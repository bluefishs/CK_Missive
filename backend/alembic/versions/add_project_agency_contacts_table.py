"""add project_agency_contacts table

Revision ID: add_agency_contacts
Revises: 41ae83315df9
Create Date: 2025-01-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_agency_contacts'
down_revision: Union[str, None] = '41ae83315df9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增專案機關承辦資料表"""
    op.create_table(
        'project_agency_contacts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('contract_projects.id', ondelete='CASCADE'), nullable=False, index=True, comment='關聯的專案ID'),
        sa.Column('contact_name', sa.String(100), nullable=False, comment='承辦人姓名'),
        sa.Column('position', sa.String(100), comment='職稱'),
        sa.Column('department', sa.String(200), comment='單位/科室'),
        sa.Column('phone', sa.String(50), comment='電話'),
        sa.Column('mobile', sa.String(50), comment='手機'),
        sa.Column('email', sa.String(100), comment='電子郵件'),
        sa.Column('is_primary', sa.Boolean(), default=False, comment='是否為主要承辦人'),
        sa.Column('notes', sa.Text(), comment='備註'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='建立時間'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), comment='更新時間'),
    )


def downgrade() -> None:
    """移除專案機關承辦資料表"""
    op.drop_table('project_agency_contacts')
