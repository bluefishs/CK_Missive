"""add tender subscription and bookmark tables

Revision ID: 20260401a002
Revises: 20260401a001
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa

revision = '20260401a002'
down_revision = '20260401a001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'tender_subscriptions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('keyword', sa.String(100), nullable=False),
        sa.Column('category', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('notify_line', sa.Boolean(), default=True),
        sa.Column('notify_system', sa.Boolean(), default=True),
        sa.Column('last_checked_at', sa.DateTime(), nullable=True),
        sa.Column('last_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        'tender_bookmarks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('unit_id', sa.String(50), nullable=False),
        sa.Column('job_number', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('unit_name', sa.String(200), nullable=True),
        sa.Column('budget', sa.String(100), nullable=True),
        sa.Column('deadline', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), default='tracking'),
        sa.Column('case_code', sa.String(50), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_index('ix_tender_bookmark_unit_job', 'tender_bookmarks',
                     ['unit_id', 'job_number'], unique=True)


def downgrade() -> None:
    op.drop_table('tender_bookmarks')
    op.drop_table('tender_subscriptions')
