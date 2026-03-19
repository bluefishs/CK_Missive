"""create PM module tables (pm_cases, pm_milestones, pm_case_staff)

獨立專案管理模組，零耦合於現有公文/派工系統。

Revision ID: 20260316b001
Revises: 20260315a003
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa

revision = "20260316b001"
down_revision = "20260315a003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === pm_cases ===
    op.create_table(
        "pm_cases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("case_code", sa.String(50), nullable=False, comment="案號 (跨模組橋樑)"),
        sa.Column("case_name", sa.String(500), nullable=False, comment="案名"),
        sa.Column("year", sa.Integer(), nullable=True, comment="年度 (民國)"),
        sa.Column("category", sa.String(50), nullable=True, comment="案件類別"),
        sa.Column("client_name", sa.String(200), nullable=True, comment="業主/委託單位"),
        sa.Column("client_contact", sa.String(100), nullable=True, comment="業主聯絡人"),
        sa.Column("client_phone", sa.String(50), nullable=True, comment="業主電話"),
        sa.Column("contract_amount", sa.Numeric(15, 2), nullable=True, comment="合約金額"),
        sa.Column("status", sa.String(30), nullable=False, server_default="planning",
                  comment="狀態: planning/in_progress/completed/suspended/closed"),
        sa.Column("progress", sa.Integer(), server_default="0", comment="進度 (0-100)"),
        sa.Column("start_date", sa.Date(), nullable=True, comment="開工日期"),
        sa.Column("end_date", sa.Date(), nullable=True, comment="完工期限"),
        sa.Column("actual_end_date", sa.Date(), nullable=True, comment="實際完工日期"),
        sa.Column("location", sa.String(300), nullable=True, comment="工程地點"),
        sa.Column("description", sa.Text(), nullable=True, comment="案件說明"),
        sa.Column("notes", sa.Text(), nullable=True, comment="備註"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="建立者"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pm_cases_id", "pm_cases", ["id"])
    op.create_index("ix_pm_cases_case_code", "pm_cases", ["case_code"], unique=True)
    op.create_index("ix_pm_cases_case_name", "pm_cases", ["case_name"])
    op.create_index("ix_pm_cases_year", "pm_cases", ["year"])
    op.create_index("ix_pm_cases_status", "pm_cases", ["status"])

    # === pm_milestones ===
    op.create_table(
        "pm_milestones",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pm_case_id", sa.Integer(), sa.ForeignKey("pm_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("milestone_name", sa.String(200), nullable=False, comment="里程碑名稱"),
        sa.Column("milestone_type", sa.String(50), nullable=True,
                  comment="類型: kickoff/design/review/submission/acceptance/warranty/other"),
        sa.Column("planned_date", sa.Date(), nullable=True, comment="預計日期"),
        sa.Column("actual_date", sa.Date(), nullable=True, comment="實際完成日期"),
        sa.Column("status", sa.String(30), server_default="pending",
                  comment="狀態: pending/in_progress/completed/overdue/skipped"),
        sa.Column("sort_order", sa.Integer(), server_default="0", comment="排序"),
        sa.Column("notes", sa.Text(), nullable=True, comment="備註"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pm_milestones_id", "pm_milestones", ["id"])
    op.create_index("ix_pm_milestones_pm_case_id", "pm_milestones", ["pm_case_id"])
    op.create_index("ix_pm_milestones_milestone_type", "pm_milestones", ["milestone_type"])

    # === pm_case_staff ===
    op.create_table(
        "pm_case_staff",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pm_case_id", sa.Integer(), sa.ForeignKey("pm_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
                  comment="系統使用者 (optional)"),
        sa.Column("staff_name", sa.String(100), nullable=False, comment="人員姓名"),
        sa.Column("role", sa.String(50), nullable=False,
                  comment="角色: project_manager/engineer/surveyor/assistant/other"),
        sa.Column("is_primary", sa.Boolean(), server_default="false", comment="是否主要負責人"),
        sa.Column("start_date", sa.Date(), nullable=True, comment="起始日期"),
        sa.Column("end_date", sa.Date(), nullable=True, comment="結束日期"),
        sa.Column("notes", sa.String(300), nullable=True, comment="備註"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pm_case_staff_id", "pm_case_staff", ["id"])
    op.create_index("ix_pm_case_staff_pm_case_id", "pm_case_staff", ["pm_case_id"])
    op.create_index("ix_pm_case_staff_user_id", "pm_case_staff", ["user_id"])


def downgrade() -> None:
    op.drop_table("pm_case_staff")
    op.drop_table("pm_milestones")
    op.drop_table("pm_cases")
