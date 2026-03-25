"""統一跨模組案號橋樑：contract_projects +case_code, pm_cases +project_code, erp_quotations +project_code

case_code = 建案編碼 (邀標/報價階段產生)
project_code = 成案編碼 (確認執行時產生，避免跳號)

Revision ID: 20260324a001
Revises: 20260322a004
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa

revision = '20260324a001'
down_revision = '20260322a004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # contract_projects: 新增 case_code (建案案號，來自 pm_cases)
    op.add_column('contract_projects', sa.Column(
        'case_code', sa.String(50), nullable=True,
        comment='建案案號 (來自 pm_cases.case_code，跨模組橋樑)'
    ))
    op.create_index('ix_contract_projects_case_code', 'contract_projects', ['case_code'], unique=True)

    # pm_cases: 新增 project_code (成案專案編號)
    op.add_column('pm_cases', sa.Column(
        'project_code', sa.String(100), nullable=True,
        comment='成案專案編號 (成案後產生，對應 contract_projects.project_code)'
    ))
    op.create_index('ix_pm_cases_project_code', 'pm_cases', ['project_code'], unique=False)

    # erp_quotations: 新增 project_code (成案專案編號)
    op.add_column('erp_quotations', sa.Column(
        'project_code', sa.String(100), nullable=True,
        comment='成案專案編號 (成案後同步，對應 contract_projects.project_code)'
    ))
    op.create_index('ix_erp_quotations_project_code', 'erp_quotations', ['project_code'], unique=False)

    # 回填：將現有 contract_projects.project_code 值複製到 case_code
    # (舊資料的 project_code 同時扮演 case_code 角色)
    op.execute("""
        UPDATE contract_projects
        SET case_code = project_code
        WHERE project_code IS NOT NULL AND case_code IS NULL
    """)


def downgrade() -> None:
    op.drop_index('ix_erp_quotations_project_code', table_name='erp_quotations')
    op.drop_column('erp_quotations', 'project_code')
    op.drop_index('ix_pm_cases_project_code', table_name='pm_cases')
    op.drop_column('pm_cases', 'project_code')
    op.drop_index('ix_contract_projects_case_code', table_name='contract_projects')
    op.drop_column('contract_projects', 'case_code')
