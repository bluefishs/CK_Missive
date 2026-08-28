# -*- coding: utf-8 -*-
"""contract_projects.status 的 DB 預設值對齊 ORM（'active' -> '執行中'）

2026-08-29 專案管理域複查 L3：DDL default 'active' 與 ORM default '執行中'
不一致 —— 目前 0 筆 active，但任何繞過 ORM 的 INSERT 會產生一個前端
顯示不了的狀態值（前端選項只有 執行中/已結案/待執行/未得標）。
L02 Dead Config 型態：沒壞是因為還沒有人走到那條路。

Revision ID: 20260829a002
Revises: 20260829a001
"""
from alembic import op

revision = "20260829a002"
down_revision = "20260829a001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE contract_projects ALTER COLUMN status SET DEFAULT '執行中'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE contract_projects ALTER COLUMN status SET DEFAULT 'active'"
    )
