import React, { useState, useEffect, useCallback } from 'react';
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
  PlusOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { navigationService } from '../services/navigationService';

const { Header, Sider, Content } = AntLayout;
const { Title } = Typography;

interface LayoutProps {
  children: React.ReactNode;
}

interface NavigationItem {
  id: number;
  title: string;
  key: string;
  path?: string;
  icon?: string;
  parent_id?: number;
  sort_order: number;
  is_visible: boolean;
  is_enabled: boolean;
  level: number;
  description?: string;
  target: string;
  permission_required?: string;
  children?: NavigationItem[];
}

const DynamicLayout: React.FC<LayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [menuItems, setMenuItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  // 載入動態導覽列數據
  const loadNavigationData = useCallback(async (useCache = true) => {
    setLoading(true);
    try {
      // 使用 navigationService 統一管理導覽資料和快取
      const items = await navigationService.getNavigationItems(useCache);
      const dynamicMenuItems = convertToMenuItems(items as unknown as NavigationItem[]);
      setMenuItems(dynamicMenuItems);
    } catch (error) {
      console.error('Failed to load navigation:', error);
      setMenuItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // 初始載入
  useEffect(() => {
    loadNavigationData();
  }, [loadNavigationData]);

  // 監聽導覽更新事件（從網站管理頁面觸發）
  useEffect(() => {
    const handleNavigationUpdate = () => {
      loadNavigationData(false); // 強制重新載入，不使用快取
    };
    window.addEventListener('navigation-updated', handleNavigationUpdate);
    return () => {
      window.removeEventListener('navigation-updated', handleNavigationUpdate);
    };
  }, [loadNavigationData]);

  // 圖示映射
  const getIcon = (iconName?: string) => {
    const iconMap: { [key: string]: React.ReactNode } = {
      'home': <DashboardOutlined />,
      'dashboard': <DashboardOutlined />,
      'file-text': <FileTextOutlined />,
      'file': <FileTextOutlined />,
      'plus': <PlusOutlined />,
      'project': <ProjectOutlined />,
      'calendar': <CalendarOutlined />,
      'bar-chart': <BarChartOutlined />,
      'setting': <SettingOutlined />,
      'global': <GlobalOutlined />,
      'database': <BankOutlined />,
      'user': <UserOutlined />,
      'team': <TeamOutlined />,
      'number': <NumberOutlined />,
      'shop': <ShopOutlined />,
      'api': <ApiOutlined />
    };
    return iconMap[iconName || ''] || <FileTextOutlined />;
  };

  // 將導覽項目轉換為Ant Design Menu格式
  const convertToMenuItems = (items: NavigationItem[]) => {
    const convertItem = (item: NavigationItem): any => {
      const menuItem: any = {
        key: item.path || item.key,
        icon: getIcon(item.icon),
        label: item.title,
      };

      // 如果有路徑，添加點擊事件
      if (item.path) {
        menuItem.onClick = () => navigate(item.path!);
      }

      // 如果有子項目，遞歸轉換
      if (item.children && item.children.length > 0) {
        menuItem.children = item.children.map(convertItem);
        // 父項目如果沒有路徑，就不添加點擊事件
        if (!item.path) {
          delete menuItem.onClick;
        }
      }

      return menuItem;
    };

    return items
      .filter(item => item.is_visible && item.is_enabled)
      .map(convertItem);
  };

  // 獲取當前選中的鍵值
  const getCurrentKey = () => {
    return location.pathname;
  };

  // 獲取默認展開的鍵值
  const getDefaultOpenKeys = () => {
    const pathname = location.pathname;
    const openKeys: string[] = [];
    
    // 檢查當前路徑是否匹配某個子項目的路徑
    menuItems.forEach(item => {
      if (item.children) {
        item.children.forEach((child: any) => {
          if (child.key === pathname) {
            openKeys.push(item.key);
          }
        });
      }
    });
    
    return openKeys;
  };

  const userMenuItems = [
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
      onClick: () => {
        // TODO: 實作登出邏輯
        console.log('Logout clicked');
      },
    },
  ];

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider 
        collapsible 
        collapsed={collapsed} 
        onCollapse={setCollapsed}
        width={200}
        style={{
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 1000,
        }}
      >
        <div style={{ 
          height: 32, 
          margin: 16, 
          background: 'rgba(255, 255, 255, 0.2)',
          borderRadius: 4,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontWeight: 'bold'
        }}>
          {collapsed ? 'CK' : 'CK Missive'}
        </div>
        
        {loading ? (
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <Spin />
          </div>
        ) : (
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[getCurrentKey()]}
            defaultOpenKeys={getDefaultOpenKeys()}
            items={menuItems}
            style={{ borderRight: 0 }}
          />
        )}
      </Sider>

      <AntLayout style={{ marginLeft: collapsed ? 80 : 200, transition: 'margin-left 0.2s' }}>
        <Header style={{ 
          background: '#fff', 
          padding: '0 24px', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{ fontSize: '16px', width: 40, height: 40 }}
            />
            <Title level={4} style={{ margin: '0 0 0 16px' }}>
              公文管理系統
            </Title>
          </div>
          
          <Space size="middle">
            <Badge count={5}>
              <Button type="text" icon={<BellOutlined />} />
            </Badge>
            <Dropdown 
              menu={{ items: userMenuItems }}
              placement="bottomRight"
            >
              <Space style={{ cursor: 'pointer' }}>
                <Avatar icon={<UserOutlined />} />
                <span>管理員</span>
              </Space>
            </Dropdown>
          </Space>
        </Header>
        
        <Content style={{ 
          margin: '16px', 
          minHeight: 280,
          background: '#f5f5f5'
        }}>
          {children}
        </Content>
      </AntLayout>
    </AntLayout>
  );
};

export default DynamicLayout;