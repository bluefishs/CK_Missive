import React, { useState, useEffect } from 'react';
import {
  Layout as AntLayout,
  Menu,
  Typography,
  Button,
  Avatar,
  Dropdown,
  Badge,
  Space,
  Spin
} from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DashboardOutlined,
  FileTextOutlined,
  UserOutlined,
  BankOutlined,
  TeamOutlined,
  SettingOutlined,
  BellOutlined,
  LogoutOutlined,
  ProfileOutlined,
  NumberOutlined,
  ApiOutlined,
  ShopOutlined,
  ProjectOutlined,
  GlobalOutlined,
  CalendarOutlined,
  BarChartOutlined,
  DatabaseOutlined,
  EyeOutlined,
  ImportOutlined,
  ExportOutlined,
  ApartmentOutlined,
  LineChartOutlined,
  FormOutlined,
  SecurityScanOutlined,
  MonitorOutlined,
  GoogleOutlined,
  ScheduleOutlined,
  FolderOutlined,
  ToolOutlined,
  LinkOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { ROUTES } from '../router/types';
import authService, { UserInfo } from '../services/authService';
import { usePermissions, NavigationItem as PermissionNavigationItem } from '../hooks/usePermissions';
import { isAuthDisabled, isInternalIP } from '../config/env';
import { navigationService } from '../services/navigationService';
import { secureApiService } from '../services/secureApiService';
import NotificationCenter from './NotificationCenter';

const { Header, Sider, Content } = AntLayout;
const { Title } = Typography;

interface LayoutProps {
  children: React.ReactNode;
}

// 擴展導覽項目介面，包含 API 回傳的額外欄位
interface NavigationItem extends PermissionNavigationItem {
  id?: number;
  parent_id?: number;
  level?: number;
  description?: string;
  target?: string;
}

// 不需要布局的公開頁面路徑
const PUBLIC_ROUTES = ['/entry', '/login', '/register', '/forgot-password'];

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [menuItems, setMenuItems] = useState<any[]>([]);
  const [navigationLoading, setNavigationLoading] = useState(true);
  const [forceReload, setForceReload] = useState(0);
  const [currentUser, setCurrentUser] = useState<UserInfo | null>(null);
  const navigate = useNavigate();
  const location = useLocation();

  // 檢查是否為公開頁面（不需要布局）
  const isPublicRoute = PUBLIC_ROUTES.some(route => location.pathname === route || location.pathname.startsWith(route + '/'));

  // 使用權限 Hook
  const {
    userPermissions,
    loading: permissionsLoading,
    filterNavigationByRole,
    hasPermission,
    isAdmin,
    reloadPermissions
  } = usePermissions();

  // 載入動態導覽列數據和用戶資訊
  useEffect(() => {
    loadNavigationData();
    loadUserInfo();
  }, []);

  // 當權限資訊載入完成後，重新載入導覽列
  useEffect(() => {
    if (userPermissions && !permissionsLoading) {
      loadNavigationData();
    }
  }, [userPermissions, permissionsLoading]);

  // 監聽導覽更新事件（從網站管理頁面觸發）
  useEffect(() => {
    const handleNavigationUpdate = () => {
      console.log('🔄 Navigation update event received, reloading navigation data...');
      loadNavigationData();
    };
    window.addEventListener('navigation-updated', handleNavigationUpdate);
    return () => {
      window.removeEventListener('navigation-updated', handleNavigationUpdate);
    };
  }, []);

  // 監聽登入事件，重新載入使用者資訊和權限
  useEffect(() => {
    const handleUserLogin = async () => {
      console.log('🔐 User login event received, reloading user info and permissions...');
      loadUserInfo();
      // 重新載入權限資訊
      await reloadPermissions();
      // 重新載入導覽列
      loadNavigationData();
    };
    window.addEventListener('user-logged-in', handleUserLogin);
    return () => {
      window.removeEventListener('user-logged-in', handleUserLogin);
    };
  }, [reloadPermissions]);

  // 載入用戶資訊
  const loadUserInfo = () => {
    const userInfo = authService.getUserInfo();
    const authDisabled = isAuthDisabled();

    // 優先使用 localStorage 中的使用者資訊（由登入流程設定）
    if (userInfo) {
      setCurrentUser(userInfo);
      console.log('✅ 使用 localStorage 中的使用者資訊:', userInfo.full_name || userInfo.username);
      return;
    }

    // 僅在認證停用且無 localStorage 資訊時使用預設開發者資訊
    if (authDisabled) {
      setCurrentUser({
        id: 0,
        username: 'developer',
        full_name: '開發者',
        email: 'dev@ck-missive.local',
        role: 'superuser',
        is_admin: true,
        is_active: true,
        permissions: '[]',
        created_at: new Date().toISOString(),
        login_count: 0,
        email_verified: true
      });
      console.log('⚠️ 使用預設開發者資訊 (AUTH_DISABLED=true, 無 localStorage)');
      return;
    }

    // 無使用者資訊
    setCurrentUser(null);
  };

  // 舊版權限檢查 (保留相容性)
  const hasPermissionLegacy = (permission?: string, userRole?: string) => {
    if (!currentUser) {
      return false;
    }

    // 無權限要求的項目都可存取
    if (!permission) return true;

    // 超級管理員有所有權限
    if (currentUser.role === 'superuser') {
      return true;
    }

    // 角色權限檢查
    if (permission.startsWith('role:')) {
      const requiredRole = permission.replace('role:', '');
      if (requiredRole === 'admin') {
        return currentUser.is_admin || currentUser.role === 'admin' || currentUser.role === 'superuser';
      }
      if (requiredRole === 'superuser') {
        return currentUser.role === 'superuser';
      }
      return currentUser.role === requiredRole;
    }
    
    // 系統管理權限（只有管理員以上可存取）
    if (permission.startsWith('admin:')) {
      const adminPermissions = ['admin:users', 'admin:database', 'admin:site_management'];
      if (adminPermissions.includes(permission)) {
        const hasAccess = currentUser.is_admin || currentUser.role === 'admin' || currentUser.role === 'superuser';
        console.log(`Admin permission ${permission} check result:`, hasAccess);
        return hasAccess;
      }
      // admin:settings 只有超級管理員可存取
      if (permission === 'admin:settings') {
        const hasAccess = currentUser.role === 'superuser';
        console.log(`Settings permission ${permission} check result:`, hasAccess);
        return hasAccess;
      }
      console.log(`Unknown admin permission: ${permission}`);
      return false;
    }
    
    // 功能模組權限檢查
    if (permission.includes(':')) {
      const parts = permission.split(':');
      const module = parts[0] ?? '';
      const action = parts[1] ?? '';

      // 基本功能模組（一般使用者可存取讀取權限）
      const basicModules = ['documents', 'projects', 'agencies', 'vendors', 'calendar', 'reports'];

      if (basicModules.includes(module)) {
        // 管理員有完整權限
        if (currentUser.is_admin || currentUser.role === 'admin') return true;

        // 一般使用者只能讀取
        const readActions = ['read', 'view'];
        return readActions.includes(action);
      }
    }
    
    // 其他權限預設拒絕
    return false;
  };

  // 舊版權限過濾 (保留相容性)
  const filterMenuItemsByPermissionLegacy = (items: any[]): any[] => {
    return items.filter(item => {
      // 檢查項目權限 - 使用新的權限檢查Hook
      if (item.permission_required && !hasPermission(item.permission_required)) {
        return false;
      }

      // 特殊處理某些選單項目
      if (item.key === 'admin' || item.key === 'admin-menu') {
        return isAdmin();
      }

      // 遞歸處理子項目
      if (item.children) {
        item.children = filterMenuItemsByPermissionLegacy(item.children);
        return item.children.length > 0;
      }

      return true;
    });
  };

  const loadNavigationData = async () => {
    try {
      setNavigationLoading(true);

      // 檢查是否為開發模式 - 根據環境變數或內網 IP 決定
      const authDisabled = isAuthDisabled();
      console.log('🔧 Environment variables:', {
        VITE_AUTH_DISABLED: import.meta.env.VITE_AUTH_DISABLED,
        VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
        isInternalIP: isInternalIP(),
        authDisabled
      });

      // 開發模式也使用動態導覽列，確保與網站管理頁面一致
      // if (authDisabled) {
      //   console.log('🛠️ Development mode: Using static navigation');
      //   const staticItems = getStaticMenuItems();
      //   setMenuItems(staticItems);
      //   return;
      // }

      // 正常模式：使用 secureApiService 載入動態導覽列（與 SiteManagementPage 一致）
      navigationService.clearNavigationCache();
      localStorage.removeItem('cache_navigation_items');
      sessionStorage.removeItem('cache_navigation_items');
      console.log('🗑️ All navigation caches cleared');

      // 使用 secureApiService 確保與網站管理頁面資料一致
      const result = await secureApiService.getNavigationItems() as { items?: NavigationItem[] };
      const navigationItems = result.items || [];
      console.log('📥 Raw navigation items received:', navigationItems.length, 'items');

      // 根據使用者權限和角色過濾導覽項目
      let filteredItems: NavigationItem[];

      if (authDisabled) {
        // 開發模式：不進行權限過濾，顯示所有導覽項目
        console.log('🛠️ Development mode: Showing all navigation items without permission filtering');
        filteredItems = navigationItems;
      } else {
        // 正式模式：根據權限過濾
        filteredItems = userPermissions
          ? filterNavigationByRole(navigationItems)
          : [];

        // 如果過濾後沒有項目，顯示基本選單（已登入用戶至少能看到一些功能）
        if (filteredItems.length === 0 && navigationItems.length > 0) {
          console.log('⚠️ No items after permission filter, showing public items');
          // 顯示不需要權限的項目，或 permission_required 為空的項目
          filteredItems = navigationItems.filter(item => {
            const permRequired = item.permission_required;
            return !permRequired || !Array.isArray(permRequired) || permRequired.length === 0;
          });
        }
      }

      // 轉換為 Ant Design Menu 格式
      const menuItems = convertToMenuItems(filteredItems);
      console.log('🌲 Dynamic menu items loaded:', menuItems.length, 'items');
      setMenuItems(menuItems);

    } catch (error) {
      console.error('❌ Failed to load navigation:', error);
      // 如果完全失敗，使用靜態導覽列作為備用
      const staticItems = getStaticMenuItems();
      const authDisabled = isAuthDisabled();
      const filteredStaticItems = authDisabled
        ? staticItems
        : filterMenuItemsByPermissionLegacy(staticItems);
      console.log('🔄 Using static menu items as fallback:', filteredStaticItems.length, 'items');
      setMenuItems(filteredStaticItems);
    } finally {
      setNavigationLoading(false);
    }
  };

  // 將導覽項目轉換為Ant Design Menu格式
  const convertToMenuItems = (items: NavigationItem[]) => {
    const getIcon = (iconName?: string) => {
      const iconMap: { [key: string]: React.ReactNode } = {
        // 簡化名稱映射 (向後兼容)
        'home': <DashboardOutlined />,
        'dashboard': <DashboardOutlined />,
        'file-text': <FileTextOutlined />,
        'file': <FileTextOutlined />,
        'plus': <FileTextOutlined />,
        'upload': <FileTextOutlined />,
        'download': <FileTextOutlined />,
        'workflow': <SettingOutlined />,
        'number': <NumberOutlined />,
        'project': <ProjectOutlined />,
        'contract': <ProjectOutlined />,
        'bank': <BankOutlined />,
        'shop': <ShopOutlined />,
        'calendar': <CalendarOutlined />,
        'bar-chart': <BarChartOutlined />,
        'api': <ApiOutlined />,
        'setting': <SettingOutlined />,
        'form': <FileTextOutlined />,
        'global': <GlobalOutlined />,
        'database': <BankOutlined />,
        'user': <UserOutlined />,
        'team': <TeamOutlined />,
        'key': <SettingOutlined />,

        // 完整Ant Design圖標名稱映射
        'FileTextOutlined': <FileTextOutlined />,
        'FolderOutlined': <FolderOutlined />,
        'CalendarOutlined': <CalendarOutlined />,
        'BarChartOutlined': <BarChartOutlined />,
        'SettingOutlined': <SettingOutlined />,
        'UserOutlined': <UserOutlined />,
        'DashboardOutlined': <DashboardOutlined />,
        'ProjectOutlined': <ProjectOutlined />,
        'BankOutlined': <BankOutlined />,
        'ShopOutlined': <ShopOutlined />,
        'TeamOutlined': <TeamOutlined />,
        'GlobalOutlined': <GlobalOutlined />,
        'DatabaseOutlined': <DatabaseOutlined />,
        'ApiOutlined': <ApiOutlined />,
        'EyeOutlined': <EyeOutlined />,
        'ImportOutlined': <ImportOutlined />,
        'ExportOutlined': <ExportOutlined />,
        'ApartmentOutlined': <ApartmentOutlined />,
        'LineChartOutlined': <LineChartOutlined />,
        'FormOutlined': <FormOutlined />,
        'SecurityScanOutlined': <SecurityScanOutlined />,
        'MonitorOutlined': <MonitorOutlined />,
        'GoogleOutlined': <GoogleOutlined />,
        'ScheduleOutlined': <ScheduleOutlined />
      };
      return iconMap[iconName || ''] || <FileTextOutlined />;
    };

    const convertItem = (item: NavigationItem, parentKey = ''): any => {
      // 為了避免重複 key，為子項目添加父級前綴
      const uniqueKey = item.children && item.children.length > 0
        ? `parent-${item.key || item.path || `nav-${Date.now()}`}`
        : item.path || item.key || `leaf-${Date.now()}`;

      const menuItem: any = {
        key: uniqueKey,
        icon: getIcon(item.icon),
        label: item.title,
        path: item.path, // 儲存路徑供 Menu onClick 使用
      };

      // 如果有子項目，遞歸轉換
      if (item.children && item.children.length > 0) {
        menuItem.children = item.children.map((child, index) =>
          convertItem(child, `${uniqueKey}-child-${index}`)
        );
      }
      // 不再需要個別的 onClick，使用 Menu 統一處理

      return menuItem;
    };

    return items.map((item) => convertItem(item));
  };

  // 靜態導覽列按照新需求結構重新設計
  const getStaticMenuItems = () => [
    {
      key: ROUTES.DASHBOARD,
      icon: <DashboardOutlined />,
      label: '儀表板',
      path: ROUTES.DASHBOARD,
    },
    // 1. 公文管理 (5個子項目)
    {
      key: 'documents-menu',
      icon: <FileTextOutlined />,
      label: '公文管理',
      children: [
        {
          key: ROUTES.DOCUMENTS,
          icon: <EyeOutlined />,
          label: '文件瀏覽',
          path: ROUTES.DOCUMENTS,
        },
        {
          key: ROUTES.DOCUMENT_NUMBERS,
          icon: <NumberOutlined />,
          label: '文號管理',
          path: ROUTES.DOCUMENT_NUMBERS,
        },
      ],
    },
    // 2. 案件資料 (3個子項目)
    {
      key: 'case-data-menu',
      icon: <ProjectOutlined />,
      label: '案件資料',
      children: [
        {
          key: ROUTES.CONTRACT_CASES,
          icon: <ProjectOutlined />,
          label: '專案管理',
          path: ROUTES.CONTRACT_CASES,
        },
        {
          key: ROUTES.AGENCIES,
          icon: <BankOutlined />,
          label: '機關管理',
          path: ROUTES.AGENCIES,
        },
        {
          key: ROUTES.VENDORS,
          icon: <ShopOutlined />,
          label: '廠商管理',
          path: ROUTES.VENDORS,
        },
        {
          key: ROUTES.STAFF,
          icon: <TeamOutlined />,
          label: '承辦同仁',
          path: ROUTES.STAFF,
        },
      ],
    },
    // 3. 行事曆 (直接連結)
    {
      key: ROUTES.CALENDAR,
      icon: <CalendarOutlined />,
      label: '行事曆',
      path: ROUTES.CALENDAR,
    },
    // 4. 報表分析 (3個子項目)
    {
      key: 'reports-menu',
      icon: <BarChartOutlined />,
      label: '報表分析',
      children: [
        {
          key: ROUTES.REPORTS,
          icon: <LineChartOutlined />,
          label: '統計報表',
          path: ROUTES.REPORTS,
        },
        {
          key: ROUTES.API_DOCS,
          icon: <ApiOutlined />,
          label: 'API文件',
          path: ROUTES.API_DOCS,
        },
        {
          key: ROUTES.UNIFIED_FORM_DEMO,
          icon: <FormOutlined />,
          label: '統一表單示例',
          path: ROUTES.UNIFIED_FORM_DEMO,
        },
        {
          key: ROUTES.API_MAPPING,
          icon: <LinkOutlined />,
          label: 'API對應表',
          path: ROUTES.API_MAPPING,
        },
      ],
    },
    // 5. 系統管理 (7個子項目)
    {
      key: 'admin-menu',
      icon: <SettingOutlined />,
      label: '系統管理',
      children: [
        {
          key: ROUTES.USER_MANAGEMENT,
          icon: <UserOutlined />,
          label: '使用者管理',
          path: ROUTES.USER_MANAGEMENT,
        },
        {
          key: ROUTES.PERMISSION_MANAGEMENT,
          icon: <SecurityScanOutlined />,
          label: '權限管理',
          path: ROUTES.PERMISSION_MANAGEMENT,
        },
        {
          key: ROUTES.DATABASE,
          icon: <DatabaseOutlined />,
          label: '資料庫管理',
          path: ROUTES.DATABASE,
        },
        {
          key: ROUTES.SITE_MANAGEMENT,
          icon: <GlobalOutlined />,
          label: '網站管理',
          path: ROUTES.SITE_MANAGEMENT,
        },
        {
          key: ROUTES.ADMIN_DASHBOARD,
          icon: <DashboardOutlined />,
          label: '管理員面板',
          path: ROUTES.ADMIN_DASHBOARD,
        },
        {
          key: ROUTES.GOOGLE_AUTH_DIAGNOSTIC,
          icon: <GoogleOutlined />,
          label: 'Google認證診斷',
          path: ROUTES.GOOGLE_AUTH_DIAGNOSTIC,
        },
      ],
    },
    // 6. 個人設定 (1個項目)
    {
      key: 'personal-menu',
      icon: <UserOutlined />,
      label: '個人設定',
      children: [
        {
          key: ROUTES.PROFILE,
          icon: <ProfileOutlined />,
          label: '個人設定',
          path: ROUTES.PROFILE,
        },
      ],
    },
  ];

  const userMenuItems = [
    {
      key: 'user-info',
      icon: <UserOutlined />,
      label: `角色：${currentUser?.role === 'superuser' ? '超級管理員' : 
                    currentUser?.role === 'admin' ? '管理員' : '一般使用者'}`,
      disabled: true,
      style: { color: '#666', fontSize: '12px' }
    },
    { type: "divider" as const },
    {
      key: 'profile',
      icon: <ProfileOutlined />,
      label: '個人設定',
      onClick: () => navigate('/profile'),
    },
    { type: "divider" as const },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '登出',
      onClick: async () => {
        try {
          await authService.logout();
          setCurrentUser(null);
          navigate('/login');
        } catch (error) {
          console.error('Logout failed:', error);
        }
      },
    },
  ];

  const getCurrentKey = () => {
    const path = location.pathname;
    if (path === '/' || path === '/dashboard') return '/dashboard';
    return path;
  };

  const getDefaultOpenKeys = () => {
    const path = location.pathname;

    // 根據當前路徑確定應該打開的選單項目
    if (path.startsWith('/documents')) return ['/documents', 'documents'];
    if (path.startsWith('/cases')) return ['/cases', 'cases'];
    if (path.startsWith('/projects')) return ['/cases', 'cases'];
    if (path.startsWith('/agencies')) return ['/cases', 'cases'];
    if (path.startsWith('/vendors')) return ['/cases', 'cases'];
    if (path.startsWith('/calendar')) return ['/calendar', 'calendar'];
    if (path.startsWith('/reports')) return ['/reports', 'reports'];
    if (path.startsWith('/api-docs')) return ['/reports', 'reports'];
    if (path.startsWith('/demo/unified-form')) return ['/reports', 'reports'];
    if (path.startsWith('/admin')) return ['/admin/system', 'system'];
    if (path.startsWith('/settings')) return ['/settings', 'settings'];

    return [];
  };

  // 公開頁面直接渲染內容，不顯示布局
  if (isPublicRoute) {
    return <>{children}</>;
  }

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        theme="dark"
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        <div style={{
          padding: '16px',
          textAlign: 'center',
          borderBottom: '1px solid #303030'
        }}>
          <Title 
            level={4} 
            style={{ 
              color: 'white', 
              margin: 0,
              fontSize: collapsed ? 12 : 16,
            }}
          >
            {collapsed ? 'CK' : '乾坤測繪'}
          </Title>
        </div>
        
        {(navigationLoading || permissionsLoading) ? (
          <div style={{ padding: '20px', textAlign: 'center' }}>
            <Spin size="large" />
          </div>
        ) : (
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[getCurrentKey()]}
            defaultOpenKeys={getDefaultOpenKeys()}
            items={menuItems}
            style={{ borderRight: 0 }}
            onClick={({ key }) => {
              console.log(`🔗 Menu clicked: ${key}`);
              // 查找對應的導覽項目並導航
              const findItemByKey = (items: any[], targetKey: string): any => {
                for (const item of items) {
                  if (item.key === targetKey) return item;
                  if (item.children) {
                    const found = findItemByKey(item.children, targetKey);
                    if (found) return found;
                  }
                }
                return null;
              };

              const clickedItem = findItemByKey(menuItems, key);
              if (clickedItem && clickedItem.path) {
                console.log(`🚀 Navigating to: ${clickedItem.path}`);
                navigate(clickedItem.path);
              } else {
                console.log(`❌ No path found for key: ${key}`);
              }
            }}
          />
        )}
      </Sider>

      <AntLayout style={{ marginLeft: collapsed ? 80 : 200, transition: 'margin-left 0.2s' }}>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'sticky',
          top: 0,
          zIndex: 999,
        }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{
                fontSize: '16px',
                width: 40,
                height: 40,
              }}
            />
            
            <Title 
              level={3} 
              style={{ 
                margin: '0 0 0 16px', 
                color: '#1976d2',
                fontSize: 18,
              }}
            >
              公文管理系統
            </Title>
          </div>

          <Space size="large">
            <NotificationCenter />
            
            <Dropdown 
              menu={{ items: userMenuItems }}
              placement="bottomRight"
            >
              <Space style={{ cursor: 'pointer' }}>
                <Avatar 
                  src={currentUser?.avatar_url}
                  icon={<UserOutlined />} 
                  style={{ backgroundColor: '#1976d2' }}
                />
                <span style={{ color: '#666' }}>
                  {currentUser?.full_name || currentUser?.username || '訪客'}
                </span>
              </Space>
            </Dropdown>
          </Space>
        </Header>

        <Content style={{
          padding: '24px',
          background: '#f5f5f5',
          minHeight: 'calc(100vh - 64px)',
        }}>
          {children}
        </Content>
      </AntLayout>
    </AntLayout>
  );
};

export default Layout;