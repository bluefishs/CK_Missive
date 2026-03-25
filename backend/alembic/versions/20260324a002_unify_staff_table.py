"""統一人員指派表：project_user_assignments 支援 case_code + nullable project_id/user_id + staff_name

Revision ID: 20260324a002
Revises: 20260324a001
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa

revision = '20260324a002'
down_revision = '20260324a001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 新增 case_code 欄位
    op.add_column('project_user_assignments', sa.Column(
        'case_code', sa.String(50), nullable=True,
        comment='建案案號 (跨模組橋樑，未成案時透過此欄關聯)'
    ))
    op.create_index('ix_project_user_assignments_case_code', 'project_user_assignments', ['case_code'])

    # 2. 新增 staff_name 欄位 (支援外部人員或 user_id 為空時)
    op.add_column('project_user_assignments', sa.Column(
        'staff_name', sa.String(100), nullable=True,
        comment='人員姓名 (user_id 為空時使用)'
    ))

    # 3. project_id 改為 nullable (未成案時無 project)
    op.alter_column('project_user_assignments', 'project_id',
                     existing_type=sa.Integer(), nullable=True)

    # 4. user_id 改為 nullable (支援外部人員)
    op.alter_column('project_user_assignments', 'user_id',
                     existing_type=sa.Integer(), nullable=True)

    # 5. 遷移 pm_case_staff 資料到 project_user_assignments
    op.execute("""
        INSERT INTO project_user_assignments
            (case_code, user_id, staff_name, role, is_primary, start_date, end_date, status, notes, created_at)
        SELECT
            pc.case_code,
            ps.user_id,
            ps.staff_name,
            CASE ps.role
                WHEN 'project_manager' THEN '專案PM'
                WHEN 'engineer' THEN '協辦'
                WHEN 'surveyor' THEN '支援'
                WHEN 'assistant' THEN '支援'
                ELSE 'member'
            END,
            ps.is_primary,
            ps.start_date,
            ps.end_date,
            'active',
            ps.notes,
            ps.created_at
        FROM pm_case_staff ps
        JOIN pm_cases pc ON ps.pm_case_id = pc.id
        WHERE NOT EXISTS (
            SELECT 1 FROM project_user_assignments pua
            WHERE pua.case_code = pc.case_code
              AND pua.user_id = ps.user_id
              AND pua.role = CASE ps.role
                WHEN 'project_manager' THEN '專案PM'
                WHEN 'engineer' THEN '協辦'
                WHEN 'surveyor' THEN '支援'
                WHEN 'assistant' THEN '支援'
                ELSE 'member'
              END
        )
    """)

    # 6. 回填 case_code: 既有 project_user_assignments 的 project_id → contract_projects.case_code
    op.execute("""
        UPDATE project_user_assignments pua
        SET case_code = cp.case_code
        FROM contract_projects cp
        WHERE pua.project_id = cp.id
          AND pua.case_code IS NULL
          AND cp.case_code IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_index('ix_project_user_assignments_case_code', table_name='project_user_assignments')
    op.drop_column('project_user_assignments', 'staff_name')
    op.drop_column('project_user_assignments', 'case_code')
    op.alter_column('project_user_assignments', 'project_id',
                     existing_type=sa.Integer(), nullable=False)
    op.alter_column('project_user_assignments', 'user_id',
                     existing_type=sa.Integer(), nullable=False)
