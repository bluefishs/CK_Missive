"""add users.department + position columns (idempotent sync)

Revision ID: 20260521a001
Revises: 20260506a001
Create Date: 2026-05-21

事故觸發：5/21 SSO 跨 repo 整合時，oauth callback 寫入 department/position 欄位
觸發 UndefinedColumn 500（CK_Website + lvrland + pile 三個入口都炸）。為解燃眉
急用 `ALTER TABLE users ADD COLUMN IF NOT EXISTS department/position` 直接跑 DDL，
但沒進 alembic history → 其他環境（fresh deploy / staging / dev 機器）會缺欄再次
爆同型 500。

設計：採 raw SQL `ADD COLUMN IF NOT EXISTS` 確保所有環境冪等執行（含已手動 ALTER
過的 prod）。

關聯：
- lesson_l41_jwt_secret_drift_silent_fail（SSO 跨 repo 三重 dormant 事故）
- session_20260521_l41_sso_cross_repo_governance（解決過程）
- next_session_resume_20260521 P0-1（接手清單第一順位）
"""
from alembic import op

# revision identifiers
revision = "20260521a001"
down_revision = "20260506a001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add department + position columns to users (idempotent for prod hot-patched envs)."""
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(100)"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS position VARCHAR(100)"
    )

    op.execute(
        "COMMENT ON COLUMN users.department IS '部門名稱'"
    )
    op.execute(
        "COMMENT ON COLUMN users.position IS '職稱'"
    )


def downgrade() -> None:
    """Drop department + position columns (data-destructive; intentional for full rollback)."""
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS position")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS department")
