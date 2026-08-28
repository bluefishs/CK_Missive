# -*- coding: utf-8 -*-
"""finance_ledgers (source_type, source_id) 部分唯一索引

2026-08-29 財務域複查 P0-1：帳本曾雙重入帳（id 88/89 相差 0.18 秒、
id 90/91 相差 0.05 秒）——冪等只靠應用層 `find_by_source` 的
check-then-insert，非原子，併發重送就穿過去，AR 一度虛增 1,681 萬。
資料已修正（對帳歸零 22,435,123 兩側相等）；本索引讓同一來源的
第二筆在資料庫層直接被擋，不再依賴應用層時序。

`manual` 排除在外：手工分錄本來就允許同來源多筆。

Revision ID: 20260829a001
Revises: 20260819a002
"""
from alembic import op

revision = "20260829a001"
down_revision = "20260819a002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_ledger_source_nonmanual "
        "ON finance_ledgers (source_type, source_id) "
        "WHERE source_type <> 'manual' AND source_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_ledger_source_nonmanual")
