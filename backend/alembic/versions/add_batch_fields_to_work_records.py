"""新增 batch_no / batch_label 欄位至 taoyuan_work_records

支援批次結案分組，如「第1批結案」「第2批結案」

Revision ID: add_batch_fields
Revises: add_work_records_table
Create Date: 2026-02-13
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_batch_fields'
down_revision = 'add_work_records_table'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('taoyuan_work_records',
        sa.Column('batch_no', sa.Integer(), nullable=True,
                  comment='批次序號 (第幾批結案，如 1,2,3...)'))
    op.add_column('taoyuan_work_records',
        sa.Column('batch_label', sa.String(50), nullable=True,
                  comment='批次標籤 (如：第1批結案、補充結案)'))
    op.create_index('ix_work_records_batch_no', 'taoyuan_work_records', ['batch_no'])


def downgrade():
    op.drop_index('ix_work_records_batch_no', table_name='taoyuan_work_records')
    op.drop_column('taoyuan_work_records', 'batch_label')
    op.drop_column('taoyuan_work_records', 'batch_no')
