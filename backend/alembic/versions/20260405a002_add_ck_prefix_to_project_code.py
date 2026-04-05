"""add CK prefix to existing project_code values

Revision ID: 20260405a002
Revises: 20260405a001
Create Date: 2026-04-05

Affected tables:
  - contract_projects.project_code (source of truth)
  - pm_cases.project_code (synced from contract_projects)
  - erp_quotations.project_code (synced from contract_projects)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '20260405a002'
down_revision: Union[str, Sequence[str], None] = '20260405a001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add CK prefix to project_code in contract_projects table (source of truth)
    op.execute("""
        UPDATE contract_projects
        SET project_code = CONCAT('CK', project_code)
        WHERE project_code IS NOT NULL
          AND project_code != ''
          AND project_code NOT LIKE 'CK%'
    """)

    # Also update project_code in pm_cases table (synced reference)
    op.execute("""
        UPDATE pm_cases
        SET project_code = CONCAT('CK', project_code)
        WHERE project_code IS NOT NULL
          AND project_code != ''
          AND project_code NOT LIKE 'CK%'
    """)

    # Also update project_code in erp_quotations table (synced reference)
    op.execute("""
        UPDATE erp_quotations
        SET project_code = CONCAT('CK', project_code)
        WHERE project_code IS NOT NULL
          AND project_code != ''
          AND project_code NOT LIKE 'CK%'
    """)


def downgrade() -> None:
    # Remove CK prefix from contract_projects
    op.execute("""
        UPDATE contract_projects
        SET project_code = SUBSTRING(project_code FROM 3)
        WHERE project_code LIKE 'CK%'
    """)

    # Remove CK prefix from pm_cases
    op.execute("""
        UPDATE pm_cases
        SET project_code = SUBSTRING(project_code FROM 3)
        WHERE project_code LIKE 'CK%'
    """)

    # Remove CK prefix from erp_quotations
    op.execute("""
        UPDATE erp_quotations
        SET project_code = SUBSTRING(project_code FROM 3)
        WHERE project_code LIKE 'CK%'
    """)
