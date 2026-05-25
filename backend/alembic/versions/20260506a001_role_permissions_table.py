"""role_permissions table — 動態角色權限管理（ADR-0034）

Revision ID: 20260506a001
Revises: 20260429a001
Create Date: 2026-05-06

事故觸發：李昭德 admin role 側邊欄只 3 項（前端 hardcoded role 白名單跟 DB
nav_items 命名不一致；前端 admin → 自動 superuser 全權限短路）。

設計：以 DB role_permissions 表為 SSOT，與 site_navigation_items.permission_required
動態對應，PermissionManagementPage 編輯。

關聯：
- ADR-0034 動態 role permissions
- failure-adr-0025-rls-half-wired.md（同類雙軌不同步事故）
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
import json

# revision identifiers
revision = "20260506a001"
down_revision = "20260429a001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "role_permissions",
        sa.Column("role", sa.String(20), primary_key=True),
        sa.Column("permissions", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("can_login", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("name_zh", sa.String(50), nullable=True),
        sa.Column("description_zh", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )

    # GIN index for permissions JSONB（支援 contains 查詢）
    op.create_index(
        "ix_role_permissions_permissions_gin",
        "role_permissions",
        ["permissions"],
        postgresql_using="gin",
    )

    # 種子資料：4 個角色初始配置（與既有 hardcode 對齊）
    base_user_perms = [
        "documents:read", "projects:read", "agencies:read", "vendors:read",
        "calendar:read",
    ]
    admin_perms = base_user_perms + [
        "documents:create", "documents:edit", "documents:delete",
        "projects:create", "projects:edit", "projects:delete",
        "agencies:create", "agencies:edit", "agencies:delete",
        "vendors:create", "vendors:edit", "vendors:delete",
        "calendar:edit",
        "reports:view", "reports:export",
        "system_docs:read", "system_docs:create", "system_docs:edit", "system_docs:delete",
        "admin:users", "admin:settings", "admin:site_management", "admin:database",
    ]
    # superuser: wildcard，hasPermission 短路
    superuser_perms = ["*"]

    seeds = [
        ("unverified", [], False, "未驗證者", "新註冊使用者，需要管理者驗證後才能使用系統"),
        ("user", base_user_perms, True, "一般使用者", "已驗證的一般使用者，具備基本檢視權限"),
        ("staff", base_user_perms + ["documents:create", "documents:edit"], True,
         "業務同仁", "業務人員，可建立/編輯公文與專案資料"),
        ("admin", admin_perms, True, "管理員",
         "系統管理員，具備大部分管理權限。實際範圍可由 superuser 在 /admin/permissions/admin 編輯"),
        ("superuser", superuser_perms, True, "超級管理員",
         "系統超級管理員，具備所有權限（wildcard *，無法被 PermissionManagementPage 編輯）"),
    ]

    op.bulk_insert(
        sa.table(
            "role_permissions",
            sa.column("role", sa.String),
            sa.column("permissions", JSONB),
            sa.column("can_login", sa.Boolean),
            sa.column("name_zh", sa.String),
            sa.column("description_zh", sa.Text),
        ),
        [
            {
                "role": role,
                "permissions": perms,
                "can_login": can_login,
                "name_zh": name,
                "description_zh": desc,
            }
            for role, perms, can_login, name, desc in seeds
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_role_permissions_permissions_gin", table_name="role_permissions")
    op.drop_table("role_permissions")
