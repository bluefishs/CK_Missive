"""add_coordinate_fields_to_project

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-21

新增「起點坐標」和「迄點坐標」欄位到轄管工程表 (taoyuan_projects)
用於空間定位運用
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增坐標欄位"""
    op.add_column('taoyuan_projects',
        sa.Column('start_coordinate', sa.String(100), nullable=True, comment='起點坐標(經緯度)'))
    op.add_column('taoyuan_projects',
        sa.Column('end_coordinate', sa.String(100), nullable=True, comment='迄點坐標(經緯度)'))


def downgrade() -> None:
    """移除坐標欄位"""
    op.drop_column('taoyuan_projects', 'end_coordinate')
    op.drop_column('taoyuan_projects', 'start_coordinate')
