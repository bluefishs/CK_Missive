"""Implement complete navigation tree structure

Revision ID: nav_tree_structure
Revises: 41ae83315df9
Create Date: 2025-09-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'nav_tree_structure'
down_revision = '41ae83315df9'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create the complete navigation tree structure
    connection = op.get_bind()

    # First, clear existing navigation data to rebuild properly
    connection.execute(sa.text("DELETE FROM site_navigation_items"))

    # Insert the complete tree structure
    navigation_items = [
        # Root level items
        (1, '公文管理', 'documents', '/documents', 'FileTextOutlined', None, 1, True, '文件,公文,管理', '[]'),
        (2, '案件資料', 'cases', None, 'FolderOutlined', None, 2, True, '案件,專案,資料', '["documents:read"]'),
        (3, '行事曆', 'calendar', '/calendar', 'CalendarOutlined', None, 3, True, '行事曆,排程', '["calendar:read"]'),
        (4, '報表分析', 'reports', None, 'BarChartOutlined', None, 4, True, '報表,分析,統計', '["reports:view"]'),
        (5, '系統管理', 'system', None, 'SettingOutlined', None, 5, True, '系統,管理,設定', '["admin:users"]'),
        (6, '個人設定', 'settings', '/settings', 'UserOutlined', None, 6, True, '個人,設定,偏好', '[]'),

        # 公文管理 sub-items
        (7, '文件瀏覽', 'document-browse', '/documents', 'EyeOutlined', 1, 1, True, '瀏覽,查看', '["documents:read"]'),
        (8, '文件匯入', 'document-import', '/documents/import', 'ImportOutlined', 1, 2, True, '匯入,上傳', '["documents:create"]'),
        (9, '文件匯出', 'document-export', '/documents/export', 'ExportOutlined', 1, 3, True, '匯出,下載', '["documents:read"]'),
        (10, '文件工作流', 'document-workflow', '/documents/workflow', 'ApartmentOutlined', 1, 4, True, '工作流,流程', '["documents:edit"]'),

        # 案件資料 sub-items
        (11, '專案管理', 'projects', '/projects', 'ProjectOutlined', 2, 1, True, '專案,計畫', '["projects:read"]'),
        (12, '機關管理', 'agencies', '/agencies', 'BankOutlined', 2, 2, True, '機關,單位', '["agencies:read"]'),
        (13, '廠商管理', 'vendors', '/vendors', 'ShopOutlined', 2, 3, True, '廠商,供應商', '["vendors:read"]'),

        # 報表分析 sub-items
        (14, '統計報表', 'reports-stats', '/reports/statistics', 'LineChartOutlined', 4, 1, True, '統計,圖表', '["reports:view"]'),
        (15, 'API文件', 'api-docs', '/api-docs', 'ApiOutlined', 4, 2, True, 'API,文件', '[]'),

        # 系統管理 sub-items
        (16, '使用者管理', 'user-management', '/admin/users', 'TeamOutlined', 5, 1, True, '使用者,帳號', '["admin:users"]'),
        (17, '權限管理', 'permission-management', '/admin/permissions', 'SecurityScanOutlined', 5, 2, True, '權限,角色', '["admin:users"]'),
        (18, '資料庫管理', 'database-management', '/admin/database', 'DatabaseOutlined', 5, 3, True, '資料庫,維護', '["admin:settings"]'),
        (19, '網站管理', 'site-management', '/admin/site', 'GlobalOutlined', 5, 4, True, '網站,設定', '["admin:site_management"]'),
        (20, '系統監控', 'system-monitoring', '/admin/system', 'MonitorOutlined', 5, 5, True, '監控,狀態', '["admin:settings"]'),
        (21, '管理員面板', 'admin-dashboard', '/admin/dashboard', 'DashboardOutlined', 5, 6, True, '管理,面板', '["admin:users"]'),

        # Additional functional pages
        (22, '純粹行事曆', 'pure-calendar', '/pure-calendar', 'ScheduleOutlined', 3, 1, True, '行事曆,純粹', '["calendar:read"]'),
        (23, '文件行事曆', 'document-calendar', '/documents/calendar', 'CalendarOutlined', 1, 5, True, '文件,行事曆', '["calendar:read", "documents:read"]'),
        (24, 'Google認證診斷', 'google-auth-diagnostic', '/admin/google-auth', 'GoogleOutlined', 5, 7, True, 'Google,認證', '["admin:settings"]'),
        (25, '統一表單示例', 'unified-form-demo', '/demo/unified-form', 'FormOutlined', 4, 3, True, '表單,示例', '[]'),
    ]

    # Insert all navigation items
    for item in navigation_items:
        connection.execute(sa.text("""
            INSERT INTO site_navigation_items
            (id, title, key, path, icon, parent_id, sort_order, is_visible, is_enabled, description, permission_required)
            VALUES (:id, :title, :key, :path, :icon, :parent_id, :sort_order, :is_visible, :is_enabled, :description, :permission_required)
        """), {
            'id': item[0],
            'title': item[1],
            'key': item[2],
            'path': item[3],
            'icon': item[4],
            'parent_id': item[5],
            'sort_order': item[6],
            'is_visible': item[7],
            'is_enabled': True,
            'description': item[8],
            'permission_required': item[9]
        })

    # Reset the sequence to continue from the highest ID
    connection.execute(sa.text("SELECT setval('site_navigation_items_id_seq', (SELECT MAX(id) FROM site_navigation_items))"))

def downgrade() -> None:
    # Remove all navigation items
    op.execute("DELETE FROM site_navigation_items")