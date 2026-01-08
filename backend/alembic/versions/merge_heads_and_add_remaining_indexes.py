"""
合併多個 heads 並新增剩餘效能索引

此遷移完成以下任務:
1. 合併現有多個 Alembic heads
2. 新增 SQL 腳本中尚未整合的索引

Revision ID: merge_and_remaining_indexes
Revises: create_audit_logs, add_google_sync_cols, add_assignee_column, optimize_doc_filter_idx
Create Date: 2026-01-08
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'merge_and_remaining_indexes'
down_revision = ('create_audit_logs', 'add_google_sync_cols', 'add_assignee_column', 'optimize_doc_filter_idx')
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    新增剩餘效能索引

    來源: database_indexes_optimization.sql
    涵蓋表: users, document_calendar_events, event_reminders,
           system_notifications, site_navigation_items
    """

    # =========================================================================
    # 1. users 表索引
    # =========================================================================

    # 電子郵件唯一索引 (登入查詢)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique
        ON users(email)
    """)

    # 使用者名稱唯一索引
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique
        ON users(username)
    """)

    # 活躍用戶索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_active
        ON users(is_active)
        WHERE is_active = true
    """)

    # Google ID 索引 (OAuth 登入)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_google_id
        ON users(google_id)
        WHERE google_id IS NOT NULL
    """)

    # 最後登入時間索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_last_login
        ON users(last_login)
        WHERE last_login IS NOT NULL
    """)

    # =========================================================================
    # 2. document_calendar_events 表索引
    # =========================================================================

    # 事件日期範圍索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_calendar_events_date_range
        ON document_calendar_events(start_date, end_date)
    """)

    # 關聯公文索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_calendar_events_document
        ON document_calendar_events(document_id)
    """)

    # 指派使用者索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_calendar_events_assigned_user
        ON document_calendar_events(assigned_user_id)
        WHERE assigned_user_id IS NOT NULL
    """)

    # 事件類型索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_calendar_events_type
        ON document_calendar_events(event_type)
        WHERE event_type IS NOT NULL
    """)

    # =========================================================================
    # 3. event_reminders 表索引
    # =========================================================================

    # 提醒時間索引 (用於排程查詢)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_reminders_time
        ON event_reminders(reminder_time)
    """)

    # 待發送提醒索引 (複合索引優化排程查詢)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_reminders_pending
        ON event_reminders(is_sent, reminder_time)
        WHERE is_sent = false
    """)

    # 接收用戶索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_reminders_recipient
        ON event_reminders(recipient_user_id)
        WHERE recipient_user_id IS NOT NULL
    """)

    # =========================================================================
    # 4. system_notifications 表索引
    # =========================================================================

    # 用戶通知索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_notifications_user
        ON system_notifications(user_id)
        WHERE user_id IS NOT NULL
    """)

    # 未讀通知索引 (複合索引優化通知查詢)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_notifications_unread
        ON system_notifications(user_id, is_read, created_at)
        WHERE is_read = false
    """)

    # 通知創建時間索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_notifications_created_at
        ON system_notifications(created_at)
    """)

    # =========================================================================
    # 5. site_navigation_items 表索引
    # =========================================================================

    # 啟用狀態 + 排序索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_navigation_enabled_order
        ON site_navigation_items(is_enabled, sort_order)
        WHERE is_enabled = true
    """)

    # 父級項目索引
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_navigation_parent
        ON site_navigation_items(parent_id)
        WHERE parent_id IS NOT NULL
    """)


def downgrade() -> None:
    """移除新增的索引"""

    # users 表
    op.execute("DROP INDEX IF EXISTS idx_users_email_unique")
    op.execute("DROP INDEX IF EXISTS idx_users_username_unique")
    op.execute("DROP INDEX IF EXISTS idx_users_active")
    op.execute("DROP INDEX IF EXISTS idx_users_google_id")
    op.execute("DROP INDEX IF EXISTS idx_users_last_login")

    # document_calendar_events 表
    op.execute("DROP INDEX IF EXISTS idx_calendar_events_date_range")
    op.execute("DROP INDEX IF EXISTS idx_calendar_events_document")
    op.execute("DROP INDEX IF EXISTS idx_calendar_events_assigned_user")
    op.execute("DROP INDEX IF EXISTS idx_calendar_events_type")

    # event_reminders 表
    op.execute("DROP INDEX IF EXISTS idx_reminders_time")
    op.execute("DROP INDEX IF EXISTS idx_reminders_pending")
    op.execute("DROP INDEX IF EXISTS idx_reminders_recipient")

    # system_notifications 表
    op.execute("DROP INDEX IF EXISTS idx_notifications_user")
    op.execute("DROP INDEX IF EXISTS idx_notifications_unread")
    op.execute("DROP INDEX IF EXISTS idx_notifications_created_at")

    # site_navigation_items 表
    op.execute("DROP INDEX IF EXISTS idx_navigation_enabled_order")
    op.execute("DROP INDEX IF EXISTS idx_navigation_parent")
